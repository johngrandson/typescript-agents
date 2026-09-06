#!/usr/bin/env python3
"""Bounded, dependency-free hook runtime. Event data is never evaluated as code.

The shell entrypoints preserve event names and transport. Recognition is deliberately
limited to literal commands and source syntax, not a proof about arbitrary programs.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone

EXTENSIONS = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
IGNORED = {"node_modules", "dist", "build", ".next", "coverage", ".git", ".turbo"}
MAX_READ = 1_000_000


def read(path: Path, limit: int = MAX_READ) -> str:
    try:
        with path.open(encoding="utf-8") as handle:
            return handle.read(limit)
    except (OSError, UnicodeError):
        return ""


def json_file(path: Path) -> dict:
    try:
        value = json.loads(read(path))
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def resolve(value: str, base: Path) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def workspace_patterns(root: Path) -> list[str]:
    """Read pnpm's block/inline packages list without loading project code."""
    result = []
    active = False
    for line in read(root / "pnpm-workspace.yaml").splitlines():
        if re.match(r"^packages\s*:", line):
            active = True
            inline = line.split(":", 1)[1].strip()
            if inline.startswith("[") and inline.endswith("]"):
                result.extend(x.strip().strip("\"'") for x in inline[1:-1].split(","))
            continue
        if active and line and not line[0].isspace() and not line.startswith("#"):
            break
        if active:
            match = re.match(r"\s+-\s+(.+?)\s*(?:\s+#.*)?$", line)
            if match:
                result.append(match[1].strip().strip("\"'"))
    return [
        p
        for p in result
        if p and not p.startswith("/") and ".." not in Path(p.lstrip("!")).parts
    ]


def workspace_members(root: Path) -> dict[Path, dict]:
    patterns = workspace_patterns(root)
    excludes = [p[1:].rstrip("/") for p in patterns if p.startswith("!")]
    result = {}
    for pattern in patterns:
        if pattern.startswith("!"):
            continue
        # Never traverse dependency/cache trees. The starter declares shallow globs.
        if "**" in pattern or any(part in IGNORED for part in Path(pattern).parts):
            continue
        for directory in root.glob(pattern):
            canonical = directory.resolve()
            if not inside(canonical, root) or any(
                p in IGNORED for p in canonical.relative_to(root).parts
            ):
                continue
            relative = directory.relative_to(root).as_posix()
            if any(fnmatch.fnmatchcase(relative, p) for p in excludes):
                continue
            manifest = json_file(canonical / "package.json")
            if manifest:
                result[canonical] = manifest
    return result


def dependencies(manifest: dict) -> set[str]:
    return {
        name
        for key in ("dependencies", "devDependencies", "peerDependencies")
        for name in manifest.get(key, {})
    }


@dataclass
class Context:
    event: dict
    start: Path
    cwd: Path
    root: Path | None
    members: dict[Path, dict]

    @classmethod
    def create(cls, event: dict) -> Context:
        process = Path.cwd().resolve()
        start = resolve(
            os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or str(process),
            process,
        )
        cwd = resolve(event.get("cwd") or str(start), start)
        root, members = None, {}
        for candidate in (start, *start.parents):
            if not all(
                (candidate / name).is_file()
                for name in ("pnpm-workspace.yaml", "package.json", "turbo.json")
            ):
                continue
            found = workspace_members(candidate)
            manifests = [json_file(candidate / "package.json"), *found.values()]
            if any("typescript" in dependencies(manifest) for manifest in manifests):
                root, members = candidate, found
            break
        return cls(event, start, cwd, root, members)

    @property
    def base(self) -> Path:
        return self.root or self.start

    @property
    def tool_input(self) -> dict:
        value = self.event.get("tool_input", {})
        return value if isinstance(value, dict) else {}

    @property
    def file(self) -> Path | None:
        value = self.tool_input.get("file_path") or self.tool_input.get("notebook_path")
        return resolve(value, self.cwd) if isinstance(value, str) and value else None

    def package(self, path: Path | None = None) -> Path | None:
        path = path or self.cwd
        return next((p for p in (path, *path.parents) if p in self.members), None)

    def relative(self, path: Path) -> str:
        return path.relative_to(self.base).as_posix()

    def scoped(self, path: Path | None) -> bool:
        return bool(self.root and path and inside(path, self.root))

    def source(self) -> bool:
        path = self.file
        if not self.scoped(path) or path.suffix not in EXTENSIONS:
            return False
        parts = path.relative_to(self.root).parts
        if (
            any(p in IGNORED for p in parts)
            or ".timestamp-" in path.name
            or path.name == "next-env.d.ts"
        ):
            return False
        return not ignored_by_project(path, self)

    def application(self) -> bool:
        if not self.source() or not self.package(self.file):
            return False
        path = self.file
        parts = path.relative_to(self.root).parts
        return not (
            any(
                p
                in {
                    "__tests__",
                    "__fixtures__",
                    "fixtures",
                    "test",
                    "tests",
                    "scripts",
                    "generated",
                    "__generated__",
                }
                for p in parts
            )
            or re.search(r"\.(test|spec|config|generated)\.", path.name)
            or path.name.endswith(".d.ts")
            or self.package(path) == self.root / "packages/config"
        )


def ignored_by_project(path: Path, ctx: Context) -> bool:
    # Common gitignore syntax; formatter also asks Prettier about its own ignores.
    ignored = False
    package = ctx.package(path)
    for parent in dict.fromkeys([ctx.root, package]):
        if parent is None:
            continue
        relative = path.relative_to(parent).as_posix()
        for name in (".gitignore", ".prettierignore"):
            for entry in read(parent / name, 64_000).splitlines():
                entry = entry.strip()
                if not entry or entry.startswith("#"):
                    continue
                negate = entry.startswith("!")
                pattern = entry.lstrip("!").lstrip("/").rstrip("/")
                if (
                    fnmatch.fnmatchcase(relative, pattern)
                    or relative.startswith(pattern + "/")
                    or (
                        "/" not in pattern
                        and any(
                            fnmatch.fnmatchcase(p, pattern)
                            for p in Path(relative).parts
                        )
                    )
                ):
                    ignored = not negate
    return ignored


def emit_context(event: str, message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": message,
                }
            }
        )
    )


def deny(reason: str, context: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                    "additionalContext": context,
                }
            }
        )
    )


def warning(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def run(
    argv: list[str], cwd: Path, timeout: float = 3, env: dict | None = None
) -> subprocess.CompletedProcess:
    # Kill the process group on timeout, including children of local CLI launchers.
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def shell_commands(command: str, keep_prefix: bool = False):
    """Literal command boundaries, with quotes/comments interpreted only as data."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        tokens = list(lexer)
    except ValueError:
        return
    current = []
    for token in tokens:
        if token and all(c in ";&|()\n" for c in token):
            if current:
                yield current if keep_prefix else unwrap(current)
            current = []
        else:
            current.append(token)
    if current:
        yield current if keep_prefix else unwrap(current)


def unwrap(argv: list[str]) -> list[str]:
    args = list(argv)
    while args and re.match(r"^[A-Za-z_][\w]*=", args[0]):
        args.pop(0)
    if args and Path(args[0]).name in {"env", "command", "exec"}:
        wrapper = Path(args.pop(0)).name
        while args:
            if args[0] in {"-u", "--unset", "-C", "--chdir"} and wrapper == "env":
                args = args[2:]
            elif args[0].startswith("-") or re.match(r"^[A-Za-z_][\w]*=", args[0]):
                args.pop(0)
            else:
                break
    return args


def selected_packages(ctx: Context, filters: list[str], cwd: Path) -> list[Path]:
    if not filters:
        return [ctx.package(cwd) or ctx.root]
    result = []
    for directory, manifest in ctx.members.items():
        relative = ctx.relative(directory)
        if any(
            fnmatch.fnmatchcase(manifest.get("name", ""), f.strip("."))
            or fnmatch.fnmatchcase(relative, f.removeprefix("./").rstrip("."))
            for f in filters
        ):
            result.append(directory)
    return result


def parse_runner(argv: list[str], cwd: Path) -> tuple[str, list[str], list[str], Path]:
    args = argv[1:]
    filters = []
    prefix_flags = []
    while args:
        token = args[0]
        if token.split("=", 1)[0] in (
            "--frozen-lockfile",
            "--lockfile-only",
            "--ignore-scripts",
            "--ignore-pnpmfile",
            "--no-frozen-lockfile",
            "--no-lockfile-only",
            "--no-ignore-scripts",
            "--no-ignore-pnpmfile",
            "--no-lockfile",
            "--no-shared-workspace-lockfile",
        ):
            prefix_flags.append(token)
            args = args[1:]
        elif (
            token
            in (
                "--registry",
                "--userconfig",
                "--globalconfig",
                "--pnpmfile",
                "--configfile",
                "--lockfile-dir",
                "--shared-workspace-lockfile",
                "--modules-dir",
                "--store-dir",
                "--virtual-store-dir",
                "--reporter",
                "--loglevel",
                "--network-concurrency",
                "--workspace-concurrency",
                "--child-concurrency",
                "--fetch-retries",
                "--fetch-retry-mintimeout",
                "--fetch-retry-maxtimeout",
            )
            or token.startswith("--config.")
            and "=" not in token
        ):
            prefix_flags.extend(args[:2])
            args = args[2:]
        elif token.startswith(
            (
                "--registry=",
                "--userconfig=",
                "--globalconfig=",
                "--pnpmfile=",
                "--configfile=",
                "--config.",
                "--lockfile-dir=",
                "--shared-workspace-lockfile=",
                "--modules-dir=",
                "--store-dir=",
                "--virtual-store-dir=",
            )
        ):
            prefix_flags.append(token)
            args = args[1:]
        elif token in ("--filter", "-F", "--filter-prod") and len(args) > 1:
            filters.append(args[1])
            args = args[2:]
        elif token.startswith(("--filter=", "--filter-prod=")):
            filters.append(token.split("=", 1)[1])
            args = args[1:]
        elif token in ("-C", "--dir", "--cwd") and len(args) > 1:
            cwd = resolve(args[1], cwd)
            args = args[2:]
        elif token.startswith(("--dir=", "--cwd=")):
            cwd = resolve(token.split("=", 1)[1], cwd)
            args = args[1:]
        elif token in ("-w", "--workspace-root"):
            cwd = next(
                (
                    p
                    for p in (cwd, *cwd.parents)
                    if (p / "pnpm-workspace.yaml").is_file()
                ),
                cwd,
            )
            args = args[1:]
        elif token in ("run", "-r", "--recursive", "--silent"):
            args = args[1:]
        elif token.startswith("-"):
            # Remaining boolean or equals-form pnpm options can precede tasks.
            prefix_flags.append(token)
            args = args[1:]
        else:
            break
    if not args:
        return "", [], filters, cwd
    task, tail = args[0], prefix_flags + args[1:]
    # Turbo accepts filters after the task, as do common pnpm invocations.
    forwarded = []
    index = 0
    while index < len(tail):
        if tail[index] in ("--filter", "-F") and index + 1 < len(tail):
            filters.append(tail[index + 1])
            index += 2
        elif tail[index].startswith("--filter="):
            filters.append(tail[index].split("=", 1)[1])
            index += 1
        else:
            if tail[index] != "--":
                forwarded.append(tail[index])
            index += 1
    return task, forwarded, filters, cwd


def literal_commands(
    ctx: Context,
    command: str,
    cwd: Path | None = None,
    seen=None,
    depth: int = 0,
    inherited_policy: frozenset[str] = frozenset(),
):
    if depth > 8:
        return
    cwd = cwd or ctx.cwd
    seen = seen or set()
    for raw in shell_commands(command, keep_prefix=True):
        args = unwrap(raw)
        policy_override = set(inherited_policy)
        if any(
            re.match(
                r"(?i)^(?:npm_config_|pnpm_|node_options=|node_extra_ca_certs=|node_tls_reject_unauthorized=)",
                arg,
            )
            for arg in raw
        ):
            policy_override.add("environment")
        for arg in args:
            key = arg.split("=", 1)[0]
            if key.startswith(
                (
                    "--registry",
                    "--config.",
                    "--userconfig",
                    "--globalconfig",
                    "--pnpmfile",
                    "--configfile",
                    "--ignore-pnpmfile",
                    "--no-ignore-pnpmfile",
                    "--ignore-scripts",
                    "--no-ignore-scripts",
                    "--lockfile",
                    "--no-lockfile",
                    "--shared-workspace-lockfile",
                    "--no-shared-workspace-lockfile",
                    "--modules-dir",
                    "--store-dir",
                    "--virtual-store-dir",
                )
            ):
                policy_override.add(key)
        policy_override = frozenset(policy_override)
        if not args:
            continue
        executable = Path(args[0]).name
        if executable == "cd" and len(args) == 2 and "$" not in args[1]:
            cwd = resolve(args[1], cwd)
            continue
        yield args, cwd, policy_override
        if not ctx.root or not inside(cwd, ctx.root):
            continue
        if executable not in {"pnpm", "turbo"}:
            continue
        task, forwarded, filters, target_cwd = parse_runner(args, cwd)
        if task == "exec" and forwarded:
            yield from literal_commands(
                ctx, shlex.join(forwarded), target_cwd, seen, depth + 1, policy_override
            )
            continue
        if task == "dlx":
            continue
        targets = selected_packages(ctx, filters, target_cwd)
        if not filters and (
            executable == "turbo" or any(flag in args for flag in ("-r", "--recursive"))
        ):
            targets = list(ctx.members)
        for target in targets:
            if not target or not inside(target, ctx.root):
                continue
            scripts = json_file(target / "package.json").get("scripts", {})
            script = scripts.get(task)
            key = (str(target), task)
            if isinstance(script, str) and key not in seen:
                yield from literal_commands(
                    ctx,
                    script + " " + shlex.join(forwarded),
                    target,
                    seen | {key},
                    depth + 1,
                    policy_override,
                )


def destructive(ctx: Context) -> int:
    if ctx.event.get("tool_name") != "Bash":
        return 0
    command = ctx.tool_input.get("command", "")
    for args, cwd, _policy_override in literal_commands(ctx, command):
        if not args:
            continue
        executable = Path(args[0]).name
        if executable == "git":
            git_args = args[1:]
            while git_args and git_args[0] in ("-C", "-c", "--git-dir", "--work-tree"):
                git_args = git_args[2:]
            if (
                git_args
                and git_args[0] == "push"
                and any(a in ("--force", "-f") for a in git_args[1:])
            ):
                deny(
                    "Force push rewrites remote history.",
                    "Use git push --force-with-lease to protect unseen commits. Do not retry the unguarded force push.",
                )
                return 0
        if not ctx.root or not inside(cwd, ctx.root):
            continue
        reason = ""
        if executable == "dropdb":
            reason = "Explicit database deletion (dropdb)."
        elif (
            executable == "drizzle-kit" and "push" in args[1:] and "--force" in args[1:]
        ):
            reason = "Forced Drizzle push may discard database data."
        elif executable in {"psql", "mysql", "mariadb", "sqlite3"}:
            sql_args = []
            for index, arg in enumerate(args[1:], 1):
                if arg in ("-c", "--command", "-e", "--execute") and index + 1 < len(
                    args
                ):
                    sql_args.append(args[index + 1])
                elif arg.startswith(("--command=", "--execute=")):
                    sql_args.append(arg.split("=", 1)[1])
            if executable == "sqlite3" and len(args) >= 3:
                sql_args.append(args[-1])
            for sql in sql_args:
                sql = re.sub(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'", " ", sql)
                if re.search(
                    r"\b(?:DROP\s+(?:DATABASE|SCHEMA)|TRUNCATE(?:\s+TABLE)?)\b",
                    sql,
                    re.I,
                ):
                    reason = "Explicit destructive SQL was passed to a database client."
        elif executable in {"docker", "docker-compose"}:
            compose = executable == "docker-compose" or args[1:2] == ["compose"]
            files = [
                resolve(args[i + 1], cwd)
                for i, a in enumerate(args[:-1])
                if a in ("-f", "--file")
            ]
            project_compose = (
                all(inside(p, ctx.root) for p in files)
                if files
                else any(
                    (cwd / f).is_file()
                    for f in (
                        "compose.yaml",
                        "compose.yml",
                        "docker-compose.yml",
                        "docker-compose.yaml",
                    )
                )
            )
            if (
                compose
                and project_compose
                and "down" in args
                and any(a in ("--volumes", "-v") for a in args)
            ):
                reason = "Compose volume removal can destroy persisted project data."
        if reason:
            deny(
                reason,
                "Inspect the target database or volume and preserve recovery evidence. Prefer a corrective migration when appropriate. Do not retry destructive operations automatically; follow the user’s existing authorization and target constraints.",
            )
            return 0
    return 0


def freeze(ctx: Context) -> int:
    if ctx.event.get("tool_name") not in ("Edit", "Write", "NotebookEdit"):
        return 0
    sentinel = ctx.base / ".claude/.freeze"
    if not sentinel.is_file() or ctx.file is None:
        return 0
    allowed = [
        line.strip()
        for line in read(sentinel).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    for entry in allowed:
        prefix = resolve(entry, ctx.base)
        if inside(prefix, ctx.base) and inside(ctx.file, prefix):
            return 0
    reason = (
        "All edits are frozen."
        if not allowed
        else "Edit is outside the allowed directories."
    )
    deny(
        reason,
        "The explicit edit freeze is active. Use /ts:freeze off or /ts:freeze <dir> according to the user’s authorized scope. Do not retry the same edit. Freeze covers Edit, Write and NotebookEdit only.",
    )
    return 0


@dataclass
class Token:
    value: str
    kind: str
    start: int
    end: int


def source_tokens(source: str) -> list[Token]:
    """Small lexical scanner: skip comments, string/template text and regex bodies.

    This supports the hook's syntactic warnings only. It is not a type checker or
    data-flow analyzer. Unresolved template interpolation is left to code review.
    """
    tokens = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            end = source.find("\n", index)
            index = len(source) if end < 0 else end
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = len(source) if end < 0 else end + 2
            continue
        start = index
        if char in "\"'`":
            quote = char
            index += 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            tokens.append(Token(source[start + 1 : index - 1], "string", start, index))
            continue
        if char == "/" and (
            not tokens
            or tokens[-1].value
            in ("=", "(", "[", ",", ":", "return", "=>", "!", "&&", "||")
        ):
            index += 1
            bracket = False
            while index < len(source) and source[index] != "\n":
                if source[index] == "\\":
                    index += 2
                    continue
                if source[index] == "[":
                    bracket = True
                if source[index] == "]":
                    bracket = False
                if source[index] == "/" and not bracket:
                    index += 1
                    while index < len(source) and source[index].isalpha():
                        index += 1
                    break
                index += 1
            tokens.append(Token("", "string", start, index))
            continue
        match = re.match(
            r"[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|=>|\?\.|&&|\|\|", source[index:]
        )
        if match:
            index += len(match[0])
        else:
            index += 1
        tokens.append(Token(source[start:index], "code", start, index))
    return tokens


def code_view(source: str) -> str:
    view = ["\n" if c == "\n" else " " for c in source]
    for token in source_tokens(source):
        if token.kind == "code":
            view[token.start : token.end] = source[token.start : token.end]
    return "".join(view)


def introduced(ctx: Context) -> str:
    value = ctx.tool_input.get("new_string", ctx.tool_input.get("content", ""))
    return value[:MAX_READ] if isinstance(value, str) else ""


def verify_code(ctx: Context) -> int:
    if not ctx.application():
        return 0
    source = introduced(ctx)
    if not source:
        return 0
    code = code_view(source)
    tokens = source_tokens(source)
    path = ctx.relative(ctx.file)
    full = read(ctx.file)
    findings = []

    def add(pattern, message):
        match = re.search(pattern, code)
        if match:
            findings.append(
                f"Edit line {source.count(chr(10), 0, match.start()) + 1}: {message}"
            )

    if not path.startswith("packages/env/"):
        env_code = code
        if path == "apps/mobile/src/services/config.ts":
            env_code = re.sub(
                r"\bprocess\s*\.\s*env\s*\.\s*EXPO_PUBLIC_API_URL\b", "", env_code
            )
        if re.search(r"\bprocess\s*\.\s*env\b", env_code):
            findings.append(
                "Centralize runtime configuration in @starter/env; only the literal EXPO_PUBLIC_API_URL bridge belongs in the Expo adapter."
            )
    if path.startswith("apps/web/"):
        full_tokens = source_tokens(full or source)
        client = bool(
            full_tokens
            and full_tokens[0].kind == "string"
            and full_tokens[0].value == "use client"
        )
        if client:
            for i, token in enumerate(tokens):
                if token.value != "import" or token.kind != "code":
                    continue
                declaration = []
                for following in tokens[i + 1 :]:
                    if following.value == ";":
                        break
                    declaration.append(following)
                    if following.kind == "string":
                        break
                if not declaration or declaration[0].value == "type":
                    continue
                specifier = next(
                    (t.value for t in declaration if t.kind == "string"), ""
                )
                # `import { type Foo }` is also erased by TypeScript.
                named = [t.value for t in declaration if t.kind == "code"]
                if named[:1] == ["{"] and named[-2:] == ["}", "from"]:
                    groups = " ".join(named[1:-2]).split(",")
                    if groups and all(g.strip().startswith("type ") for g in groups):
                        continue
                target = (
                    resolve(specifier, ctx.file.parent)
                    if specifier.startswith(".")
                    else None
                )
                if (
                    re.match(
                        r"^(?:@starter/(?:db|env|logger)(?:/|$)|@fastify/|fastify$|drizzle-orm(?:/|$)|node:)",
                        specifier,
                    )
                    or target
                    and (
                        inside(target, ctx.root / "apps/api")
                        or inside(target, ctx.root / "packages/db")
                        or "/lib/server/" in str(target)
                    )
                ):
                    findings.append(
                        "Client boundary: move the server/database implementation import behind the existing server boundary. Shared contracts and type-only imports remain valid."
                    )
        if "/components/" in path or (
            ctx.file.suffix in {".tsx", ".jsx"} and "/app/" in path
        ):
            add(
                r"(?<![\w$.])fetch\s*\(",
                "Route web component mutations through the existing actions and API client. Review any intentional read separately.",
            )
    add(
        r"\bdangerouslySetInnerHTML\s*=",
        "Review the HTML origin and sanitization before using dangerouslySetInnerHTML; this API alone does not prove unsafe input.",
    )
    add(
        r"\bsql\s*\.\s*raw\s*\(",
        "Review sql.raw and its interpolation. Distinguish static SQL from external input; prefer the existing parameterized Drizzle queries.",
    )
    if path.startswith("packages/db/"):
        monetary = r"(?:price|amount|cost|total|balance|fee|charge|payment|salary|wage|budget|revenue|discount)(?:_[a-z]+|[A-Z][A-Za-z]*)?"
        for index, token in enumerate(tokens):
            if token.kind != "code" or token.value not in ("real", "doublePrecision"):
                continue
            previous = tokens[max(0, index - 2) : index]
            argument = tokens[index + 1 : index + 3]
            column = (
                argument[1].value
                if len(argument) == 2
                and argument[0].value == "("
                and argument[1].kind == "string"
                else ""
            )
            prop = (
                previous[0].value
                if len(previous) == 2 and previous[1].value == ":"
                else ""
            )
            if re.fullmatch(monetary, column) or re.fullmatch(monetary, prop):
                findings.append(
                    "Money column: use a decimal or integer representation appropriate to the domain instead of real/doublePrecision."
                )
    # A fragment inside an existing function must not be mistaken for module scope.
    positions = (
        [m.start() for m in re.finditer(re.escape(source), full)] if full else [0]
    )
    if len(positions) == 1:
        depth = 0
        prefix = code_view(full[: positions[0]]) if full else ""
        depth = prefix.count("{") - prefix.count("}")
        for token in tokens:
            if token.kind != "code":
                continue
            if token.value == "{":
                depth += 1
            elif token.value == "}":
                depth -= 1
            elif token.value in ("setTimeout", "setInterval") and depth == 0:
                at = next((i for i, t in enumerate(tokens) if t is token), -1)
                if at >= 0 and at + 1 < len(tokens) and tokens[at + 1].value == "(":
                    findings.append(
                        "Module-level timer: establish an explicit start/stop lifecycle and cleanup for this resource."
                    )
    if findings:
        return warning(
            f"Review introduced code in {path} (line numbers are relative to the edit):\n"
            + "\n".join("- " + finding for finding in dict.fromkeys(findings))
            + "\nUse the shared ESLint configuration for type/lint findings; this hook does not run lint or prove data-flow safety."
        )
    return 0


def debug(ctx: Context) -> int:
    if not ctx.application() or not ctx.file.is_file():
        return 0
    code = code_view(read(ctx.file))
    matches = list(
        re.finditer(
            r"(?<![\w$.])debugger\b|\bconsole\s*\.\s*(?:log|debug|trace)\s*\(", code
        )
    )[:5]
    if matches:
        lines = ", ".join(str(code.count("\n", 0, m.start()) + 1) for m in matches)
        return warning(
            f"Debug review in {ctx.relative(ctx.file)}, lines {lines}. Review debugger and console calls before committing. no-console is off; retain intentional logging. Prefer @starter/logger for server logging where appropriate."
        )
    return 0


def security(ctx: Context) -> int:
    if ctx.source() and re.search(
        r"(^|[_.-])(auth|session|password|token|permission|admin|payment|login|credential|secret)([_.-]|$)",
        ctx.file.name,
        re.I,
    ):
        return warning(
            f"Security review for {ctx.file.name}: validate boundary inputs with the existing TypeBox contracts; keep server secrets outside client bundles; inspect HTML sanitization and parameterized SQL. Verify authorization where an identity exists. The Session domain alone does not imply authentication. Use /ts:review security for broader review."
        )
    return 0


def check_format(ctx: Context) -> int:
    if not ctx.source() or not ctx.file.is_file():
        return 0
    package = ctx.package(ctx.file)
    candidates = [ctx.root / "node_modules/.bin/prettier"]
    if package:
        candidates.append(package / "node_modules/.bin/prettier")
    prettier = next(
        (p for p in candidates if p.is_file() and os.access(p, os.X_OK)), None
    )
    if prettier is None:
        return warning(
            f"Formatting not checked for {ctx.relative(ctx.file)}: local Prettier is unavailable. No installation was attempted."
        )
    ignores = []
    for directory in dict.fromkeys([ctx.root, package]):
        if directory:
            for name in (".gitignore", ".prettierignore"):
                if (directory / name).is_file():
                    ignores.extend(["--ignore-path", str(directory / name)])
    deadline = time.monotonic() + 25
    try:
        info = run(
            [str(prettier), "--file-info", str(ctx.file), *ignores],
            ctx.root,
            max(0.01, deadline - time.monotonic()),
        )
        if info.returncode != 0:
            return warning(
                f"Formatting not checked for {ctx.relative(ctx.file)}: Prettier could not inspect the file."
            )
        file_info = json.loads(info.stdout)
        if file_info.get("ignored"):
            return 0
        if not file_info.get("inferredParser"):
            return warning(
                f"Formatting not checked for {ctx.relative(ctx.file)}: Prettier has no parser for this file."
            )
        result = run(
            [str(prettier), "--check", str(ctx.file), *ignores],
            ctx.root,
            max(0.01, deadline - time.monotonic()),
        )
    except subprocess.TimeoutExpired:
        return warning(
            f"Formatting not checked for {ctx.relative(ctx.file)}: Prettier timed out after at most 25 seconds."
        )
    except (OSError, ValueError, AttributeError):
        return warning(
            f"Formatting not checked for {ctx.relative(ctx.file)}: local Prettier inspection failed."
        )
    if result.returncode == 1:
        return warning(
            f"Formatting differs for {ctx.relative(ctx.file)}. Review and correct it manually with pnpm exec prettier --write {shlex.quote(ctx.relative(ctx.file))}. The hook only used --check."
        )
    if result.returncode:
        return warning(
            f"Formatting not checked for {ctx.relative(ctx.file)}: Prettier reported an internal/configuration error."
        )
    return 0


def plans(ctx: Context) -> list[Path]:
    parent = ctx.base / ".claude/plans"
    if not inside(parent.resolve(), ctx.base):
        return []
    return sorted(
        p
        for p in parent.glob("*/plan.md")
        if p.is_file() and inside(p.resolve(), ctx.base)
    )


def pending(plan: Path) -> int:
    return len(re.findall(r"^- \[ \]", read(plan), re.M))


def setup(ctx: Context) -> int:
    if ctx.root:
        for name in (
            "plans",
            "reviews",
            "solutions",
            "audit",
            "skill-metrics",
            "research",
        ):
            directory = ctx.root / ".claude" / name
            if inside(directory.resolve(), ctx.root):
                directory.mkdir(parents=True, exist_ok=True)
        if os.environ.get("CLAUDE_PLUGIN_DATA"):
            (Path(os.environ["CLAUDE_PLUGIN_DATA"]) / "skill-metrics").mkdir(
                parents=True, exist_ok=True
            )
    return 0


def resume(ctx: Context) -> int:
    found = False
    for plan in plans(ctx):
        count = pending(plan)
        if count:
            checked = len(re.findall(r"^- \[[xX]\]", read(plan), re.M))
            print(
                f"Plan '{plan.parent.name}' has {count} remaining tasks ({checked} done). Resume with /ts:work {ctx.relative(plan)}. Confirm this is the intended plan before taking over its tasks."
            )
            found = True
    if ctx.root and not found:
        print(
            "TypeScript starter plugin loaded. Describe the task to select a workflow."
        )
    return 0


def scratchpad(ctx: Context) -> int:
    candidates = [
        p.parent / "scratchpad.md"
        for p in plans(ctx)
        if (p.parent / "scratchpad.md").is_file()
        and inside((p.parent / "scratchpad.md").resolve(), ctx.base)
    ]
    if candidates:
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        count = len(re.findall(r"^- ", read(latest), re.M))
        print(
            f"Scratchpad: {len(candidates)} note(s); latest {ctx.relative(latest)} ({count} scratchpad entries). Read the notes before retrying earlier approaches."
        )
    for plan in plans(ctx):
        target = plan.parent / "scratchpad.md"
        if target.exists() or not inside(target.resolve(), ctx.base):
            continue
        try:
            branch = (
                run(["git", "branch", "--show-current"], ctx.base).stdout.strip()
                or "unknown"
            )
        except (OSError, subprocess.TimeoutExpired):
            branch = "unknown"
        with target.open("x", encoding="utf-8") as handle:
            handle.write(
                f"# Scratchpad: {plan.parent.name}\n\n## Dead Ends (DO NOT RETRY)\n\n(none yet)\n\n## Decisions\n\n(none yet)\n\n## Open Questions\n\n(none yet)\n\n## Handoff\n\n- Branch: {branch}\n- Plan: {ctx.relative(plan)}\n- Next: (to be filled on session end)\n"
            )
    return 0


def branch_freshness(ctx: Context) -> int:
    if not ctx.root:
        return 0
    try:
        git_root = run(["git", "rev-parse", "--show-toplevel"], ctx.root)
        if git_root.returncode or not git_root.stdout.strip():
            return 0
        root = Path(git_root.stdout.strip()).resolve()
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
        if branch in ("main", "master", "HEAD", ""):
            return 0
        environment = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_SSH_COMMAND": "ssh -oBatchMode=yes -oConnectTimeout=5",
        }
        fetched = run(["git", "fetch", "--quiet", "origin"], root, 25, env=environment)
        if fetched.returncode:
            return 0
        for base in ("origin/main", "origin/master"):
            if run(["git", "rev-parse", "--verify", base], root).returncode == 0:
                behind = run(
                    ["git", "rev-list", "--count", f"HEAD..{base}"], root
                ).stdout.strip()
                if behind.isdigit() and int(behind):
                    print(
                        f"Branch '{branch}' is {behind} commits behind {base}. Review branch freshness before integration."
                    )
                break
    except (OSError, subprocess.TimeoutExpired):
        pass
    return 0


def domain_resources(ctx: Context) -> int:
    if not ctx.root:
        return 0
    found = []
    for package, manifest in ctx.members.items():
        deps = dependencies(manifest)
        candidates = []
        if "@sinclair/typebox" in deps:
            candidates.append(("TypeBox contracts", package / "src"))
        if "fastify" in deps:
            candidates.append(("Fastify modules", package / "src/modules"))
        if "drizzle-orm" in deps:
            candidates.extend(
                [
                    ("Drizzle repositories", package / "src/drizzle-repository.ts"),
                    (
                        "Drizzle job repository",
                        package / "src/drizzle-job-repository.ts",
                    ),
                ]
            )
        if package.name == "worker" and (package / "src/index.ts").is_file():
            candidates.append(("worker lifecycle", package / "src/index.ts"))
        for label, path in candidates:
            if path.exists():
                found.append(f"{label}: {ctx.relative(path)}")
    if found:
        print(
            "Load the domain-resources knowledge skill through native discovery/selection when relevant. Detected "
            + "; ".join(found)
            + ". Follow the existing contracts, services and repositories."
        )
    return 0


def runtime_tools(ctx: Context) -> int:
    if not ctx.root:
        return 0
    scripts = json_file(ctx.root / "package.json").get("scripts", {})
    development = [name for name in scripts if name == "dev" or name.startswith("dev:")]
    if development:
        print(
            "Development scripts available: "
            + ", ".join("pnpm " + name for name in development)
            + "."
        )
    api = next(
        (
            p
            for p, m in ctx.members.items()
            if "fastify" in dependencies(m)
            and (p / "src/modules/health/routes.ts").is_file()
        ),
        None,
    )
    if api is None:
        return 0
    route = read(api / "src/modules/health/routes.ts")
    if not re.search(r"['\"]/health['\"]", route) or not all(
        name in route for name in ("uptimeSeconds", "environment", "sessions", "status")
    ):
        return 0
    explicit = os.environ.get("API_PORT")
    schema = read(ctx.root / "packages/env/src/server.ts")
    default = re.search(
        r"API_PORT\s*:\s*Type\.Integer\(\{[^}]*\bdefault\s*:\s*(\d+)", code_view(schema)
    )
    port = explicit if explicit is not None else default[1] if default else ""
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        print(
            "API health not checked: no valid explicit API_PORT or confirmed schema default."
        )
        return 0
    note = (
        "explicit API_PORT"
        if explicit is not None
        else "schema default; the running server may use another port"
    )
    url = f"http://127.0.0.1:{int(port)}/health"
    try:
        # No redirects, proxies, credentials, env-file evaluation, or second request.
        response = run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--fail",
                "--noproxy",
                "*",
                "--proto",
                "=http",
                "--connect-timeout",
                "2",
                "--max-time",
                "3",
                "--max-filesize",
                "65536",
                "--write-out",
                "\n%{http_code}",
                url,
            ],
            ctx.root,
            3.5,
        )
        payload, _, http_status = response.stdout.rpartition("\n")
        body = (
            json.loads(payload)
            if response.returncode == 0 and http_status == "200"
            else {}
        )
        data = body.get("data", {}) if isinstance(body, dict) else {}
        valid = (
            isinstance(data, dict)
            and data.get("status") == "ok"
            and isinstance(data.get("environment"), str)
            and type(data.get("uptimeSeconds")) in (int, float)
            and data["uptimeSeconds"] >= 0
            and type(data.get("sessions")) is int
            and data["sessions"] >= 0
            and ("driver" not in data or isinstance(data["driver"], str))
        )
        if valid:
            driver = f"; driver={data['driver']}" if "driver" in data else ""
            print(
                f"API health available at {url}{driver} ({note}). Use the existing HTTP/OpenAPI and available inspection tools."
            )
        else:
            print(
                f"API health not confirmed at {url} ({note}); response unavailable or envelope unrecognized."
            )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print(f"API health not confirmed at {url} ({note}).")
    return 0


def inject_rules(ctx: Context) -> int:
    if ctx.root:
        emit_context(
            "SubagentStart",
            "TypeScript starter rules: read the affected package instructions and real scripts. "
            "Validate inputs with shared TypeBox contracts and local type barrels. Keep Fastify transport, domain services and Drizzle repositories separate. "
            "Use @starter/env; preserve the literal Expo public-config adapter. Session is a domain, not proof of identity or authorization. "
            "Own async resources with explicit lifecycle/cleanup; prevent stale responses in clients. Jobs need idempotency, transactional claims, leases/fencing and bounded shutdown using the existing worker. "
            "Web mutations follow actions and the API client; mobile uses its own services/hooks and public configuration. Keep server implementations out of client bundles. "
            "Inspect raw SQL/HTML sources and use parameterized queries and appropriate sanitization. Do not log secrets or complete Drizzle SQL/error parameters. "
            "Run scoped checks with the real pnpm/Turbo scripts, then pnpm verify before claiming completion. After three failed attempts, document failures, research alternatives and change approach. Preserve the user’s authorization and scope.",
        )
    return 0


def plan_reminder(ctx: Context) -> int:
    if (
        not ctx.root
        or not ctx.scoped(ctx.file)
        or not re.fullmatch(r"\.claude/plans/[^/]+/plan\.md", ctx.relative(ctx.file))
    ):
        return 0
    if (
        ctx.event.get("tool_name", "Write") != "Write"
        or "content" not in ctx.tool_input
        or "old_string" in ctx.tool_input
    ):
        return 0
    response = ctx.event.get("tool_response")
    if isinstance(response, dict) and response.get("type") in ("update", "overwrite"):
        return 0
    if "**State**:" in read(ctx.file.parent / "progress.md"):
        return 0
    return warning(
        "Plan file created. For planning-only scope, present the plan and finish the requested planning work. If execution was already authorized, continue within that authorization. /ts:brief can explain the plan; /ts:work executes it. Do not invent a new approval checkpoint."
    )


def metrics(ctx: Context) -> int:
    location = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not ctx.scoped(ctx.file) or not location:
        return 0
    directory = Path(location) / "skill-metrics"
    if not directory.is_dir():
        return 0
    now = datetime.now(timezone.utc)
    package = ctx.package(ctx.file)
    record = {
        "ts": now.isoformat(),
        "file": ctx.relative(ctx.file),
        "project": ctx.root.name,
        "package": ctx.members[package].get("name", ctx.relative(package))
        if package
        else None,
    }
    with (directory / f"edits-{now:%Y-%m}.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


def precompact(ctx: Context) -> int:
    if not ctx.root and not plans(ctx):
        return 0
    parent = ctx.base / ".claude/plans"
    if not inside(parent.resolve(), ctx.base):
        return 0
    full, planning, working = False, False, False
    for directory in sorted(parent.glob("*")):
        if not directory.is_dir() or not inside(directory.resolve(), ctx.base):
            continue
        if "**State**:" in read(directory / "progress.md"):
            full = True
        elif (directory / "research").is_dir() and not (
            directory / "plan.md"
        ).is_file():
            planning = True
        elif re.search(r"Status.*PENDING", read(directory / "plan.md")):
            planning = True
        elif pending(directory / "plan.md"):
            working = True
    if not any((full, planning, working)):
        return 0
    phase = "/ts:full" if full else "/ts:work" if working else "/ts:plan"
    message = f"Preserve across compaction: {phase}. Re-read the selected plan.md, progress.md and scratchpad.md; preserve current phase and user authorization. "
    if full:
        message += "Continue the authorized plan/work/review cycle within the recorded cycle and blocker limits. "
    elif working:
        message += "Continue authorized tasks; after three failed attempts document failures, research alternatives and change approach. Finish when the requested scope is done. "
    else:
        message += "Planning-only scope ends by presenting the plan. Execution already authorized may continue; do not add an approval checkpoint. "
    message += "Use scoped pnpm exec turbo run check-types lint test:run --filter=<package> checks where those scripts exist, and pnpm verify before claiming completion. Preserve existing retry/cycle limits. "
    active = next((p for p in plans(ctx) if pending(p)), None)
    if active:
        message += f"First pending plan: {ctx.relative(active)}. Multiple plans require confirming the intended task; selection by file order grants no authorization. "
        scratch = active.parent / "scratchpad.md"
        if inside(scratch.resolve(), ctx.base):
            match = re.search(
                r"^## Dead Ends[^\n]*\n(.*?)(?=^## |\Z)", read(scratch), re.M | re.S
            )
            if match and "(none yet)" not in match[1]:
                message += "\nDead Ends (do not retry):\n" + "\n".join(
                    match[1].splitlines()[:20]
                )
    print(json.dumps({"systemMessage": message}))
    return 0


def postcompact(ctx: Context) -> int:
    active = next((p for p in plans(ctx) if pending(p)), None)
    if active:
        return warning(
            f"After compaction: pending plan {ctx.relative(active)}. Re-read that plan.md and its scratchpad.md to restore context. Preserve scope and existing authorization; file order does not select another task for you."
        )
    return 0


def stop_failure(ctx: Context) -> int:
    candidates = plans(ctx)
    if candidates:
        selected = max(candidates, key=lambda p: p.parent.stat().st_mtime)
        target = selected.parent / "scratchpad.md"
        if inside(target.resolve(), ctx.base):
            with target.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"\n## API Failure {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n\nTurn ended due to an API error. Check progress.md for the last completed task.\nResume with: /ts:work --continue\n"
                )
    return 0


def pending_stop(ctx: Context) -> int:
    if ctx.event.get("stop_hook_active") is True:
        return 0
    background = ctx.event.get("background_tasks", [])
    crons = ctx.event.get("session_crons", [])
    background = len(background) if isinstance(background, list) else 0
    crons = len(crons) if isinstance(crons, list) else 0
    if not background and not crons:
        return 0
    messages = []
    if background:
        messages.append(
            f"{background} background task(s) still running; stop or detach explicitly."
        )
    if crons:
        messages.append(f"{crons} session cron(s) scheduled; inspect /schedule list.")
    count = sum(bool(pending(p)) for p in plans(ctx))
    if count:
        messages.append(f"{count} plan(s) have pending tasks.")
    try:
        branch = run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], ctx.base
        ).stdout.strip()
        if branch not in ("", "HEAD", "main", "master"):
            dirty = run(["git", "status", "--porcelain"], ctx.base).stdout.splitlines()
            if dirty:
                messages.append(f"{len(dirty)} uncommitted change(s) on {branch}.")
    except (OSError, subprocess.TimeoutExpired):
        pass
    print(json.dumps({"systemMessage": "\n".join(messages)}))
    return 0


def failure_details(ctx: Context):
    if not ctx.root or ctx.event.get("tool_name", "Bash") != "Bash":
        return None
    command = ctx.tool_input.get("command", "")
    classified = None
    for args, cwd, _policy_override in literal_commands(ctx, command):
        if not args or Path(args[0]).name not in {
            "pnpm",
            "turbo",
            "tsc",
            "vitest",
            "eslint",
            "prettier",
            "drizzle-kit",
            "next",
            "vite",
            "tsup",
        }:
            continue
        name = Path(args[0]).name
        joined = " ".join(args)
        category = "pnpm/Turbo"
        if name == "drizzle-kit" or re.search(
            r"\bdb:(?:migrate|push|generate|deploy)\b", joined
        ):
            category = "Drizzle"
        elif name == "tsc" or re.search(r"\b(check-types|typecheck)\b", joined):
            category = "TypeScript"
        elif name == "vitest" or re.search(r"\btest(?::[\w-]+)?\b", joined):
            category = "Vitest"
        elif name in ("eslint", "prettier") or re.search(
            r"\b(lint|format)(?::[\w-]+)?\b", joined
        ):
            category = "lint/format"
        elif re.search(r"\bbuild\b", joined):
            category = "build"
        if classified is None or category != "pnpm/Turbo":
            classified = (category, cwd)
        if category != "pnpm/Turbo":
            break
    if classified is None:
        return None
    category, cwd = classified
    package = ctx.package(cwd)
    # Include literal filters/cwd in the key, without persisting command arguments.
    identity = json.dumps(
        [
            str(ctx.root),
            ctx.event.get("session_id", "nosession"),
            str(ctx.cwd),
            list(shell_commands(command)),
        ],
        sort_keys=True,
    )
    error = ctx.event.get("error", "")
    if isinstance(error, dict):
        error = error.get("message", "")
    if not isinstance(error, str):
        error = ""
    evidence = []
    for line in error.splitlines():
        codes = re.findall(
            r"\b(?:TS\d{3,6}|SQLSTATE\s*[:=]?\s*[A-Z0-9]{5}|ERR_PNPM_[A-Z_]+|[A-Z][A-Za-z]+Error)\b",
            line,
        )
        paths = re.findall(
            r"(?<![\w:/])(?:apps|packages)/[\w./-]+\.(?:tsx?|mts|cts|jsx?|mjs|cjs)(?::\d+(?::\d+)?)?",
            line,
        )
        if codes or paths:
            evidence.append(" ".join([*codes, *paths])[:300])
        if len(evidence) == 20:
            break
    label = (
        ctx.members[package].get("name", ctx.relative(package))
        if package
        else "workspace"
    )
    # Filters in root commands identify consumers even when the cwd is the root.
    first = next(iter(shell_commands(command)), [])
    if first and Path(first[0]).name in ("pnpm", "turbo"):
        _, _, filters, _ = parse_runner(first, ctx.cwd)
        if filters:
            label = ", ".join(filters)
    return category, label, evidence, hashlib.sha256(identity.encode()).hexdigest()


def failure_hints(ctx: Context) -> int:
    details = failure_details(ctx)
    if details is None:
        return 0
    category, package, evidence, _ = details
    hints = {
        "Drizzle": "Inspect the first SQLSTATE, schema and migration state. Check the driver and use disposable Postgres tests when appropriate. Do not reset databases as default recovery or persist complete ORM errors/SQL parameters.",
        "TypeScript": "Read the first diagnostic before cascading errors. Check package exports, declared dependencies and NodeNext .js import extensions. Run the affected package check-types script.",
        "Vitest": "Inspect the first failing assertion and isolated setup. Run the named file with pnpm --filter <package> exec vitest run <file> -t <test>. Check timers, cleanup and disposable database state.",
        "lint/format": "Read the first rule from the actual shared/package config. Run the affected package lint script or local Prettier --check on the file. Preserve configured test exceptions and no-console: off.",
        "build": "Find the first failing package and build diagnostic in Turbo output. Check its exports, configuration and dependencies before rebuilding the affected package.",
        "pnpm/Turbo": "Identify the first failing task and package/filter. Inspect manifests, lock consistency and the original diagnostic; do not install or rerun automatically.",
    }
    emit_context(
        "PostToolUseFailure",
        f"{category} failure in {package}. {hints[category]}"
        + (
            " First diagnostic identifiers: " + evidence[0]
            if evidence
            else " Read the first error in the tool output."
        ),
    )
    return 0


def state_directory(ctx: Context, name: str) -> Path:
    digest = hashlib.sha256(
        json.dumps([str(ctx.base), ctx.event.get("session_id", "nosession")]).encode()
    ).hexdigest()
    parent = Path(tempfile.gettempdir()) / f"typescript-starter-{os.getuid()}"
    for directory in (parent, parent / digest, parent / digest / name):
        if directory.is_symlink():
            raise OSError("refusing a symlink in hook state")
        directory.mkdir(mode=0o700, exist_ok=True)
        if directory.stat().st_uid != os.getuid():
            raise OSError("hook state belongs to another user")
    return parent / digest / name


def error_critic(ctx: Context) -> int:
    details = failure_details(ctx)
    if details is None:
        return 0
    import fcntl

    category, package, evidence, key = details
    path = state_directory(ctx, "failures") / (key + ".json")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "r+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            record = json.loads(handle.read(MAX_READ))
        except ValueError:
            record = {}
        count = int(record.get("count", 0)) + 1
        history = record.get("history", [])[-4:]
        history.append(
            {
                "attempt": count,
                "category": category,
                "package": package,
                "evidence": evidence[:18],
            }
        )
        handle.seek(0)
        handle.truncate()
        json.dump({"count": count, "history": history}, handle)
    if count == 1:
        return 0
    if count == 2:
        message = f"Repeated failure (attempt #2), {category} in {package}. Pause and compare the first diagnostics. Re-read the source and consider /ts:investigate before another attempt."
    else:
        summary = "\n".join(
            f"Attempt #{item['attempt']}: {item['category']} in {item['package']}; "
            + ("; ".join(item["evidence"]) or "inspect original tool output")
            for item in history
        )
        message = f"Three-attempt limit reached (attempt #{count}), {category} in {package}.\n{summary}\nStop retrying the same approach. Document what failed, research alternatives, question the approach, and use /ts:investigate or existing .claude/solutions. Do not run a fourth attempt of the same approach."
    emit_context("PostToolUseFailure", message)
    return 0


def route_intent(ctx: Context) -> int:
    if not ctx.root:
        return 0
    prompt = ctx.event.get("prompt", "")
    if not isinstance(prompt, str):
        return 0
    prompt = prompt[:4000]
    if not prompt.strip() or prompt.lstrip().startswith(("/", "$")):
        return 0
    choices = [
        (
            "pr-review",
            r"github\.com/[^/\s]+/[^/\s]+/pull/\d+|review (?:this|the|my) pr|pr (?:comments|feedback|review)|reviewer feedback|address .{0,20}review|code review",
            "/ts:pr-review can inspect PR feedback and plan the requested changes.",
        ),
        (
            "investigate-ui",
            r"<context name=[\"\']current-page[\"\']>|(?:web|mobile|expo|react native).{0,50}(?:crash|broken|bug|stale|not updating)",
            "/ts:investigate can trace this web/mobile problem through the existing client and API boundaries.",
        ),
        (
            "investigate-error",
            r"\b(?:TypeError|ReferenceError|SyntaxError|RangeError|ERR_PNPM_[A-Z_]+|error TS\d+)\b|(?:apps|packages)/[\w./-]+\.[cm]?[jt]sx?:\d+",
            "/ts:investigate can trace the first JavaScript/TypeScript error and its affected package.",
        ),
    ]
    state = state_directory(ctx, "routing")
    for category, pattern, hint in choices:
        if re.search(pattern, prompt, re.I):
            marker = state / category
            try:
                with marker.open("x", encoding="utf-8") as handle:
                    handle.write("suggested\n")
            except FileExistsError:
                continue
            emit_context(
                "UserPromptSubmit", "[plugin hint] " + hint + " Suggestion only."
            )
            return 0
    return 0


def explicit_boolean(flags: list[str], name: str) -> bool:
    """Require an unambiguous true CLI switch; contradictions cannot prove safety."""
    enabled = name in flags or name + "=true" in flags
    for index, flag in enumerate(flags):
        if flag.split("=", 1)[0] == "--no-" + name[2:]:
            return False
        if flag.startswith(name + "=") and flag != name + "=true":
            return False
        if (
            flag == name
            and index + 1 < len(flags)
            and flags[index + 1].lower() in ("false", "0", "no")
        ):
            return False
    return enabled


def dependency_gate(ctx: Context) -> int:
    if not ctx.root or ctx.event.get("tool_name") != "Bash":
        return 0
    operations = []
    for args, cwd, policy_override in literal_commands(
        ctx, ctx.tool_input.get("command", "")
    ):
        if not args or Path(args[0]).name != "pnpm" or not inside(cwd, ctx.root):
            continue
        task, flags, _, target_cwd = parse_runner(args, cwd)
        if not inside(target_cwd, ctx.root):
            continue
        if task in (
            "install",
            "i",
            "add",
            "update",
            "up",
            "rebuild",
            "remove",
            "rm",
            "unlink",
        ):
            preparation_flags = {
                "--lockfile-only",
                "--ignore-scripts",
                "--ignore-pnpmfile",
            }
            if policy_override <= preparation_flags and all(
                explicit_boolean(flags, flag) for flag in preparation_flags
            ):
                continue
            operations.append((task, flags, policy_override))
    if not operations:
        return 0
    ledger_path = ctx.root / "dependency-vet.json"

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate ledger key")
            result[key] = value
        return result

    try:
        ledger = (
            json.loads(read(ledger_path), object_pairs_hook=unique_keys)
            if ledger_path.exists()
            else {}
        )
        if not isinstance(ledger, dict):
            ledger = {}
    except ValueError:
        ledger = {}
    policy = ledger.get("policy", {})
    mode = (
        policy.get("block_on_unvetted", "warn")
        if isinstance(policy, dict)
        else "invalid"
    )
    mandatory = mode != "warn"
    if ledger_path.exists() and not ledger:
        mandatory, mode = True, "invalid"
    reason = ""
    if mode not in ("warn", "new_only", "strict", "full"):
        reason = (
            "Dependency policy is invalid or unreadable; audit coverage is unavailable."
        )
    elif any(override for _, _, override in operations):
        reason = "Inline registry, runtime or install-policy overrides differ from the audited configuration."
    elif any(
        task not in ("rebuild", "install", "i")
        or task in ("install", "i")
        and not explicit_boolean(flags, "--frozen-lockfile")
        for task, flags, _ in operations
    ):
        reason = "This command may resolve a new lock state; an audit of the old lock cannot approve it."
    else:
        driver = (
            Path(__file__).resolve().parents[2]
            / "skills/deps-audit/scripts/deps_audit.py"
        )
        try:
            checked = run(
                [
                    sys.executable,
                    str(driver),
                    "--root",
                    str(ctx.root),
                    "--gate-check",
                    "--gate-mode",
                    mode,
                ],
                ctx.root,
                2,
            )
            report = json.loads(checked.stdout)
            if checked.returncode == 0 and report.get("allowed") is True:
                return 0
            reason = report.get("reason", "Dependency audit is incomplete or blocked.")
        except (OSError, ValueError, AttributeError, subprocess.TimeoutExpired):
            reason = "Dependency audit coverage is unavailable; the offline gate could not validate the cache."
    instruction = (
        " Prepare the lock with --lockfile-only --ignore-scripts --ignore-pnpmfile, audit that exact state using /ts:deps-audit, then install with --frozen-lockfile. "
        "dependency-vet.json and .claude/deps-audit must match the current inputs; quick/fixture results are not approval."
    )
    if mandatory:
        deny("Dependency policy not satisfied: " + reason, reason + instruction)
    else:
        emit_context("PreToolUse", "Dependency audit advisory: " + reason + instruction)
    return 0


HANDLERS = {
    "block-dangerous-ops": destructive,
    "check-branch-freshness": branch_freshness,
    "check-pending-plans": pending_stop,
    "check-resume": resume,
    "check-scratchpad": scratchpad,
    "debug-statement-warning": debug,
    "deps-audit-gate": dependency_gate,
    "detect-domain-resources": domain_resources,
    "detect-runtime-tools": runtime_tools,
    "typescript-failure-hints": failure_hints,
    "error-critic": error_critic,
    "check-format": check_format,
    "freeze-gate": freeze,
    "inject-iron-laws": inject_rules,
    "iron-law-verifier": verify_code,
    "log-progress": metrics,
    "plan-stop-reminder": plan_reminder,
    "postcompact-verify": postcompact,
    "precompact-rules": precompact,
    "route-intent": route_intent,
    "security-reminder": security,
    "setup-dirs": setup,
    "stop-failure-log": stop_failure,
}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in HANDLERS:
        return 0
    try:
        payload = sys.stdin.read(2_000_001)
        if len(payload) > 2_000_000:
            return 0
        event = json.loads(payload) if payload.strip() else {}
        if not isinstance(event, dict):
            return 0
        return HANDLERS[argv[0]](Context.create(event))
    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        subprocess.SubprocessError,
    ):
        # Incidental failures are not evidence of a code violation. Mandatory
        # dependency-policy failures are handled inside dependency_gate above.
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Shared source-to-target transforms for Agent Skills."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable

AGENTSKILLS_FIELDS = {"name", "description", "license", "compatibility", "metadata"}
CANONICAL_PORTABLE_NAMES = {
    "audit": "ts-audit",
    "boundaries": "ts-boundaries",
    "brainstorm": "ts-brainstorm",
    "brief": "ts-brief",
    "challenge": "ts-challenge",
    "codex-loop": "ts-codex-loop",
    "compound": "ts-compound",
    "deploy": "ts-deploy",
    "deps-audit": "ts-deps-audit",
    "deps-update": "ts-deps-update",
    "deps-vet": "ts-deps-vet",
    "docs-fetcher": "ts-docs-fetcher",
    "document": "ts-document",
    "drizzle-constraint-debug": "drizzle-constraint-debug",
    "drizzle-n1-check": "drizzle-n1-check",
    "examples": "ts-examples",
    "freeze": "ts-freeze",
    "full": "ts-full",
    "help": "ts-help",
    "init": "ts-init",
    "intro": "ts-intro",
    "investigate": "ts-investigate",
    "learn-from-fix": "ts-learn-from-fix",
    "narrow-catch": "ts-narrow-catch",
    "perf": "ts-perf",
    "permissions": "ts-permissions",
    "plan": "ts-plan",
    "pnpm-compression": "ts-pnpm-compression",
    "pr-review": "ts-pr-review",
    "quick": "ts-quick",
    "react-state-audit": "react-state-audit",
    "recall": "ts-recall",
    "research": "ts-research",
    "review": "ts-review",
    "techdebt": "ts-techdebt",
    "trace": "ts-trace",
    "triage": "ts-triage",
    "verify": "ts-verify",
    "watch-pr": "ts-watch-pr",
    "work": "ts-work"
}


def portable_skill_name(directory_name: str, command_name: str) -> str:
    """Return the stable generated-runtime name for a canonical Claude skill."""
    return CANONICAL_PORTABLE_NAMES.get(
        directory_name,
        normalize_skill_name(command_name),
    )


def normalize_skill_name(name: str) -> str:
    """Normalize namespaced skill names for targets that disallow colons."""
    if not name:
        return name
    return name.replace(":", "-")


def transform_frontmatter(data: dict, target: str) -> dict:
    """Preserve Claude frontmatter or project it to Agent Skills fields."""
    if target == "claude":
        return dict(data)

    if target not in ("amp", "codex", "pi", "opencode"):
        raise ValueError(f"Unknown target: {target}")

    output: dict = {}

    for key, value in data.items():
        if key == "name":
            output["name"] = normalize_skill_name(value)
        elif key in AGENTSKILLS_FIELDS:
            output[key] = value

    metadata = output.get("metadata")
    if metadata is not None and (
        not isinstance(metadata, dict)
        or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in metadata.items()
        )
    ):
        raise ValueError("Agent Skills metadata must be a string-to-string mapping")

    if isinstance(output.get("description"), str):
        output["description"] = rewrite_slash_commands(
            output["description"],
            target,
        )

    return output


_CLAUDE_REF_RE = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/references/([\w./-]+)")
_SLASH_CMD_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])/(ts|react|drizzle):"
    r"([a-z][a-z0-9-]*)(?![A-Za-z0-9_:-])"
)
_SLASH_NAMESPACE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])/(ts|react|drizzle):"
    r"(?:\*(?![A-Za-z0-9_:-])|(?![A-Za-z0-9_*:-]))"
)


def rewrite_reference_paths(body: str, target: str) -> str:
    """Rewrite Claude skill reference paths to skill-relative paths."""
    if target == "claude":
        return body
    return _CLAUDE_REF_RE.sub(r"references/\1", body)


def port_references(
    refs_src: str | Path,
    refs_dst: str | Path,
    target: str,
) -> None:
    """Copy references, transforming Markdown and preserving other files."""
    source = Path(refs_src)
    destination = Path(refs_dst)

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    for src in source.rglob("*"):
        if src.is_dir():
            continue

        output = destination / src.relative_to(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".md":
            text = src.read_text(encoding="utf-8")
            text = rewrite_reference_paths(text, target)
            text = rewrite_slash_commands(text, target)
            output.write_text(text, encoding="utf-8")
        else:
            shutil.copy2(src, output)


def rewrite_slash_commands(body: str, target: str) -> str:
    """Rewrite Claude namespaced command references for a target."""
    if target == "claude":
        return body
    prefixes = {"amp": "", "codex": "$", "pi": "/skill:", "opencode": "/"}
    if target not in prefixes:
        raise ValueError(f"Unknown target: {target}")
    prefix = prefixes[target]

    def command(match: re.Match) -> str:
        namespace, name = match.groups()
        portable = f"{namespace}-{name}"
        if namespace == "ts":
            portable = CANONICAL_PORTABLE_NAMES.get(name, portable)
        return prefix + portable

    body = _SLASH_CMD_RE.sub(command, body)
    return _SLASH_NAMESPACE_RE.sub(lambda match: prefix + match.group(1) + "-*", body)


_IRON_LAW_HEADER = "## Iron Laws (Inlined)"


def inline_iron_laws(body: str, laws: Iterable[str], target: str) -> str:
    """Append or replace an inlined Iron Laws section."""
    if target == "claude":
        return body

    laws_list = list(laws)
    if not laws_list:
        return body

    bullets = "\n".join(f"- {law}" for law in laws_list)
    block = f"\n\n{_IRON_LAW_HEADER}\n\n{bullets}\n"
    pattern = re.compile(
        rf"\n*{re.escape(_IRON_LAW_HEADER)}\n.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    cleaned = pattern.sub("", body).rstrip()
    return cleaned + block

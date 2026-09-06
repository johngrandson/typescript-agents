"""Behavioral hook contracts. All application projects and executables are fixtures."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location(
    "ts_hook_runtime", SCRIPTS / "hook_runtime.py"
)
hook = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hook
spec.loader.exec_module(hook)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if isinstance(value, dict) else value)
    return path


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "arbitrary project name"
    write(
        root / "package.json",
        {
            "name": "renamed",
            "devDependencies": {"typescript": "^5.7"},
            "scripts": {
                "build": "turbo run build",
                "db:push": "turbo run db:push --filter=@starter/db",
                "dev": "turbo run dev",
            },
        },
    )
    write(root / "turbo.json", {})
    write(
        root / "pnpm-workspace.yaml",
        'packages:\n  - apps/*\n  - packages/*\n  - "!packages/excluded"\n',
    )
    packages = {
        "apps/api": {"fastify": "*", "@sinclair/typebox": "*"},
        "apps/web": {"next": "*"},
        "apps/mobile": {"expo": "*"},
        "apps/worker": {},
        "packages/db": {"drizzle-orm": "*"},
        "packages/env": {},
        "packages/types": {"@sinclair/typebox": "*"},
    }
    for directory, deps in packages.items():
        write(
            root / directory / "package.json",
            {
                "name": "@starter/" + directory.split("/")[-1],
                "dependencies": deps,
                "scripts": {
                    "db:push": "drizzle-kit push",
                    "test": "vitest run",
                    "cycle": "pnpm cycle",
                },
            },
        )
        (root / directory / "src").mkdir()
    write(root / "compose.yaml", "services: {}\n")
    return root


@pytest.fixture
def invoke(workspace, tmp_path):
    def call(name, payload=None, *, cwd=None, project=None, env=None):
        payload = dict(payload or {})
        payload.setdefault("cwd", str(cwd or workspace))
        payload.setdefault("session_id", "fixture-session")
        environment = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project or workspace),
            "TMPDIR": str(tmp_path),
            **(env or {}),
        }
        result = subprocess.run(
            ["bash", str(SCRIPTS / (name + ".sh"))],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=cwd or workspace,
            env=environment,
            timeout=8,
        )
        return result

    return call


def event(path=None, content="", tool="Write", command=None):
    values = {"tool_name": tool, "tool_input": {}}
    if path is not None:
        values["tool_input"] = {"file_path": str(path), "content": content}
    if command is not None:
        values["tool_input"]["command"] = command
    return values


def blocked(result):
    assert result.returncode == 0, result.stderr
    return bool(
        result.stdout
        and json.loads(result.stdout)
        .get("hookSpecificOutput", {})
        .get("permissionDecision")
        == "deny"
    )


@pytest.mark.parametrize(
    "command",
    [
        "git push --force",
        "git push origin main -f",
        "\t git\tpush --force",
        "(git push --force)",
        "env X=y git push --force",
        "FOO=bar git push --force",
        "echo safe && git push --force",
        "echo safe\ngit push --force",
        "git -C . push --force",
        "dropdb example",
        "env DB=test dropdb example",
        "pnpm exec drizzle-kit push --force",
        "pnpm db:push --force",
        "pnpm --filter @starter/db db:push --force",
        "pnpm -C packages/db db:push -- --force",
        'psql -c "DROP DATABASE example"',
        'psql --command="TRUNCATE TABLE examples"',
        'mysql -e "DROP SCHEMA example"',
        "docker compose down --volumes",
        "docker compose down -v",
    ],
)
def test_destructive_commands_are_denied_without_execution(invoke, command):
    assert blocked(invoke("block-dangerous-ops", event(tool="Bash", command=command)))


@pytest.mark.parametrize(
    "command",
    [
        "git push --force-with-lease",
        "git push --force-with-lease=main:abc",
        'echo "git push --force"',
        'echo "(git push --force)"',
        'echo "safe; git push --force"',
        "printf '%s' 'git push --force'",
        "git push && echo --force",
        'echo "dropdb example"',
        'echo "pnpm db:push --force"',
        "pnpm db:generate",
        "pnpm db:migrate",
        "pnpm db:deploy",
        "pnpm db:push",
        "pnpm cycle",
        "NODE_ENV=production pnpm build",
        "ENVIRONMENT=production pnpm build",
        "docker compose build",
        "docker compose down",
        'psql -c "SELECT 1"',
        "psql -c \"SELECT 'DROP DATABASE x'\"",
        'psql -c "-- DROP DATABASE example"',
    ],
)
def test_safe_commands_and_mentions_remain_allowed(invoke, command):
    assert not blocked(
        invoke("block-dangerous-ops", event(tool="Bash", command=command))
    )


def test_global_force_push_and_workspace_only_database(invoke, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    assert blocked(
        invoke(
            "block-dangerous-ops",
            event(tool="Bash", command="git push -f"),
            project=outside,
            cwd=outside,
        )
    )
    assert not blocked(
        invoke(
            "block-dangerous-ops",
            event(tool="Bash", command="dropdb example"),
            project=outside,
            cwd=outside,
        )
    )
    assert not blocked(
        invoke("block-dangerous-ops", event(tool="Edit", command="git push -f"))
    )


def test_command_cd_does_not_apply_application_rules_outside(invoke, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    assert not blocked(
        invoke(
            "block-dangerous-ops",
            event(tool="Bash", command=f'cd "{outside}" && dropdb example'),
        )
    )


def test_workspace_resolution_cwd_packages_and_new_paths(workspace, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(workspace / "apps/mobile"))
    context = hook.Context.create(
        {
            "cwd": str(workspace / "packages/db"),
            "tool_input": {"file_path": 'src/space "quoted"/../new.ts'},
        }
    )
    assert context.root == workspace
    assert context.package(context.file) == workspace / "packages/db"
    assert context.file == workspace / "packages/db/src/new.ts"
    assert context.package(workspace / "README.md") is None


def test_project_env_is_optional(workspace, monkeypatch):
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    context = hook.Context.create({"cwd": str(workspace / "apps/mobile")})
    assert context.root == workspace


def test_excluded_workspace_and_escape(invoke, workspace, tmp_path):
    write(workspace / "packages/excluded/package.json", {"name": "excluded"})
    assert not hook.workspace_members(workspace).get(workspace / "packages/excluded")
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "apps/mobile/src/link").symlink_to(outside)
    result = invoke(
        "iron-law-verifier", event("apps/mobile/src/link/new.ts", "process.env.SECRET")
    )
    assert result.returncode == 0 and not result.stderr


@pytest.mark.parametrize("extension", sorted(hook.EXTENSIONS))
def test_all_code_extensions(invoke, workspace, extension):
    path = write(
        workspace / ("apps/api/src/example" + extension),
        "const value = process.env.PORT;",
    )
    assert invoke("iron-law-verifier", event(path, path.read_text())).returncode == 2


@pytest.mark.parametrize(
    "path,content,warn",
    [
        ("apps/api/src/x.ts", "const port = process.env.PORT;", True),
        ("packages/env/src/x.ts", "const port = process.env.PORT;", False),
        (
            "apps/mobile/src/services/config.ts",
            "const url = process.env.EXPO_PUBLIC_API_URL;",
            False,
        ),
        (
            "apps/mobile/src/services/config.ts",
            "const secret = process.env.SECRET;",
            True,
        ),
        ("apps/web/components/item.tsx", 'fetch("/api/items");', True),
        ("apps/mobile/src/services/items.ts", 'fetch("/api/items");', False),
        ("apps/web/app/api/proxy/route.ts", 'fetch("/api/items");', False),
        (
            "apps/api/src/x.ts",
            '// process.env.BAD\nconst text = "process.env.BAD";',
            False,
        ),
        (
            "apps/api/src/x.ts",
            "/* process.env.BAD */ const regex = /process.env.BAD/;",
            False,
        ),
        ("apps/api/src/x.ts", "const text = `process.env.BAD`;", False),
        ("apps/api/src/x.ts", "function start() { setInterval(work, 10); }", False),
        ("apps/api/src/x.ts", "setInterval(work, 10);", True),
        (
            "apps/web/components/item.tsx",
            "<div dangerouslySetInnerHTML={{__html: content}} />;",
            True,
        ),
        ("packages/db/src/schema.ts", 'const money = {price: real("price")};', True),
        (
            "packages/db/src/schema.ts",
            'const dimensions = {height: real("height")};',
            False,
        ),
        ("packages/db/src/schema.ts", "const x = sql.raw(value);", True),
        ("apps/api/src/__tests__/x.test.ts", "const x = process.env.TEST;", False),
        ("apps/api/scripts/x.ts", "const x = process.env.TEST;", False),
        ("apps/api/src/x.config.ts", "const x = process.env.TEST;", False),
        ("root.ts", "const x = process.env.TEST;", False),
    ],
)
def test_code_rules_respect_package_and_syntax(invoke, workspace, path, content, warn):
    path = write(workspace / path, content)
    result = invoke("iron-law-verifier", event(path, content))
    assert (result.returncode == 2) == warn, result.stderr


@pytest.mark.parametrize(
    "statement,warn",
    [
        ("import { db } from '@starter/db';", True),
        ("import type { Database } from '@starter/db';", False),
        ("import { type Database } from '@starter/db';", False),
        ("import { Type } from '@sinclair/typebox';", False),
        ("const mention = \"import {db} from '@starter/db'\";", False),
    ],
)
def test_client_import_boundaries(invoke, workspace, statement, warn):
    path = write(
        workspace / "apps/web/components/item.tsx", "'use client';\n" + statement
    )
    result = invoke("iron-law-verifier", event(path, statement))
    assert (result.returncode == 2) == warn, result.stderr


def test_only_introduced_code_and_existing_timer_scope(invoke, workspace):
    path = write(
        workspace / "apps/api/src/x.ts",
        "const old = process.env.BAD;\nfunction start() {\n setTimeout(run, 20);\n}\nconst good = 1;",
    )
    result = invoke(
        "iron-law-verifier",
        {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(path), "new_string": "const good = 1;"},
        },
    )
    assert result.returncode == 0
    result = invoke(
        "iron-law-verifier",
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(path),
                "new_string": " setTimeout(run, 20);",
            },
        },
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    "content,warn",
    [
        ("debugger;", True),
        ('console.log("intentional");', True),
        ("console.debug(value);", True),
        ("console.trace();", True),
        ('getLogger().info("hello");', False),
        ('// debugger;\nconst s = "console.log()";', False),
    ],
)
def test_debug_review_preserves_intentional_logging(invoke, workspace, content, warn):
    path = write(workspace / "apps/api/src/x.ts", content)
    result = invoke("debug-statement-warning", event(path, content))
    assert (result.returncode == 2) == warn
    if warn:
        assert (
            "no-console is off" in result.stderr
            and "retain intentional logging" in result.stderr
        )


@pytest.mark.parametrize(
    "path,warn",
    [
        ("apps/api/src/auth-token.ts", True),
        ("apps/api/src/session.ts", True),
        ("apps/api/src/tokenizer.ts", False),
        ("apps/api/src/admin/index.ts", False),
    ],
)
def test_security_basename_boundaries(invoke, path, warn):
    result = invoke("security-reminder", event(path))
    assert (result.returncode == 2) == warn
    if warn:
        assert "does not imply authentication" in result.stderr


def test_freeze_absent_empty_allowlist_and_normalization(invoke, workspace, tmp_path):
    payload = event("apps/mobile/src/new.ts")
    assert not blocked(invoke("freeze-gate", payload))
    sentinel = write(workspace / ".claude/.freeze", "")
    assert blocked(invoke("freeze-gate", payload))
    sentinel.write_text("# scope\napps/mobile/src")
    assert not blocked(invoke("freeze-gate", payload))
    assert blocked(invoke("freeze-gate", event("apps/mobile/src-evil/new.ts")))
    assert blocked(invoke("freeze-gate", event("apps/mobile/src/../../api/src/new.ts")))
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "apps/mobile/src/link").symlink_to(outside)
    assert blocked(invoke("freeze-gate", event("apps/mobile/src/link/new.ts")))
    assert not blocked(
        invoke("freeze-gate", event(tool="Bash", command="echo example"))
    )


def test_freeze_without_typescript_workspace(invoke, tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    write(root / ".claude/.freeze", "")
    assert blocked(invoke("freeze-gate", event("x.txt"), project=root, cwd=root))


def test_setup_uses_workspace_root_only(invoke, workspace):
    result = invoke(
        "setup-dirs", cwd=workspace / "apps/mobile", project=workspace / "apps/mobile"
    )
    assert result.returncode == 0
    assert sorted(p.name for p in (workspace / ".claude").iterdir()) == [
        "audit",
        "plans",
        "research",
        "reviews",
        "skill-metrics",
        "solutions",
    ]
    assert not (workspace / "apps/mobile/.claude").exists()


def test_setup_cannot_follow_claude_symlink(invoke, workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / ".claude").symlink_to(outside)
    invoke("setup-dirs")
    assert not list(outside.iterdir())


def test_metrics_jsonl_and_package_without_plan_mutation(invoke, workspace, tmp_path):
    data = tmp_path / "plugin-data"
    (data / "skill-metrics").mkdir(parents=True)
    plan = write(workspace / ".claude/plans/one/progress.md", "original")
    payload = event('src/a "quoted".ts')
    invoke(
        "log-progress",
        payload,
        cwd=workspace / "apps/mobile",
        env={"CLAUDE_PLUGIN_DATA": str(data)},
    )
    rows = list((data / "skill-metrics").glob("edits-*.jsonl"))
    record = json.loads(rows[0].read_text())
    assert record["file"] == 'apps/mobile/src/a "quoted".ts'
    assert (
        record["package"] == "@starter/mobile" and record["project"] == workspace.name
    )
    assert plan.read_text() == "original"


def test_metrics_does_not_create_fallback(invoke, workspace, tmp_path):
    data = tmp_path / "absent"
    invoke("log-progress", event("README.md"), env={"CLAUDE_PLUGIN_DATA": str(data)})
    assert not data.exists() and not (workspace / ".claude").exists()


def test_plans_resume_scratchpad_compaction_and_failure(invoke, workspace):
    plan = write(
        workspace / ".claude/plans/one/plan.md", "# Feature\n- [ ] first\n- [x] done\n"
    )
    assert "1 remaining tasks (1 done)" in invoke("check-resume").stdout
    invoke("check-scratchpad")
    scratch = plan.parent / "scratchpad.md"
    assert "## Dead Ends" in scratch.read_text()
    original = scratch.read_text()
    assert "scratchpad entries" in invoke("check-scratchpad").stdout
    assert scratch.read_text() == original
    assert "plan.md" in invoke("postcompact-verify").stderr
    write(plan.parent / "progress.md", "**State**: IMPLEMENTING\ncycle: 2\n")
    before = invoke("precompact-rules")
    assert "/ts:full" in before.stdout and "pnpm verify" in before.stdout
    assert invoke("plan-stop-reminder", event(plan, plan.read_text())).returncode == 0
    invoke("stop-failure-log", {"error": "SECRET=do-not-persist"})
    assert (
        "/ts:work --continue" in scratch.read_text()
        and "SECRET" not in scratch.read_text()
    )
    assert plan.read_text() == "# Feature\n- [ ] first\n- [x] done\n"


def test_plan_reminder_preserves_authorized_execution(invoke, workspace):
    plan = write(workspace / ".claude/plans/one/plan.md", "# feature")
    result = invoke("plan-stop-reminder", event(plan, plan.read_text()))
    assert (
        result.returncode == 2 and "execution was already authorized" in result.stderr
    )
    result = invoke(
        "plan-stop-reminder",
        {**event(plan, plan.read_text()), "tool_response": {"type": "update"}},
    )
    assert result.returncode == 0
    assert invoke("plan-stop-reminder", event("notes/plan.md", "x")).returncode == 0


def test_resume_outside_workspace_only_with_existing_plans(invoke, tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    assert not invoke("check-resume", project=root, cwd=root).stdout
    write(root / ".claude/plans/one/plan.md", "- [ ] first")
    assert "/ts:work" in invoke("check-resume", project=root, cwd=root).stdout


def test_stop_only_warns_for_background_and_allows_stopping(invoke):
    result = invoke("check-pending-plans")
    assert not result.stdout and result.returncode == 0
    result = invoke(
        "check-pending-plans", {"background_tasks": [{}], "session_crons": [{}, {}]}
    )
    body = json.loads(result.stdout)
    assert result.returncode == 0 and "systemMessage" in body
    assert (
        "1 background" in body["systemMessage"]
        and "2 session cron" in body["systemMessage"]
    )
    assert not invoke(
        "check-pending-plans", {"background_tasks": [{}], "stop_hook_active": True}
    ).stdout


def fake_prettier(root, *, info=None, status=0):
    executable = root / "node_modules/.bin/prettier"
    program = "#!/usr/bin/env python3\nimport json, pathlib, sys\n"
    program += f'pathlib.Path({str(root / "formatter-argv.jsonl")!r}).open("a").write(json.dumps(sys.argv[1:]) + "\\n")\n'
    program += f'if "--file-info" in sys.argv: print({json.dumps(info or {"ignored": False, "inferredParser": "typescript"})!r}); sys.exit(0)\n'
    program += f"sys.exit({status})\n"
    write(executable, program).chmod(0o755)


@pytest.mark.parametrize(
    "mode,phrase",
    [
        ("missing", "unavailable"),
        ("invalid", "Formatting differs"),
        ("error", "internal/configuration"),
        ("ignored", ""),
        ("valid", ""),
    ],
)
def test_prettier_states_never_write_or_install(invoke, workspace, mode, phrase):
    path = write(workspace / "apps/mobile/src/x.ts", "const x=1")
    if mode != "missing":
        fake_prettier(
            workspace,
            info={"ignored": mode == "ignored", "inferredParser": "typescript"},
            status={"invalid": 1, "error": 2}.get(mode, 0),
        )
    result = invoke("check-format", event(path))
    assert path.read_text() == "const x=1"
    assert (result.returncode == 2) == bool(phrase)
    if phrase:
        assert phrase in result.stderr
    if mode != "missing":
        calls = [
            json.loads(x)
            for x in (workspace / "formatter-argv.jsonl").read_text().splitlines()
        ]
        assert all("--write" not in call for call in calls)
        assert all(str(path) in call for call in calls)
        assert len(calls) == (1 if mode == "ignored" else 2)


def test_prettier_timeout_is_unverified(workspace, monkeypatch, capsys):
    fake_prettier(workspace)
    path = write(workspace / "apps/api/src/x.ts", "x")
    context = hook.Context.create({"cwd": str(workspace), **event(path)})
    monkeypatch.setattr(
        hook,
        "run",
        lambda argv, *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(argv, 25)
        ),
    )
    assert hook.check_format(context) == 2
    assert "not checked" in capsys.readouterr().err


@pytest.mark.parametrize(
    "path",
    [
        "apps/api/dist/a.ts",
        "apps/api/coverage/a.ts",
        "apps/api/node_modules/a.ts",
        "apps/api/vite.config.ts.timestamp-123.mjs",
        "apps/web/next-env.d.ts",
    ],
)
def test_generated_ignored_sources_do_not_run_formatter(invoke, workspace, path):
    target = write(workspace / path, "process.env.SECRET")
    assert invoke("check-format", event(target)).returncode == 0
    assert (
        invoke("iron-law-verifier", event(target, target.read_text())).returncode == 0
    )


def test_project_ignores(invoke, workspace):
    write(workspace / ".prettierignore", "apps/api/src/generated/**\n")
    path = write(workspace / "apps/api/src/generated/a.ts", "process.env.SECRET")
    assert invoke("check-format", event(path)).returncode == 0
    assert invoke("iron-law-verifier", event(path, path.read_text())).returncode == 0


def test_failure_counter_separates_packages_and_sessions(invoke, workspace, tmp_path):
    payload = event(tool="Bash", command="pnpm --filter @starter/web test")
    payload["error"] = (
        "TypeError at apps/web/components/item.tsx:20\nDATABASE_URL=postgres://private:secret@host/db\nTRUNCATE private_table"
    )
    assert not invoke("error-critic", payload).stdout
    assert "attempt #2" in invoke("error-critic", payload).stdout
    other = event(tool="Bash", command="pnpm --filter @starter/mobile test")
    assert not invoke("error-critic", other).stdout
    assert not invoke("error-critic", {**payload, "session_id": "another"}).stdout
    result = invoke("error-critic", payload)
    assert (
        "Three-attempt limit" in result.stdout
        and "Do not run a fourth" in result.stdout
    )
    for _ in range(4):
        invoke("error-critic", payload)
    records = list(tmp_path.glob("typescript-starter-*/*/failures/*.json"))
    record = max(
        (json.loads(path.read_text()) for path in records),
        key=lambda data: data["count"],
    )
    assert len(record["history"]) == 5
    serialized = json.dumps(record)
    assert all(
        value not in serialized
        for value in ("private_table", "DATABASE_URL", "secret@", "TRUNCATE")
    )


@pytest.mark.parametrize(
    "command,category,recovery_step",
    [
        ("pnpm exec tsc --noEmit", "TypeScript", "NodeNext .js import extensions"),
        ("pnpm test", "Vitest", "vitest run <file> -t <test>"),
        ("pnpm build", "build", "first failing package"),
        ("pnpm exec eslint .", "lint/format", "local Prettier --check"),
        ("pnpm db:migrate", "Drizzle", "Do not reset databases"),
        ("pnpm install", "pnpm/Turbo", "do not install or rerun automatically"),
    ],
)
def test_failure_classification(invoke, command, category, recovery_step):
    result = invoke(
        "typescript-failure-hints",
        {
            **event(tool="Bash", command=command),
            "error": "error TS2322 apps/api/src/a.ts:12",
        },
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUseFailure"
    context = output["additionalContext"]
    assert context.startswith(f"{category} failure in ")
    assert "TS2322" in context and recovery_step in context


def test_route_intent_is_bounded_deduplicated_and_safe(invoke, tmp_path):
    payload = {
        "prompt": "Review this PR https://github.com/owner/repo/pull/12",
        "session_id": "../../bad/session",
    }
    result = invoke("route-intent", payload)
    assert result.returncode == 0 and "/ts:pr-review" in result.stdout
    assert not invoke("route-intent", payload).stdout
    assert (
        "/ts:investigate"
        in invoke("route-intent", {"prompt": "TypeError: failed"}).stdout
    )
    assert not invoke(
        "route-intent", {"prompt": "x" * 4001 + " TypeError", "session_id": "bounded"}
    ).stdout
    assert not invoke(
        "route-intent",
        {"prompt": " /ts:investigate TypeError", "session_id": "explicit"},
    ).stdout
    assert not (tmp_path / "bad").exists()


def test_invalid_json_and_missing_jq_never_block_prompt(tmp_path):
    process = subprocess.run(
        ["bash", str(SCRIPTS / "route-intent.sh")],
        input="{bad",
        text=True,
        capture_output=True,
    )
    assert process.returncode == 0 and not process.stdout
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "python3").symlink_to(sys.executable)
    process = subprocess.run(
        ["/bin/bash", str(SCRIPTS / "route-intent.sh")],
        input="{}",
        text=True,
        capture_output=True,
        env={**os.environ, "PATH": str(bins)},
    )
    assert process.returncode == 0 and not process.stdout


def runtime_fixture(workspace):
    write(
        workspace / "apps/api/src/modules/health/routes.ts",
        "app.get('/health', () => ({data: {status: 'ok', environment, uptimeSeconds, driver, sessions}}));",
    )
    write(
        workspace / "packages/env/src/server.ts",
        "API_PORT: Type.Integer({minimum: 1, default: 3001})",
    )
    return hook.Context.create({"cwd": str(workspace)})


@pytest.mark.parametrize(
    "data,available",
    [
        (
            {
                "data": {
                    "status": "ok",
                    "environment": "test",
                    "uptimeSeconds": 2,
                    "driver": "memory",
                    "sessions": 0,
                }
            },
            True,
        ),
        ({"status": "ok"}, False),
        ({"data": {"status": "ok"}}, False),
        (
            {
                "data": {
                    "status": "ok",
                    "environment": "test",
                    "uptimeSeconds": True,
                    "sessions": 0,
                }
            },
            False,
        ),
    ],
)
def test_health_requires_real_envelope(workspace, monkeypatch, capsys, data, available):
    context = runtime_fixture(workspace)
    calls = []

    def fake(argv, cwd, timeout, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(data) + "\n200", "")

    monkeypatch.setattr(hook, "run", fake)
    hook.runtime_tools(context)
    output = capsys.readouterr().out
    assert ("API health available" in output) == available
    assert len(calls) == 1
    assert calls[0][-1] == "http://127.0.0.1:3001/health"
    assert "--location" not in calls[0] and "-L" not in calls[0]
    assert calls[0][calls[0].index("--connect-timeout") + 1] == "2"
    assert calls[0][calls[0].index("--max-time") + 1] == "3"
    if available:
        assert "driver=memory" in output


@pytest.mark.parametrize(
    "response,status",
    [("", 7), ('<a href="https://external.invalid/">redirect</a>', 0)],
)
def test_runtime_offline_redirect_no_second_probe(
    workspace, monkeypatch, capsys, response, status
):
    context = runtime_fixture(workspace)
    calls = []

    def fake(argv, *args, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, status, response, "")

    monkeypatch.setattr(hook, "run", fake)
    hook.runtime_tools(context)
    assert len(calls) == 1 and "API health not confirmed" in capsys.readouterr().out


def test_runtime_explicit_port_and_no_env_execution(workspace, monkeypatch):
    context = runtime_fixture(workspace)
    write(workspace / ".env", "API_PORT=$(touch SHOULD_NOT_EXIST)\n")
    monkeypatch.setenv("API_PORT", "4567")
    calls = []
    monkeypatch.setattr(
        hook,
        "run",
        lambda argv, *args, **kwargs: calls.append(argv)
        or subprocess.CompletedProcess(argv, 7, "", ""),
    )
    hook.runtime_tools(context)
    assert calls[0][-1] == "http://127.0.0.1:4567/health"
    assert not (workspace / "SHOULD_NOT_EXIST").exists()


def test_runtime_no_api_no_probe(workspace, monkeypatch):
    calls = []
    monkeypatch.setattr(hook, "run", lambda *args, **kwargs: calls.append(args))
    hook.runtime_tools(hook.Context.create({"cwd": str(workspace)}))
    assert not calls


def test_domain_knowledge_and_subagent_rules(invoke, workspace):
    (workspace / "apps/api/src/modules").mkdir()
    write(
        workspace / "packages/db/src/drizzle-repository.ts",
        "export const repository = {};",
    )
    write(workspace / "apps/worker/src/index.ts", "export const start = 1;")
    result = invoke("detect-domain-resources")
    assert (
        "domain-resources" in result.stdout
        and "/ts:domain-resources" not in result.stdout
    )
    assert (
        "Drizzle repositories" in result.stdout and "worker lifecycle" in result.stdout
    )
    rules = invoke("inject-iron-laws")
    assert "Session is a domain" in rules.stdout and "@starter/env" in rules.stdout


def test_git_offline_has_no_mutation_other_than_fetch(workspace, monkeypatch, capsys):
    calls = []
    outputs = iter([str(workspace), "feature", ""])

    def fake(argv, *args, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(
            argv, 1 if "fetch" in argv else 0, next(outputs), ""
        )

    monkeypatch.setattr(hook, "run", fake)
    hook.branch_freshness(hook.Context.create({"cwd": str(workspace)}))
    assert not capsys.readouterr().out
    assert all(
        not set(argv).intersection({"merge", "checkout", "rebase"}) for argv in calls
    )
    assert calls[-1] == ["git", "fetch", "--quiet", "origin"]


def test_branch_freshness_falls_back_to_master(workspace, monkeypatch, capsys):
    calls = []

    def fake(argv, *args, **kwargs):
        calls.append(argv)
        out, code = "", 0
        if "--show-toplevel" in argv:
            out = str(workspace)
        elif "--abbrev-ref" in argv:
            out = "feature"
        elif "origin/main" in argv:
            code = 1
        elif "--count" in argv:
            out = "3"
        return subprocess.CompletedProcess(argv, code, out, "")

    monkeypatch.setattr(hook, "run", fake)
    hook.branch_freshness(hook.Context.create({"cwd": str(workspace)}))
    assert "3 commits behind origin/master" in capsys.readouterr().out


def test_deps_gate_requires_exact_state_not_old_lock(invoke, workspace):
    write(
        workspace / "dependency-vet.json",
        {
            "schemaVersion": 1,
            "policy": {"block_on_unvetted": "strict"},
            "audits": [],
            "imports": [],
        },
    )
    assert blocked(invoke("deps-audit-gate", event(tool="Bash", command="pnpm update")))
    assert not blocked(
        invoke(
            "deps-audit-gate",
            event(
                tool="Bash",
                command="pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile",
            ),
        )
    )
    assert blocked(
        invoke(
            "deps-audit-gate",
            event(tool="Bash", command="pnpm install --frozen-lockfile"),
        )
    )
    assert blocked(
        invoke("deps-audit-gate", event(tool="Bash", command="pnpm rebuild"))
    )
    assert not (workspace / ".claude/deps-audit/last-run.json").exists()


def test_deps_gate_no_policy_is_advisory(invoke):
    result = invoke("deps-audit-gate", event(tool="Bash", command="pnpm install"))
    assert not blocked(result) and "advisory" in result.stdout
    assert not invoke(
        "deps-audit-gate", event(tool="Bash", command='echo "pnpm install"')
    ).stdout


def test_deps_valid_cache_contract(workspace, monkeypatch, capsys):
    write(
        workspace / "dependency-vet.json",
        {"schemaVersion": 1, "policy": {"block_on_unvetted": "strict"}},
    )
    context = hook.Context.create(
        {
            "cwd": str(workspace),
            **event(tool="Bash", command="pnpm install --frozen-lockfile"),
        }
    )
    calls = []

    def fake(argv, cwd, timeout):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"allowed":true}', "")

    monkeypatch.setattr(hook, "run", fake)
    assert hook.dependency_gate(context) == 0 and not capsys.readouterr().out
    assert "--gate-check" in calls[0]
    assert calls[0][-2:] == ["--gate-mode", "strict"]


def test_all_responsibilities_registered_once_per_event():
    config = json.loads((SCRIPTS.parent / "hooks.json").read_text())["hooks"]
    assert len(config) == 10
    registered = set()
    for groups in config.values():
        for group in groups:
            names = [Path(item["command"].split()[0]).stem for item in group["hooks"]]
            assert len(names) == len(set(names))
            registered.update(names)
    assert registered == set(hook.HANDLERS) and len(registered) == 23
    assert len(list(SCRIPTS.glob("*.sh"))) == 23


def test_stack_hooks_silent_outside_workspace(invoke, tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    for name in (
        "setup-dirs",
        "detect-domain-resources",
        "detect-runtime-tools",
        "inject-iron-laws",
        "check-format",
        "iron-law-verifier",
        "security-reminder",
        "typescript-failure-hints",
        "route-intent",
    ):
        payload = {
            **event("session.ts", "process.env.SECRET"),
            "prompt": "TypeError",
            "error": "TypeError",
        }
        result = invoke(name, payload, project=root, cwd=root)
        assert result.returncode == 0 and not result.stdout and not result.stderr, name
    assert not (root / ".claude").exists()


def test_workspace_root_recursive_and_package_script_resolution(invoke, workspace):
    assert blocked(
        invoke(
            "block-dangerous-ops",
            event(tool="Bash", command="pnpm -w db:push --force"),
            cwd=workspace / "apps/mobile",
        )
    )
    assert blocked(
        invoke(
            "block-dangerous-ops", event(tool="Bash", command="pnpm -r db:push --force")
        )
    )


def test_dependency_gate_rejects_duplicate_policy_keys(invoke, workspace):
    write(
        workspace / "dependency-vet.json",
        '{"policy":{"block_on_unvetted":"strict"},"policy":{"block_on_unvetted":"warn"}}',
    )
    assert blocked(
        invoke("deps-audit-gate", event(tool="Bash", command="pnpm install"))
    )


def test_redirect_with_valid_json_is_not_healthy(workspace, monkeypatch, capsys):
    context = runtime_fixture(workspace)
    data = {
        "data": {
            "status": "ok",
            "environment": "test",
            "uptimeSeconds": 2,
            "driver": "memory",
            "sessions": 0,
        }
    }
    monkeypatch.setattr(
        hook,
        "run",
        lambda argv, *args, **kwargs: subprocess.CompletedProcess(
            argv, 0, json.dumps(data) + "\n302", ""
        ),
    )
    hook.runtime_tools(context)
    assert "API health not confirmed" in capsys.readouterr().out


@pytest.mark.parametrize(
    "command",
    [
        "pnpm install --frozen-lockfile --registry=https://other.invalid",
        "pnpm --config.registry=https://other.invalid install --frozen-lockfile",
        "pnpm install --frozen-lockfile --config.onlyBuiltDependencies=other",
        "npm_config_registry=https://other.invalid pnpm install --frozen-lockfile",
        "env NODE_OPTIONS=--require=other pnpm rebuild",
        "pnpm --ignore-pnpmfile install --frozen-lockfile",
    ],
)
def test_deps_inline_policy_overrides_cannot_reuse_cache(
    workspace, monkeypatch, capsys, command
):
    write(
        workspace / "dependency-vet.json",
        {"schemaVersion": 1, "policy": {"block_on_unvetted": "strict"}},
    )

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "An old cache cannot certify an inline configuration override"
        )

    monkeypatch.setattr(hook, "run", forbidden)
    hook.dependency_gate(
        hook.Context.create(
            {"cwd": str(workspace), **event(tool="Bash", command=command)}
        )
    )
    result = json.loads(capsys.readouterr().out)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "overrides" in result["hookSpecificOutput"]["permissionDecisionReason"]


def test_deps_policy_override_propagates_from_script(workspace, monkeypatch, capsys):
    manifest = json.loads((workspace / "package.json").read_text())
    manifest["scripts"]["bootstrap"] = (
        "npm_config_registry=https://other.invalid pnpm install --frozen-lockfile"
    )
    write(workspace / "package.json", manifest)
    write(
        workspace / "dependency-vet.json",
        {"schemaVersion": 1, "policy": {"block_on_unvetted": "strict"}},
    )
    hook.dependency_gate(
        hook.Context.create(
            {"cwd": str(workspace), **event(tool="Bash", command="pnpm bootstrap")}
        )
    )
    assert (
        json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )


@pytest.mark.parametrize(
    "command",
    [
        "pnpm install --frozen-lockfile --no-frozen-lockfile",
        "pnpm install --frozen-lockfile --frozen-lockfile=false",
        "pnpm --no-frozen-lockfile install --frozen-lockfile",
        "pnpm install --frozen-lockfile --lockfile-dir=/tmp/other",
        "pnpm --lockfile-dir=/tmp/other install --frozen-lockfile",
        "pnpm install --frozen-lockfile --shared-workspace-lockfile=false",
        "pnpm install --frozen-lockfile --no-lockfile",
        "pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile --lockfile-only=false --ignore-scripts=false",
        "pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile --no-lockfile-only --no-ignore-scripts",
        "pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile=false",
        "pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile --no-ignore-scripts=true",
        "pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile --config.ignore-scripts=false",
        "NODE_OPTIONS=--require=other pnpm update --lockfile-only --ignore-scripts --ignore-pnpmfile",
        "pnpm install --frozen-lockfile --no-frozen-lockfile=true",
        "pnpm install --frozen-lockfile --lockfile=false",
        "pnpm --offline install --frozen-lockfile=false",
        "pnpm --reporter append-only install --frozen-lockfile=false",
        "pnpm --offline update --lockfile-only --ignore-scripts --ignore-pnpmfile --no-ignore-scripts",
    ],
)
def test_deps_contradictory_boolean_and_lock_overrides_cannot_bypass(
    workspace, monkeypatch, capsys, command
):
    write(
        workspace / "dependency-vet.json",
        {"schemaVersion": 1, "policy": {"block_on_unvetted": "strict"}},
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed lock semantics cannot reuse prior audit evidence")

    monkeypatch.setattr(hook, "run", forbidden)
    hook.dependency_gate(
        hook.Context.create(
            {"cwd": str(workspace), **event(tool="Bash", command=command)}
        )
    )
    assert (
        json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )


def test_deps_explicit_true_lock_preparation_remains_allowed(invoke):
    assert not invoke(
        "deps-audit-gate",
        event(
            tool="Bash",
            command="pnpm update --lockfile-only=true --ignore-scripts=true --ignore-pnpmfile=true",
        ),
    ).stdout

"""Offline semantic guardrails for the TypeScript starter harness."""

import json
import hashlib
from pathlib import Path
import re
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins/typescript-starter"
EXTERNAL = {"deps-audit", "deps-update", "deps-vet", "docs-fetcher"}


def test_skill_identity_and_selection():
    identity = json.loads((ROOT / "docs/quality/inventory.json").read_text())
    skills = list((PLUGIN / "skills").glob("*/SKILL.md"))
    assert len(skills) == 51
    hidden = 0
    for path in skills:
        metadata = yaml.safe_load(path.read_text().split("---", 2)[1])
        hidden += metadata.get("user-invocable") is False
        if path.parent.name in EXTERNAL:
            continue
        assert metadata["name"] == path.parent.name
        assert len(metadata["description"]) < 250
        assert metadata["effort"] in {"low", "medium", "high"}
    assert hidden == 11
    assert {p.parent.name for p in skills} == {record["name"] for record in identity["skills"]}


def test_current_inventory_covers_canonical_resources():
    from scripts.validate_harness import validate, validate_coverage

    assert validate(ROOT) == []
    assert validate_coverage(ROOT) == []


def test_resource_coverage_rejects_invalid_ownership_and_paths(tmp_path):
    from scripts.validate_harness import validate_coverage

    docs = tmp_path / "docs/quality"
    docs.mkdir(parents=True)
    reference = tmp_path / "docs/reference"
    reference.mkdir(parents=True)
    (reference / "starter-snapshot.json").write_text(json.dumps({"snapshotSha256": "captured"}))
    canonical = tmp_path / "plugins/typescript-starter/skills/example/SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("example")
    item = {
        "id": "example",
        "kind": "skill",
        "paths": ["../outside"],
        "status": "active",
        "evidencePaths": ["docs/quality/missing.md"],
    }
    (docs / "coverage.json").write_text(json.dumps({
        "schemaVersion": 2,
        "plugin": "typescript-starter",
        "starterSnapshotSha256": "different",
        "items": [item, item],
    }))
    errors = validate_coverage(tmp_path)
    for expected in ("snapshot differs", "duplicate resource id", "invalid paths entry",
                     "invalid evidencePaths entry", "multiple owners", "canonical resource missing"):
        assert any(expected in error for error in errors), expected


def test_architecture_does_not_invent_frameworks():
    expected = {
        "fastify-modules": ["SessionService", "AppContext", "registry", "routes.ts"],
        "domain-resources": ["TypeBox", "packages/types", "service", "authorization"],
        "drizzle-patterns": ["Postgres", "memory", "contract", "migration"],
        "react-patterns": ["Server Actions", "mobile", "REST", "SSE", "WS", "applySessionEvent"],
        "background-jobs": ["sequential", "batchSize", "lease", "idempot", "Postgres"],
        "runtime-inspection": ["HTTP", "OpenAPI", "logs", "SQL", "MCP"],
        "testing": ["Vitest", "inject", "Playwright", "mobile"],
    }
    for name, terms in expected.items():
        content = (PLUGIN / "skills" / name / "SKILL.md").read_text()
        for term in terms:
            assert term in content, (name, term)


def test_bounded_workflows_keep_their_contracts():
    expected = {
        "work": ["--from", "--continue", "--skip-blockers", "[Pn-Tm]", "scratchpad", "3 retries"],
        "full": ["--max-cycles", "--max-retries", "--max-blockers", "COMPOUNDING", "INCOMPLETE"],
        "review": ["--no-requirements", "--codex", "UNMET", "PARTIAL", "NOT AVAILABLE", "READ-ONLY"],
        "codex-loop": ["--base", "--uncommitted", "--max-rounds", "MAX ROUNDS REACHED"],
        "watch-pr": ["--checks-only", "--fix", "--codex-rounds", "codex_clean"],
        "plan": ["--existing", "--depth", "scratchpad", "planning-orchestrator"],
    }
    for name, terms in expected.items():
        content = (PLUGIN / "skills" / name / "SKILL.md").read_text()
        for term in terms:
            assert term in content, (name, term)


def test_agent_identity_and_distinct_roles():
    identity = json.loads((ROOT / "docs/quality/inventory.json").read_text())
    agents = list((PLUGIN / "agents").glob("*.md"))
    assert {p.stem for p in agents} == {record["name"] for record in identity["agents"]}
    for path in agents:
        metadata = yaml.safe_load(path.read_text().split("---", 2)[1])
        assert metadata["name"] == path.stem
    auth = (PLUGIN / "agents/authorization-reviewer.md").read_text()
    assert "clientId" in auth and "identity" in auth


def test_copied_examples_match_captured_starter_bytes():
    """Examples are actual source excerpts, including the captured local edits."""
    folder = PLUGIN / "skills/examples"
    examples = json.loads((folder / "references/starter-examples.json").read_text())
    snapshot = json.loads((ROOT / "docs/reference/starter-snapshot.json").read_text())
    hashes = {entry["path"]: entry["sha256"] for entry in snapshot["files"]}
    assert examples["starterSnapshotSha256"] == snapshot["snapshotSha256"]
    rendered = (folder / "references/starter-examples.md").read_text()
    required = {
        "typebox-contract": ("packages/types/src/schemas/session.ts", "packages/types/src/__tests__/session-inputs.test.ts"),
        "fastify-route": ("apps/api/src/modules/sessions/routes.ts", "apps/api/src/modules/sessions/__tests__/routes.test.ts"),
        "fastify-service": ("apps/api/src/modules/sessions/service.ts", "apps/api/src/modules/sessions/__tests__/service.test.ts"),
        "repository-memory": ("packages/db/src/memory-repository.ts", "packages/db/src/__tests__/repositories.test.ts"),
        "repository-postgres": ("packages/db/src/drizzle-repository.ts", "packages/db/src/__tests__/postgres.test.ts"),
        "server-action": ("apps/web/app/actions/actions.ts", "apps/web/lib/__tests__/action-results.test.ts"),
        "sse-update": ("apps/web/lib/session-stream.ts", "apps/web/lib/__tests__/session-stream.test.ts"),
        "mobile-service": ("apps/mobile/src/services/apiService.ts", "apps/mobile/src/services/__tests__/apiService.test.ts"),
        "mobile-store": ("apps/mobile/src/store/sessionsStore.ts", "apps/mobile/src/store/__tests__/sessionsStore.test.ts"),
        "mobile-hook": ("apps/mobile/src/screens/SessionDetail/useSessionDetail.ts", "apps/mobile/src/screens/SessionDetail/__tests__/useSessionDetail.test.ts"),
        "job-retry": ("apps/worker/src/runner.ts", "apps/worker/src/__tests__/runner.test.ts"),
        "job-idempotency": ("apps/worker/src/handlers/archive-session.ts", "apps/worker/src/handlers/__tests__/archive-session.test.ts"),
        "schema-migration": ("packages/db/drizzle/0004_session_revisions.sql", "packages/db/src/__tests__/postgres-session-migration.ts"),
    }
    runs = {run["id"]: run for run in examples["verificationRuns"]}
    assert len(runs) == len(examples["verificationRuns"])
    for run in runs.values():
        assert run["command"][:2] == ["pnpm", "--filter"]
        assert run["exitCode"] == 0 and run["passedTests"] > 0
        evidence = ROOT / run["evidencePath"]
        assert evidence.is_file() and run["id"] in evidence.read_text()
        for test_file in run["testFiles"]:
            assert test_file["sha256"] == hashes[test_file["path"]]
    observed = {}
    assert len({example["id"] for example in examples["examples"]}) == len(examples["examples"])
    for example in examples["examples"]:
        raw = (folder / example["fixturePath"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == example["sourceSha256"]
        assert example["sourceSha256"] == hashes[example["sourcePath"]]
        assert example["snippet"] in raw.decode()
        assert example["snippet"] in rendered
        covered_tests = {
            test_file["path"]
            for run_id in example["verificationRunIds"]
            for test_file in runs[run_id]["testFiles"]
        }
        assert covered_tests
        for category in example["categories"]:
            if category in required:
                source_path, test_path = required[category]
                assert example["sourcePath"] == source_path, category
                assert test_path in covered_tests, category
                observed[category] = example["id"]
    assert required.keys() <= observed.keys(), set(required) - set(observed)


def test_compression_preserves_later_failures_and_diagnostics():
    """Conservative filters cannot turn an early success into a whole-log pass."""
    path = PLUGIN / "skills/pnpm-compression/references/rtk-filters.toml"
    config = tomllib.loads(path.read_text())
    for name, definition in config["filters"].items():
        assert not definition.get("match_output")
        assert "tail_lines" not in definition
        patterns = [re.compile(p) for p in definition["strip_lines_matching"]]
        for fixture in config["tests"][name]:
            actual = "\n".join(
                line for line in fixture["input"].splitlines()
                if not any(pattern.search(line) for pattern in patterns)
            )
            assert actual == fixture["expected"]
            assert re.search(r"FAIL|error|warning|AssertionError", actual)


def test_bundled_reference_paths_resolve():
    for path in (PLUGIN / "skills").glob("*/SKILL.md"):
        if path.parent.name in EXTERNAL:
            continue
        for relative in re.findall(r"\]\((references/[^)#]+)(?:#[^)]+)?\)", path.read_text()):
            assert (path.parent / relative).is_file(), (path, relative)

from __future__ import annotations

from scripts.harness_lib.generated_tree import ignored_resource

import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from scripts import build_codex_skills
from scripts.harness_lib import SOURCE_PLUGIN_DIR, TARGETS_DIR
from scripts.harness_lib import codex
from scripts.harness_lib.frontmatter import parse_file
from scripts.harness_lib.generated_tree import tree_differences


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(stat.S_IMODE(path.stat().st_mode).to_bytes(2, "big"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_skill(
    root: Path,
    directory: str,
    name: str,
    body: str = "# Skill\n",
    description: str = "Use /ts:review for tests.",
) -> Path:
    manifest_dir = root / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = manifest_dir / "plugin.json"
    if not manifest_file.exists():
        manifest_file.write_text(
            json.dumps({"name": "fixture", "version": "1.2.3"}),
            encoding="utf-8",
        )
    skill_dir = root / "skills" / directory
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\neffort: high\n---\n\n{body}",
        encoding="utf-8",
    )
    return skill_dir


def test_builds_every_canonical_skill_without_mutating_claude_or_amp(tmp_path) -> None:
    source_before = _tree_hash(SOURCE_PLUGIN_DIR)
    amp_before = _tree_hash(TARGETS_DIR / "amp")
    output = tmp_path / "codex"

    result = codex.build(SOURCE_PLUGIN_DIR, output)
    discovered = codex.discover_skills(SOURCE_PLUGIN_DIR)

    assert result == {"skills": len(discovered)}
    assert len(discovered) == 51
    assert codex.validate(output) == len(discovered)
    assert {item.target_name for item in discovered} == {
        path.parent.name for path in (output / "skills").glob("*/SKILL.md")
    }
    assert _tree_hash(SOURCE_PLUGIN_DIR) == source_before
    assert _tree_hash(TARGETS_DIR / "amp") == amp_before


def test_complete_subtree_is_copied_and_only_markdown_is_transformed(tmp_path) -> None:
    plugin = tmp_path / "plugin"
    skill = _write_skill(
        plugin,
        "source",
        "ts:source",
        "Read `${CLAUDE_SKILL_DIR}/notes/guide.md` and run /ts:source.\n",
    )
    (skill / "notes").mkdir()
    (skill / "notes" / "guide.md").write_text(
        "Use /ts:source and /drizzle:n1-check.\n", encoding="utf-8"
    )
    (skill / "notes" / "guide.md").chmod(0o744)
    payload = b"\x00\xff\x10"
    (skill / "assets").mkdir()
    (skill / "assets" / "payload.bin").write_bytes(payload)
    executable = skill / "scripts" / "run.sh"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    output = tmp_path / "codex"
    codex.build(plugin, output)
    generated = output / "skills" / "ts-source"

    assert (generated / "assets" / "payload.bin").read_bytes() == payload
    assert stat.S_IMODE((generated / "scripts" / "run.sh").stat().st_mode) == 0o755
    assert "$typescript-starter:ts-source" in (generated / "SKILL.md").read_text()
    assert (
        "$typescript-starter:ts-source" in (generated / "notes" / "guide.md").read_text()
    )
    assert (
        "$typescript-starter:drizzle-n1-check"
        in (generated / "notes" / "guide.md").read_text()
    )
    assert stat.S_IMODE((generated / "notes" / "guide.md").stat().st_mode) == 0o744
    assert "notes/guide.md" in (generated / "SKILL.md").read_text()
    assert set(
        path.relative_to(skill) for path in skill.rglob("*") if path.is_file()
    ) == {
        path.relative_to(generated) for path in generated.rglob("*") if path.is_file()
    }


def test_frontmatter_and_all_markdown_use_codex_invocation_syntax(tmp_path) -> None:
    plugin = tmp_path / "plugin"
    skill = _write_skill(
        plugin,
        "source",
        "ts:source",
        "Use /ts:review, /react:state-audit, and /drizzle:n1-check.\n",
    )
    (skill / "references").mkdir()
    (skill / "references" / "guide.md").write_text(
        "Use /ts:review.\n", encoding="utf-8"
    )

    output = tmp_path / "codex"
    codex.build(plugin, output)
    generated = output / "skills" / "ts-source" / "SKILL.md"
    frontmatter = parse_file(generated)

    assert frontmatter.data == {
        "name": "ts-source",
        "description": "Use $typescript-starter:ts-review for tests.",
    }
    all_markdown = "\n".join(
        path.read_text(encoding="utf-8") for path in output.rglob("*.md")
    )
    assert "$typescript-starter:ts-review" in all_markdown
    assert "$typescript-starter:react-state-audit" in all_markdown
    assert "$typescript-starter:drizzle-n1-check" in all_markdown
    assert not any(token in all_markdown for token in ("$ts-", "$react-", "$drizzle-"))
    assert not any(token in all_markdown for token in ("/ts:", "/react:", "/drizzle:"))


def test_codex_descriptions_preserve_summary_and_trigger_within_budget() -> None:
    description = (
        "Audit npm dependencies for supply-chain security risks including bidirectional "
        "characters, compile-time execution, maintainer changes, typosquats, and CVEs. "
        "Use after pnpm update or when reviewing dependency changes."
    )

    compact = codex.compact_skill_description(description)

    assert len(compact) <= codex.CODEX_SKILL_DESCRIPTION_LIMIT
    assert compact.startswith("Audit npm dependencies for supply-chain security risks")
    assert "Use after pnpm update" in compact
    assert codex.compact_skill_description(compact) == compact


def test_codex_plugin_skill_mentions_are_qualified_as_complete_tokens() -> None:
    source = (
        "Use $ts-review, $react-state-audit, $drizzle-n1-check, and $ts-*. "
        "Keep $other:ts-review and prefix$ts-review unchanged."
    )

    assert codex._qualify_codex_skill_mentions(source, "typescript-starter") == (
        "Use $typescript-starter:ts-review, $typescript-starter:react-state-audit, "
        "$typescript-starter:drizzle-n1-check, and $typescript-starter:ts-*. "
        "Keep $other:ts-review and prefix$ts-review unchanged."
    )


def test_namespace_expansion_wraps_only_affected_prose() -> None:
    prose = "- " + ("word " * 37) + "$typescript-starter:ts-review result\n"
    fenced = "```text\n" + ("word " * 45) + "$typescript-starter:ts-review\n```\n"

    wrapped = codex._wrap_namespace_expanded_lines(prose + fenced, "typescript-starter")
    prose_output, fenced_output = wrapped.split("```text\n", maxsplit=1)

    assert max(map(len, prose_output.splitlines())) <= 200
    assert "\n  " in prose_output
    assert fenced_output == fenced.removeprefix("```text\n")


@pytest.mark.parametrize(
    ("skill_name", "required"),
    [
        ("drizzle-n1-check", "not for broad database performance"),
        (
            "ts-deps-update",
            "$typescript-starter:ts-investigate for install failures",
        ),
        ("ts-deps-vet", "not to scan them"),
        ("ts-document", "Not for docs lookup"),
        ("ts-full", "$typescript-starter:ts-work for an existing plan"),
        ("ts-help", "not for Codex /help"),
        ("ts-investigate", "Codex subagents are optional"),
        ("ts-review", "return a verdict"),
    ],
)
def test_route_sensitive_codex_descriptions_remain_complete(
    skill_name: str, required: str
) -> None:
    skill = parse_file(TARGETS_DIR / "codex" / "skills" / skill_name / "SKILL.md")
    description = skill.data["description"]

    expected = codex._qualify_codex_skill_mentions(
        codex.CODEX_SKILL_DESCRIPTION_OVERRIDES[skill_name], "typescript-starter"
    )
    assert description == expected
    assert required in description
    assert len(description) <= codex.CODEX_SKILL_DESCRIPTION_LIMIT


def test_repository_codex_descriptions_reduce_catalog_pressure() -> None:
    canonical = codex.discover_skills(SOURCE_PLUGIN_DIR)
    generated = [
        parse_file(path).data["description"]
        for path in sorted((TARGETS_DIR / "codex" / "skills").glob("*/SKILL.md"))
    ]
    canonical_chars = sum(
        len(str(skill.frontmatter.data["description"])) for skill in canonical
    )

    assert len(generated) == len(canonical)
    assert all(
        1 <= len(description) <= codex.CODEX_SKILL_DESCRIPTION_LIMIT
        for description in generated
    )
    assert all(description == description.strip() for description in generated)
    assert not any(
        description.removesuffix("…").rsplit(maxsplit=1)[-1].lower()
        in codex.DESCRIPTION_DANGLING_WORDS
        for description in generated
    )
    assert sum(map(len, generated)) <= 6_000
    assert sum(map(len, generated)) <= canonical_chars * 0.7


def test_rewrites_cross_skill_resources_and_rejects_missing_or_escaping_paths(
    tmp_path,
) -> None:
    plugin = tmp_path / "plugin"
    _write_skill(
        plugin,
        "first",
        "ts:first",
        "Read `${CLAUDE_SKILL_DIR}/../second/references/guide.md`.\n",
    )
    second = _write_skill(plugin, "second", "ts:second")
    (second / "references").mkdir()
    (second / "references" / "guide.md").write_text("Guide\n", encoding="utf-8")
    first_references = plugin / "skills" / "first" / "references"
    first_references.mkdir()
    (first_references / "nested.md").write_text(
        "Read `second/references/guide.md`.\n",
        encoding="utf-8",
    )

    output = tmp_path / "codex"
    codex.build(plugin, output)
    assert (
        "../ts-second/references/guide.md"
        in (output / "skills" / "ts-first" / "SKILL.md").read_text()
    )
    assert (
        "../../ts-second/references/guide.md"
        in (output / "skills" / "ts-first" / "references" / "nested.md").read_text()
    )

    missing = tmp_path / "missing"
    broken = _write_skill(
        missing,
        "broken",
        "ts:broken",
        "Read `${CLAUDE_SKILL_DIR}/references/missing.md`.\n",
    )
    with pytest.raises(ValueError, match=str(broken / "SKILL.md")):
        codex.build(missing, tmp_path / "missing-output")

    escaping = tmp_path / "escaping"
    bad = _write_skill(
        escaping,
        "bad",
        "ts:bad",
        "Read `${CLAUDE_SKILL_DIR}/../../secret.md`.\n",
    )
    (escaping / "secret.md").write_text("secret\n", encoding="utf-8")
    with pytest.raises(ValueError, match=str(bad / "SKILL.md")):
        codex.build(escaping, tmp_path / "escaping-output")


def test_normalized_names_are_valid_unique_and_collisions_preserve_target(
    tmp_path,
) -> None:
    plugin = tmp_path / "plugin"
    _write_skill(plugin, "first", "ts:plan")
    _write_skill(plugin, "second", "ts-plan")
    output = tmp_path / "codex"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("unchanged", encoding="utf-8")

    with pytest.raises(ValueError, match="collision.*ts-plan"):
        codex.build(plugin, output)

    assert sentinel.read_text(encoding="utf-8") == "unchanged"


def test_build_rejects_symlinked_resources(tmp_path) -> None:
    plugin = tmp_path / "plugin"
    skill = _write_skill(plugin, "one", "ts:one")
    outside = tmp_path / "outside.txt"
    outside.write_text("must not be packaged\n", encoding="utf-8")
    (skill / "linked.txt").symlink_to(outside)

    with pytest.raises(ValueError, match="linked.txt.*symlinks are not supported"):
        codex.build(plugin, tmp_path / "codex")


def test_projection_is_deterministic_byte_for_byte_and_mode_for_mode(tmp_path) -> None:
    plugin = tmp_path / "plugin"
    skill = _write_skill(plugin, "one", "ts:one")
    script = skill / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    first = tmp_path / "first"
    second = tmp_path / "second"

    codex.build(plugin, first)
    codex.build(plugin, second)

    assert _tree_hash(first) == _tree_hash(second)
    assert tree_differences(first, second) == []


def test_drift_comparison_detects_added_removed_and_type_changes(tmp_path) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    (expected / "missing.txt").write_text("missing\n", encoding="utf-8")
    (actual / "extra.txt").write_text("extra\n", encoding="utf-8")
    (expected / "node").write_text("file\n", encoding="utf-8")
    (actual / "node").mkdir()

    assert tree_differences(expected, actual) == [
        "extra in target: extra.txt",
        "missing in target: missing.txt",
        "type differs: node (file != directory)",
    ]


def test_build_restores_previous_target_when_installation_fails(
    tmp_path, monkeypatch
) -> None:
    plugin = tmp_path / "plugin"
    _write_skill(plugin, "one", "ts:one")
    output = tmp_path / "codex"
    codex.build(plugin, output)
    before = _tree_hash(output)
    original_rename = Path.rename

    def fail_replacement(self, target):
        if self.name == "replacement" and Path(target) == output:
            raise OSError("simulated installation failure")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", fail_replacement)
    with pytest.raises(OSError, match="simulated installation failure"):
        codex.build(plugin, output)

    assert _tree_hash(output) == before
    assert not list(output.parent.glob(".codex.backup-*"))


def test_drift_check_is_read_only_and_detects_content_and_mode(
    tmp_path, monkeypatch
) -> None:
    plugin = tmp_path / "plugin"
    skill = _write_skill(plugin, "one", "ts:one")
    script = skill / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    output = tmp_path / "codex"
    codex.build(plugin, output)
    monkeypatch.setattr(build_codex_skills, "SOURCE_PLUGIN_DIR", plugin)
    monkeypatch.setattr(build_codex_skills, "OUTPUT_DIR", output)
    before = _tree_hash(output)

    assert build_codex_skills.check() == 0
    assert _tree_hash(output) == before

    generated_script = output / "skills" / "ts-one" / "run.sh"
    generated_script.chmod(0o644)
    mode_drift = _tree_hash(output)
    assert build_codex_skills.check() == 1
    assert _tree_hash(output) == mode_drift

    generated_script.chmod(0o755)
    skill_file = output / "skills" / "ts-one" / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "drift\n", encoding="utf-8")
    content_drift = _tree_hash(output)
    assert build_codex_skills.check() == 1
    assert _tree_hash(output) == content_drift


def test_manifests_are_conformant_and_every_declared_path_resolves() -> None:
    root = TARGETS_DIR.parent
    target = TARGETS_DIR / "codex"
    plugin_manifest = json.loads(
        (target / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    canonical_manifest = json.loads(
        (SOURCE_PLUGIN_DIR / ".claude-plugin" / "plugin.json").read_text(
            encoding="utf-8"
        )
    )
    marketplace = json.loads(
        (root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )

    assert plugin_manifest["skills"] == "./skills/"
    assert canonical_manifest["name"] == "ts"
    assert plugin_manifest["name"] == codex.CODEX_PLUGIN_NAME == "typescript-starter"
    assert plugin_manifest["version"] == canonical_manifest["version"]
    assert "skills" not in plugin_manifest.get("interface", {})
    assert "agents" not in plugin_manifest
    assert "commands" not in plugin_manifest
    assert (target / plugin_manifest["skills"]).is_dir()

    [entry] = marketplace["plugins"]
    assert entry["name"] == plugin_manifest["name"]
    assert entry["source"] == {"source": "local", "path": "./targets/codex"}
    assert (root / entry["source"]["path"]).resolve() == target.resolve()
    assert (root / entry["source"]["path"] / ".codex-plugin/plugin.json").is_file()


def test_repository_hook_is_native_synchronous_and_projects_source(tmp_path) -> None:
    target = TARGETS_DIR / "codex"
    hooks_file = target / "hooks" / "hooks.json"
    hooks = json.loads(hooks_file.read_text(encoding="utf-8"))
    [group] = hooks["hooks"]["PreToolUse"]
    [handler] = group["hooks"]

    assert hooks == codex.CODEX_HOOKS
    assert group["matcher"] == "Bash"
    assert handler["type"] == "command"
    assert handler["command"].startswith('"${PLUGIN_ROOT}/')
    assert "async" not in handler
    assert "if" not in handler

    source = SOURCE_PLUGIN_DIR / "hooks" / "scripts" / codex.CODEX_HOOK_SCRIPT
    generated = target / "hooks" / "scripts" / codex.CODEX_HOOK_SCRIPT
    assert generated.read_text(encoding="utf-8") == source.read_text(
        encoding="utf-8"
    ).replace("Claude Code", "Codex").replace("Claude's", "Codex's")
    helper = generated.parent / "hook_runtime.py"
    assert helper.is_file() and not helper.is_symlink()
    assert helper.read_bytes() == (source.parent / helper.name).read_bytes()
    assert stat.S_IMODE(generated.stat().st_mode) == stat.S_IMODE(source.stat().st_mode)
    assert os.access(generated, os.X_OK)

    plugin_root = tmp_path / "plugin root with spaces"
    shutil.copytree(target / "hooks", plugin_root / "hooks")
    command = handler["command"].replace("${PLUGIN_ROOT}", str(plugin_root))
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "package.json").write_text(
        '{"name":"fixture","devDependencies":{"typescript":"5.7.3"},'
        '"scripts":{"db:push":"drizzle-kit push"}}\n'
    )
    (fixture / "pnpm-workspace.yaml").write_text('packages: []\n')
    (fixture / "turbo.json").write_text('{}\n')
    environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(fixture)}
    blocked = subprocess.run(
        ["/bin/bash", "-lc", command],
        input=json.dumps(
            {"cwd": str(fixture), "tool_name": "Bash", "tool_input": {"command": "pnpm db:push --force"}}
        ),
        text=True,
        capture_output=True,
        cwd=fixture,
        env=environment,
        check=True,
    )
    output = json.loads(blocked.stdout)
    assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert output["hookSpecificOutput"]["permissionDecisionReason"]
    assert output["hookSpecificOutput"]["additionalContext"]

    safe = subprocess.run(
        ["/bin/bash", "-lc", command],
        input=json.dumps({"cwd": str(fixture), "tool_name": "Bash", "tool_input": {"command": "pnpm db:push"}}),
        text=True,
        capture_output=True,
        cwd=fixture,
        env=environment,
        check=True,
    )
    assert safe.stdout == ""

    installed_script = plugin_root / "hooks" / "scripts" / codex.CODEX_HOOK_SCRIPT
    installed_script.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    installed_script.chmod(0o755)
    failed_open = subprocess.run(
        ["/bin/bash", "-lc", command],
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "pnpm db:push"}}
        ),
        text=True,
        capture_output=True,
        cwd=fixture,
        check=True,
    )
    assert failed_open.stdout == ""

    bin_dir = tmp_path / "bin-without-python"
    bin_dir.mkdir()
    (bin_dir / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
    missing_python = subprocess.run(
        [str(generated)],
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "pnpm db:push"}}
        ),
        text=True,
        capture_output=True,
        cwd=fixture,
        env={**os.environ, "PATH": str(bin_dir)},
        check=True,
    )
    assert missing_python.stdout == "" and missing_python.stderr == ""

    # JSON is parsed by the stdlib helper; jq is no longer a dependency.
    (bin_dir / "python3").symlink_to(shutil.which("python3"))
    (bin_dir / "dirname").symlink_to(shutil.which("dirname"))
    without_jq = subprocess.run(
        [str(generated)],
        input=json.dumps({"cwd": str(fixture), "tool_name": "Bash", "tool_input": {"command": "pnpm db:push --force"}}),
        text=True,
        capture_output=True,
        cwd=fixture,
        env={**environment, "PATH": str(bin_dir)},
        check=True,
    )
    assert json.loads(without_jq.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_flagship_overlays_are_anchored_and_remove_claude_runtime_dependencies() -> (
    None
):
    target = TARGETS_DIR / "codex" / "skills"
    investigate = (target / "ts-investigate" / "SKILL.md").read_text()
    review = (target / "ts-review" / "SKILL.md").read_text()
    review_agents = (
        target / "ts-review" / "references" / "agent-spawning.md"
    ).read_text()
    review_requirements = (
        target / "ts-review" / "references" / "requirements-detection.md"
    ).read_text()
    investigate_patterns = (
        target / "ts-investigate" / "references" / "error-patterns.md"
    ).read_text()
    investigate_template = (
        target / "ts-investigate" / "references" / "investigation-template.md"
    ).read_text()
    trace = (target / "ts-trace" / "SKILL.md").read_text()
    audit = (target / "ts-audit" / "SKILL.md").read_text()
    research = (target / "ts-research" / "SKILL.md").read_text()

    assert "$typescript-starter:ts-investigate" in investigate
    assert "Reproduce Before Fixing" in investigate
    assert "Runtime probing is optional" in investigate
    assert "$typescript-starter:ts-review" in review
    assert "Review is read-only" in review
    assert "sequential review is fully valid" in review
    assert "optional performance optimization" in review_agents
    assert "Mark `NOT AVAILABLE` and continue" in review_requirements
    assert "generic read-only subagent" in investigate_patterns
    assert "Only when the user explicitly authorizes" in investigate_patterns
    assert "do not write a report file" in investigate_template
    assert "same-session sequential path is fully supported" in trace
    assert "named custom agent" in trace
    assert "Portable Audit Workflow" in audit
    assert "Never require named custom agents" in audit
    assert "Portable Research Workflow" in research
    assert "same-session sequential path must remain complete" in research

    combined = (
        investigate
        + review
        + review_agents
        + review_requirements
        + investigate_patterns
        + investigate_template
        + trace
        + audit
        + research
    )
    forbidden = (
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
        "AskUserQuestion",
        "subagent_type",
        "$ARGUMENTS",
        "mcp__",
        "mcp__linear__",
        "${CODEX_PLUGIN_ROOT}",
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH",
        "Agent(",
    )
    assert not any(token in combined for token in forbidden)


def test_plan_work_overlays_are_portable_resumable_and_anchored(tmp_path) -> None:
    generated = tmp_path / "codex"
    codex.build(SOURCE_PLUGIN_DIR, generated)
    target = generated / "skills"
    plan_tree = "\n".join(
        path.read_text() for path in (target / "ts-plan").rglob("*.md")
    )
    work_tree = "\n".join(
        path.read_text() for path in (target / "ts-work").rglob("*.md")
    )

    assert "Research checklist" in plan_tree
    assert "perform the same tracks sequentially" in plan_tree
    assert ".claude/plans/{feature-slug}/plan.md" in plan_tree
    assert "Use the plan file as the portable task list" in work_tree
    assert "progress.md" in work_tree
    assert "execute every task sequentially" in work_tree
    assert "pnpm check-types" in work_tree
    assert "[BLOCKED]" in work_tree
    assert "first unchecked task not tagged `[BLOCKED]`" in work_tree
    assert "clears `[BLOCKED]` when starting" in work_tree
    assert "append-only" in work_tree
    assert "**Started**:" in work_tree
    forbidden = (
        "Agent(",
        "subagent_type",
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
        "AskUserQuestion",
        "$ARGUMENTS",
        "mcp__",
        "PostToolUse hook",
        "starter-patterns-analyst",
        "drizzle-schema-designer",
        "react-architect",
        "background-jobs-specialist",
        "node-runtime-advisor",
        "security-analyzer",
        "testing-reviewer",
        "npm-library-researcher",
        "web-researcher",
        "call-tracer",
        "planning-orchestrator",
        "Spawn SPECIALIST",
        "run_in_background",
        "[agent]",
        "Agent annotation",
        "agent routing",
        "project_eval",
        "get_logs",
        "| Hook |",
        "Each hook",
        "/commit",
        "${CLAUDE_SKILL_DIR}",
        "${CLAUDE_PLUGIN_ROOT}",
        "spawning TypeScript specialist agents",
        "Spawns TypeScript specialist agents",
        "skip to agents",
        "Spawn agents selectively",
        "while agents still running",
        "agent spawning",
        "agent count",
        "Explore agents",
        "execute via subagents",
        "After spawning",
    )
    assert not any(token in plan_tree + work_tree for token in forbidden)

    plugin = tmp_path / "plugin"
    skill = _write_skill(plugin, "plan", "ts:plan", "# Plan TypeScript starter Feature\n")
    current = codex.discover_skills(plugin)[0]
    with pytest.raises(ValueError, match="portable plan overlay anchors changed"):
        codex._codex_overlay(skill / "SKILL.md", current)

    with pytest.raises(ValueError, match="heading order changed"):
        codex._replace_section("## End\n## Start\n", "## Start", "## End", "", skill)

    with pytest.raises(ValueError, match="canonical marker order changed"):
        codex._assert_ordered_markers("## Two\n## One\n", ("## One", "## Two"), skill)


def test_pr_review_full_overlays_are_portable_and_anchored(tmp_path) -> None:
    generated = tmp_path / "codex"
    codex.build(SOURCE_PLUGIN_DIR, generated)
    skills = generated / "skills"
    pr_review = "\n".join(
        p.read_text() for p in (skills / "ts-pr-review").rglob("*.md")
    )
    full = "\n".join(p.read_text() for p in (skills / "ts-full").rglob("*.md"))
    assert "gh auth status" in pr_review
    assert "originalLine" in pr_review
    assert "query($threadId: ID!, $endCursor: String)" in pr_review
    assert "comments(first:100, after:$endCursor)" in pr_review
    assert "pageInfo { hasNextPage endCursor }" in pr_review
    assert "deduplicate by GraphQL `id`" in pr_review and "Block triage" in pr_review
    assert all(f"Gate {gate}" in pr_review for gate in range(1, 5))
    assert "EDIT: NOT APPLICABLE" in pr_review and "`--fix` approves none" in pr_review
    assert "NOT POSTED" in pr_review
    assert "$endCursor: String" in pr_review
    assert "after: $endCursor" in pr_review
    assert pr_review.count("--paginate") >= 2
    assert "comments.totalCount > nodes.length" in pr_review
    outer_query = pr_review.split("gh api graphql --paginate", 2)[1]
    outer_query = outer_query.split("gh api graphql --paginate", 1)[0]
    assert outer_query.count("pageInfo { hasNextPage endCursor }") == 1
    assert "comments(first: 100)" in outer_query
    assert "author.__typename" in pr_review
    assert "Outdated means location drift" in pr_review
    assert "CHANGES_REQUESTED" in pr_review and "zero inline" in pr_review
    assert "confirm the post" in pr_review and "`--no-resolve` always" in pr_review
    assert "same-session" in pr_review and "processing is complete" in pr_review
    assert "discover → plan → work → verify → read-only review" in full
    assert "Honor user gates" in full
    assert "--max-cycles" in full and "--max-retries" in full
    assert "Runtime probing is optional" in full
    assert "sole state authority" in full and "append-only" in full
    assert all(
        field in full
        for field in (
            "`seq`",
            "`phase_visit`",
            "`phase`",
            "`cycle`",
            "`task`",
            "`task_attempt`",
            "`blockers`",
            "`outcome`",
        )
    )
    assert "next legal phase is VERIFYING" in full
    assert "Completion requires all required plan tasks checked" in full
    assert "latest VERIFYING PASS after the last edit" in full
    assert "latest accepted REVIEWING after" in full
    assert "COMPOUNDING passed or explicitly skipped" in full
    assert "REVIEWING → COMPOUNDING → COMPLETED" in full
    assert "task retry, and blocker counters" in full
    assert "COMPOUNDING SKIPPED" in full
    assert "Do not\n   invoke `ts-compound`" in full
    forbidden = (
        "Agent(",
        "TaskCreate",
        "AskUserQuestion",
        "mcp__",
        "run_in_background",
        "Ralph Wiggum",
        "workflow-orchestrator",
    )
    assert not any(token in pr_review + full for token in forbidden)

    plugin = tmp_path / "plugin"
    skill = _write_skill(
        plugin,
        "full",
        "ts:full",
        "# Full Fastify Feature Development\n## State Machine\n",
    )
    current = codex.discover_skills(plugin)[0]
    with pytest.raises(ValueError, match="wholesale portable overlay source changed"):
        codex._codex_overlay(skill / "SKILL.md", current)

    canonical_pr = SOURCE_PLUGIN_DIR / "skills/pr-review/SKILL.md"
    original = canonical_pr.read_text()
    canonical_pr.write_text(original.replace("## Step 1:", "## Step one:", 1))
    try:
        current = next(
            s
            for s in codex.discover_skills(SOURCE_PLUGIN_DIR)
            if s.target_name == "ts-pr-review"
        )
        with pytest.raises(
            ValueError, match="wholesale portable overlay source changed"
        ):
            codex._codex_overlay(canonical_pr, current)
    finally:
        canonical_pr.write_text(original)

    canonical_ref = SOURCE_PLUGIN_DIR / "skills/full/references/execution-steps.md"
    original = canonical_ref.read_text()
    canonical_ref.write_text(original.replace("## Step 1:", "## Step one:", 1))
    try:
        current = next(
            s
            for s in codex.discover_skills(SOURCE_PLUGIN_DIR)
            if s.target_name == "ts-full"
        )
        with pytest.raises(
            ValueError, match="wholesale portable overlay source changed"
        ):
            codex._codex_overlay(canonical_ref, current)
    finally:
        canonical_ref.write_text(original)

    assert not any(
        token in pr_review + full for token in ("--codex", "--Pi", "--OpenCode")
    )
    assert "specialist agents" not in (skills / "ts-full/SKILL.md").read_text()


def test_repository_target_has_no_unresolved_claude_tokens() -> None:
    markdown = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (TARGETS_DIR / "codex").rglob("*.md")
    )
    assert not any(
        token in markdown
        for token in (
            "${CLAUDE_SKILL_DIR}",
            "${CLAUDE_PLUGIN_ROOT}",
            "${CODEX_PLUGIN_ROOT}",
            "/ts:",
            "/react:",
            "/drizzle:",
            "$ts-",
            "$react-",
            "$drizzle-",
        )
    )


def test_repository_non_markdown_bytes_and_modes_match_canonical_source() -> None:
    output = TARGETS_DIR / "codex" / "skills"
    for skill in codex.discover_skills(SOURCE_PLUGIN_DIR):
        generated = output / skill.target_name
        for source in skill.source_dir.rglob("*"):
            if source.is_dir() or ignored_resource(source, skill.source_dir, codex.IGNORED_FILES):
                continue
            target = generated / source.relative_to(skill.source_dir)
            assert target.is_file(), f"missing packaged resource: {target}"
            if source.suffix.lower() != ".md":
                assert target.read_bytes() == source.read_bytes()
                assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(
                    source.stat().st_mode
                )

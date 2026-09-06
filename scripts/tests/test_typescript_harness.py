from scripts.harness_lib import SOURCE_PLUGIN_DIR
from scripts.harness_lib.skill_transforms import (
    portable_skill_name,
    rewrite_slash_commands,
)


def test_canonical_source_is_the_typescript_plugin():
    assert SOURCE_PLUGIN_DIR.name == "typescript-starter"
    assert (SOURCE_PLUGIN_DIR / "skills" / "typescript-idioms" / "SKILL.md").is_file()


def test_public_workflows_and_specialists_have_distinct_portable_names():
    cases = {
        "plan": "ts-plan",
        "deploy": "ts-deploy",
        "docs-fetcher": "ts-docs-fetcher",
        "narrow-catch": "ts-narrow-catch",
        "pnpm-compression": "ts-pnpm-compression",
        "drizzle-n1-check": "drizzle-n1-check",
        "drizzle-constraint-debug": "drizzle-constraint-debug",
        "react-state-audit": "react-state-audit",
        "typescript-idioms": "typescript-idioms",
        "fastify-modules": "fastify-modules",
    }
    for directory, expected in cases.items():
        assert portable_skill_name(directory, directory) == expected


def test_cross_runtime_invocations_cover_all_three_namespaces():
    source = "Use /ts:review, /drizzle:n1-check and /react:state-audit."
    expected = {
        "codex": "Use $ts-review, $drizzle-n1-check and $react-state-audit.",
        "pi": "Use /skill:ts-review, /skill:drizzle-n1-check and /skill:react-state-audit.",
    }
    for target, text in expected.items():
        assert rewrite_slash_commands(source, target) == text


def test_canonical_specialist_commands_resolve_to_the_same_alias():
    for target in ("amp", "codex", "pi", "opencode"):
        for canonical, alias in (
            ("drizzle-n1-check", "/drizzle:n1-check"),
            ("drizzle-constraint-debug", "/drizzle:constraint-debug"),
            ("react-state-audit", "/react:state-audit"),
        ):
            assert rewrite_slash_commands(
                "/ts:" + canonical, target
            ) == rewrite_slash_commands(alias, target)


def test_manifest_validation_accepts_a_consistent_new_release(tmp_path):
    import json
    import shutil
    from scripts.harness_lib import REPO_ROOT
    from scripts.validate_harness import validate

    for relative in ("plugins", "docs/quality", ".claude-plugin"):
        shutil.copytree(
            REPO_ROOT / relative,
            tmp_path / relative,
            ignore=shutil.ignore_patterns("__pycache__", "node_modules", "test-assets"),
        )
    shutil.copy2(REPO_ROOT / "package.json", tmp_path / "package.json")
    manifests = [tmp_path / "package.json"] + [
        tmp_path / f"plugins/{name}/.claude-plugin/plugin.json"
        for name in ("typescript-starter", "drizzle", "react")
    ]
    for manifest in manifests:
        data = json.loads(manifest.read_text())
        data["version"] = "1.1.0"
        manifest.write_text(json.dumps(data))
    marketplace = tmp_path / ".claude-plugin/marketplace.json"
    data = json.loads(marketplace.read_text())
    data["metadata"]["version"] = "1.1.0"
    marketplace.write_text(json.dumps(data))
    assert validate(tmp_path) == []
    manifest = manifests[-1]
    data = json.loads(manifest.read_text())
    data["version"] = "1.0.0"
    manifest.write_text(json.dumps(data))
    assert any("incorrect plugin identity" in error for error in validate(tmp_path))

from __future__ import annotations

import pytest

from scripts.harness_lib.skill_transforms import (
    inline_iron_laws,
    normalize_skill_name,
    portable_skill_name,
    port_references,
    rewrite_reference_paths,
    rewrite_slash_commands,
    transform_frontmatter,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("ts:plan", "ts-plan"),
        ("react:state-audit", "react-state-audit"),
        ("drizzle:n1-check", "drizzle-n1-check"),
        ("react-patterns", "react-patterns"),
        ("", ""),
    ],
)
def test_normalize_skill_name(source: str, expected: str) -> None:
    assert normalize_skill_name(source) == expected


@pytest.mark.parametrize(
    ("directory", "command", "expected"),
    [
        ("plan", "plan", "ts-plan"),
        ("react-state-audit", "react-state-audit", "react-state-audit"),
        ("drizzle-constraint-debug", "drizzle-constraint-debug", "drizzle-constraint-debug"),
        ("drizzle-n1-check", "drizzle-n1-check", "drizzle-n1-check"),
    ],
)
def test_portable_skill_name(directory: str, command: str, expected: str) -> None:
    assert portable_skill_name(directory, command) == expected


def test_claude_frontmatter_is_preserved() -> None:
    data = {
        "name": "ts:plan",
        "description": "Use after /ts:review.",
        "effort": "high",
        "paths": ["**/*.ts"],
    }

    transformed = transform_frontmatter(data, "claude")

    assert transformed == data
    assert transformed is not data


@pytest.mark.parametrize("target", ["codex", "pi", "opencode"])
def test_non_claude_frontmatter_drops_claude_extensions(target: str) -> None:
    data = {
        "name": "ts:plan",
        "description": "Use after /ts:review.",
        "compatibility": "Requires TypeScript",
        "metadata": {"author": "example"},
        "effort": "high",
        "paths": ["**/*.ts"],
    }

    transformed = transform_frontmatter(data, target)

    assert transformed["name"] == "ts-plan"
    assert transformed["compatibility"] == "Requires TypeScript"
    assert transformed["metadata"] == {"author": "example"}
    assert "effort" not in transformed
    assert "paths" not in transformed
    assert "/ts:review" not in transformed["description"]


def test_amp_frontmatter_omits_claude_extensions() -> None:
    transformed = transform_frontmatter(
        {
            "name": "ts:plan",
            "description": "Use after /ts:review.",
            "effort": "high",
        },
        "amp",
    )

    assert transformed == {
        "name": "ts-plan",
        "description": "Use after ts-review.",
    }


def test_non_claude_frontmatter_rejects_non_string_metadata() -> None:
    with pytest.raises(ValueError, match="string-to-string mapping"):
        transform_frontmatter(
            {"name": "testing", "metadata": {"paths": ["**/*.ts"]}},
            "codex",
        )


def test_transform_frontmatter_rejects_unknown_target() -> None:
    with pytest.raises(ValueError, match="Unknown target: other"):
        transform_frontmatter({"name": "testing"}, "other")


def test_reference_paths_are_relative_outside_claude() -> None:
    body = "Read `${CLAUDE_SKILL_DIR}/references/nested/example.md`."

    assert rewrite_reference_paths(body, "codex") == (
        "Read `references/nested/example.md`."
    )
    assert rewrite_reference_paths(body, "claude") == body


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("claude", "Run /ts:plan, /react:state-audit, and /drizzle:n1-check."),
        ("amp", "Run ts-plan, react-state-audit, and drizzle-n1-check."),
        ("codex", "Run $ts-plan, $react-state-audit, and $drizzle-n1-check."),
        ("pi", "Run /skill:ts-plan, /skill:react-state-audit, and /skill:drizzle-n1-check."),
        ("opencode", "Run /ts-plan, /react-state-audit, and /drizzle-n1-check."),
    ],
)
def test_rewrite_slash_commands(target: str, expected: str) -> None:
    body = "Run /ts:plan, /react:state-audit, and /drizzle:n1-check."

    assert rewrite_slash_commands(body, target) == expected


def test_rewrite_slash_commands_rejects_unknown_target() -> None:
    with pytest.raises(ValueError, match="Unknown target: other"):
        rewrite_slash_commands("Run /ts:plan.", "other")


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("amp", "Use a ts-* workflow or `drizzle-*` command."),
        ("codex", "Use a $ts-* workflow or `$drizzle-*` command."),
        ("pi", "Use a /skill:ts-* workflow or `/skill:drizzle-*` command."),
        ("opencode", "Use a /ts-* workflow or `/drizzle-*` command."),
    ],
)
def test_rewrites_generic_claude_namespaces(target: str, expected: str) -> None:
    body = "Use a /ts: workflow or `/drizzle:*` command."

    assert rewrite_slash_commands(body, target) == expected


@pytest.mark.parametrize("target", ["amp", "codex", "pi", "opencode"])
@pytest.mark.parametrize(
    "text",
    [
        "/tmp/ts:review",
        "https://example.test/ts:review",
        "/ts:Review",
        "/ts:review_more",
        "/ts:*extra",
    ],
)
def test_slash_command_rewrite_requires_complete_tokens(target: str, text: str) -> None:
    assert rewrite_slash_commands(text, target) == text


def test_port_references_transforms_markdown_and_preserves_binary(tmp_path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    (source / "guide.md").write_text(
        "Use /ts:review and read ${CLAUDE_SKILL_DIR}/references/details.md.\n",
        encoding="utf-8",
    )
    payload = b"\x00\x01\xff"
    (source / "asset.bin").write_bytes(payload)

    port_references(source, destination, "codex")

    assert (destination / "guide.md").read_text(encoding="utf-8") == (
        "Use $ts-review and read references/details.md.\n"
    )
    assert (destination / "asset.bin").read_bytes() == payload


def test_inline_iron_laws_is_idempotent() -> None:
    body = "# Skill\n\nInstructions.\n"
    laws = ["Do one thing", "Do another thing"]

    once = inline_iron_laws(body, laws, "codex")
    twice = inline_iron_laws(once, laws, "codex")

    assert twice == once
    assert once.count("## Iron Laws (Inlined)") == 1
    assert "- Do one thing" in once


def test_inline_iron_laws_preserves_claude_body() -> None:
    body = "# Skill\n"

    assert inline_iron_laws(body, ["Law"], "claude") == body

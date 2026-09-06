"""Shared filesystem projection for generated skill subtrees."""

from __future__ import annotations

import shutil
import stat
import re
import textwrap
from pathlib import Path
from typing import Callable, Protocol, TypeVar


class SkillTreeSource(Protocol):
    source_dir: Path
    target_name: str


Skill = TypeVar("Skill", bound=SkillTreeSource)

RUNTIME_ARTIFACTS = {"__pycache__", ".pytest_cache", "node_modules", ".venv", ".DS_Store"}


def ignored_resource(path: Path, root: Path, ignored_files: set[str] | None = None) -> bool:
    """Exclude tool installation/cache state without dropping packaged resources."""
    return bool(set(path.relative_to(root).parts) & (RUNTIME_ARTIFACTS | (ignored_files or set())))


def wrap_markdown_prose(text: str, width: int = 200, *, only_containing: str | None = None) -> str:
    """Reflow expanded prose references while preserving YAML, tables and code."""
    result = []
    fence = None
    frontmatter = text.startswith("---\n")
    for index, line in enumerate(text.splitlines(keepends=True)):
        content = line.rstrip("\r\n")
        newline = line[len(content):]
        stripped = content.lstrip()
        if frontmatter:
            result.append(line)
            if index > 0 and stripped == "---":
                frontmatter = False
            continue
        marker = re.match(r"(?:>\s*)*(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            result.append(line)
            continue
        if fence or (only_containing is not None and only_containing not in content) or len(content) <= width or content.startswith(("    ", "\t")) or stripped.startswith(("|", "#")):
            result.append(line)
            continue
        leading = content[:len(content) - len(stripped)]
        quote = re.match(r"(?:>\s*)+", stripped)
        prefix = leading + (quote.group() if quote else "")
        body = stripped[len(quote.group()):] if quote else stripped
        listing = re.match(r"(?:[-*+] |\d+[.)] )", body)
        subsequent = prefix + (" " * len(listing.group()) if listing else "")
        hard_break = "  " if content.endswith("  ") else ""
        result.append("\n".join(textwrap.wrap(content, width=width - len(hard_break), subsequent_indent=subsequent,
                                             break_long_words=False, break_on_hyphens=False,
                                             replace_whitespace=False)) + hard_break + newline)
    return "".join(result)


def copy_skill_subtrees(
    skills: list[Skill],
    output_dir: Path,
    ignored_files: set[str],
    transform_markdown: Callable[[Path, Skill, list[Skill]], str],
    *,
    preserve_markdown_mode: bool = True,
) -> None:
    """Project complete skill trees while transforming Markdown only."""
    for skill in skills:
        target_skill = output_dir / skill.target_name
        for source_file in sorted(skill.source_dir.rglob("*")):
            if source_file.is_dir() or ignored_resource(source_file, skill.source_dir, ignored_files):
                continue

            destination = target_skill / source_file.relative_to(skill.source_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source_file.suffix.lower() == ".md":
                destination.write_text(
                    wrap_markdown_prose(transform_markdown(source_file, skill, skills)),
                    encoding="utf-8",
                )
                if preserve_markdown_mode:
                    destination.chmod(source_file.stat().st_mode & 0o7777)
            else:
                shutil.copy2(source_file, destination)


def tree_differences(expected: Path, actual: Path) -> list[str]:
    """Compare paths, node types, bytes, and Git's tracked executable bit."""

    def entries(root: Path) -> dict[str, tuple[str, int, Path]]:
        result: dict[str, tuple[str, int, Path]] = {}
        for path in sorted(root.rglob("*")):
            mode = path.lstat().st_mode
            kind = (
                "symlink"
                if stat.S_ISLNK(mode)
                else "directory"
                if stat.S_ISDIR(mode)
                else "file"
                if stat.S_ISREG(mode)
                else "special"
            )
            result[path.relative_to(root).as_posix()] = (
                kind,
                # Git restores other permission bits using the checkout's
                # umask; they cannot indicate drift in a committed target.
                int(bool(mode & stat.S_IXUSR)) if kind == "file" else 0,
                path,
            )
        return result

    expected_entries = entries(expected)
    actual_entries = entries(actual)
    differences: list[str] = []
    for relative in sorted(expected_entries.keys() | actual_entries.keys()):
        if relative not in actual_entries:
            differences.append(f"missing in target: {relative}")
            continue
        if relative not in expected_entries:
            differences.append(f"extra in target: {relative}")
            continue
        expected_kind, expected_mode, expected_path = expected_entries[relative]
        actual_kind, actual_mode, actual_path = actual_entries[relative]
        if expected_kind != actual_kind:
            differences.append(
                f"type differs: {relative} ({expected_kind} != {actual_kind})"
            )
        elif expected_kind == "file" and (
            expected_path.read_bytes() != actual_path.read_bytes()
        ):
            differences.append(f"differs: {relative}")
        elif expected_mode != actual_mode:
            differences.append(f"mode differs: {relative}")
    return differences

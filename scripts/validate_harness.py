"""Validate the local plugin inventory, manifests and concrete resource links."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from .harness_lib import REPO_ROOT, SOURCE_PLUGIN_DIR
from .harness_lib.frontmatter import parse_file
from .harness_lib.skill_transforms import CANONICAL_PORTABLE_NAMES


def validate(root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    plugin = root / "plugins/typescript-starter"
    identity = json.loads((root / "docs/quality/inventory.json").read_text())
    if identity.get("schemaVersion") != 2 or identity.get("plugin") != "typescript-starter" or identity.get("namespace") != "ts":
        errors.append("invalid TypeScript inventory identity/schema")
    version = json.loads((root / "package.json").read_text()).get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version):
        errors.append("invalid root package version")
    for kind, pattern in (("skills", "*/SKILL.md"), ("agents", "*.md")):
        files = sorted((plugin / kind).glob(pattern))
        records = identity[kind]
        expected = {record["name"] for record in records}
        if len(expected) != len(records):
            errors.append(f"{kind}: duplicate inventory names")
        actual = {p.parent.name if kind == "skills" else p.stem for p in files}
        if actual != expected:
            errors.append(f"{kind} inventory: missing={expected - actual}, extra={actual - expected}")
        for path in files:
            fm = parse_file(path)
            name = path.parent.name if kind == "skills" else path.stem
            if fm.data.get("name") != name or not isinstance(fm.data.get("description"), str):
                errors.append(f"{path.relative_to(root)}: invalid name/description")
            if kind == "skills" and (fm.data.get("user-invocable", True) is not False) != (name in CANONICAL_PORTABLE_NAMES):
                errors.append(f"{name}: public discovery flag differs from the 40-command contract")
            records_for_name = [record for record in records if record["name"] == name]
            if len(records_for_name) == 1:
                record = records_for_name[0]
                if record.get("path") != path.relative_to(root).as_posix():
                    errors.append(f"{name}: inventory path differs from definition")
                if kind == "skills":
                    if record.get("userInvocable") is not (fm.data.get("user-invocable", True) is not False):
                        errors.append(f"{name}: inventory discovery flag differs from definition")
                    if record.get("portableName") != CANONICAL_PORTABLE_NAMES.get(name, name):
                        errors.append(f"{name}: inventory portable name differs from generator")

    registered: dict[str, set[str]] = {}
    hook_config = json.loads((plugin / "hooks/hooks.json").read_text())
    for event, groups in hook_config["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                match = re.search(r"/hooks/scripts/([A-Za-z0-9_-]+\.sh)", hook.get("command", ""))
                if match:
                    registered.setdefault(match[1], set()).add(event)
    hooks = identity["hooks"]
    names = {record["name"] for record in hooks}
    if len(names) != len(hooks) or names != set(registered):
        errors.append("hook inventory differs from command registrations")
    for record in hooks:
        name = record["name"]
        if (record.get("path") != f"plugins/typescript-starter/hooks/scripts/{name}"
                or not (root / record["path"]).is_file()
                or set(record.get("events", [])) != registered.get(name, set())):
            errors.append(f"{name}: invalid hook inventory path/events")

    for path in sorted(plugin.glob("skills/**/*.md")):
        # These are concrete packaged resources, not project/example paths.
        for relative in re.findall(r"\$\{CLAUDE_SKILL_DIR\}/([A-Za-z0-9_.\-/]+)", path.read_text()):
            skill_root = next(parent for parent in path.parents if parent.parent == plugin / "skills")
            target = skill_root / relative.rstrip(".")
            if not target.exists():
                errors.append(f"{path.relative_to(root)}: missing resource {relative}")

    for name, namespace in (("typescript-starter", "ts"), ("drizzle", "drizzle"), ("react", "react")):
        path = root / "plugins" / name / ".claude-plugin/plugin.json"
        manifest = json.loads(path.read_text())
        if manifest.get("name") != namespace or manifest.get("version") != version:
            errors.append(f"{path.relative_to(root)}: incorrect plugin identity")
        if name == "typescript-starter" and manifest.get("dependencies") != ["drizzle", "react"]:
            errors.append("main Claude plugin must depend on both compatibility namespaces")

    marketplace = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    if marketplace.get("name") != "typescript-starter-harness" or marketplace.get("owner") != {"name": "João"}:
        errors.append("incorrect marketplace owner/identity")
    if marketplace.get("metadata", {}).get("version") != version:
        errors.append("marketplace metadata version differs from the release")
    for entry in marketplace["plugins"]:
        if not (root / entry["source"] / ".claude-plugin/plugin.json").is_file():
            errors.append(f"marketplace source does not resolve: {entry['source']}")
    # Parse shipped fixtures and projections as well as contributor configuration.
    # Runtime state and installed dependencies are outside this syntax gate.
    for directory, subdirs, names in os.walk(root):
        subdirs[:] = [name for name in subdirs if name not in {
            ".git", ".venv", ".worktrees", "node_modules", "__pycache__",
            ".pytest_cache", ".claude", ".remember", ".superpowers", ".rtk",
        } and not (Path(directory) / name).is_symlink()]
        for name in names:
            path = Path(directory) / name
            if path.suffix not in {".json", ".yml", ".yaml"}:
                continue
            try:
                text = path.read_text()
                if path.suffix == ".json":
                    json.loads(text)
                else:
                    list(yaml.safe_load_all(text))
            except (ValueError, OSError, yaml.YAMLError) as error:
                errors.append(f"{path.relative_to(root)}: invalid structured document: {error}")
    return errors


def validate_coverage(root: Path = REPO_ROOT) -> list[str]:
    """Check current resource coverage separately from release manifest validation."""
    errors: list[str] = []
    document = json.loads((root / "docs/quality/coverage.json").read_text())
    snapshot = json.loads((root / "docs/reference/starter-snapshot.json").read_text())
    if document.get("schemaVersion") != 2 or document.get("plugin") != "typescript-starter":
        errors.append("invalid resource coverage identity/schema")
    if document.get("starterSnapshotSha256") != snapshot["snapshotSha256"]:
        errors.append("resource coverage snapshot differs from captured starter")
    ids: set[str] = set()
    covered: set[str] = set()
    for item in document["items"]:
        if set(item) != {"id", "kind", "paths", "status", "evidencePaths"}:
            errors.append(f"{item.get('id')}: invalid resource record fields")
        identifier = item["id"]
        if identifier in ids:
            errors.append(f"duplicate resource id: {identifier}")
        ids.add(identifier)
        if not item["paths"] or item["status"] != "active" or not item["evidencePaths"]:
            errors.append(f"{identifier}: resource needs active paths and evidence")
        for field in ("paths", "evidencePaths"):
            for relative in item[field]:
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts or not (root / path).exists():
                    errors.append(f"{identifier}: invalid {field} entry: {relative}")
                if field == "paths":
                    if relative in covered:
                        errors.append(f"resource has multiple owners: {relative}")
                    covered.add(relative)
    plugin = root / "plugins/typescript-starter"
    canonical = {
        path.relative_to(root).as_posix()
        for path in plugin.rglob("*")
        if path.is_file() and not {"node_modules", "__pycache__", ".pytest_cache"}.intersection(path.parts)
    }
    for missing in sorted(canonical - covered):
        errors.append(f"canonical resource missing from coverage: {missing}")
    return errors


def main() -> int:
    errors = validate() + validate_coverage()
    if errors:
        print("\n".join(errors))
        return 1
    print("Offline inventory, manifests and resource links: passed")
    if shutil.which("claude"):
        for path in (SOURCE_PLUGIN_DIR, REPO_ROOT / "plugins/drizzle", REPO_ROOT / "plugins/react", REPO_ROOT / "plugins/catchup", REPO_ROOT):
            result = subprocess.run(["claude", "plugin", "validate", str(path)], cwd=REPO_ROOT, check=False)
            if result.returncode:
                return result.returncode
    else:
        print("Claude native manifest validator: not_run (CLI unavailable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

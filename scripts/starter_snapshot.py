"""Capture a consistent, credential-free copy of the local reference starter."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDED = {".git", ".remember", "node_modules", ".next", ".turbo", ".expo",
            "dist", "build", "coverage", "playwright-report", "test-results",
            "reports", "data", ".cache", "__pycache__"}


def source_files(root: Path) -> list[Path]:
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
    ).decode().split("\0")
    selected = []
    for name in sorted(set(filter(None, names))):
        path = Path(name)
        if EXCLUDED.intersection(path.parts):
            continue
        if (path.name.startswith(".env") and path.name != ".env.example") or path.name == ".npmrc":
            continue
        if path.suffix in {".pem", ".key", ".p12", ".tsbuildinfo", ".log", ".sqlite", ".db"}:
            continue
        full = root / path
        if full.is_symlink() or not full.is_file():
            continue
        selected.append(path)
    return selected


def read_selection(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.as_posix(): ((root / path).read_bytes(), int(bool((root / path).stat().st_mode & stat.S_IXUSR)))
        for path in source_files(root)
    }


def capture(root: Path, destination: Path, manifest: Path) -> dict:
    if destination.exists():
        raise ValueError(f"Copy destination already exists: {destination}")
    first = read_selection(root)
    for _ in range(3):
        second = read_selection(root)
        if first == second:
            break
        changed = sorted(key for key in first.keys() | second.keys() if first.get(key) != second.get(key))
        first = second
    else:
        raise ValueError(f"Reference changed during all three capture attempts: {changed}")
    destination.mkdir(parents=True)
    files = []
    digest = hashlib.sha256()
    for relative, (payload, executable) in sorted(second.items()):
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        output.chmod(0o755 if executable else 0o644)
        sha = hashlib.sha256(payload).hexdigest()
        files.append({"path": relative, "sha256": sha, "executable": executable})
        record = json.dumps([relative, "file", executable, sha], separators=(",", ":"), ensure_ascii=True)
        digest.update(record.encode() + b"\n")
    result = {
        "schemaVersion": 1,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip(),
        "sourceRoot": str(root.resolve()),
        "gitStatus": subprocess.check_output(["git", "status", "--short"], cwd=root).decode().splitlines(),
        "files": files,
        "snapshotSha256": digest.hexdigest(),
        "copyRoot": str(destination.resolve()),
        "exclusions": sorted(EXCLUDED) + [".env (except .env.example)", ".npmrc", "private keys, database files, logs, compiler cache"],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def check_copy(manifest: Path, copy: Path) -> list[str]:
    data = json.loads(manifest.read_text())
    failed = []
    for item in data["files"]:
        path = copy / item["path"]
        if not path.is_file() or path.is_symlink():
            failed.append(item["path"])
        elif (hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
              or int(bool(path.stat().st_mode & stat.S_IXUSR)) != item["executable"]):
            failed.append(item["path"])
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--copy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("docs/reference/starter-snapshot.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        failed = check_copy(args.manifest, args.copy)
        print(json.dumps({"status": "failed" if failed else "passed", "changed": failed}))
        return int(bool(failed))
    if args.source is None:
        parser.error("capture requires --source")
    data = capture(args.source, args.copy, args.manifest)
    print(json.dumps({"files": len(data["files"]), "sha256": data["snapshotSha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import subprocess

from scripts.starter_snapshot import capture, check_copy


def test_snapshot_preserves_dirty_and_new_source_but_excludes_credentials(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    (source / "package.json").write_text('{"name":"fixture"}\n')
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                    "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture"], cwd=source, check=True)
    # Deliberately dirty/new bytes must be captured, independent of HEAD.
    (source / "package.json").write_text('{"name":"dirty"}\n')
    (source / "new.ts").write_text("export const answer = 42;\n")
    (source / ".env").write_text("SECRET=must-not-be-copied\n")
    (source / ".npmrc").write_text("//registry.example.test/:_authToken=secret\n")
    (source / ".env.example").write_text("PORT=3000\n")
    executable = source / "check.sh"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    copy, manifest = tmp_path / "copy", tmp_path / "manifest.json"
    result = capture(source, copy, manifest)
    assert len(result["files"]) == 4
    assert json.loads((copy / "package.json").read_text())["name"] == "dirty"
    assert not (copy / ".env").exists()
    assert not (copy / ".npmrc").exists()
    assert check_copy(manifest, copy) == []
    (copy / "new.ts").write_text("changed")
    assert check_copy(manifest, copy) == ["new.ts"]

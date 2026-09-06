from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.harness_lib.generated_tree import tree_differences


def test_drift_check_survives_git_checkout_with_different_umask(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    expected = repository / "target"
    metadata = expected / ".plugin"
    metadata.mkdir(parents=True)
    metadata.chmod(0o755)
    manifest = metadata / "plugin.json"
    manifest.write_text('{}\n', encoding="utf-8")
    manifest.chmod(0o644)
    script = expected / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    for arguments in [
        ["init", "-q"],
        ["add", "target"],
        ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
         "commit", "-qm", "fixture"],
    ]:
        subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)

    checkout = tmp_path / "checkout"
    subprocess.run(
        ["git", "clone", "--no-hardlinks", "-q", str(repository), str(checkout)],
        check=True, capture_output=True, umask=0o002,
    )
    actual = checkout / "target"
    assert (actual / ".plugin/plugin.json").stat().st_mode & 0o777 == 0o664
    assert (actual / "run.sh").stat().st_mode & 0o777 == 0o775
    assert tree_differences(expected, actual) == []

    (actual / "run.sh").chmod(0o664)
    assert tree_differences(expected, actual) == ["mode differs: run.sh"]
    (actual / "run.sh").chmod(0o775)
    (actual / ".plugin/plugin.json").write_text('{"changed":true}\n', encoding="utf-8")
    assert tree_differences(expected, actual) == ["differs: .plugin/plugin.json"]

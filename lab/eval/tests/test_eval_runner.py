"""Exercise the real evaluation runner before and after the first commit."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("committed", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_evaluation_verdict_does_not_require_an_existing_commit(tmp_path, committed, valid):
    project = tmp_path / "harness"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "config", "core.hooksPath", str(tmp_path / "fixture-hooks")], cwd=project, check=True)
    shutil.copytree(ROOT / "lab/eval", project / "lab/eval", ignore=shutil.ignore_patterns("tests", "__pycache__", ".last-eval-commit"))
    relative = "plugins/typescript-starter/skills/typescript-idioms"
    shutil.copytree(ROOT / relative, project / relative)
    if not valid:
        (project / relative / "SKILL.md").write_text("---\nname: typescript-idioms\ndescription: Empty fixture\n---\n# Empty\n")
    if committed:
        subprocess.run(["git", "add", "."], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "fixture"], cwd=project, check=True)

    result = subprocess.run(
        ["bash", "lab/eval/run_eval.sh", "--skills"],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(project)},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == (0 if valid else 1), result.stdout + result.stderr
    assert ("EVAL PASSED" if valid else "EVAL FAILED") in result.stdout
    marker = project / "lab/eval/.last-eval-commit"
    if committed:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
        assert marker.read_text().strip() == head
    else:
        assert not marker.exists()

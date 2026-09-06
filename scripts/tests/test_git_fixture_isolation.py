"""A Git hook must not redirect fixture repositories into its caller."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import conftest

ROOT = Path(__file__).resolve().parents[2]


def test_nested_pytest_preserves_foreign_git_repository(tmp_path):
    owner = tmp_path / "owner"
    owner.mkdir()
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env["GIT_CONFIG_GLOBAL"] = str(tmp_path / "empty-global-config")
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    subprocess.run(["git", "init", "-q", str(owner)], env=env, check=True)
    (owner / "owner.txt").write_text("The invoking repository must remain unchanged.\n")
    subprocess.run(["git", "add", "."], cwd=owner, env=env, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "owner",
        ],
        cwd=owner,
        env=env,
        check=True,
    )

    def state():
        return {
            str(path.relative_to(owner)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in owner.rglob("*")
            if path.is_file()
        }

    before = state()
    nested = tmp_path / "nested"
    nested.mkdir()
    source = ROOT / "conftest.py"
    (nested / "conftest.py").write_text(source.read_text() if source.exists() else "")
    (nested / "test_child.py").write_text("""import os
from pathlib import Path
import subprocess

def test_independent_repository(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    subprocess.run(["git", "init", "-q", str(app)], check=True)
    actual = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=app, text=True).strip()
    assert Path(actual).resolve() == app.resolve()
    git_dir = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=app, text=True).strip()
    assert Path(git_dir).resolve() == (app / ".git").resolve()
    (app / "fixture.txt").write_text("fixture")
    subprocess.run(["git", "add", "."], cwd=app, check=True)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "fixture"], cwd=app, check=True)
""")
    inherited = {
        **env,
        "GIT_DIR": str(owner / ".git"),
        "GIT_INDEX_FILE": str(owner / ".git/index"),
        "GIT_OBJECT_DIRECTORY": str(owner / ".git/objects"),
        "GIT_CONFIG": str(owner / ".git/config"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "user.name",
        "GIT_CONFIG_VALUE_0": "Leaked hook configuration",
    }
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short"],
        cwd=nested,
        env=inherited,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert state() == before


@pytest.mark.parametrize("configured", [True, False])
def test_git_environment_restores_only_after_capture(monkeypatch, configured):
    monkeypatch.setenv("GIT_DIR", "/owned/caller/git")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/owned/caller/config")
    before = {key: value for key, value in os.environ.items() if key.startswith("GIT_")}
    config = SimpleNamespace()
    if configured:
        conftest.pytest_configure(config)
        assert "GIT_DIR" not in os.environ
        assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
        assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    conftest.pytest_unconfigure(config)
    assert {
        key: value for key, value in os.environ.items() if key.startswith("GIT_")
    } == before

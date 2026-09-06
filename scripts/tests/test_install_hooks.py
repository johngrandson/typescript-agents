"""Hook installation migrations run only in isolated Git repositories."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

INSTALLER = Path(__file__).resolve().parents[1] / "install-hooks.mjs"


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "repo with spaces"
    root.mkdir()
    bin_dir = tmp_path / "fixture-bin"
    bin_dir.mkdir()
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_CONFIG_")
        and key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"}
    }
    environment.update(
        PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
        GIT_CONFIG_GLOBAL=str(tmp_path / "global.gitconfig"),
        GIT_CONFIG_NOSYSTEM="1",
        HOOK_INSTALL_FIXTURE_LOG=str(tmp_path / "install.json"),
    )
    subprocess.run(["git", "init", "-q", str(root)], env=environment, check=True)
    fake = bin_dir / "lefthook"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, subprocess, sys\n"
        "configured = subprocess.run(['git', 'config', '--local', '--null', '--get-all', 'core.hooksPath'], capture_output=True, text=True)\n"
        "pathlib.Path(os.environ['HOOK_INSTALL_FIXTURE_LOG']).write_text(json.dumps({'args': sys.argv[1:], 'localPaths': configured.stdout.split('\\0')[:-1]}))\n"
        "sys.exit(int(os.environ.get('HOOK_INSTALL_FIXTURE_EXIT', '0')))\n"
    )
    fake.chmod(0o755)
    return root, environment


def config(repository, *args):
    root, environment = repository
    return subprocess.run(
        ["git", "config", *args],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
    )


def install(repository, exit_code=0):
    root, environment = repository
    result = subprocess.run(
        [shutil.which("node"), str(INSTALLER)],
        cwd=root,
        env={**environment, "HOOK_INSTALL_FIXTURE_EXIT": str(exit_code)},
        capture_output=True,
        text=True,
    )
    called = json.loads(Path(environment["HOOK_INSTALL_FIXTURE_LOG"]).read_text())
    assert called["args"] == ["install"]
    return result, called


@pytest.mark.parametrize("old_path", [".husky/_", ".husky"])
def test_legacy_local_path_is_removed_before_install(repository, old_path):
    assert config(repository, "--local", "core.hooksPath", old_path).returncode == 0
    result, called = install(repository)
    assert result.returncode == 0 and called["localPaths"] == []
    assert config(repository, "--local", "--get", "core.hooksPath").returncode == 1


@pytest.mark.parametrize(
    "custom_path", [".custom-hooks", "hooks with spaces", ".husky/custom", ".husky/_/"]
)
def test_custom_local_path_is_preserved(repository, custom_path):
    config(repository, "--local", "core.hooksPath", custom_path)
    result, called = install(repository)
    assert result.returncode == 0 and called["localPaths"] == [custom_path]
    assert (
        config(repository, "--local", "--get", "core.hooksPath").stdout.rstrip("\n")
        == custom_path
    )


@pytest.mark.parametrize("global_path", [".husky/_", ".husky/"])
def test_global_legacy_value_gets_local_default_override(repository, global_path):
    root, environment = repository
    config(repository, "--global", "core.hooksPath", global_path)
    global_before = Path(environment["GIT_CONFIG_GLOBAL"]).read_bytes()
    result, called = install(repository)
    expected = str(root / ".git/hooks")
    assert result.returncode == 0 and called["localPaths"] == [expected]
    assert (
        config(repository, "--local", "--get", "core.hooksPath").stdout
        == expected + "\n"
    )
    assert Path(environment["GIT_CONFIG_GLOBAL"]).read_bytes() == global_before


def test_custom_global_path_remains_effective(repository):
    config(repository, "--global", "core.hooksPath", "custom/global hooks")
    result, called = install(repository)
    assert result.returncode == 0 and called["localPaths"] == []
    assert (
        config(repository, "--get", "core.hooksPath").stdout == "custom/global hooks\n"
    )


@pytest.mark.parametrize("previous_local", [None, ".husky/_"])
def test_failed_global_override_restores_previous_local_or_inheritance(
    repository, previous_local
):
    config(repository, "--global", "core.hooksPath", ".husky/")
    if previous_local:
        config(repository, "--local", "core.hooksPath", previous_local)
    result, called = install(repository, exit_code=8)
    assert result.returncode == 8 and called["localPaths"] == [
        str(repository[0] / ".git/hooks")
    ]
    if previous_local:
        assert (
            config(repository, "--local", "--get", "core.hooksPath").stdout
            == previous_local + "\n"
        )
    else:
        assert config(repository, "--local", "--get", "core.hooksPath").returncode == 1
        assert config(repository, "--get", "core.hooksPath").stdout == ".husky/\n"
    assert (
        config(repository, "--global", "--get", "core.hooksPath").stdout == ".husky/\n"
    )


def test_linked_worktree_uses_common_git_hooks_directory(repository, tmp_path):
    root, environment = repository
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
    )
    linked = tmp_path / "linked worktree"
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(linked), "HEAD"],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
    )
    config(repository, "--global", "core.hooksPath", ".husky/")
    result, called = install((linked, environment))
    expected = str(root / ".git/hooks")
    assert result.returncode == 0 and called["localPaths"] == [expected]
    assert (
        config((linked, environment), "--local", "--get", "core.hooksPath").stdout
        == expected + "\n"
    )
    assert (
        config(repository, "--global", "--get", "core.hooksPath").stdout == ".husky/\n"
    )


def test_failed_install_restores_duplicate_legacy_values(repository):
    for value in [".husky", ".husky/_"]:
        config(repository, "--local", "--add", "core.hooksPath", value)
    result, called = install(repository, exit_code=7)
    assert result.returncode == 7 and called["localPaths"] == []
    assert (
        config(repository, "--local", "--get-all", "core.hooksPath").stdout
        == ".husky\n.husky/_\n"
    )
    assert "restored" in result.stderr


def test_mixed_custom_values_are_preserved_on_failure(repository):
    for value in [".custom-hooks", ".husky/_"]:
        config(repository, "--local", "--add", "core.hooksPath", value)
    result, called = install(repository, exit_code=9)
    assert result.returncode == 9 and called["localPaths"] == [
        ".custom-hooks",
        ".husky/_",
    ]
    assert (
        config(repository, "--local", "--get-all", "core.hooksPath").stdout
        == ".custom-hooks\n.husky/_\n"
    )


def test_absent_configuration_stays_absent(repository):
    result, called = install(repository)
    assert result.returncode == 0 and called["localPaths"] == []
    assert config(repository, "--local", "--get", "core.hooksPath").returncode == 1


def test_unavailable_installer_restores_legacy_value(repository):
    root, environment = repository
    config(repository, "--local", "core.hooksPath", ".husky/_")
    bin_dir = Path(environment["PATH"].split(os.pathsep)[0])
    (bin_dir / "lefthook").unlink()
    (bin_dir / "git").symlink_to(shutil.which("git"))
    result = subprocess.run(
        [shutil.which("node"), str(INSTALLER)],
        cwd=root,
        env={**environment, "PATH": str(bin_dir)},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "restored" in result.stderr
    assert (
        config(repository, "--local", "--get", "core.hooksPath").stdout == ".husky/_\n"
    )

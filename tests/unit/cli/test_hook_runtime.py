"""Portable Git-hook launcher and runtime-provenance contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.repository.hooks import hook_launcher
from ethos.repository.hooks import hook_runtime_binding
from ethos.repository.hooks import initiating_hook_transaction
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane


def _git(root: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_install_materializes_a_common_dir_package_runtime(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    checkout_python = tmp_path / "stale-checkout" / ".venv" / "bin" / "python"
    checkout_python.parent.mkdir(parents=True)
    checkout_python.symlink_to(Path(sys.executable))

    report = install_hook_launchers(repo, python=checkout_python)
    common_runtime = Path(git_common_dir(repo)) / "ethos" / "runtime"

    assert Path(str(report["python"])).is_relative_to(common_runtime)
    manifest = Path(str(report["runtime_manifest_path"]))
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["runtime_digest"] == report["runtime_digest"]
    assert payload["wheel_sha256"] == report["wheel_sha256"]
    assert len(payload["wheel_sha256"]) == 64
    assert report["scripts"] == ["pre-commit", "pre-push", "reference-transaction"]
    assert report["required_gaps"] == []
    for name in report["scripts"]:
        text = (Path(str(report["hooks_path"])) / name).read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n")
        assert checkout_python.as_posix() not in text
        assert 'exec "$HOOK_DIR/../ethos/runtime/' in text


def test_hook_launcher_uses_a_validated_git_for_windows_sh_runtime() -> None:
    """Git-for-Windows invokes hooks through sh; this is not a PowerShell launcher."""
    runtime = "../ethos/runtime/" + "a" * 64 + "/venv/Scripts/python.exe"

    text = hook_launcher(runtime, "pre-commit")

    assert 'HOOK_DIR=${0%/*}; [ "$HOOK_DIR" = "$0" ] && HOOK_DIR=.' in text
    assert 'HOOK_DIR=$(CDPATH= cd "$HOOK_DIR" && pwd)' in text
    assert f'exec "$HOOK_DIR/{runtime}" -I -m ethos.cli hook run pre-commit' in text
    assert len(text.splitlines()) == 5


def test_initiating_hook_transaction_binds_package_runtime_to_audit_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    with initiating_hook_transaction(repo) as environment:
        hooks = Path(environment["GIT_CONFIG_VALUE_0"])
        launcher = (hooks / "pre-commit").read_text(encoding="utf-8")

    assert f'ETHOS_HOOK_TRANSACTION_ROOT="{repo.resolve().as_posix()}"' in launcher
    assert "export ETHOS_HOOK_TRANSACTION_ROOT" in launcher


def test_hook_runtime_observation_rejects_launcher_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    report = install_hook_launchers(repo)
    launcher = Path(str(report["hooks_path"])) / "pre-push"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


def test_pre_commit_skips_unselected_staged_secret_capability(monkeypatch, tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    readme = fixture.worktree / "README.md"
    readme.write_text("# governed work lane\n", encoding="utf-8")
    assert _git(fixture.worktree, "add", "README.md").returncode == 0

    commit = _git(fixture.worktree, "commit", "-m", "change without secret policy")

    assert commit.returncode == 0, commit.stderr


def test_governed_repository_git_reads_real_hook_configuration(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    git(repository, "init", "-b", "dev")
    git(repository, "config", "core.hooksPath", ".githooks")

    assert git(repository, "config", "--get", "core.hooksPath") == ".githooks"


def test_repository_does_not_track_host_specific_hook_launchers() -> None:
    root = Path(__file__).resolve().parents[3]

    assert _git(root, "ls-files", ".githooks").stdout == ""

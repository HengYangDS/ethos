"""Portable Git-hook launcher and runtime-provenance contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.repository.hooks import hook_launcher
from ethos.repository.hooks import hook_runtime_binding
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


def test_hook_install_materializes_thin_launchers_bound_to_the_current_python(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0

    runtime = tmp_path / "runtime" / "python"
    runtime.parent.mkdir()
    runtime.write_text("", encoding="utf-8")

    report = install_hook_launchers(repo, python=runtime)

    assert report["hooks_path"].endswith("/.git/ethos-hooks")
    assert report["python"] == runtime.as_posix()
    assert report["scripts"] == ["pre-commit", "pre-push", "reference-transaction"]
    assert report["required_gaps"] == []
    for name in report["scripts"]:
        text = (Path(str(report["hooks_path"])) / name).read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n")
        assert f"exec {runtime.as_posix()} -I -m ethos.cli hook run" in text
        assert len(text.splitlines()) == 3


def test_hook_launcher_quotes_a_windows_runtime_without_shell_policy() -> None:
    text = hook_launcher("C:/Program Files/ETHOS/python.exe", "pre-commit")

    assert "exec 'C:/Program Files/ETHOS/python.exe' -I -m ethos.cli hook run pre-commit" in text
    assert len(text.splitlines()) == 3


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

from __future__ import annotations

import importlib
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.repo.git import ref_progress
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_ref_progress_projects_reflog_advances_without_persisting_metrics(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", head)
    first = commit_fixture_file(repo, "first.txt", "first\n", "first")
    second = commit_fixture_file(repo, "second.txt", "second\n", "second")
    git(repo, "update-ref", "-m", "first", "refs/heads/candidate/dev", first, head)
    git(repo, "update-ref", "-m", "second", "refs/heads/candidate/dev", second, first)

    observed = ref_progress(
        repo,
        "candidate/dev",
        observed_at=datetime.now(UTC),
    )

    assert observed["observation"] == "git_reflog"
    assert observed["ref"] == "candidate/dev"
    assert observed["advance_count"] == 2
    assert observed["interval_seconds"] >= 0
    assert observed["latest_interval_seconds"] >= 0
    assert observed["latest_advance_age_seconds"] >= 0
    assert observed["advances_per_hour"] >= 0
    assert "history" not in observed
    assert "recorded_at" not in observed


def test_ref_progress_preserves_unknown_when_reflog_is_unavailable(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    observed = ref_progress(
        repo,
        "candidate/missing",
        observed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert observed == {
        "observation": "git_reflog",
        "ref": "candidate/missing",
        "advance_count": 0,
        "interval_seconds": None,
        "latest_interval_seconds": None,
        "latest_advance_age_seconds": None,
        "advances_per_hour": None,
    }


def test_run_git_resolves_git_from_the_execution_environment_not_import_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git = git_adapter.shutil.which("git")
    assert git is not None
    git_directory = str(Path(git).resolve().parent)

    monkeypatch.setenv("PATH", "")
    importlib.reload(git_adapter)
    monkeypatch.setenv("PATH", git_directory)

    completed = git_adapter.run_git(repo, "rev-parse", "HEAD")

    assert completed.returncode == 0


def test_run_git_fails_closed_when_effective_path_has_no_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))

    with pytest.raises(ValueError, match=r"^git_executable_unavailable$"):
        run_git(repo, "rev-parse", "HEAD")


def test_run_git_distinguishes_an_invalid_working_directory(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(ValueError, match=r"^git_process_spawn_failed$") as error:
        run_git(missing, "rev-parse", "HEAD")

    assert getattr(error.value, "reason", "") == "working_directory_unavailable"


def test_network_git_preserves_effective_global_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/effective-global-gitconfig")
    monkeypatch.setattr(
        git_adapter,
        "_execute",
        lambda _root, command, **kwargs: (
            observed.update(command=command, **kwargs)
            or type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        ),
    )

    git_adapter.run_network_git(init_git_repo(tmp_path / "repo"), "ls-remote", "origin")

    environment = observed["env"]
    assert environment["GIT_CONFIG_GLOBAL"] == "/tmp/effective-global-gitconfig"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"

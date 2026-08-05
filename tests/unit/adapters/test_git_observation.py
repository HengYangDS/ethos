from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import ref_progress
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


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

"""Shared fixtures for the Work Lane test suites.

The lane coverage is split across sibling `test_lanes*.py` modules by theme
(status, lifecycle, lease projection); these helpers — git plumbing, sample-repo
and candidate-worktree scaffolding, branch-role policy authoring, and the
no-UI-projection assertion — are the setup every split imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.store.state.lease.lifecycle import core as state
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo as init_repo

if TYPE_CHECKING:
    from pathlib import Path

__all__ = (
    "absorb_obsolete_delta_in_accepted",
    "add_candidate_worktree",
    "assert_no_ui_projection",
    "git",
    "init_repo",
    "leased_worktree",
    "orphan_work_lane",
    "superseded_work_lane",
)


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def leased_worktree(repo: Path, path: Path, *, holder_ref: str = "agent:test:case:agent-a") -> Path:
    """Create one owned worktree with a matching lease for admission tests."""
    git(repo, "worktree", "add", "-b", "work/feature", path.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        holder_ref=holder_ref,
        payload={
            "path": path.as_posix(),
            "branch": "work/feature",
            "expected_head": git(path, "rev-parse", "HEAD"),
        },
    )
    return path


def absorb_obsolete_delta_in_accepted(repo: Path) -> str:
    """Commit a fixture change directly on the accepted branch."""
    (repo / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(repo, "add", "obsolete.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "absorb obsolete lane delta",
    )
    return git(repo, "rev-parse", "dev")


def orphan_work_lane(tmp_path: Path) -> tuple[Path, Path]:
    """Create an unleased Work Lane for exceptional-resolution tests."""
    repo = init_repo(tmp_path / "repo")
    lane = tmp_path / "repo-work-orphan"
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), "dev")
    return repo, lane


def superseded_work_lane(
    tmp_path: Path,
    *,
    absorbed: bool = True,
    holder_ref: str = "agent:test:case:agent-a",
) -> tuple[Path, Path, str, str, Path]:
    """Create an owned obsolete lane and optionally absorb its change on dev."""
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    lane = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", "work/superseded", lane.as_posix(), "dev")
    (lane / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(lane, "add", "obsolete.txt")
    git(
        lane,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "obsolete lane delta",
    )
    head = git(lane, "rev-parse", "HEAD")
    accepted = (
        absorb_obsolete_delta_in_accepted(repo) if absorbed else git(repo, "rev-parse", "dev")
    )
    database = repo / ".ethos" / "state" / "state.sqlite"
    state.acquire_lease(
        database, subject="work/superseded", holder_ref=holder_ref, ttl_seconds=3600
    )
    return repo, lane, head, accepted, database


def assert_no_ui_projection(value: object) -> None:
    if isinstance(value, dict):
        forbidden = {"open_action", "open_label", "action", "label"}
        assert not (forbidden & set(value))
        for child in value.values():
            assert_no_ui_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_ui_projection(child)

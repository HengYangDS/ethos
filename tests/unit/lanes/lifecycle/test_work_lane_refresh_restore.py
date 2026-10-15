"""Restore refused and interrupted Work Lane refreshes on a real repository."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh
import ethos.adapters.repo.worktree_effects as worktree_effects
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_record import read_pending_refresh
from ethos.adapters.repo.git import GitExecutionError
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

BRANCH = "work/feature"


class _Interrupted(BaseException):
    """Stand in for a deadline that kills the refresh between its rebase and ref update."""


def _lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, dict[str, object]]:
    """Create a lane one commit off a moved candidate; only effect evidence is stubbed."""
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "branch", "candidate/dev")
    git(repo, "branch", BRANCH)
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", candidate.as_posix(), "candidate/dev")
    candidate_head = commit_fixture_file(candidate, "candidate.txt", "candidate\n", "candidate")
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", lane.as_posix(), BRANCH)
    original = commit_fixture_file(lane, "lane.txt", "lane\n", "lane")
    status: dict[str, object] = {
        "branch": BRANCH,
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "head": candidate_head,
            "worktree_path": candidate.as_posix(),
        },
    }
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    monkeypatch.setattr(refresh, "workspace_status", lambda _root: status)
    monkeypatch.setattr(refresh, "hook_runtime_binding", lambda _root: {"required_gaps": []})
    monkeypatch.setattr(refresh, "validate_replayed_commits", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(refresh, "leases_by_branch", lambda _root: {})
    monkeypatch.setattr(
        refresh,
        "compile_observed_git_effect",
        lambda *_args, **_kwargs: SimpleNamespace(digest="plan"),
    )
    for module in (refresh, worktree_effects):
        monkeypatch.setattr(module, "repository_identity", lambda *_args, **_kwargs: "repo:test")
    return lane, original, status


def _interrupt(monkeypatch: pytest.MonkeyPatch, lane: Path, original: str) -> str:
    monkeypatch.setattr(
        refresh,
        "execute_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(_Interrupted()),
    )
    with pytest.raises(_Interrupted):
        refresh.refresh_work_lane_base(root=lane, apply=True, authorized=True, expect_head=original)
    return git(lane, "rev-parse", "HEAD")


def _attachment(lane: Path) -> tuple[str, str]:
    return git(lane, "branch", "--show-current"), git(lane, "rev-parse", "HEAD")


def test_refused_refresh_returns_the_lane_attached_to_its_original_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane, original, _status = _lane(tmp_path, monkeypatch)
    refused = GitExecutionError(
        "git_effect_cas_rejected",
        reason="native_exit_nonzero",
        observation={"stderr": "reference-transaction hook refused"},
    )
    monkeypatch.setattr(
        refresh,
        "execute_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(refused),
    )

    report = refresh.refresh_work_lane_base(
        root=lane, apply=True, authorized=True, expect_head=original
    )

    assert report["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]
    assert _attachment(lane) == (BRANCH, original)
    assert git(lane, "status", "--porcelain") == ""
    assert read_pending_refresh(lane) is None


def test_interrupted_refresh_is_restored_from_its_pending_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane, original, status = _lane(tmp_path, monkeypatch)
    rebased = _interrupt(monkeypatch, lane, original)
    assert _attachment(lane) == ("", rebased)
    assert read_pending_refresh(lane) is not None
    status["branch"] = "detached"
    monkeypatch.setattr(refresh, "recover_plan", lambda *_args, **_kwargs: None)

    report = refresh.refresh_work_lane_base(root=lane, apply=True)

    assert (report["state"], report["head"], report["previous_head"]) == (
        "base_restored",
        original,
        rebased,
    )
    assert str(report["next_action"]).startswith(
        f"ethos lane refresh-base --apply --authorize --expect-head {original} "
    )
    assert _attachment(lane) == (BRANCH, original)
    assert read_pending_refresh(lane) is None


@pytest.mark.parametrize("case", ["moved", "dirty"])
def test_unmatched_pending_record_blocks_without_moving_the_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    lane, original, status = _lane(tmp_path, monkeypatch)
    rebased = _interrupt(monkeypatch, lane, original)
    status.update(branch="detached", dirty=case == "dirty")
    if case == "moved":
        git(lane, "branch", "--force", BRANCH, rebased)
    monkeypatch.setattr(refresh, "recover_plan", lambda *_args, **_kwargs: None)

    report = refresh.refresh_work_lane_base(root=lane, apply=True)

    assert report["required_gaps"] == [
        "git_effect_recovery_unproven" if case == "moved" else "work_lane_dirty"
    ]
    assert _attachment(lane) == ("", rebased)

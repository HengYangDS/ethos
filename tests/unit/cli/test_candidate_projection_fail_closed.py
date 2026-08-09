from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as projection
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repo_without_candidate(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    return repo, git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("should_apply", [False, True])
def test_candidate_bootstrap_distinguishes_plan_from_path_collision(
    tmp_path: Path, should_apply: object
) -> None:
    repo, head = _repo_without_candidate(tmp_path)
    target = tmp_path / "candidate"
    target.mkdir()

    report = projection.bootstrap_candidate(
        root=repo,
        path=target,
        expect_head=head,
        apply=should_apply,
    )

    assert report["state"] == ("planned" if not should_apply else "blocked")
    assert report["required_gaps"] == (
        [] if not should_apply else ["candidate_worktree_path_exists"]
    )
    assert git(repo, "branch", "--list", "candidate/dev") == ""


def test_candidate_bootstrap_reports_unproven_recovery_before_any_ref_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repo_without_candidate(tmp_path)
    candidate = tmp_path / "candidate"
    git(repo, "branch", "candidate/dev", head)
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a, **_k: None)

    report = projection.bootstrap_candidate(
        root=repo,
        path=candidate,
        expect_head=head,
        apply=True,
    )

    assert report["required_gaps"] == ["git_effect_recovery_unproven"]
    assert not candidate.exists()
    assert git(repo, "rev-parse", "candidate/dev") == head


@pytest.mark.parametrize(
    ("status", "should_apply", "is_authorized", "expect_head", "gap"),
    [
        ({"role": "other", "dirty": False}, False, False, None, "accepted_root_required"),
        ({"role": "accepted_root", "dirty": True}, False, False, None, "accepted_root_dirty"),
        ({"role": "accepted_root", "dirty": False}, True, False, "head", "authorization_required"),
        ({"role": "accepted_root", "dirty": False}, True, True, None, "expect_head_required"),
        ({"role": "accepted_root", "dirty": False}, True, True, "other", "expect_head_mismatch"),
    ],
)
def test_candidate_refresh_public_preconditions_fail_before_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: dict[str, object],
    should_apply: object,
    is_authorized: object,
    expect_head: str | None,
    gap: str,
) -> None:
    repo, head = _repo_without_candidate(tmp_path)
    candidate = {
        "exists": True,
        "worktree_exists": True,
        "head": head,
        "worktree_path": (tmp_path / "candidate").as_posix(),
    }
    monkeypatch.setattr(
        projection,
        "workspace_status",
        lambda *_a, **_k: status | {"candidate": candidate},
    )
    monkeypatch.setattr(
        projection,
        "execute_git_effect",
        lambda *_a, **_k: pytest.fail("blocked refresh must not execute a git effect"),
    )

    report = projection.refresh_candidate_from_accepted(
        root=repo,
        apply=should_apply,
        authorized=is_authorized,
        expect_head=head if expect_head == "head" else expect_head,
    )

    assert gap in report["required_gaps"]

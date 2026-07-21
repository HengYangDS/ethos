from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.lease.lifecycle.core as state
import ethos.adapters.store.state.lease.projection as state_read
from ethos.adapters.mutation.lane_lifecycle import core as lane_lifecycle_core
from ethos.adapters.mutation.lane_retirement import core
from ethos.adapters.mutation.lane_retirement.core import LinkedRetirementRequest
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import superseded_work_lane

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


_ACTOR = "agent:test:case:agent-a"
_SUPERSEDED_BRANCH = "work/superseded"


@contextmanager
def _actor_env(actor: str) -> Iterator[None]:
    previous = os.environ.get("ETHOS_ACTOR")
    os.environ["ETHOS_ACTOR"] = actor
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("ETHOS_ACTOR", None)
        else:
            os.environ["ETHOS_ACTOR"] = previous


def _retire_superseded(
    repo: Path,
    head: str,
    accepted: str,
    *,
    apply: bool = False,
) -> dict[str, object]:
    with _actor_env(_ACTOR):
        return _retire(
            repo,
            expect_head=head,
            absorbed_by=accepted,
            apply=apply,
            authorize=apply,
        )


def _retire(
    root: Path,
    *,
    branch: str = _SUPERSEDED_BRANCH,
    expect_head: str | None = None,
    absorbed_by: str = "",
    reason: str = "accepted root already carries the semantic fix",
    apply: bool = False,
    authorize: bool = False,
) -> dict[str, object]:
    return core.retire_linked_work_lane(
        root=root,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch=branch,
            expect_head=expect_head,
            absorbed_by=absorbed_by,
            reason=reason,
            apply=apply,
            authorize=authorize,
        ),
    )


@pytest.mark.parametrize(
    ("branch", "expect_head", "gap"),
    [
        ("", "x", "superseded_retire_branch_required"),
        ("work/missing", "x", "superseded_retire_branch_not_found"),
        ("feature/not-work", "feature_head", "superseded_retire_not_work_lane"),
    ],
)
def test_superseded_retirement_reports_branch_shape_gaps(
    tmp_path: Path, branch: str, expect_head: str, gap: str
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "feature/not-work", "dev")
    accepted = git(repo, "rev-parse", "dev")

    report = _retire(
        repo,
        branch=branch,
        expect_head=(
            git(repo, "rev-parse", "feature/not-work")
            if expect_head == "feature_head"
            else expect_head
        ),
        absorbed_by=accepted,
        reason="invalid branch shape",
    )
    assert report["required_gaps"] == [gap]


def test_superseded_retirement_rejects_mismatched_expected_head(tmp_path: Path) -> None:
    repo, _lane, _head, accepted, _database = superseded_work_lane(tmp_path)
    with _actor_env(_ACTOR):
        report = _retire(repo, expect_head="other-head", absorbed_by=accepted)
    assert report["required_gaps"] == ["expect_head_mismatch"]


def test_superseded_retirement_requires_stable_control_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _lane, head, accepted, _database = superseded_work_lane(tmp_path)
    status = core.workspace_status(repo)
    status["worktrees"] = [
        worktree for worktree in status["worktrees"] if worktree["role"] != "accepted_root"
    ]
    monkeypatch.setattr(core, "workspace_status", lambda _root: status)
    report = _retire_superseded(repo, head, accepted, apply=True)
    assert report["required_gaps"] == ["retirement_control_root_unavailable"]


def test_superseded_retirement_reports_unlinked_and_unavailable_heads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "work/unlinked", "dev")
    head = git(repo, "rev-parse", "work/unlinked")

    def fail_accepted_head(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args == ("rev-parse", "dev"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="missing")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    monkeypatch.setattr(core, "run_git", fail_accepted_head)

    report = _retire(
        repo,
        branch="work/unlinked",
        expect_head=head,
        reason="not linked",
    )

    expected = report["mutation"]["decision"]["subject"]["expected_state"]
    assert expected["accepted_head"] == ""
    assert expected["head"] == head
    assert report["required_gaps"] == [
        "absorbed_by_required",
        "accepted_head_unavailable",
        "superseded_retire_worktree_not_linked",
    ]


def test_superseded_retirement_reports_apply_remove_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _lane, head, accepted, _database = superseded_work_lane(tmp_path)

    def fail_worktree_remove(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="locked")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    monkeypatch.setattr(core, "run_git", fail_worktree_remove)
    report = _retire_superseded(repo, head, accepted, apply=True)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["worktree_remove_failed"]
    assert report["stderr"] == "locked"
    assert report["mutation"]["decision"]["verdict"] == "block"


def test_superseded_retirement_blocks_when_target_changes_after_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane, head, accepted, _database = superseded_work_lane(tmp_path)

    def stale_ref(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args == ("rev-parse", f"refs/heads/{_SUPERSEDED_BRANCH}"):
            return subprocess.CompletedProcess(args, 0, stdout="b" * 40 + "\n", stderr="")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    monkeypatch.setattr(core, "run_git", stale_ref)
    report = _retire_superseded(repo, head, accepted, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["retirement_ref_stale"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", _SUPERSEDED_BRANCH) == head


def test_superseded_retirement_rechecks_current_accepted_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane, head, accepted, _database = superseded_work_lane(tmp_path)
    tree = git(repo, "rev-parse", f"{accepted}^{{tree}}")
    replacement = lane_lifecycle_core.run_git(
        repo, "commit-tree", tree, "-m", "replacement accepted root"
    ).stdout.strip()
    holder_ref = core.current_holder_ref
    calls = 0

    def move_after_observation() -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            lane_lifecycle_core.run_git(
                repo,
                "update-ref",
                "refs/heads/dev",
                replacement,
                accepted,
            )
        return holder_ref()

    monkeypatch.setattr(core, "current_holder_ref", move_after_observation)
    report = _retire_superseded(repo, head, accepted, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["accepted_ref_stale"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", _SUPERSEDED_BRANCH) == head


def test_superseded_retirement_dry_run_requires_absorbed_accepted_head(
    tmp_path: Path,
) -> None:
    repo, lane, head, accepted, _database = superseded_work_lane(tmp_path)
    report = _retire_superseded(repo, head, accepted)

    assert report["ok"] is True
    assert report["state"] == "ready_to_retire_superseded"
    expected = report["mutation"]["decision"]["subject"]["expected_state"]
    assert report["lane"]["head"] == head
    assert expected["accepted_head"] == accepted
    assert expected["absorbed_by"] == accepted
    assert report["lane"]["required_gaps"] == []
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == head


@pytest.mark.parametrize(
    ("case", "failure_command", "stderr"),
    [
        ("unabsorbed", "", ""),
        ("absorbed", "merge-base", "no merge base"),
        ("absorbed", "diff", "diff unavailable"),
    ],
    ids=("unabsorbed", "merge-base-unavailable", "delta-diff-unavailable"),
)
def test_superseded_retirement_fails_closed_without_absorption_proof(
    tmp_path: Path,
    case: str,
    failure_command: str,
    stderr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane, head, accepted, _database = superseded_work_lane(
        tmp_path, absorbed=case == "absorbed"
    )
    if failure_command:
        original = lane_lifecycle_core.run_git

        def fail_command(root: Path, *args: str, check: bool = False):
            if args[:1] == (failure_command,):
                return subprocess.CompletedProcess(args, 128, stdout="", stderr=stderr)
            return original(root, *args, check=check)

        monkeypatch.setattr(core, "run_git", fail_command)
    report = _retire_superseded(lane, head, accepted, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", _SUPERSEDED_BRANCH) == head


def test_retire_superseded_preserves_leading_space_paths(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    lane = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", _SUPERSEDED_BRANCH, lane.as_posix(), "dev")
    for root, content, message in ((lane, "lane\n", "lane"), (repo, "accepted\n", "accepted")):
        (root / " leading.txt").write_text(content, encoding="utf-8")
        git(root, "add", " leading.txt")
        git(
            root,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            message,
        )
    head, accepted = git(lane, "rev-parse", "HEAD"), git(repo, "rev-parse", "dev")
    state.acquire_lease(
        repo / ".ethos/state/state.sqlite",
        subject=_SUPERSEDED_BRANCH,
        holder_ref=_ACTOR,
        payload={"expected_head": head},
    )

    report = _retire_superseded(repo, head, accepted)

    assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()


def test_superseded_retirement_apply_removes_clean_linked_unmerged_lane(
    tmp_path: Path,
) -> None:
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path)
    report = _retire_superseded(repo, head, accepted, apply=True)

    assert report["ok"] is True
    assert report["state"] == "retired_superseded"
    assert report["retired"]["branch"] == _SUPERSEDED_BRANCH
    assert not lane.exists()
    assert git(repo, "branch", "--list", _SUPERSEDED_BRANCH) == ""
    assert all(
        lease["subject"] != _SUPERSEDED_BRANCH for lease in state_read.active_leases(database)
    )


def test_superseded_retirement_fails_closed_for_dirty_or_merged_lanes(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    dirty = tmp_path / "repo-work-dirty"
    merged = tmp_path / "repo-work-merged"
    git(repo, "worktree", "add", "-b", "work/dirty", dirty.as_posix(), "dev")
    git(repo, "worktree", "add", "-b", "work/merged", merged.as_posix(), "dev")
    (dirty / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    accepted = git(repo, "rev-parse", "dev")
    dirty_head = git(dirty, "rev-parse", "HEAD")
    merged_head = git(merged, "rev-parse", "HEAD")
    db = repo / ".ethos" / "state" / "state.sqlite"
    state.acquire_lease(
        db,
        subject="work/dirty",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
        payload={"expected_head": dirty_head},
    )
    state.acquire_lease(
        db,
        subject="work/merged",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
        payload={"expected_head": merged_head},
    )

    with _actor_env("agent:test:case:agent-a"):
        dirty_report = _retire(
            repo,
            branch="work/dirty",
            expect_head=dirty_head,
            absorbed_by=accepted,
            reason="dirty lane must not be silently removed",
            apply=True,
            authorize=True,
        )
        merged_report = _retire(
            repo,
            branch="work/merged",
            expect_head=merged_head,
            absorbed_by=accepted,
            reason="merged lane must use the landed path",
            apply=True,
            authorize=True,
        )

    assert dirty_report["ok"] is False
    assert "work_lane_dirty" in dirty_report["required_gaps"]
    assert dirty.exists()
    assert merged_report["ok"] is False
    assert "work_lane_already_merged_use_retire_landed" in merged_report["required_gaps"]
    assert merged.exists()


def test_superseded_retirement_requires_owner_head_reason_absorption_and_authorization(
    tmp_path: Path,
) -> None:
    repo, lane, _head, _accepted, _database = superseded_work_lane(tmp_path)
    with _actor_env("agent:test:case:agent-b"):
        report = _retire(
            repo,
            absorbed_by="old-head",
            reason="",
            apply=True,
        )

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "absorbed_by_not_current_accepted_head",
        "authorization_required",
        "expect_head_required",
        "foreign_work_lane_retire_authority_required",
        "retire_reason_required",
    ]
    assert report["next_action"] == "set ETHOS_ACTOR to the current holder_ref or obtain handoff"
    assert lane.exists()

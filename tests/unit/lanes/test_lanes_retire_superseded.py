from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_retirement.core as lane_retirement_core
import ethos.adapters.store.state.lease.core as state
from ethos.adapters.mutation.lane_lifecycle import core as lane_lifecycle_core
from ethos.adapters.mutation.lane_retirement.core import SupersededLaneRetirementRequest
from ethos.adapters.mutation.lane_retirement.shared.core import RetirementRuntime
from tests.unit.lanes.test_lanes_retire import add_candidate_worktree
from tests.unit.lanes.test_lanes_retire import git
from tests.unit.lanes.test_lanes_retire import init_repo

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


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


def absorb_obsolete_delta_in_accepted(repo: Path) -> str:
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


def test_retire_superseded_work_lane_reports_branch_shape_gaps(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "feature/not-work", "dev")
    accepted = git(repo, "rev-parse", "dev")

    missing_branch = lane_retirement_core.retire_superseded_work_lane(
        root=repo,
        request=SupersededLaneRetirementRequest(
            branch="",
            expect_head="x",
            absorbed_by=accepted,
            reason="missing branch",
        ),
    )
    not_found = lane_retirement_core.retire_superseded_work_lane(
        root=repo,
        request=SupersededLaneRetirementRequest(
            branch="work/missing",
            expect_head="x",
            absorbed_by=accepted,
            reason="missing branch",
        ),
    )
    wrong_role = lane_retirement_core.retire_superseded_work_lane(
        root=repo,
        request=SupersededLaneRetirementRequest(
            branch="feature/not-work",
            expect_head=git(repo, "rev-parse", "feature/not-work"),
            absorbed_by=accepted,
            reason="wrong role",
        ),
    )

    assert missing_branch["required_gaps"] == ["superseded_retire_branch_required"]
    assert not_found["required_gaps"] == ["superseded_retire_branch_not_found"]
    assert wrong_role["required_gaps"] == ["superseded_retire_not_work_lane"]


def test_retire_superseded_work_lane_reports_unlinked_and_unavailable_heads(
    tmp_path: Path,
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

    runtime = lane_retirement_core.SupersededRetirementRuntime(
        run_git=fail_accepted_head,
        shared=RetirementRuntime(run_git=fail_accepted_head),
    )

    report = lane_retirement_core.retire_superseded_work_lane(
        root=repo,
        request=SupersededLaneRetirementRequest(
            branch="work/unlinked",
            expect_head=head,
            absorbed_by="",
            reason="not linked",
        ),
        runtime=runtime,
    )

    assert report["accepted_head"] == ""
    assert report["head"] == head
    assert report["required_gaps"] == [
        "absorbed_by_required",
        "accepted_head_unavailable",
        "superseded_retire_worktree_not_linked",
    ]


def test_retire_superseded_work_lane_reports_apply_remove_failure(
    tmp_path: Path,
) -> None:
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
    accepted = absorb_obsolete_delta_in_accepted(repo)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    def fail_worktree_remove(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args[:3] == ("worktree", "remove", "--force"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="locked")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    runtime = lane_retirement_core.SupersededRetirementRuntime(
        shared=RetirementRuntime(run_git=fail_worktree_remove),
    )

    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="accepted root already carries the semantic fix",
                apply=True,
                authorized=True,
            ),
            runtime=runtime,
        )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["worktree_remove_failed"]
    assert report["stderr"] == "locked"


def test_retire_superseded_private_helpers_cover_unavailable_status(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    assert lane_retirement_core._branch_head(repo, "") == ""
    assert lane_retirement_core._linked_work_lane({"worktrees": "bad"}, "work/x") is None

    def fail_status(
        _root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        return subprocess.CompletedProcess(args, 128, stdout="", stderr="fatal")

    runtime = lane_retirement_core.SupersededRetirementRuntime(
        run_git=fail_status,
        shared=RetirementRuntime(run_git=fail_status),
    )

    assert lane_retirement_core._branch_exists(repo, "work/x", runtime=runtime) is False
    assert lane_retirement_core._branch_head(repo, "work/x", runtime=runtime) == ""
    assert lane_retirement_core._has_changed_paths(repo, runtime=runtime) is True


def test_retire_superseded_work_lane_dry_run_requires_absorbed_accepted_head(
    tmp_path: Path,
) -> None:
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
    accepted = absorb_obsolete_delta_in_accepted(repo)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="obsolete lane truth was reimplemented in accepted root",
            ),
        )

    assert report["ok"] is True
    assert report["state"] == "ready_to_retire_superseded"
    assert report["head"] == head
    assert report["accepted_head"] == accepted
    assert report["retire_ready"] is True
    assert report["lane"]["required_gaps"] == []
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == head


def test_retire_superseded_work_lane_blocks_unabsorbed_lane_delta(
    tmp_path: Path,
) -> None:
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
    accepted = git(repo, "rev-parse", "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="accepted root already carries the semantic fix",
                apply=True,
                authorized=True,
            ),
        )

    assert report["ok"] is False
    assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == head


def test_retire_superseded_work_lane_fails_closed_when_merge_base_unavailable(
    tmp_path: Path,
) -> None:
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
    accepted = absorb_obsolete_delta_in_accepted(repo)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    def fail_merge_base(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args[:1] == ("merge-base",):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="no merge base")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    runtime = lane_retirement_core.SupersededRetirementRuntime(
        run_git=fail_merge_base,
        shared=RetirementRuntime(run_git=fail_merge_base),
    )

    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="accepted root already carries the semantic fix",
                apply=True,
                authorized=True,
            ),
            runtime=runtime,
        )

    assert report["ok"] is False
    assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == head


def test_retire_superseded_work_lane_fails_closed_when_delta_diff_unavailable(
    tmp_path: Path,
) -> None:
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
    accepted = absorb_obsolete_delta_in_accepted(repo)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    def fail_diff(
        root: Path,
        *args: str,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        if args[:1] == ("diff",):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="diff unavailable")
        return lane_lifecycle_core.run_git(root, *args, check=check)

    runtime = lane_retirement_core.SupersededRetirementRuntime(
        run_git=fail_diff,
        shared=RetirementRuntime(run_git=fail_diff),
    )

    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="accepted root already carries the semantic fix",
                apply=True,
                authorized=True,
            ),
            runtime=runtime,
        )

    assert report["ok"] is False
    assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == head


def test_retire_superseded_work_lane_apply_removes_clean_linked_unmerged_lane(
    tmp_path: Path,
) -> None:
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
    accepted = absorb_obsolete_delta_in_accepted(repo)
    db = repo / ".ethos" / "state" / "state.sqlite"
    state.acquire_lease(
        db,
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    with _actor_env("agent:test:case:agent-a"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                expect_head=head,
                absorbed_by=accepted,
                reason="accepted root already carries the semantic fix",
                apply=True,
                authorized=True,
            ),
        )

    assert report["ok"] is True
    assert report["state"] == "retired_superseded"
    assert report["retired"]["branch"] == "work/superseded"
    assert not lane.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert all(lease["subject"] != "work/superseded" for lease in state.active_leases(db))


def test_retire_superseded_work_lane_fails_closed_for_dirty_or_merged_lanes(
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
        db, subject="work/dirty", holder_ref="agent:test:case:agent-a", ttl_seconds=3600
    )
    state.acquire_lease(
        db,
        subject="work/merged",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )

    with _actor_env("agent:test:case:agent-a"):
        dirty_report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/dirty",
                expect_head=dirty_head,
                absorbed_by=accepted,
                reason="dirty lane must not be silently removed",
                apply=True,
                authorized=True,
            ),
        )
        merged_report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/merged",
                expect_head=merged_head,
                absorbed_by=accepted,
                reason="merged lane must use the landed path",
                apply=True,
                authorized=True,
            ),
        )

    assert dirty_report["ok"] is False
    assert "work_lane_dirty" in dirty_report["required_gaps"]
    assert dirty.exists()
    assert merged_report["ok"] is False
    assert "work_lane_already_merged_use_retire_landed" in merged_report["required_gaps"]
    assert merged.exists()


def test_retire_superseded_work_lane_requires_owner_head_reason_absorption_and_authorization(
    tmp_path: Path,
) -> None:
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
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    with _actor_env("agent:test:case:agent-b"):
        report = lane_retirement_core.retire_superseded_work_lane(
            root=repo,
            request=SupersededLaneRetirementRequest(
                branch="work/superseded",
                absorbed_by="old-head",
                apply=True,
            ),
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


def test_superseded_helper_edges_cover_head_mismatch_and_empty_actor_selection() -> None:
    assert lane_retirement_core._superseded_expected_head_gaps(
        head="actual",
        expect_head="expected",
    ) == ["expect_head_mismatch"]
    assert lane_retirement_core._landed_actor_gaps([]) == []

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.change_rollover as rollover
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.normalization.coercion import integer
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import OpenSpecLifecycle
from tests.support.openspec_lifecycle import completed_lifecycle

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _archived_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> OpenSpecLifecycle:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archived = lifecycle.apply_archive()
    assert archived["verdict"] == "pass", archived
    return lifecycle


def test_start_change_rolls_an_archived_owned_lane_to_a_new_commitment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree, branch, previous_lease = lifecycle.worktree, lifecycle.branch, lifecycle.lease
    archived_head = current_tracked_head(worktree)

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification without reopening archived work.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    current = current_tracked_head(worktree)
    lease = leases_by_branch(worktree)[branch]
    assert report["verdict"] == "pass", report
    assert report["state"] == "started"
    assert report["previous_head"] == archived_head
    assert report["head"] == current
    assert current != archived_head
    assert lease["expected_head"] == current
    assert lease["base_commitment_path"] == (
        "openspec/changes/hosted-verification-fix/commitment.toml"
    )
    assert integer(lease["epoch"]) == integer(previous_lease["epoch"]) + 1
    assert git(worktree, "status", "--short") == ""
    assert (
        prewrite_guard(
            root=worktree,
            paths=[worktree / "tests/governance/test_repository.py"],
            editor_root=worktree,
            require_editor_root=True,
        )["verdict"]
        == "pass"
    )


def test_start_change_rejects_a_different_holder_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:different")

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_actor_mismatch"]
    assert current_tracked_head(worktree) == archived_head
    assert not (worktree / "openspec/changes/hosted-verification-fix").exists()


def test_start_change_rejects_a_dirty_overlay_without_an_exact_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = _archived_lane(tmp_path, monkeypatch).worktree
    archived_head = current_tracked_head(worktree)
    target = worktree / "tests/governance/test_repository.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("forward fix\n", encoding="utf-8")
    git(worktree, "add", target.relative_to(worktree).as_posix())

    report = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_change_overlay_digest_required"]
    assert current_tracked_head(worktree) == archived_head
    assert git(worktree, "status", "--short")


def test_start_change_recovers_after_commit_before_commitment_rebind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _archived_lane(tmp_path, monkeypatch)
    worktree, branch, previous_lease = lifecycle.worktree, lifecycle.branch, lifecycle.lease
    archived_head = current_tracked_head(worktree)
    apply_rebind = rollover.rebind_lease_commitment
    monkeypatch.setattr(
        rollover,
        "rebind_lease_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected_after_commit")),
    )

    interrupted = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    committed_head = current_tracked_head(worktree)
    assert interrupted["state"] == "repair_required"
    assert interrupted["required_gaps"] == ["injected_after_commit"]
    assert committed_head != archived_head
    assert leases_by_branch(worktree)[branch]["expected_head"] == committed_head
    monkeypatch.setattr(rollover, "rebind_lease_commitment", apply_rebind)

    recovered = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair hosted verification.",
        scope=("tests/**",),
        expect_head=archived_head,
        apply=True,
    )

    lease = leases_by_branch(worktree)[branch]
    assert recovered["verdict"] == "pass", recovered
    assert recovered["state"] == "recovered"
    assert lease["base_commitment_path"] == (
        "openspec/changes/hosted-verification-fix/commitment.toml"
    )
    assert integer(lease["epoch"]) == integer(previous_lease["epoch"]) + 1

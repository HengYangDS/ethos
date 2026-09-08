from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from tests.support.openspec_lifecycle import OpenSpecLifecycle


@pytest.fixture(autouse=True)
def _avoid_unrelated_runtime_materialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep archive tests on lifecycle semantics, not self-host runtime setup."""
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.start.install_hook_launchers",
        lambda _root: {},
    )


def _stage_exact_archive(lifecycle: OpenSpecLifecycle) -> str:
    archive_path = "openspec/changes/archive/2026-08-04-fixture-change"
    target = lifecycle.worktree / archive_path
    target.parent.mkdir(parents=True, exist_ok=True)
    lifecycle.active.rename(target)
    git(lifecycle.worktree, "add", "--all")
    return archive_path


def _staged_postimage(root: Path, *, head: str, change: str) -> ArchivePostimage:
    with observe_worktree_postimage(root, previous=head) as observed:
        archive_root = next(
            path.rsplit("/", 1)[0]
            for path in observed.changed_paths
            if path.startswith("openspec/changes/archive/") and path.endswith("/proposal.md")
        )
        return ArchivePostimage(
            change=change,
            head=head,
            scope={
                "archive_path": archive_root,
                "changed_paths": observed.changed_paths,
                "tree": observed.tree,
            },
            active_present=False,
        )


def _compiled_archive_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[OpenSpecLifecycle, TransitionPlan, str, str]:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archive_path = _stage_exact_archive(lifecycle)
    tree = git(lifecycle.worktree, "write-tree")
    target = git(
        lifecycle.worktree,
        "commit-tree",
        tree,
        "-p",
        lifecycle.completed_head,
        "-m",
        "chore(openspec): archive fixture-change",
    )
    monkeypatch.setattr(
        archive_effect,
        "archive_postimage_scope_report",
        lambda *_args, **_kwargs: {"verdict": "pass", "archive_path": archive_path},
    )
    commitment = commitment_fixture(id="change:fixture-change")
    monkeypatch.setattr(
        archive_effect,
        "load_profile_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("archive plan must consume the resolved Commitment")
        ),
        raising=False,
    )
    plan = archive_effect.compile_archive_plan(
        lifecycle.worktree,
        lifecycle.branch,
        "fixture-change",
        lifecycle.completed_head,
        target,
        lifecycle.lease,
        commitment=commitment,
    )
    return lifecycle, plan, target, archive_path


def test_archive_plan_is_one_common_git_ref_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, archive_path = _compiled_archive_plan(tmp_path, monkeypatch)

    assert plan.policy["operation"] == "git.ref.compare-and-swap"
    assert plan.policy["transition"] == "openspec.archive"
    assert plan.policy["branch"] == lifecycle.branch
    update = git_effect_from_plan(plan).updates[f"refs/heads/{lifecycle.branch}"]
    assert (update.expected, update.desired) == (lifecycle.completed_head, target)
    values = plan.facts["values"]
    assert isinstance(values, Mapping)
    assert values["archive_path"] == archive_path


def test_archive_executor_replay_recognizes_the_durable_effect_without_reexecution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, archive_path = _compiled_archive_plan(tmp_path, monkeypatch)
    issued = archive_effect.execute_git_effect(
        lifecycle.worktree,
        plan,
        issuer=str(lifecycle.lease["holder_ref"]),
    )
    assert issued.predicate == "effect:git-ref-update"
    assert git(lifecycle.worktree, "rev-parse", "HEAD") == target

    monkeypatch.setattr(
        archive_effect, "execute_git_effect", lambda *_a, **_k: pytest.fail("replayed Git effect")
    )

    recovered, replayed = [
        archive_effect.complete_archive(
            lifecycle.worktree, lifecycle.branch, "fixture-change", plan, target, apply=True
        )
        for _ in range(2)
    ]

    assert (recovered["state"], replayed["state"]) == ("recognized", "recognized")
    assert (recovered["attestation"], replayed["attestation"]) == (
        issued.model_dump(mode="json"),
    ) * 2
    assert recovered["archive_path"] == archive_path
    assert (replayed["lease"], recovered["lease"]) == (lifecycle.lease,) * 2


def test_archive_common_effect_rejects_cas_drift_before_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, _archive_path = _compiled_archive_plan(tmp_path, monkeypatch)
    drift = git(
        lifecycle.worktree,
        "commit-tree",
        "HEAD^{tree}",
        "-p",
        lifecycle.completed_head,
        "-m",
        "drift",
    )
    git(
        lifecycle.worktree,
        "update-ref",
        f"refs/heads/{lifecycle.branch}",
        drift,
        lifecycle.completed_head,
    )

    with pytest.raises(ValueError, match=r"git_effect_(plan_prestate_stale|cas_mismatch)"):
        archive_effect.execute_git_effect(
            lifecycle.worktree,
            plan,
            issuer=str(lifecycle.lease["holder_ref"]),
        )

    assert git(lifecycle.worktree, "rev-parse", lifecycle.branch) == drift
    assert git(lifecycle.worktree, "rev-parse", lifecycle.branch) != target


def test_archive_change_blocks_when_the_work_lane_lease_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    with closing(sqlite3.connect(state_database(lifecycle.worktree))) as connection, connection:
        connection.execute("delete from leases where lane_ref = ?", (lifecycle.branch,))

    report = archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
        apply=True,
    )

    assert report["state"] == "lease_missing"
    assert report["required_gaps"] == [f"work_lane_missing_lease:{lifecycle.branch}"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        f"ethos lane lease reacquire --path {lifecycle.worktree.resolve().as_posix()} "
        "--holder-ref agent:test:case:agent-test "
        f"--root {lifecycle.worktree.resolve().as_posix()} --json",
        user_decision_required=True,
    )
    assert lifecycle.head == lifecycle.completed_head
    assert lifecycle.active.is_dir()


def test_staged_archive_recovery_resolves_intent_from_the_exact_source_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    _stage_exact_archive(lifecycle)
    monkeypatch.setattr(archive, "archive_postimage", _staged_postimage)
    resolve = Mock(wraps=archive.resolve_current_resolution)
    monkeypatch.setattr(archive, "resolve_current_resolution", resolve)

    report = archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
    )

    assert report["state"] == "ready_to_finalize_archive"
    assert resolve.call_count == 1
    assert resolve.call_args.kwargs["intent_tree_ref"] == lifecycle.completed_head


def test_archive_finalization_failure_restores_the_exact_staged_postimage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archive_path = _stage_exact_archive(lifecycle)
    index_tree = git(lifecycle.worktree, "write-tree")
    status = git(lifecycle.worktree, "status", "--short")
    monkeypatch.setattr(archive, "archive_postimage", _staged_postimage)
    monkeypatch.setattr(archive, "_archive_coordinate_gaps", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        archive_effect,
        "create_git_commit",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 1, "stdout": "", "stderr": "hook rejected"}
        )(),
    )

    report = archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
        apply=True,
    )

    assert report["required_gaps"] == ["openspec_archive_commit_failed"]
    assert report["effect_state"] == "mutated"
    assert report["compensation_state"] == "completed"
    assert git(lifecycle.worktree, "write-tree") == index_tree
    assert git(lifecycle.worktree, "status", "--short") == status
    assert (lifecycle.worktree / archive_path / "proposal.md").is_file()

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import cast

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
    monkeypatch.setattr(
        archive_effect,
        "load_profile_commitment",
        lambda *_args, **_kwargs: commitment_fixture(id="change:fixture-change"),
    )
    plan = archive_effect.compile_archive_plan(
        lifecycle.worktree,
        lifecycle.branch,
        "fixture-change",
        lifecycle.completed_head,
        target,
        lifecycle.lease,
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
    values = cast("dict[str, object]", plan.facts["values"])
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

    native_execute = archive_effect.execute_git_effect
    calls = {"execute": 0}

    def execute(*args: object, **kwargs: object):
        calls["execute"] += 1
        return native_execute(*args, **kwargs)

    monkeypatch.setattr(archive_effect, "execute_git_effect", execute)
    monkeypatch.setattr(
        archive,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"required_gaps": []},
    )

    recovered = archive_effect.complete_archive(
        lifecycle.worktree,
        lifecycle.branch,
        "fixture-change",
        plan,
        target,
        apply=True,
    )
    replayed = archive_effect.complete_archive(
        lifecycle.worktree,
        lifecycle.branch,
        "fixture-change",
        plan,
        target,
        apply=True,
    )

    assert recovered["state"] == "recognized"
    assert replayed["state"] == "recognized"
    assert calls == {"execute": 0}
    assert recovered["attestation"] == replayed["attestation"]
    assert recovered["attestation"]["predicate"] == "effect:git-ref-update"
    assert recovered["archive_path"] == archive_path
    for field in ("lane_ref", "holder_ref", "generation", "expires_at"):
        assert replayed["lease"][field] == recovered["lease"][field]


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
        "ethos lane status --json",
        user_decision_required=True,
    )
    assert lifecycle.head == lifecycle.completed_head
    assert lifecycle.active.is_dir()


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
        archive,
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

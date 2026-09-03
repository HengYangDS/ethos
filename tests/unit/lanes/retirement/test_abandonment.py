from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.abandonment as abandonment
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_abandonment_derives_the_common_retirement_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(abandonment, "repository_root", lambda root: root)
    monkeypatch.setattr(
        abandonment,
        "abandonment_coordinates",
        lambda *_args, **_kwargs: {
            "repository_common_dir": (tmp_path / ".git").as_posix(),
            "control_root": tmp_path.as_posix(),
            "branch": "work/source",
            "head": "a" * 40,
            "tree": "b" * 40,
            "accepted_branch": "dev",
            "accepted_head": "c" * 40,
            "worktree_path": (tmp_path / "lane").as_posix(),
            "worktree_initial": "linked",
            "lease_state": "valid",
            "lease": {
                "holder_ref": "agent:test:case:holder",
                "generation": 1,
                "expires_at": "2026-09-03T00:00:00+00:00",
            },
            "authority": {"kind": "owner", "actor": "agent:test:case:holder"},
        },
    )
    monkeypatch.setattr(
        abandonment,
        "compile_abandonment_plan",
        lambda *_args, **_kwargs: (
            tmp_path,
            SimpleNamespace(model_dump=lambda **_kwargs: {"digest": "d" * 64}),
        ),
    )

    def persist(_root: Path, request: object) -> dict[str, object]:
        captured["request"] = request
        return {"path": "/receipt", "sha256": "sha256:" + "e" * 64}

    monkeypatch.setattr(abandonment, "persist_operation", persist)

    report = abandonment.derive_lane_abandonment(
        root=tmp_path,
        branch="work/source",
        reason_code="duplicate-empty-lane",
        reason="duplicate empty lane",
    )

    request = captured["request"]
    assert request.mode == "abandon"
    assert request.effects == ("remove_worktree", "delete_ref", "revoke_lease")
    assert report["state"] == "derived"
    assert "ethos lane retire abandon" in report["next_action"]


def test_abandonment_rejects_active_foreign_holder_before_persisting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(abandonment, "repository_root", lambda root: root)
    monkeypatch.setattr(
        abandonment,
        "abandonment_coordinates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("foreign_work_lane_retire_authority_required")
        ),
    )
    monkeypatch.setattr(
        abandonment,
        "persist_operation",
        lambda *_args: pytest.fail("foreign authority must not persist a request"),
    )

    report = abandonment.derive_lane_abandonment(
        root=tmp_path,
        branch="work/source",
        reason_code="duplicate-empty-lane",
        reason="duplicate empty lane",
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]


def test_abandonment_apply_requires_authorization_before_loading_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        abandonment,
        "load_operation",
        lambda *_args: pytest.fail("unauthorized abandonment must not load or execute"),
    )

    report = abandonment.execute_lane_abandonment(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=False,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required"]


def test_real_abandonment_recovers_after_worktree_removal_and_git_spawn_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = "agent:test:case:abandonment-recovery"
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    lane = tmp_path / "repo-work-abandon"
    git(repo, "worktree", "add", "-b", "work/abandon", lane.as_posix(), "dev")
    (repo / "accepted.txt").write_text("accepted\n", encoding="utf-8")
    git(repo, "add", "accepted.txt")
    git(repo, "commit", "-m", "advance accepted independently")
    (lane / "abandoned.txt").write_text("abandoned\n", encoding="utf-8")
    git(lane, "add", "abandoned.txt")
    git(lane, "commit", "-m", "create abandoned lane")
    head = git(lane, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repo),
        lease=exact_lease(branch="work/abandon", holder_ref=actor),
    )
    monkeypatch.setenv("ETHOS_ACTOR", actor)

    derived = abandonment.derive_lane_abandonment(
        root=repo,
        branch="work/abandon",
        reason_code="duplicate-empty-lane",
        reason="duplicate empty lane",
    )
    receipt = derived["receipt"]
    original = operation.delete_operation_ref
    monkeypatch.setattr(
        operation,
        "delete_operation_ref",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_process_spawn_failed")),
    )

    partial = abandonment.execute_lane_abandonment(
        root=repo,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert partial["state"] == "partial_transition"
    assert partial["completed_effects"] == ["remove_worktree"]
    assert partial["remaining_effects"] == ["delete_ref", "revoke_lease"]
    assert not lane.exists()
    assert git(repo, "rev-parse", "work/abandon") == head
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"

    monkeypatch.setattr(operation, "delete_operation_ref", original)
    recovered = operation.recover_retirement_operation(
        root=repo,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )
    repeated = operation.recover_retirement_operation(
        root=repo,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert recovered["state"] == "retired"
    assert repeated["state"] == "retired"
    assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == "missing"

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.resolution._effects as effect_adapter
import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos.surface.cli.lane.resolution import _default_decision_path
from ethos_core.contracts.resolution.lane import LaneObservation
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import orphan_work_lane

_COMPETING_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000099"


def _decide(root: Path, decision_path: Path) -> dict[str, object]:
    return plan_lane_resolution(
        root=root,
        branch="work/orphan",
        disposition="retire",
        reason="Exercise exact ownerless cleanup recovery.",
        evidence_refs=("evidence:maintainer-decision",),
        chronicle_ref=write_chronicle_decision(
            root,
            topic="ownerless-cleanup-recovery-20260722",
            token="retire",
        ),
        recovery_plan="Recover only an exact durable completion.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )


def _ownerless_preflight(*, expected: Any, **_kwargs: object) -> dict[str, object]:
    decision = json.loads(expected.decision_bytes)
    return {
        "schema_version": "workstation.repo-family-governance.v1",
        "decision_sha256": hashlib.sha256(expected.decision_bytes).hexdigest(),
        "executor_ref": expected.executor_ref,
        "observation_digest": hashlib.sha256(
            json.dumps(expected.observation, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "chronicle_digest": decision["chronicle_digest"],
        "source": {"head": expected.accepted_head},
        "coordination": {"binding_digest": "d" * 64},
    }


def _setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, object], Path, Path]:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _decide(repo, decision_path)
    decision = planned["decision"]
    assert isinstance(decision, dict)
    observation = decision["observation"]
    assert isinstance(observation, dict)
    artifact_root = records_artifact_root(repo)
    target = record_store.target_digest(
        str(observation["lane_ref"]),
        str(observation["head"]),
    )
    ownerless_reservation = record_store.ownerless_closeout_reservation_path(
        repo,
        target,
        artifact_root=artifact_root,
    )
    receipt = record_store.receipt_path(
        repo,
        str(decision["decision_id"]),
        artifact_root=artifact_root,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:codex:thread:executor")
    monkeypatch.setattr(effect_adapter, "run_worktree_closeout_check", _ownerless_preflight)
    return repo, decision_path, decision, ownerless_reservation, receipt


def _apply(repo: Path, decision_path: Path) -> dict[str, object]:
    return apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=True,
        apply=True,
    )


def _receipt_snapshot(path: Path) -> tuple[int, bytes]:
    return path.stat().st_ino, path.read_bytes()


def _assert_cleanup_converged(
    *,
    report: dict[str, object],
    repo: Path,
    receipt: Path,
    snapshot: tuple[int, bytes],
    ownerless_reservation: Path,
) -> None:
    assert (report["ok"], report["state"], report["required_gaps"]) == (True, "retired", [])
    assert _receipt_snapshot(receipt) == snapshot
    assert not ownerless_reservation.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert not tuple((records_artifact_root(repo) / "receipts").glob(".*.receipt-reservation"))


def test_retry_converges_when_receipt_link_succeeds_but_directory_fsync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_fsync = vars(record_store)["_fsync_directory"]
    failed = False

    def fail_after_receipt_link(directory: Path) -> None:
        nonlocal failed
        linked = receipt.is_file()
        if directory == receipt.parent and linked and not failed:
            failed = True
            message = "receipt directory fsync interrupted"
            raise OSError(message)
        real_fsync(directory)

    monkeypatch.setattr(record_store, "_fsync_directory", fail_after_receipt_link)
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]
    assert receipt.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(record_store, "_fsync_directory", real_fsync)
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("exact receipt recovery must not rerun WCP"),
    )

    recovered = _apply(repo, decision_path)

    _assert_cleanup_converged(
        report=recovered,
        repo=repo,
        receipt=receipt,
        snapshot=snapshot,
        ownerless_reservation=ownerless_reservation,
    )


def test_retry_converges_after_fence_release_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_release = lane_adapter.release_closeout_fence
    monkeypatch.setattr(
        lane_adapter,
        "release_closeout_fence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fence retained")),
    )
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(lane_adapter, "release_closeout_fence", real_release)
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("exact receipt recovery must not rerun WCP"),
    )

    recovered = _apply(repo, decision_path)

    _assert_cleanup_converged(
        report=recovered,
        repo=repo,
        receipt=receipt,
        snapshot=snapshot,
        ownerless_reservation=ownerless_reservation,
    )


def test_retry_converges_after_reservation_unlink_failure_with_fence_already_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_unlink = Path.unlink
    failed = False

    def fail_ownerless_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal failed
        if path == ownerless_reservation and not failed:
            failed = True
            message = "reservation unlink interrupted"
            raise OSError(message)
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_ownerless_unlink)
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert ownerless_reservation.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(Path, "unlink", real_unlink)
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("exact receipt recovery must not rerun WCP"),
    )
    real_verify = vars(effect_adapter)["_verify_ownerless_postconditions"]
    verified_fences: list[dict[str, object] | None] = []

    def observe_verification(**kwargs: object) -> dict[str, object]:
        verified_fences.append(kwargs.get("fence"))
        return real_verify(**kwargs)

    monkeypatch.setattr(effect_adapter, "_verify_ownerless_postconditions", observe_verification)

    recovered = _apply(repo, decision_path)

    _assert_cleanup_converged(
        report=recovered,
        repo=repo,
        receipt=receipt,
        snapshot=snapshot,
        ownerless_reservation=ownerless_reservation,
    )
    assert verified_fences == [None]


@pytest.mark.parametrize(
    ("case", "expected_gap"),
    [
        ("binding_mismatch", "lane_resolution_ownerless_receipt_mismatch"),
        ("schema_invalid", "lane_resolution_receipt_invalid"),
    ],
)
def test_retry_blocks_invalid_or_mismatched_existing_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected_gap: str,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        lane_adapter,
        "release_closeout_fence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fence retained")),
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    if case == "binding_mismatch":
        payload["ownerless_closeout_binding"]["accepted_head"] = "f" * 40
    else:
        payload["unexpected"] = True
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("mismatched receipt must block before WCP"),
    )

    blocked = _apply(repo, decision_path)

    assert (blocked["ok"], blocked["state"], blocked["required_gaps"]) == (
        False,
        "partial_transition",
        [expected_gap],
    )
    assert ownerless_reservation.is_file()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None


def test_retry_blocks_a_different_fence_after_cleanup_was_partially_released(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, ownerless_reservation, _receipt = _setup(tmp_path, monkeypatch)
    observation = decision["observation"]
    assert isinstance(observation, dict)
    real_unlink = Path.unlink
    failed = False

    def fail_ownerless_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal failed
        if path == ownerless_reservation and not failed:
            failed = True
            message = "reservation unlink interrupted"
            raise OSError(message)
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_ownerless_unlink)
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    monkeypatch.setattr(Path, "unlink", real_unlink)
    acquire_closeout_fence(
        state_database(repo),
        subject="work/orphan",
        expected_head=str(observation["head"]),
        decision_id=_COMPETING_DECISION_ID,
        executor_ref="agent:codex:thread:competitor",
        accepted_branch="dev",
        accepted_head=git(repo, "rev-parse", "dev"),
        target_path=str(observation["path"]),
        lane_incarnation_id=str(observation["lane_incarnation_id"]),
        observation_digest=str(decision["observation_digest"]),
        decision_sha256="1" * 64,
        chronicle_digest="2" * 64,
        wcp_schema_version="workstation.repo-family-governance.v1",
        wcp_decision_sha256="1" * 64,
        wcp_binding_digest="3" * 64,
    )

    blocked = _apply(repo, decision_path)

    assert blocked["required_gaps"] == ["lane_resolution_ownerless_fence_stale"]
    assert ownerless_reservation.is_file()


def _completed_with_retained_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, dict[str, object], LaneObservation, dict[str, object], dict[str, object]]:
    repo, decision_path, decision, ownerless_reservation, receipt_path = _setup(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(
        lane_adapter,
        "release_closeout_fence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fence retained")),
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    observation = LaneObservation.model_validate(decision["observation"])
    reservation = record_store.read_ownerless_closeout_reservation(
        record_root=records_artifact_root(repo),
        path=ownerless_reservation,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return repo, decision_path, decision, observation, reservation, receipt


def test_retry_converges_when_ownerless_reservation_unlink_precedes_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_fsync = vars(record_store)["_fsync_directory"]
    failed = False

    def fail_after_ownerless_unlink(directory: Path) -> None:
        nonlocal failed
        if (
            directory == ownerless_reservation.parent
            and receipt.is_file()
            and not ownerless_reservation.exists()
            and not failed
        ):
            failed = True
            message = "ownerless reservation directory fsync interrupted"
            raise OSError(message)
        real_fsync(directory)

    monkeypatch.setattr(record_store, "_fsync_directory", fail_after_ownerless_unlink)
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert receipt.is_file()
    assert not ownerless_reservation.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(record_store, "_fsync_directory", real_fsync)
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("receipt-first recovery must not rerun WCP"),
    )

    recovered = _apply(repo, decision_path)

    _assert_cleanup_converged(
        report=recovered,
        repo=repo,
        receipt=receipt,
        snapshot=snapshot,
        ownerless_reservation=ownerless_reservation,
    )


def test_retry_rejects_unverifiable_fence_absence_even_with_exact_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, _receipt = _setup(tmp_path, monkeypatch)
    real_unlink = Path.unlink
    failed = False

    def fail_ownerless_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal failed
        if path == ownerless_reservation and not failed:
            failed = True
            message = "reservation unlink interrupted"
            raise OSError(message)
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_ownerless_unlink)
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    monkeypatch.setattr(Path, "unlink", real_unlink)
    database = state_database(repo)
    assert database.is_file()
    database.unlink()

    blocked = _apply(repo, decision_path)

    assert (blocked["ok"], blocked["state"], blocked["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_ownerless_fence_unverifiable"],
    )
    assert ownerless_reservation.is_file()


def test_retry_maps_malformed_fence_schema_to_stable_unverifiable_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_unlink = Path.unlink
    failed = False

    def fail_ownerless_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal failed
        if path == ownerless_reservation and not failed:
            failed = True
            message = "reservation unlink interrupted"
            raise OSError(message)
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_ownerless_unlink)
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert ownerless_reservation.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(Path, "unlink", real_unlink)
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute("drop index closeout_fences_subject_unique")
    monkeypatch.setattr(
        effect_adapter,
        "run_worktree_closeout_check",
        lambda **_kwargs: pytest.fail("receipt-first recovery must not rerun WCP"),
    )

    blocked = _apply(repo, decision_path)

    assert (blocked["ok"], blocked["state"], blocked["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_ownerless_fence_unverifiable"],
    )
    assert ownerless_reservation.is_file()
    assert _receipt_snapshot(receipt) == snapshot


def test_completed_recovery_requires_exact_receipt_to_accept_an_absent_fence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, observation, reservation, receipt = (
        _completed_with_retained_cleanup(tmp_path, monkeypatch)
    )
    binding = receipt["ownerless_closeout_binding"]
    assert isinstance(binding, dict)
    release_closeout_fence(
        state_database(repo),
        subject=observation.lane_ref,
        decision_id=str(decision["decision_id"]),
        target_binding_digest=str(binding["target_binding_digest"]),
    )

    recovered = effect_adapter.recover_completed_ownerless_closeout(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=str(binding["executor_ref"]),
        reservation=reservation,
        receipt=receipt,
    )
    assert recovered == binding

    tampered = json.loads(json.dumps(receipt))
    tampered["ownerless_closeout_binding"]["accepted_head"] = "f" * 40
    with pytest.raises(
        effect_adapter.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_receipt_mismatch",
    ):
        effect_adapter.recover_completed_ownerless_closeout(
            root=repo,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            executor_ref=str(binding["executor_ref"]),
            reservation=reservation,
            receipt=tampered,
        )


def test_completed_recovery_rejects_noncanonical_initial_decision_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, observation, reservation, _receipt = (
        _completed_with_retained_cleanup(tmp_path, monkeypatch)
    )
    tampered = dict(decision)
    tampered["reason"] = "A different caller-side decision."

    with pytest.raises(
        effect_adapter.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_decision_stale",
    ):
        effect_adapter.recover_completed_ownerless_closeout(
            root=repo,
            decision_path=decision_path,
            decision=tampered,
            observation=observation,
            executor_ref=str(reservation["executor_ref"]),
            reservation=reservation,
        )


def test_completed_recovery_reads_decision_bytes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, observation, reservation, _receipt = (
        _completed_with_retained_cleanup(tmp_path, monkeypatch)
    )
    real_read_bytes = Path.read_bytes
    reads = 0

    def count_decision_read(path: Path) -> bytes:
        nonlocal reads
        if path == decision_path:
            reads += 1
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", count_decision_read)
    effect_adapter.recover_completed_ownerless_closeout(
        root=repo,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        executor_ref=str(reservation["executor_ref"]),
        reservation=reservation,
    )

    assert reads == 1

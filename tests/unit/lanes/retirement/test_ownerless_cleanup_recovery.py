from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.resolution._effects as effect_adapter
import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos.adapters.mutation.resolution._shared import current_chronicle_matches
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos.surface.cli.lane.resolution import _default_decision_path
from ethos_core.contracts.resolution.lane import LaneObservation
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    from collections.abc import Callable

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
    artifact_root = current_record_root(repo)
    target = reservation_store.target_digest(
        str(observation["lane_ref"]),
        str(observation["head"]),
    )
    ownerless_reservation = reservation_store.ownerless_closeout_reservation_path(
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


def _fail_one_directory_fsync(
    monkeypatch: pytest.MonkeyPatch,
    directory: Path,
    *,
    ready: Callable[[], bool],
    message: str,
) -> Callable[[int], None]:
    original = record_io.os.fsync
    failed = False

    def fail(descriptor: int) -> None:
        nonlocal failed
        metadata = record_io.os.fstat(descriptor)
        directory_metadata = directory.stat() if directory.exists() else None
        exact_directory = directory_metadata is not None and (
            metadata.st_dev,
            metadata.st_ino,
        ) == (directory_metadata.st_dev, directory_metadata.st_ino)
        if exact_directory and ready() and not failed:
            failed = True
            raise OSError(message)
        original(descriptor)

    monkeypatch.setattr(record_io.os, "fsync", fail)
    return original


def _fail_one_record_unlink(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
    *,
    ready: Callable[[], bool],
) -> Callable[..., None]:
    original = record_io.os.unlink
    prefix = f".{target.name}."
    failed = False

    def fail(path: object, *, dir_fd: int | None = None) -> None:
        nonlocal failed
        metadata = record_io.os.fstat(dir_fd) if dir_fd is not None else None
        parent = target.parent.stat() if target.parent.exists() else None
        exact_tombstone = (
            metadata is not None
            and parent is not None
            and (metadata.st_dev, metadata.st_ino) == (parent.st_dev, parent.st_ino)
            and prefix in str(path)
            and ".cas." in str(path)
            and str(path).endswith(".delete")
        )
        if exact_tombstone and ready() and not failed:
            failed = True
            message = "reservation unlink interrupted"
            raise OSError(message)
        original(path, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "unlink", fail)
    return original


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
    assert not tuple((current_record_root(repo) / "receipts").glob(".*.receipt-reservation"))


def test_retry_converges_when_receipt_write_fails_after_durable_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_write = lane_adapter.write_resolution_receipt

    def write_then_fail(**kwargs: Any) -> str:
        real_write(**kwargs)
        message = "receipt writer interrupted after durable link"
        raise OSError(message)

    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", write_then_fail)
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]
    assert receipt.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", real_write)
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
    real_unlink = _fail_one_record_unlink(
        monkeypatch,
        ownerless_reservation,
        ready=receipt.is_file,
    )
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    assert ownerless_reservation.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(record_io.os, "unlink", real_unlink)
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


def test_receipt_sidecar_swap_reports_release_gap_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    sidecar = receipt.with_name(f".{receipt.stem}.receipt-reservation")
    original_stage = record_io._stage_expected_record  # noqa: SLF001, RUF100
    swapped = False

    def swap_before_stage(
        parent: object,
        locked_descriptor: int,
        expected: bytes,
        staging: str,
    ) -> record_io.posix.FileIdentity:
        nonlocal swapped
        if parent.destination == sidecar and receipt.is_file() and not swapped:
            sidecar.unlink()
            sidecar.write_bytes(expected)
            swapped = True
        return original_stage(parent, locked_descriptor, expected, staging)

    monkeypatch.setattr(record_io, "_stage_expected_record", swap_before_stage)

    first = _apply(repo, decision_path)

    assert swapped is True
    assert (first["ok"], first["state"], first["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_receipt_reservation_release_failed"],
    )
    assert receipt.is_file()
    snapshot = _receipt_snapshot(receipt)
    assert sidecar.read_bytes() == f"{decision['decision_id']}\n".encode()
    assert not ownerless_reservation.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    monkeypatch.setattr(record_io, "_stage_expected_record", original_stage)
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


@pytest.mark.parametrize(
    ("case", "expected_state", "expected_gap"),
    [
        (
            "binding_mismatch",
            "partial_transition",
            "lane_resolution_ownerless_receipt_mismatch",
        ),
        ("schema_invalid", "blocked", "lane_resolution_current_record_invalid"),
    ],
)
def test_retry_blocks_invalid_or_mismatched_existing_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected_state: str,
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
        expected_state,
        [expected_gap],
    )
    assert ownerless_reservation.is_file()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None


def test_retry_blocks_a_different_fence_after_cleanup_was_partially_released(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    observation = decision["observation"]
    assert isinstance(observation, dict)
    real_unlink = _fail_one_record_unlink(
        monkeypatch,
        ownerless_reservation,
        ready=receipt.is_file,
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    monkeypatch.setattr(record_io.os, "unlink", real_unlink)
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
    reservation = reservation_store.read_ownerless_closeout_reservation(
        record_root=current_record_root(repo),
        path=ownerless_reservation,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return repo, decision_path, decision, observation, reservation, receipt


def test_retry_converges_when_ownerless_reservation_unlink_precedes_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_fsync = _fail_one_directory_fsync(
        monkeypatch,
        ownerless_reservation.parent,
        ready=lambda: receipt.is_file() and not ownerless_reservation.exists(),
        message="ownerless reservation directory fsync interrupted",
    )
    first = _apply(repo, decision_path)

    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert receipt.is_file()
    assert not ownerless_reservation.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is None
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(record_io.os, "fsync", real_fsync)
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
    repo, decision_path, _decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_unlink = _fail_one_record_unlink(
        monkeypatch,
        ownerless_reservation,
        ready=receipt.is_file,
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    monkeypatch.setattr(record_io.os, "unlink", real_unlink)
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
    real_unlink = _fail_one_record_unlink(
        monkeypatch,
        ownerless_reservation,
        ready=receipt.is_file,
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_ownerless_cleanup_failed"]
    assert ownerless_reservation.is_file()
    snapshot = _receipt_snapshot(receipt)
    monkeypatch.setattr(record_io.os, "unlink", real_unlink)
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


def test_completed_recovery_rejects_chronicle_drift_before_receipt_write_or_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, decision_path, decision, ownerless_reservation, receipt = _setup(tmp_path, monkeypatch)
    real_write = lane_adapter.write_resolution_receipt
    monkeypatch.setattr(
        lane_adapter,
        "write_resolution_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("receipt write interrupted")),
    )
    first = _apply(repo, decision_path)
    assert first["required_gaps"] == ["lane_resolution_receipt_write_failed_after_effect"]
    assert ownerless_reservation.is_file()
    assert not receipt.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None

    chronicle = repo / str(decision["chronicle_ref"])
    chronicle.write_text(
        chronicle.read_text(encoding="utf-8") + "mutated after completed effect\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lane_adapter, "write_resolution_receipt", real_write)

    blocked = _apply(repo, decision_path)

    assert (blocked["ok"], blocked["state"], blocked["required_gaps"]) == (
        False,
        "partial_transition",
        ["lane_resolution_ownerless_chronicle_stale"],
    )
    assert ownerless_reservation.is_file()
    assert not receipt.exists()
    assert get_closeout_fence(state_database(repo), subject="work/orphan") is not None


def test_current_chronicle_match_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    chronicle = root / "evidence/chronicle/fifo.md"
    chronicle.parent.mkdir(parents=True)
    os.mkfifo(chronicle)
    decision = {
        "chronicle_ref": "evidence/chronicle/fifo.md",
        "chronicle_digest": "0" * 64,
        "disposition": "retire",
    }
    script = (
        "import json\n"
        "from pathlib import Path\n"
        "from ethos.adapters.mutation.resolution._shared import current_chronicle_matches\n"
        f"root = Path({root.as_posix()!r})\n"
        f"decision = json.loads({json.dumps(decision)!r})\n"
        "raise SystemExit(1 if current_chronicle_matches(root, decision) else 0)\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=1,
    )

    assert completed.returncode == 0, completed.stderr
    assert current_chronicle_matches(root, decision) is False

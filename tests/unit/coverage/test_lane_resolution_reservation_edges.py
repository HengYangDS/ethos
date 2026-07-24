from __future__ import annotations

import importlib
import importlib.util
import json
import threading
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"


def test_ownerless_reservation_storage_has_one_defining_module() -> None:
    reservations = importlib.import_module(
        "ethos.adapters.mutation.resolution.records.reservations"
    )
    ownerless_symbols = (
        "validate_ownerless_closeout_reservation",
        "target_digest",
        "ownerless_closeout_reservation_path",
        "read_ownerless_closeout_reservation",
        "reserve_ownerless_closeout_target",
        "transition_ownerless_closeout_reservation",
        "ownerless_closeout_recovery_binding",
        "release_ownerless_closeout_reservation",
        "release_ownerless_no_effect_reservation",
    )

    assert all(symbol in vars(reservations) for symbol in ownerless_symbols)
    assert all(symbol not in vars(record_store) for symbol in ownerless_symbols)
    assert "canonical_ownerless_closeout_reservation" not in vars(reservations)
    assert importlib.util.find_spec("ethos.adapters.mutation.resolution.records.release") is None


def _reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-record-edges", "a" * 40
    return {
        "schema_version": 2,
        "decision_id": _DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:record-edges",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": reservation_store.target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _partial_reservation(
    root: Path,
) -> tuple[Path, dict[str, object], Path, dict[str, object]]:
    record_root = root / "records"
    reservation = _reservation()
    path = reservation_store.reserve_ownerless_closeout_target(
        root=root,
        reservation=reservation,
        artifact_root=record_root,
    )
    reservation_store.transition_ownerless_closeout_reservation(
        root=root,
        expected=reservation,
        phase="receipt",
        recovery_state="effect_complete_receipt_missing",
        postcondition_digest="f" * 64,
        artifact_root=record_root,
    )
    binding = reservation_store.ownerless_closeout_recovery_binding(
        root=root,
        expected=reservation,
        artifact_root=record_root,
    )
    return record_root, reservation, path, binding


def _write_completion_receipt(
    root: Path,
    record_root: Path,
    reservation: dict[str, object],
    binding: dict[str, object],
    *,
    valid: bool = True,
) -> Path:
    destination = record_store.receipt_path(
        root,
        str(reservation["decision_id"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        {
            "schema_version": 3,
            "receipt_id": "lane-resolution-receipt:record-edge",
            "completed": True,
            "decision_id": reservation["decision_id"],
            "state": "retired",
            "observation_digest": "0" * 64,
            "reconciliation_required": True,
            "lane_ref": reservation["lane_ref"],
            "head": reservation["head"],
            "preservation_package": "",
            "preservation_manifest_sha256": "",
            "ownerless_closeout_binding": binding,
            "mints_authority": False,
        }
        if valid
        else {}
    )
    destination.write_text(json.dumps(payload), encoding="utf-8")
    return destination


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": 1},
        {"schema_version": True},
        {"decision_sha256": "g" * 64},
        {"lane_ref": ""},
        {"decision_id": "invalid"},
        {"executor_ref": "invalid"},
        {"head": "g" * 40},
        {"target_digest": "f" * 64},
        {"phase": "invalid"},
        {"postcondition_digest": None},
        {"phase": "unknown", "recovery_state": "transition_unknown"},
        {"wcp_schema_version": "workstation.repo-family-governance.v1"},
        {"wcp_decision_sha256": "b" * 64},
        {"wcp_binding_digest": "c" * 64},
    ],
)
def test_ownerless_reservation_rejects_invalid_identity_or_state(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    reservation = dict(_reservation(), **updates)

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=reservation,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_rejects_non_exact_shape(tmp_path: Path) -> None:
    reservation = _reservation()
    reservation["unexpected"] = "field"

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=reservation,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_rejects_noncanonical_executor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ParsedHolder:
        @staticmethod
        def serialize() -> str:
            return "agent:codex:thread:canonical"

    monkeypatch.setattr(HolderRef, "parse", lambda _value: ParsedHolder())

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=_reservation(),
            artifact_root=tmp_path / "records",
        )


@pytest.mark.parametrize(
    ("phase", "recovery_state", "postcondition_digest"),
    [
        ("unknown", "transition_unknown", "invalid"),
        ("receipt", "effect_complete_receipt_missing", ""),
    ],
)
def test_ownerless_transition_rejects_invalid_classification_before_mutation(
    tmp_path: Path,
    phase: str,
    recovery_state: str,
    postcondition_digest: str,
) -> None:
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=_reservation(),
            phase=phase,
            recovery_state=recovery_state,
            postcondition_digest=postcondition_digest,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_reader_rejects_unsafe_path_and_invalid_json(
    tmp_path: Path,
) -> None:
    record_root = tmp_path / "records"
    outside = tmp_path / "outside.json"
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        reservation_store.read_ownerless_closeout_reservation(
            record_root=record_root,
            path=outside,
        )

    destination = reservation_store.ownerless_closeout_reservation_path(
        tmp_path,
        str(_reservation()["target_digest"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True)
    destination.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store.read_ownerless_closeout_reservation(
            record_root=record_root,
            path=destination,
        )


@pytest.mark.parametrize("checks", [(True, False), (True, True, False)])
def test_ownerless_transition_preserves_record_when_replace_path_becomes_unsafe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    checks: tuple[bool, ...],
) -> None:
    record_root = tmp_path / "records"
    reservation = _reservation()
    path = reservation_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    safety = iter(checks)

    def safe(*_args: object) -> bool:
        return next(safety)

    monkeypatch.setattr(reservation_store, "record_destination_safe", safe)
    monkeypatch.setattr(record_store, "record_destination_safe", safe)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        reservation_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            phase="unknown",
            recovery_state="transition_unknown",
            artifact_root=record_root,
        )

    assert json.loads(path.read_text(encoding="utf-8")) == reservation


def test_ownerless_transition_serializes_exact_compare_and_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    reservation = _reservation()
    path = reservation_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    first_at_replace = threading.Event()
    release_first = threading.Event()
    original_replace = reservation_store.replace_json_atomic

    def pause_first_replace(
        destination: Path,
        payload: dict[str, object],
        *,
        record_root: Path,
    ) -> None:
        if threading.current_thread().name == "first-transition":
            first_at_replace.set()
            assert release_first.wait(timeout=2)
        original_replace(destination, payload, record_root=record_root)

    monkeypatch.setattr(reservation_store, "replace_json_atomic", pause_first_replace)
    completed: list[str] = []
    errors: dict[str, ValueError] = {}

    def transition(name: str, phase: str, recovery_state: str) -> None:
        try:
            reservation_store.transition_ownerless_closeout_reservation(
                root=tmp_path,
                expected=reservation,
                phase=phase,
                recovery_state=recovery_state,
                artifact_root=record_root,
            )
        except ValueError as error:
            errors[name] = error
        else:
            completed.append(name)

    first = threading.Thread(
        target=transition,
        args=("first", "unknown", "transition_unknown"),
        name="first-transition",
    )
    second = threading.Thread(
        target=transition,
        args=("second", "effect", "worktree_removed_ref_present"),
        name="second-transition",
    )
    first.start()
    assert first_at_replace.wait(timeout=2)
    second.start()
    second.join(timeout=1)
    assert not second.is_alive()
    release_first.set()
    first.join(timeout=2)

    assert not first.is_alive()
    assert completed == ["first"]
    assert str(errors["second"]) == "lane_resolution_ownerless_reservation_busy"
    assert json.loads(path.read_text(encoding="utf-8"))["recovery_state"] == ("transition_unknown")


def test_ownerless_no_effect_release_cannot_delete_effect_started_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    reservation = _reservation()
    path = reservation_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    effect_at_replace = threading.Event()
    allow_effect = threading.Event()
    original_replace = reservation_store.replace_json_atomic

    def pause_effect_replace(
        destination: Path,
        payload: dict[str, object],
        *,
        record_root: Path,
    ) -> None:
        if threading.current_thread().name == "effect-transition":
            effect_at_replace.set()
            assert allow_effect.wait(timeout=2)
        original_replace(destination, payload, record_root=record_root)

    monkeypatch.setattr(reservation_store, "replace_json_atomic", pause_effect_replace)
    completed: list[str] = []
    release_errors: list[ValueError] = []

    def release() -> None:
        try:
            reservation_store.release_ownerless_no_effect_reservation(
                root=tmp_path,
                expected=reservation,
                artifact_root=record_root,
            )
        except ValueError as error:
            release_errors.append(error)
        else:
            completed.append("release")

    def transition() -> None:
        reservation_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            phase="effect",
            recovery_state="worktree_removed_ref_present",
            artifact_root=record_root,
        )
        completed.append("transition")

    effect = threading.Thread(target=transition, name="effect-transition")
    releasing = threading.Thread(target=release, name="no-effect-release")
    effect.start()
    assert effect_at_replace.wait(timeout=2)
    releasing.start()
    releasing.join(timeout=1)
    assert not releasing.is_alive()
    allow_effect.set()
    effect.join(timeout=2)

    assert not effect.is_alive()
    assert completed == ["transition"]
    assert len(release_errors) == 1
    assert str(release_errors[0]) == "lane_resolution_ownerless_reservation_busy"
    assert json.loads(path.read_text(encoding="utf-8"))["recovery_state"] == (
        "worktree_removed_ref_present"
    )


@pytest.mark.parametrize(
    "immutable_update",
    [
        {"executor_ref": "agent:codex:thread:other"},
        {"accepted_head": "1" * 40},
        {"target_binding_digest": "0" * 64},
    ],
)
def test_ownerless_transition_cas_rejects_immutable_mismatch_without_changing_bytes(
    tmp_path: Path,
    immutable_update: dict[str, object],
) -> None:
    record_root = tmp_path / "records"
    reservation = _reservation()
    path = reservation_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    before = path.read_bytes()

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_mismatch"):
        reservation_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=dict(reservation, **immutable_update),
            phase="unknown",
            recovery_state="transition_unknown",
            artifact_root=record_root,
        )

    assert path.read_bytes() == before


def test_ownerless_release_rejects_unsafe_or_unreadable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, reservation, _path, _binding = _partial_reservation(tmp_path)
    safety = iter((True, False))
    monkeypatch.setattr(
        reservation_store,
        "record_destination_safe",
        lambda *_args: next(safety),
    )
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        reservation_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    monkeypatch.undo()
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        reservation_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )


def test_ownerless_release_rejects_mismatched_receipt_and_unsafe_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, reservation, _path, binding = _partial_reservation(tmp_path)
    destination = _write_completion_receipt(
        tmp_path,
        record_root,
        reservation,
        binding,
        valid=False,
    )
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        reservation_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    destination.unlink()
    _write_completion_receipt(tmp_path, record_root, reservation, binding)
    safety = iter((True, True, False))

    def safe(*_args: object) -> bool:
        return next(safety)

    monkeypatch.setattr(reservation_store, "record_destination_safe", safe)
    monkeypatch.setattr(record_store, "record_destination_safe", safe)
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        reservation_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )


@pytest.mark.parametrize("case", ["five-field", "unversioned"])
def test_ownerless_release_requires_canonical_completion_receipt(
    tmp_path: Path,
    case: str,
) -> None:
    record_root, reservation, reservation_path, binding = _partial_reservation(tmp_path)
    destination = record_store.receipt_path(
        tmp_path,
        str(reservation["decision_id"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 3,
        "receipt_id": "lane-resolution-receipt:record-edge",
        "decision_id": reservation["decision_id"],
        "completed": True,
        "state": "retired",
        "observation_digest": "0" * 64,
        "reconciliation_required": True,
        "lane_ref": reservation["lane_ref"],
        "head": reservation["head"],
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "ownerless_closeout_binding": binding,
        "mints_authority": False,
    }
    if case == "five-field":
        payload = {
            field: payload[field]
            for field in (
                "completed",
                "decision_id",
                "lane_ref",
                "head",
                "ownerless_closeout_binding",
            )
        }
    else:
        del payload["schema_version"]
    destination.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        reservation_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    assert reservation_path.is_file()

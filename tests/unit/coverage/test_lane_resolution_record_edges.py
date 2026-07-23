from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store

if TYPE_CHECKING:
    from pathlib import Path


_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"


def _reservation() -> dict[str, object]:
    lane_ref, head = "work/20260722-record-edges", "a" * 40
    return {
        "schema_version": 1,
        "decision_id": _DECISION_ID,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:record-edges",
        "wcp_schema_version": "workstation.repo-family-governance.v1",
        "wcp_decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "wcp_binding_digest": "d" * 64,
        "target_digest": record_store.target_digest(lane_ref, head),
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
    path = record_store.reserve_ownerless_closeout_target(
        root=root,
        reservation=reservation,
        artifact_root=record_root,
    )
    record_store.transition_ownerless_closeout_reservation(
        root=root,
        expected=reservation,
        phase="receipt",
        recovery_state="effect_complete_receipt_missing",
        postcondition_digest="f" * 64,
        artifact_root=record_root,
    )
    binding = record_store.ownerless_closeout_recovery_binding(
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
            "schema_version": 2,
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
        {"schema_version": True},
        {"wcp_schema_version": "workstation.repo-family-governance.v2"},
        {"lane_ref": ""},
        {"decision_id": "invalid"},
        {"executor_ref": "invalid"},
        {"head": "g" * 40},
        {"wcp_decision_sha256": "g" * 64},
        {"target_digest": "f" * 64},
        {"phase": "invalid"},
        {"postcondition_digest": None},
        {"phase": "unknown", "recovery_state": "transition_unknown"},
    ],
)
def test_ownerless_reservation_rejects_invalid_identity_or_state(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    reservation = dict(_reservation(), **updates)

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
            root=tmp_path,
            reservation=reservation,
            artifact_root=tmp_path / "records",
        )


def test_ownerless_reservation_rejects_non_exact_shape(tmp_path: Path) -> None:
    reservation = _reservation()
    reservation["unexpected"] = "field"

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
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

    monkeypatch.setattr(record_store.HolderRef, "parse", lambda _value: ParsedHolder())

    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.reserve_ownerless_closeout_target(
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
        record_store.transition_ownerless_closeout_reservation(
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
        record_store.read_ownerless_closeout_reservation(
            record_root=record_root,
            path=outside,
        )

    destination = record_store.ownerless_closeout_reservation_path(
        tmp_path,
        str(_reservation()["target_digest"]),
        artifact_root=record_root,
    )
    destination.parent.mkdir(parents=True)
    destination.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        record_store.read_ownerless_closeout_reservation(
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
    path = record_store.reserve_ownerless_closeout_target(
        root=tmp_path,
        reservation=reservation,
        artifact_root=record_root,
    )
    safety = iter(checks)
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.transition_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            phase="unknown",
            recovery_state="transition_unknown",
            artifact_root=record_root,
        )

    assert json.loads(path.read_text(encoding="utf-8")) == reservation


def test_ownerless_release_rejects_unsafe_or_unreadable_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, reservation, _path, _binding = _partial_reservation(tmp_path)
    safety = iter((True, False))
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    monkeypatch.undo()
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_release_invalid"):
        record_store.release_ownerless_closeout_reservation(
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
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    destination.unlink()
    _write_completion_receipt(tmp_path, record_root, reservation, binding)
    safety = iter((True, True, False))
    monkeypatch.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.release_ownerless_closeout_reservation(
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
        "schema_version": 2,
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
        record_store.release_ownerless_closeout_reservation(
            root=tmp_path,
            expected=reservation,
            artifact_root=record_root,
        )

    assert reservation_path.is_file()


def _receipt_reservation_paths(root: Path) -> tuple[Path, Path, Path]:
    record_root = root / "records"
    destination = record_store.receipt_path(
        root,
        _DECISION_ID,
        artifact_root=record_root,
    )
    reservation = destination.with_name(f".{destination.stem}.receipt-reservation")
    reservation.parent.mkdir(parents=True)
    return record_root, destination, reservation


def test_receipt_reservation_reuse_rejects_pre_read_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")

    with monkeypatch.context() as scoped:
        safety = iter((True, True, True, True, False))
        scoped.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )

    def occupy_before_reuse(*_args: object) -> int:
        destination.write_text("occupied", encoding="utf-8")
        raise FileExistsError(reservation)

    with monkeypatch.context() as scoped:
        scoped.setattr(record_store.os, "open", occupy_before_reuse)
        with pytest.raises(FileExistsError):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )
    destination.unlink()

    def fail_both_opens(_path: object, flags: int, *_args: object) -> int:
        if flags & record_store.os.O_EXCL:
            raise FileExistsError(reservation)
        raise OSError

    with monkeypatch.context() as scoped:
        scoped.setattr(record_store.os, "open", fail_both_opens)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )


def test_receipt_reservation_reuse_rejects_post_read_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")

    with monkeypatch.context() as scoped:
        safety = iter((True, True, True, True, True, True, False))
        scoped.setattr(record_store, "record_destination_safe", lambda *_args: next(safety))
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=_DECISION_ID,
                artifact_root=record_root,
            )

    original_read = record_store.os.read

    def occupy_destination(descriptor: int, length: int) -> bytes:
        content = original_read(descriptor, length)
        destination.write_text("occupied", encoding="utf-8")
        return content

    monkeypatch.setattr(record_store.os, "read", occupy_destination)
    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
        )

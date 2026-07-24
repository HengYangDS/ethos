"""Immutable local record storage and receipt reservations."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation

_RECEIPTS = "receipts"
_CLEARS = "clears"
_RESERVATIONS = "reservations"
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_RECEIPT_RESERVATION_SUFFIX = ".receipt-reservation"
_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_OWNERLESS_RESERVATION_INVALID = "lane_resolution_ownerless_reservation_invalid"
_OWNERLESS_RESERVATION_MISMATCH = "lane_resolution_ownerless_reservation_mismatch"
_OWNERLESS_RECOVERY_BINDING_MISMATCH = "lane_resolution_ownerless_recovery_binding_mismatch"
_OWNERLESS_RECOVERY_NOT_FINALIZABLE = "lane_resolution_ownerless_recovery_not_finalizable"
_OWNERLESS_RESERVATION_RELEASE_INVALID = "lane_resolution_ownerless_reservation_release_invalid"
_RESERVATION_STATE_FIELDS = {"phase", "recovery_state", "postcondition_digest"}
_IMMUTABLE_RESERVATION_FIELDS = tuple(
    field
    for field in OwnerlessCloseoutReservation.model_fields
    if field not in _RESERVATION_STATE_FIELDS
)


def _ownerless_reservation_invalid() -> ValueError:
    return ValueError(_OWNERLESS_RESERVATION_INVALID)


def receipt_path(
    root: Path,
    decision_id: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return the deterministic immutable receipt path."""
    return record_path(root, _RECEIPTS, decision_id, artifact_root=artifact_root)


def clear_receipt_path(root: Path, decision_id: str) -> Path:
    """Return the deterministic irreversible-clear receipt path."""
    return record_path(root, _CLEARS, decision_id)


def target_digest(lane_ref: str, head: str) -> str:
    """Bind one exact lane ref and head without ambiguous concatenation."""
    return hashlib.sha256(f"{lane_ref}\0{head}".encode()).hexdigest()


def ownerless_closeout_reservation_path(
    root: Path,
    target: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return the target-scoped durable ownerless-closeout reservation path."""
    return (artifact_root or records_artifact_root(root)) / _RESERVATIONS / f"{target}.json"


def record_path(
    root: Path,
    category: str,
    decision_id: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return one digest-addressed record path under the stable owner."""
    return (
        (artifact_root or records_artifact_root(root))
        / category
        / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"
    )


def write_json_atomic(
    destination: Path,
    payload: dict[str, object],
    *,
    record_root: Path,
) -> None:
    """Durably link one JSON record without replacing existing bytes."""
    if not record_destination_safe(record_root, destination):
        raise OSError(_RECORD_PATH_UNSAFE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not record_destination_safe(record_root, destination):
        raise OSError(_RECORD_PATH_UNSAFE)
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if not record_destination_safe(record_root, destination):
            raise OSError(_RECORD_PATH_UNSAFE)
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise FileExistsError(destination) from error
        _fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def reserve_ownerless_closeout_target(
    *,
    root: Path,
    reservation: dict[str, object],
    artifact_root: Path | None = None,
) -> Path:
    """Atomically reserve one lane/head target; exact same-decision replay is idempotent."""
    payload = _validated_ownerless_reservation(reservation, initial=True)
    record_root = artifact_root or records_artifact_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(payload["target_digest"]), artifact_root=record_root
    )
    try:
        write_json_atomic(destination, payload, record_root=record_root)
    except FileExistsError:
        current = _read_ownerless_reservation(record_root, destination)
        if current == payload:
            return destination
        if current.get("decision_id") != payload["decision_id"]:
            raise
        raise ValueError(_OWNERLESS_RESERVATION_MISMATCH) from None
    return destination


def transition_ownerless_closeout_reservation(  # noqa: PLR0913, RUF100 - exact transition CAS
    *,
    root: Path,
    expected: dict[str, object],
    phase: str,
    recovery_state: str,
    postcondition_digest: str = "",
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Durably classify an inflight or partial transition without clearing it."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    if recovery_state == "reserved_no_effect":
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    record_root = artifact_root or records_artifact_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(expected_payload["target_digest"]), artifact_root=record_root
    )
    current = _read_ownerless_reservation(record_root, destination)
    _require_exact_ownerless_binding(current, expected_payload, _OWNERLESS_RESERVATION_MISMATCH)
    updated = _validated_ownerless_reservation(
        {
            **current,
            "phase": phase,
            "recovery_state": recovery_state,
            "postcondition_digest": postcondition_digest,
        }
    )
    _write_json_replace_atomic(destination, updated, record_root=record_root)
    return updated


def ownerless_closeout_recovery_binding(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Return receipt binding only for the same exact completed-effect decision."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    record_root = artifact_root or records_artifact_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(expected_payload["target_digest"]), artifact_root=record_root
    )
    current = _read_ownerless_reservation(record_root, destination)
    _require_exact_ownerless_binding(
        current, expected_payload, _OWNERLESS_RECOVERY_BINDING_MISMATCH
    )
    if current.get("recovery_state") != "effect_complete_receipt_missing":
        raise ValueError(_OWNERLESS_RECOVERY_NOT_FINALIZABLE)
    return OwnerlessCloseoutBinding(
        executor_ref=str(current["executor_ref"]),
        decision_sha256=str(current["decision_sha256"]),
        accepted_branch=str(current["accepted_branch"]),
        accepted_head=str(current["accepted_head"]),
        target_digest=str(current["target_digest"]),
        target_binding_digest=str(current["target_binding_digest"]),
        postcondition_digest=str(current["postcondition_digest"]),
    ).model_dump(mode="json")


def read_ownerless_closeout_reservation(*, record_root: Path, path: Path) -> dict[str, object]:
    """Read and validate one inventory-visible ownerless reservation."""
    return _read_ownerless_reservation(record_root, path)


def release_ownerless_closeout_reservation(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> None:
    """Release only after an exact immutable ownerless completion receipt exists."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    binding = ownerless_closeout_recovery_binding(
        root=root,
        expected=expected_payload,
        artifact_root=artifact_root,
    )
    record_root = artifact_root or records_artifact_root(root)
    completion = receipt_path(
        root,
        str(expected_payload["decision_id"]),
        artifact_root=record_root,
    )
    if not record_destination_safe(record_root, completion) or completion.is_symlink():
        raise OSError(_RECORD_PATH_UNSAFE)
    try:
        receipt = json.loads(completion.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID) from error
    _validate_ownerless_completion_receipt(
        root=root,
        receipt=receipt,
        expected=expected_payload,
        binding=binding,
    )
    reservation = ownerless_closeout_reservation_path(
        root,
        str(expected_payload["target_digest"]),
        artifact_root=record_root,
    )
    if not record_destination_safe(record_root, reservation) or reservation.is_symlink():
        raise OSError(_RECORD_PATH_UNSAFE)
    reservation.unlink()
    _fsync_directory(reservation.parent)


def _validate_ownerless_completion_receipt(
    *,
    root: Path,
    receipt: object,
    expected: dict[str, object],
    binding: dict[str, object],
) -> None:
    try:
        payload = LaneResolutionReceipt.model_validate(receipt).to_payload()
        schema_ok = validate_schema_instance(
            "lane-resolution-receipt.schema.json",
            payload,
            root=root,
        )["ok"]
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID) from error
    valid = (
        receipt == payload
        and schema_ok
        and payload["state"] == "retired"
        and payload["preservation_package"] == ""
        and payload["preservation_manifest_sha256"] == ""
        and payload["decision_id"] == expected["decision_id"]
        and payload["lane_ref"] == expected["lane_ref"]
        and payload["head"] == expected["head"]
        and payload.get("ownerless_closeout_binding") == binding
    )
    if not valid:
        raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID)


def _validated_ownerless_reservation(
    payload: dict[str, object], *, initial: bool = False
) -> dict[str, object]:
    try:
        canonical = OwnerlessCloseoutReservation.model_validate(payload).to_payload()
    except ValueError as error:
        raise ValueError(_OWNERLESS_RESERVATION_INVALID) from error
    if canonical != payload:
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    if initial and canonical["recovery_state"] != "reserved_no_effect":
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    return canonical


def _require_exact_ownerless_binding(
    current: dict[str, object], expected: dict[str, object], error: str
) -> None:
    if any(current.get(field) != expected.get(field) for field in _IMMUTABLE_RESERVATION_FIELDS):
        raise ValueError(error)


def _read_ownerless_reservation(record_root: Path, destination: Path) -> dict[str, object]:
    if not record_destination_safe(record_root, destination) or destination.is_symlink():
        raise OSError(_RECORD_PATH_UNSAFE)
    try:
        payload = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(_OWNERLESS_RESERVATION_INVALID) from error
    if not isinstance(payload, dict):
        raise _ownerless_reservation_invalid()
    return _validated_ownerless_reservation(payload)


def _write_json_replace_atomic(
    destination: Path,
    payload: dict[str, object],
    *,
    record_root: Path,
) -> None:
    if not record_destination_safe(record_root, destination) or destination.is_symlink():
        raise OSError(_RECORD_PATH_UNSAFE)
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if not record_destination_safe(record_root, destination) or destination.is_symlink():
            raise OSError(_RECORD_PATH_UNSAFE)
        temporary.replace(destination)
        _fsync_directory(destination.parent)
    finally:
        temporary.unlink(missing_ok=True)


def reserve_resolution_receipt(
    *, root: Path, decision_id: str, artifact_root: Path | None = None
) -> Path:
    """Atomically reserve one immutable receipt before any destructive effect."""
    if not valid_decision_id(decision_id):
        raise ValueError(_RECEIPT_INVALID)
    record_root = artifact_root or records_artifact_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    reservation = _receipt_reservation_path(destination)
    if not record_destination_safe(record_root, destination) or not record_destination_safe(
        record_root, reservation
    ):
        raise OSError(_RECORD_PATH_UNSAFE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not record_destination_safe(record_root, destination) or not record_destination_safe(
        record_root, reservation
    ):
        raise OSError(_RECORD_PATH_UNSAFE)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    try:
        descriptor = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _reuse_exact_receipt_reservation(
            record_root=record_root,
            destination=destination,
            reservation=reservation,
            decision_id=decision_id,
        )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"{decision_id}\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(destination.parent)
        unsafe = not record_destination_safe(record_root, destination)
        occupied = destination.exists() or destination.is_symlink()
    except Exception:
        reservation.unlink(missing_ok=True)
        raise
    if unsafe or occupied:
        release_resolution_receipt_reservation(
            root=root,
            decision_id=decision_id,
            artifact_root=record_root,
        )
        if unsafe:
            raise OSError(_RECORD_PATH_UNSAFE)
        raise FileExistsError(destination)
    return reservation


def _reuse_exact_receipt_reservation(
    *, record_root: Path, destination: Path, reservation: Path, decision_id: str
) -> Path:
    if (
        not record_destination_safe(record_root, destination)
        or not record_destination_safe(record_root, reservation)
        or reservation.is_symlink()
    ):
        raise OSError(_RECORD_PATH_UNSAFE)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(reservation, flags)
    except OSError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    expected = f"{decision_id}\n".encode()
    try:
        metadata = os.fstat(descriptor)
        content = os.read(descriptor, len(expected) + 1)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or content != expected:
        raise ValueError(_RECEIPT_INVALID)
    if (
        not record_destination_safe(record_root, destination)
        or not record_destination_safe(record_root, reservation)
        or reservation.is_symlink()
    ):
        raise OSError(_RECORD_PATH_UNSAFE)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    return reservation


def release_resolution_receipt_reservation(
    *, root: Path, decision_id: str, artifact_root: Path | None = None
) -> None:
    """Release the exact sidecar reservation for one completion receipt."""
    record_root = artifact_root or records_artifact_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    reservation = _receipt_reservation_path(destination)
    if not record_destination_safe(record_root, reservation):
        raise OSError(_RECORD_PATH_UNSAFE)
    try:
        reservation.unlink()
    except FileNotFoundError:
        return
    _fsync_directory(reservation.parent)


def _receipt_reservation_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.stem}{_RECEIPT_RESERVATION_SUFFIX}")


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

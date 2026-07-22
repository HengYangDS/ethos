"""Immutable local record storage and receipt reservations."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution._shared import valid_decision_id

_RECEIPTS = "receipts"
_CLEARS = "clears"
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_RECEIPT_RESERVATION_SUFFIX = ".receipt-reservation"
_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"


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
    descriptor = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
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

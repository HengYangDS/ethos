"""Exact compare-and-delete for ownerless reservations with no effect."""

from __future__ import annotations

import os
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution.records.core import ownerless_closeout_reservation_path
from ethos.adapters.mutation.resolution.records.core import read_ownerless_closeout_reservation

_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_RESERVATION_MISMATCH = "lane_resolution_ownerless_reservation_mismatch"


def release_ownerless_no_effect_reservation(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> None:
    """Release only one exact reservation whose destructive effect never started."""
    record_root = artifact_root or records_artifact_root(root)
    reservation = ownerless_closeout_reservation_path(
        root,
        str(expected.get("target_digest") or ""),
        artifact_root=record_root,
    )
    current = read_ownerless_closeout_reservation(record_root=record_root, path=reservation)
    if current != expected:
        message = _RESERVATION_MISMATCH
        raise ValueError(message)
    if not record_destination_safe(record_root, reservation) or reservation.is_symlink():
        message = _RECORD_PATH_UNSAFE
        raise OSError(message)
    reservation.unlink()
    _fsync_directory(reservation.parent)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

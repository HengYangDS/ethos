"""Generic immutable record paths and canonical JSON operations."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import ExitStack
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as record_posix
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.io.core import claim_record_sidecar
from ethos.adapters.mutation.resolution.records.io.core import remove_record_bytes
from ethos.adapters.mutation.resolution.records.io.core import replace_record_bytes
from ethos.adapters.mutation.resolution.records.io.core import reserve_record_sidecar
from ethos.adapters.mutation.resolution.records.io.core import write_record_bytes
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.repo.git import git_common_dir

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal


_RECEIPTS = "receipts"
_CLEARS = "clears"
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_RECEIPT_RESERVATION_SUFFIX = ".receipt-reservation"
_CLEAR_QUARANTINE_IDENTITY_FIELD_COUNT = 3
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


def clear_quarantine_name(decision_id: str, identity: tuple[int, int, int]) -> str:
    """Bind one clear quarantine name to its decision and captured filesystem identity."""
    device, inode, mode = identity
    digest = hashlib.sha256(decision_id.encode()).hexdigest()
    return f".{digest}.{device:x}-{inode:x}-{mode:x}.clear-quarantine"


def clear_quarantine_identity(name: str, decision_id: str) -> tuple[int, int, int] | None:
    """Parse the identity only from the exact quarantine namespace for one decision."""
    digest = hashlib.sha256(decision_id.encode()).hexdigest()
    prefix, suffix = f".{digest}.", ".clear-quarantine"
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    encoded = name.removeprefix(prefix).removesuffix(suffix)
    try:
        values = tuple(int(part, 16) for part in encoded.split("-"))
    except ValueError:
        return None
    if len(values) != _CLEAR_QUARANTINE_IDENTITY_FIELD_COUNT:
        return None
    identity = values[0], values[1], values[2]
    return identity if clear_quarantine_name(decision_id, identity) == name else None


def clear_quarantine_path(
    root: Path,
    decision_id: str,
    identity: tuple[int, int, int],
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return the deterministic package quarantine under the current record root."""
    return (artifact_root or current_record_root(root)) / clear_quarantine_name(
        decision_id, identity
    )


def record_path(
    root: Path,
    category: str,
    decision_id: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return one digest-addressed record path under the stable owner."""
    return (
        (artifact_root or current_record_root(root))
        / category
        / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"
    )


def canonical_current_record_bytes(payload: dict[str, object]) -> bytes:
    """Encode one current record with the canonical immutable writer format."""
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def write_json_atomic(
    destination: Path,
    payload: dict[str, object],
    *,
    record_root: Path,
) -> None:
    """Durably link one canonical JSON record without replacing existing bytes."""
    write_record_bytes(
        destination,
        canonical_current_record_bytes(payload),
        record_root=record_root,
    )


def replace_json_atomic(
    destination: Path,
    payload: dict[str, object],
    *,
    expected: dict[str, object],
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Replace only the exact locked canonical JSON record."""
    replace_record_bytes(
        destination,
        canonical_current_record_bytes(payload),
        expected=canonical_current_record_bytes(expected),
        record_root=record_root,
        locked_descriptor=locked_descriptor,
    )


def remove_record(
    destination: Path,
    *,
    expected: dict[str, object],
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Remove only the exact locked canonical JSON record."""
    remove_record_bytes(
        destination,
        expected=canonical_current_record_bytes(expected),
        record_root=record_root,
        locked_descriptor=locked_descriptor,
    )


def reserve_resolution_receipt(
    *, root: Path, decision_id: str, artifact_root: Path | None = None
) -> Path:
    """Atomically reserve one immutable receipt before any destructive effect."""
    if not valid_decision_id(decision_id):
        raise ValueError(_RECEIPT_INVALID)
    record_root = artifact_root or current_record_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    reservation = _receipt_reservation_path(destination)
    try:
        with _receipt_coordination_lock(root, record_root, reservation):
            reserve_record_sidecar(
                reservation,
                destination,
                expected=f"{decision_id}\n".encode(),
                record_root=record_root,
            )
    except ValueError as error:
        raise ValueError(_RECEIPT_INVALID) from error
    return reservation


@contextmanager
def claim_resolution_receipt_reservation(
    *,
    root: Path,
    decision_id: str,
    artifact_root: Path | None = None,
    mode: Literal["create", "recover", "recover_completed"],
) -> Iterator[int | None]:
    """Hold one receipt reservation across its complete writer or recovery attempt."""
    if not valid_decision_id(decision_id):
        raise ValueError(_RECEIPT_INVALID)
    record_root = artifact_root or current_record_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    reservation = _receipt_reservation_path(destination)
    with ExitStack() as stack:
        try:
            stack.enter_context(_receipt_coordination_lock(root, record_root, reservation))
            descriptor = stack.enter_context(
                claim_record_sidecar(
                    reservation,
                    destination,
                    expected=f"{decision_id}\n".encode(),
                    record_root=record_root,
                    mode=mode,
                )
            )
        except ValueError as error:
            raise ValueError(_RECEIPT_INVALID) from error
        yield descriptor


def release_resolution_receipt_reservation(
    *,
    root: Path,
    decision_id: str,
    artifact_root: Path | None = None,
    locked_descriptor: int | None = None,
) -> None:
    """Release only the exact descriptor-bound sidecar reservation."""
    record_root = artifact_root or current_record_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    try:
        remove_record_bytes(
            _receipt_reservation_path(destination),
            expected=f"{decision_id}\n".encode(),
            record_root=record_root,
            locked_descriptor=locked_descriptor,
        )
    except FileNotFoundError:
        return


def _receipt_reservation_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.stem}{_RECEIPT_RESERVATION_SUFFIX}")


def _receipt_coordination_root(root: Path, record_root: Path) -> Path:
    common = git_common_dir(root)
    if common:
        return Path(common)
    coordination = root.absolute()
    target = record_root.absolute()
    while not target.is_relative_to(coordination):
        parent = coordination.parent
        if parent == coordination:
            raise OSError(_RECORD_PATH_UNSAFE)
        coordination = parent
    if coordination in (coordination.parent, target):
        raise OSError(_RECORD_PATH_UNSAFE)
    return coordination


@contextmanager
def _receipt_coordination_lock(
    root: Path,
    record_root: Path,
    reservation: Path,
) -> Iterator[None]:
    coordination = _receipt_coordination_root(root, record_root)
    try:
        descriptor = record_posix.open_directory_path(coordination, create=False)
    except OSError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    identity = record_posix.directory_identity(os.fstat(descriptor))
    locked = False
    try:
        _acquire_coordination_lock(descriptor, reservation)
        locked = True
        _require_coordination_live(coordination, descriptor, identity)
        yield
        _require_coordination_live(coordination, descriptor, identity)
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _acquire_coordination_lock(descriptor: int, reservation: Path) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise FileExistsError(reservation) from error


def _require_coordination_live(
    path: Path,
    descriptor: int,
    identity: record_posix.DirectoryIdentity,
) -> None:
    if not record_posix.directory_descriptor_is_live(path, descriptor, identity):
        raise OSError(_RECORD_PATH_UNSAFE)

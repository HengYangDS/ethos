"""Canonical JSON encoding and descriptor-bound record mutation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.io.descriptor_store import remove_record_bytes
from ethos.adapters.mutation.resolution.records.io.descriptor_store import replace_record_bytes
from ethos.adapters.mutation.resolution.records.io.descriptor_store import write_record_bytes

if TYPE_CHECKING:
    from pathlib import Path


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

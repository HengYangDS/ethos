"""A retired record waits under a tombstone that the next run restores or the apply unlinks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ethos.adapters.store.retention.tombstones import restore_all
from ethos.adapters.store.retention.tombstones import retire
from ethos.adapters.store.retention.tombstones import tombstone_of

if TYPE_CHECKING:
    from pathlib import Path


def _record(directory: Path, payload: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{hashlib.sha256(payload).hexdigest()}.json"
    path.write_bytes(payload)
    return path


def test_a_retired_record_comes_back_by_its_name(tmp_path: Path) -> None:
    """Restore links the tombstone back and removes it; a rewritten name drops the tombstone."""
    directory = tmp_path / "artifacts"
    record = _record(directory, b"{}")
    stone = retire(record)
    assert stone == tombstone_of(record)
    assert not record.exists()
    assert restore_all([directory, tmp_path / "absent"]) == ()
    assert record.read_bytes() == b"{}"
    assert not stone.exists()
    stone = retire(record)
    assert stone is not None
    record.write_bytes(b"{}")
    assert restore_all([directory]) == ()
    assert record.exists()
    assert not stone.exists()


def test_differing_bytes_under_the_name_or_the_tombstone_keep_both(tmp_path: Path) -> None:
    """A name now holding other bytes is reported, and a stale foreign tombstone blocks a retire."""
    directory = tmp_path / "artifacts"
    record = _record(directory, b"{}")
    stone = retire(record)
    assert stone is not None
    record.write_bytes(b"[]")
    assert restore_all([directory]) == (stone,)
    assert (record.read_bytes(), stone.read_bytes()) == (b"[]", b"{}")
    other = _record(directory, b"{ }")
    tombstone_of(other).write_bytes(b"other")
    assert retire(other) is None
    assert other.exists()

"""A durable replacement reaches the disk before it is reported."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import ethos.adapters.store.durable as durable

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_a_durable_replacement_syncs_the_file_and_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bytes and, on POSIX, the directory entry are synced; no staging file remains."""
    synced: list[int] = []
    real = os.fsync

    def observe(descriptor: int) -> None:
        synced.append(descriptor)
        real(descriptor)

    monkeypatch.setattr(durable.os, "fsync", observe)
    target = tmp_path / "records" / "record.json"
    target.parent.mkdir()
    target.write_bytes(b"old")

    durable.replace_durably(target, b"new")

    assert target.read_bytes() == b"new"
    assert len(synced) == (2 if os.name == "posix" else 1)
    assert [path.name for path in target.parent.iterdir()] == ["record.json"]

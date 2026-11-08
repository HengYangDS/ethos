"""Verify platform-specific durability for content-addressed publication."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import ethos.adapters.store.content_addressed as content_addressed
import ethos.adapters.store.durable as durable


def test_windows_publication_does_not_open_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "packages" / "digest" / "ethos.whl"
    original_open = os.open

    def reject_directory_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
        if Path(path) == target.parent:
            message = "Windows cannot open directories this way"
            raise PermissionError(message)
        return original_open(path, flags, mode)

    with monkeypatch.context() as patch:
        patch.setattr(durable, "_DIRECTORY_FSYNC_SUPPORTED", False, raising=False)
        patch.setattr(content_addressed.os, "open", reject_directory_open)
        assert (
            content_addressed.write_content_addressed(target, b"wheel", collision="collision")
            == target
        )
    assert target.read_bytes() == b"wheel"


def test_posix_publication_synchronizes_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "packages" / "digest" / "ethos.whl"
    original_open = os.open
    opened: list[Path] = []

    def observe_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
        opened.append(Path(path))
        return original_open(path, flags, mode)

    with monkeypatch.context() as patch:
        patch.setattr(durable, "_DIRECTORY_FSYNC_SUPPORTED", True, raising=False)
        patch.setattr(content_addressed.os, "open", observe_open)
        content_addressed.write_content_addressed(target, b"wheel", collision="collision")

    assert target.parent in opened


def test_an_identical_write_adopts_the_record_again(tmp_path: Path) -> None:
    """Writing the same bytes moves an old record's mtime to now; other bytes still collide."""
    target = tmp_path / "artifacts" / "record.json"
    content_addressed.write_content_addressed(target, b"{}", collision="collision")
    os.utime(target, (1_000_000_000, 1_000_000_000))

    content_addressed.write_content_addressed(target, b"{}", collision="collision")

    assert target.stat().st_mtime > 1_000_000_000 + 86_400
    assert target.read_bytes() == b"{}"
    with pytest.raises(ValueError, match="collision"):
        content_addressed.write_content_addressed(target, b"[]", collision="collision")

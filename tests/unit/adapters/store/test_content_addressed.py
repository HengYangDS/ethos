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


@pytest.mark.parametrize("window", ["read", "refresh"])
def test_a_record_retired_during_a_write_is_linked_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, window: str
) -> None:
    """A name that vanishes before its read or its refresh is linked again, not a collision."""
    target = tmp_path / "artifacts" / "record.json"
    content_addressed.write_content_addressed(target, b"{}", collision="collision")
    original = getattr(content_addressed.os, "open" if window == "read" else "utime")
    removed: list[Path] = []

    def vanish_once(path: os.PathLike[str] | str, *args: object, **kwargs: object) -> object:
        if Path(path) == target and not removed:
            removed.append(target)
            target.unlink()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(content_addressed.os, "open" if window == "read" else "utime", vanish_once)

    assert content_addressed.write_content_addressed(target, b"{}", collision="collision") == target
    assert removed == [target]
    assert target.read_bytes() == b"{}"


@pytest.mark.parametrize("holder", ["directory", "unreadable", "vanishing"])
def test_a_name_that_cannot_be_adopted_is_a_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, holder: str
) -> None:
    """A non-file, an unreadable file or a name that keeps vanishing raises the collision."""
    target = tmp_path / "records" / "digest.json"
    target.parent.mkdir()
    if holder == "directory":
        target.mkdir()
    else:
        target.write_bytes(b"record")
    if holder == "unreadable":
        target.chmod(0)
    elif holder == "vanishing":

        def vanish(*_args: object) -> None:
            raise FileNotFoundError(target)

        monkeypatch.setattr(content_addressed, "_adopt", vanish)
    try:
        with pytest.raises(ValueError, match="record_collision"):
            content_addressed.write_content_addressed(
                target, b"record", collision="record_collision"
            )
    finally:
        if target.is_file():
            target.chmod(0o600)

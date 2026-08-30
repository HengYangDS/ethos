from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.store.content_addressed as content_addressed

if TYPE_CHECKING:
    import pytest


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

    monkeypatch.setattr(content_addressed, "_DIRECTORY_FSYNC_SUPPORTED", False, raising=False)
    monkeypatch.setattr(content_addressed.os, "open", reject_directory_open)

    assert (
        content_addressed.write_content_addressed(target, b"wheel", collision="collision") == target
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

    monkeypatch.setattr(content_addressed, "_DIRECTORY_FSYNC_SUPPORTED", True, raising=False)
    monkeypatch.setattr(content_addressed.os, "open", observe_open)

    content_addressed.write_content_addressed(target, b"wheel", collision="collision")

    assert target.parent in opened

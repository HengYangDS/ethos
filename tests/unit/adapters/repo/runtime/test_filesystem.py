"""Owned removal changes only what it must and never an external inode (QS 2233-2253)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.runtime.filesystem import remove_owned_path

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("mode", [0o755, 0o555, 0o000, 0o100])
def test_owned_removal_changes_only_required_directory_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: int
) -> None:
    """Deletion must not rewrite writable directories or POSIX file metadata."""
    target = tmp_path / "evidence"
    runtime = target / "repo/.git/ethos/runtime/digest"
    runtime.mkdir(parents=True)
    payload = runtime / "manifest.json"
    payload.write_text("{}\n", encoding="utf-8")
    payload.chmod(0o444)
    runtime.chmod(mode)
    chmod, changed = type(target).chmod, []

    def observe(path: Path, mode: int, **kwargs: bool) -> None:
        if path == runtime:
            assert kwargs.get("follow_symlinks", True) is (
                os.chmod not in os.supports_follow_symlinks
            )
        changed.append(path)
        return chmod(path, mode, **kwargs)

    monkeypatch.setattr(type(target), "chmod", observe)
    remove_owned_path(target)

    assert not target.exists()
    if os.name == "posix":
        assert changed == ([] if mode == 0o755 else [runtime])
    remove_owned_path(target)


@pytest.mark.parametrize("relation", ["root-link", "nested-link", "hardlink"])
def test_owned_removal_preserves_external_content_and_permissions(
    tmp_path: Path, relation: str
) -> None:
    """Owned cleanup unlinks references without changing an external inode."""
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = outside / "payload"
    payload.write_bytes(b"external content")
    target = tmp_path / "owned"
    if relation == "root-link":
        target.symlink_to(outside, target_is_directory=True)
    else:
        target.mkdir()
        if relation == "nested-link":
            (target / "link").symlink_to(outside, target_is_directory=True)
        else:
            os.link(payload, target / "link")
    payload.chmod(0o444)
    before = payload.stat()

    remove_owned_path(target)

    assert not target.exists()
    assert not target.is_symlink()
    after = payload.stat()
    assert payload.read_bytes() == b"external content"
    assert (after.st_ino, after.st_mode, after.st_mtime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
    )

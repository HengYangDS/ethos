"""Retire store records through recoverable tombstones, and restore those an apply left.

An apply renames each file it means to delete to `.<name>.retiring` in the same directory, rechecks
it and only then unlinks it, so a crash at any point leaves the record or a tombstone, which the
next preview or apply restores without replacing a name a writer has written again.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ethos.contracts.digest import file_sha256

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

TOMBSTONE = re.compile(r"\.([0-9a-f]{64}\.(?:json|zip))\.retiring")


def tombstone_of(path: Path) -> Path:
    """Return the tombstone name of one record."""
    return path.with_name(f".{path.name}.retiring")


def retire(path: Path) -> Path | None:
    """Rename one record to its tombstone, or keep it in place when another process holds it.

    A tombstone already there replaces only when its bytes are this record's, as its name is.
    """
    target = tombstone_of(path)
    if target.exists() and file_sha256(target) != path.stem:
        return None
    try:
        path.replace(target)
    except PermissionError:
        return None
    return target


def restore(tombstone: Path) -> bool:
    """Bring one tombstone's record back; return False when a differing record holds its name."""
    match = TOMBSTONE.fullmatch(tombstone.name)
    if match is None:
        return True
    name = tombstone.with_name(match.group(1))
    try:
        os.link(tombstone, name)
    except FileExistsError:
        if file_sha256(name) != file_sha256(tombstone):
            return False
    tombstone.unlink()
    return True


def restore_all(directories: Iterable[Path]) -> tuple[Path, ...]:
    """Restore every tombstone in the owned directories; return those whose name now differs."""
    conflicts: list[Path] = []
    for directory in directories:
        if directory.is_dir():
            conflicts.extend(
                entry
                for entry in sorted(directory.iterdir())
                if TOMBSTONE.fullmatch(entry.name) and not restore(entry)
            )
    return tuple(conflicts)

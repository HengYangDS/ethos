"""The bytes that a store holds, against the budget its paradigm declares.

A budget reports and never refuses: a row is `within` or `over`, or `unread` when a place under
it could not be read and the bytes that were counted do not already exceed it, and no verdict
reads it. Sizes are the sizes of regular files, read without
following a link or a junction, so a file system that shares blocks holds fewer bytes than a row
says. A place that cannot be read is counted and skipped; every reading asks the host for an
entry's own status, which answers alike on every supported interpreter.
"""

from __future__ import annotations

import os
import stat
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.adapters.store.retention.kinds import owned_places

if TYPE_CHECKING:
    from collections.abc import Iterator


def _status(path: Path, unread: list[OSError]) -> os.stat_result | None:
    """Return an entry's own status; nothing at the path is None, another failure is counted."""
    try:
        return path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as error:
        unread.append(error)
        return None


def _names(top: Path, unread: list[OSError]) -> Iterator[Path]:
    """Yield each name under a directory, descending into no link and no junction."""
    for parent, directories, names in os.walk(top, onerror=unread.append):
        directories[:] = [name for name in directories if not is_junction(Path(parent, name))]
        yield from (Path(parent, name) for name in names)


def tree_bytes(top: Path) -> dict[str, int]:
    """Return the regular files at or under a path, their bytes and the places not read."""
    unread: list[OSError] = []
    first = _status(top, unread)
    if first is None:
        entries: list[os.stat_result | None] = []
    elif stat.S_ISDIR(first.st_mode) and not is_junction(top):
        entries = [_status(path, unread) for path in _names(top, unread)]
    else:
        entries = [first]
    sizes = [entry.st_size for entry in entries if entry and stat.S_ISREG(entry.st_mode)]
    return {"files": len(sizes), "bytes": sum(sizes), "unread": len(unread)}


def store_report(store: Path) -> dict[str, object]:
    """Return what each top-level name of a store holds, and the time of the read in UTC.

    A store that is not there holds no names; one that cannot be listed says so in `unread`.
    """
    try:
        names, unread = sorted(store.iterdir()), 0
    except OSError as error:
        names, unread = [], int(not isinstance(error, FileNotFoundError))
    return {
        "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "names": {path.name: tree_bytes(path) for path in names},
        "unread": unread,
    }


def budget_row(held: int, budget: int, unread: int) -> dict[str, object]:
    """Return one budget row; a read that missed a place is never `within`.

    A place that was not read can only add bytes, so counted bytes above the budget are `over`
    whatever was missed; below it, a missed place leaves the row `unread`.
    """
    state = "over" if held > budget else "unread" if unread else "within"
    return {"bytes": held, "budget_bytes": budget, "state": state, "unread": unread}


def owned_budget(store: Path, budget: int) -> dict[str, object]:
    """Return the row of the directories that record retirement owns in a Git-common store."""
    directories, refused = owned_places(store)
    read = [tree_bytes(directory) for directory in directories]
    unread = len(refused) + sum(item["unread"] for item in read)
    return budget_row(sum(item["bytes"] for item in read), budget, unread)

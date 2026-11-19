"""The bytes that a store holds, against the budget its paradigm declares.

A budget reports and never refuses: a row is `within` or `over`, and no verdict reads it. Sizes
are the sizes of regular files, read without following a link, so a file system that shares
blocks holds fewer bytes than a row says. A place that cannot be read is counted and skipped;
every reading asks the host for an entry's own status, which answers alike on every supported
interpreter.
"""

from __future__ import annotations

import os
import stat
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.store.retention.kinds import owned_directories


def tree_bytes(top: Path) -> dict[str, int]:
    """Return the regular files at or under a path, their bytes and the places not read."""
    unread: list[OSError] = []
    files = size = 0
    paths = [top]
    try:
        whole = stat.S_ISDIR(top.lstat().st_mode)
    except OSError as error:
        unread.append(error)
        whole = False
    if whole:
        paths = [
            Path(parent, name)
            for parent, _directories, names in os.walk(top, onerror=unread.append)
            for name in names
        ]
    for path in paths:
        with suppress(OSError):
            status = path.lstat()
            if stat.S_ISREG(status.st_mode):
                files, size = files + 1, size + status.st_size
    return {"files": files, "bytes": size, "unread": len(unread)}


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


def budget_row(held: int, budget: int) -> dict[str, object]:
    """Return one budget row: the bytes held, the declared budget, and `within` or `over`."""
    return {"bytes": held, "budget_bytes": budget, "state": "over" if held > budget else "within"}


def owned_budget(store: Path, budget: int) -> dict[str, object]:
    """Return the row of the directories that record retirement owns in a Git-common store."""
    held = sum(tree_bytes(directory)["bytes"] for directory in owned_directories(store))
    return budget_row(held, budget)

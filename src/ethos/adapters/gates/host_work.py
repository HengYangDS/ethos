"""Mark the directory that a host ticket's holder works in with its owner.

The build tree's work home holds one directory for each purpose, and each belongs to one owner:
the actor that the holder of a host ticket declared. A scratch root that a holder makes under the
temporary root carries the same record. The mark is a file inside the directory, so it moves and
ends with the directory, and a reader learns the owner without the queue. A directory without a
mark that can be read has an unknown owner: no run takes it over, and no reader may call it
residue.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.actor import process_actor
from ethos.adapters.gates.host_admission import ADMISSION_ENV

if TYPE_CHECKING:
    from pathlib import Path

WORK_HOME = "build/runtime/work"
MARK = ".ethos-owner.json"
INVALID = "host_work_invalid"
OWNED = "host_work_owned"
UNAVAILABLE = "host_work_unavailable"
_PURPOSE = re.compile(r"[a-z0-9][a-z0-9._-]*")


def work_owner(directory: Path) -> str:
    """The owner that a work directory's mark declares; empty when no mark can be read."""
    try:
        marked = json.loads((directory / MARK).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    owner = marked.get("owner") if isinstance(marked, dict) else None
    return owner if isinstance(owner, str) else ""


def _mark(directory: Path, owner: str, operation: str) -> None:
    """Link one whole owner record into a directory; a mark that is already there stays.

    The partial record goes on every exit, also a write that fails part way. One that cannot
    be removed lies in the directory that the mark governs and decides nothing: it refuses no
    claim and replaces no exit in flight.
    """
    since = datetime.now(UTC).isoformat(timespec="seconds")
    record = {"owner": owner, "operation": operation, "since": since}
    partial = directory / f".{secrets.token_hex(8)}.partial"
    try:
        partial.write_text(json.dumps(record), encoding="utf-8")
        with suppress(FileExistsError):
            os.link(partial, directory / MARK)
    finally:
        with suppress(OSError):
            partial.unlink()


def mark_ticket_scratch(directory: Path, *, operation: str) -> None:
    """Mark a scratch root that the holder of a host ticket made for its own work.

    A root that outlives an interrupted run then still names its owner. A run outside the queue,
    or one that declares no actor, marks nothing, and a mark that cannot be written leaves the
    owner unknown: it never fails the work.
    """
    owner = process_actor()
    if owner and os.environ.get(ADMISSION_ENV):
        with suppress(OSError):
            _mark(directory, owner, operation)


def claim_work_directory(root: Path, purpose: str, *, owner: str, operation: str) -> Path:
    """Create one purpose's work directory and mark it as this owner's, once.

    The mark is linked into place whole, so of two owners that arrive together exactly one holds
    the directory and the other is refused, and a later run of the same owner keeps the first
    mark. A run that declares no actor marks nothing and enters no directory that carries a mark;
    nothing is written into a directory that already carries one.
    """
    if not _PURPOSE.fullmatch(purpose):
        raise ValueError(INVALID)
    directory = root / WORK_HOME / purpose
    mark = directory / MARK
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if owner and not os.path.lexists(mark):
            _mark(directory, owner, operation)
        marked = os.path.lexists(mark)
    except OSError as error:
        raise ValueError(UNAVAILABLE) from error
    if marked and not (owner and work_owner(directory) == owner):
        message = f"{OWNED}:{purpose}"
        raise ValueError(message)
    return directory

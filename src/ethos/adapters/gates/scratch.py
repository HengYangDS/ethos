"""The scratch directory that the declared commands of one run of gates share.

A command names it with `{scratch}` in an argument. The first command that does makes one
directory under the temporary root for its runner, marked with its owner where the run holds a
host ticket, and every later command of that runner receives the same one. The directory ends
with the runner, or with the process at the latest. A command that does not name it is launched
as it is declared, and nothing is made.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from threading import Lock
from weakref import WeakKeyDictionary
from weakref import finalize

from ethos.adapters.gates.host_work import mark_ticket_scratch
from ethos.adapters.repo.runtime.filesystem import remove_owned_path

PLACEHOLDER = "{scratch}"
_DIRECTORIES: WeakKeyDictionary[object, str] = WeakKeyDictionary()
_LOCK = Lock()


def bind_scratch(attempt: object, command: tuple[str, ...]) -> tuple[tuple[str, ...], str]:
    """Return a command with the attempt's scratch in the placeholder's place, and that scratch.

    A command without the placeholder comes back as it is, with no scratch.
    """
    if not any(PLACEHOLDER in part for part in command):
        return command, ""
    with _LOCK:
        directory = _DIRECTORIES.get(attempt)
        if directory is None:
            root = Path(mkdtemp(prefix="ethos-proof-scratch-"))
            finalize(attempt, remove_owned_path, root)
            mark_ticket_scratch(root, operation="proof.scratch")
            (root / "commands").mkdir()
            _DIRECTORIES[attempt] = directory = str(root / "commands")
    return with_scratch(command, directory), directory


def with_scratch(command: tuple[str, ...], directory: str) -> tuple[str, ...]:
    """Return a command's words with a known scratch directory in the placeholder's place."""
    return tuple(part.replace(PLACEHOLDER, directory) for part in command)

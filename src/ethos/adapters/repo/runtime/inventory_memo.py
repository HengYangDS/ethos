"""Reuse runtime inventory digests for payload files whose exact state is unchanged.

Selecting a runtime hashes its whole payload, and one command selects it more than once: the
installed command before it dispatches, the runtime again, and every hook. A recorded digest is
reused only while the file's device, inode, size, mode, mtime and ctime are all unchanged. Any
write or mode change moves ctime, which no unprivileged process can set back, so changed bytes
are hashed again and still report payload damage; enumeration is unchanged, so an added entry such
as bytecode is still refused. A file written within the racy window before its hash could change
within one timestamp tick, so it is not recorded. Windows reports a creation time as ctime there,
so it always hashes. The memo lives beside the host runtime store, outside every store whose
identity ETHOS checks; a missing, unreadable or foreign memo costs only the hashing it would have
saved. Entries are read only from a directory and a file that the current user owns and that group
and others cannot write, because another account sharing the data home could otherwise plant
them; Windows keeps the memo off until it checks the same ownership there.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.contracts.digest import is_sha256_hex

if TYPE_CHECKING:
    from collections.abc import Callable

_SCHEMA_VERSION = 1
# Below this many files, hashing costs less than reading and writing a memo.
_MIN_FILES = 256
_RACY_NS = 2 * 10**9
_RETAINED = 32
_SUPPORTED = os.name != "nt"
_HEX = frozenset("0123456789abcdef")


class InventoryMemo:
    """Digests recorded for one payload root, each bound to its file's exact state."""

    def __init__(self, root: Path, path: Path, recorded: dict[str, object]) -> None:
        self._root = root
        self._path = path
        self._recorded = recorded
        self._current: dict[str, list[object]] = {}
        self._files = 0

    def digest(self, relative: str, state: os.stat_result, compute: Callable[[], str]) -> str:
        """Return the recorded digest for an unchanged file, or compute and record it."""
        self._files += 1
        key: list[object] = [
            state.st_dev,
            state.st_ino,
            state.st_size,
            state.st_mode,
            state.st_mtime_ns,
            state.st_ctime_ns,
        ]
        recorded = self._recorded.get(relative)
        if isinstance(recorded, list) and recorded[:-1] == key and _valid_digest(recorded[-1]):
            self._current[relative] = recorded
            return recorded[-1]
        value = compute()
        if max(state.st_mtime_ns, state.st_ctime_ns) <= time.time_ns() - _RACY_NS:
            self._current[relative] = [*key, value]
        return value

    def save(self) -> None:
        """Record this complete inventory when it is large enough and anything changed."""
        if self._files < _MIN_FILES or self._current == self._recorded:
            return
        payload = {"schema_version": _SCHEMA_VERSION, "root": str(self._root)}
        payload["entries"] = self._current
        directory = self._path.parent
        with contextlib.suppress(OSError):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if _directory_access(directory) is None:
                return
            directory.chmod(0o700)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", dir=directory, prefix=".", suffix=".tmp", delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    json.dump(payload, stream, separators=(",", ":"))
                temporary.replace(self._path)
                temporary = None
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            _prune(directory)


def open_inventory_memo(root: Path) -> InventoryMemo | None:
    """Open the memo of one runtime root, or None where a memo cannot serve.

    A runtime root is named by its digest, or in a package carrier by the digest's 16-digit index.
    """
    directory = _memo_directory()
    name = root.name
    if not _SUPPORTED or len(name) not in {16, 64} or set(name) - _HEX or directory is None:
        return None
    readable = _directory_access(directory)
    if readable is None:
        return None
    path = directory / f"{hashlib.sha256(os.fsencode(root)).hexdigest()[:32]}.json"
    recorded: dict[str, object] = {}
    with contextlib.suppress(OSError, ValueError):
        payload = json.loads(_read_private(path)) if readable else None
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == _SCHEMA_VERSION
            and payload.get("root") == str(root)
            and isinstance(entries := payload.get("entries"), dict)
        ):
            recorded = entries
    return InventoryMemo(root, path, recorded)


def _memo_directory() -> Path | None:
    root = host_store_root()
    return None if root is None else root / "runtime-inventory"


def _directory_access(directory: Path) -> bool | None:
    """Whether entries may be read from the memo directory, or None where no memo may serve.

    A directory owned by the current user that group or others can write serves no entries, but a
    save may still tighten it; a link, another kind of file or another owner serves nothing.
    """
    try:
        state = directory.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return None
    if not stat.S_ISDIR(state.st_mode) or state.st_uid != os.geteuid():
        return None
    return not state.st_mode & 0o022


def _read_private(path: Path) -> bytes:
    """Read a regular memo file that only the current user can have written."""
    with open(
        path, "rb", opener=lambda name, flags: os.open(name, flags | os.O_NOFOLLOW)
    ) as stream:
        state = os.fstat(stream.fileno())
        if not stat.S_ISREG(state.st_mode) or state.st_uid != os.geteuid() or state.st_mode & 0o022:
            raise PermissionError(path)
        return stream.read()


def _prune(directory: Path) -> None:
    memos = [path for path in directory.glob("*.json") if _valid_name(path.stem)]
    if len(memos) <= _RETAINED:
        return
    memos.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for stale in memos[_RETAINED:]:
        stale.unlink(missing_ok=True)


def _valid_digest(value: object) -> bool:
    return is_sha256_hex(value)


def _valid_name(value: str) -> bool:
    return len(value) == 32 and not set(value) - _HEX

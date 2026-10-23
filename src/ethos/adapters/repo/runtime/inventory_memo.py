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
saved.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.host_store import host_store_root

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
        with contextlib.suppress(OSError):
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", dir=self._path.parent, prefix=".", suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                try:
                    json.dump(payload, stream, separators=(",", ":"))
                except (OSError, ValueError):
                    temporary.unlink(missing_ok=True)
                    raise
            temporary.replace(self._path)
            _prune(self._path.parent)


def open_inventory_memo(root: Path) -> InventoryMemo | None:
    """Open the memo of one digest-named payload root, or None where a memo cannot serve."""
    directory = _memo_directory()
    if not _SUPPORTED or not _valid_digest(root.name) or directory is None:
        return None
    path = directory / f"{hashlib.sha256(os.fsencode(root)).hexdigest()[:32]}.json"
    recorded: dict[str, object] = {}
    with contextlib.suppress(OSError, ValueError):
        payload = json.loads(path.read_bytes())
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


def _prune(directory: Path) -> None:
    memos = [path for path in directory.glob("*.json") if _valid_name(path.stem)]
    if len(memos) <= _RETAINED:
        return
    memos.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for stale in memos[_RETAINED:]:
        stale.unlink(missing_ok=True)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and not set(value) - _HEX


def _valid_name(value: str) -> bool:
    return len(value) == 32 and not set(value) - _HEX

"""Delete the planned store records that a fresh scan still selects, one batch per kind.

A batch renames its records to tombstones and rechecks them, defers while another ETHOS interpreter
of the repository runs, and unlinks under the custody lock only what the refreshed closure does not
name, at most 200 files a hold; it restores whatever it does not delete. No owner lock covers every
writer of its kind, so safety rests on the mtime refresh, the tombstones, the rechecks, the writer
check and the custody compare.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Literal

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.repo.runtime.retirement import process_commands
from ethos.adapters.store.custody import custody_lock
from ethos.adapters.store.durable import sync_directory
from ethos.adapters.store.retention.kinds import owned_directories
from ethos.adapters.store.retention.plan import KindTally
from ethos.adapters.store.retention.tombstones import restore
from ethos.adapters.store.retention.tombstones import retire
from ethos.adapters.store.retention.writers import running_writers

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Sequence
    from pathlib import Path

    from ethos.adapters.store.retention.closure import Closure
    from ethos.adapters.store.retention.kinds import StoreItem
    from ethos.adapters.store.retention.plan import PlannedItem

# Referrers go before what they name: proof checks, then attempts and preimages, then lane units.
BATCHES = (
    "proof-check",
    "native-attempt",
    "javascript-attempt",
    "merge-preimage",
    "lane-retirement",
)
_PER_HOLD = 200
_HOLDS = 3
type _Stones = list[tuple[Path, Path]]


def try_hold(path: Path) -> FileLock | None:
    """Take one lock without waiting; return None while another process holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(path, mode=0o600, fallback_to_soft=False, preserve_lock_file=True)
    try:
        lock.acquire(blocking=False)
    except Timeout:
        return None
    return lock


def hold_proof_slot(store: Path) -> FileLock | None:
    """Take the proof slot without waiting and record this run as its holder."""
    lock = try_hold(store / "proof-slot.lock")
    if lock is not None:
        since = datetime.now(UTC).isoformat()
        holder = {"pid": os.getpid(), "command": "hook retire-records", "since": since}
        (store / "proof-slot.json").write_text(json.dumps(holder), encoding="utf-8")
    return lock


@dataclass(frozen=True)
class Work:
    """One planned item that the fresh scan still selects: each file, size and mtime to delete."""

    item: StoreItem
    facts: tuple[tuple[Path, int, int], ...]


@dataclass
class Apply:
    """One apply run: the closure it keeps current, what is still pending and each kind's tally."""

    repo: Path
    store: Path
    closure: Closure
    selected: Callable[[], bool]
    writer_roots: Callable[[], tuple[Path, ...]]
    pending: list[StoreItem] = field(default_factory=list)
    tally: dict[str, KindTally] = field(default_factory=dict)
    deleted: list[StoreItem] = field(default_factory=list)
    touched: set[Path] = field(default_factory=set)
    # The writer roots that deferred a batch, never their command lines.
    writers: set[str] = field(default_factory=set)

    def select(
        self,
        planned: Sequence[PlannedItem],
        fresh: Sequence[StoreItem],
        old: Callable[[StoreItem], bool],
    ) -> dict[str, list[Work]]:
        """Match each planned item to the fresh item it still is; every other item stays."""
        directories = set(owned_directories(self.store))
        by_files = {frozenset(item.paths): item for item in fresh}
        works: dict[str, list[Work]] = {}
        for entry in planned:
            facts = [
                (path, file.size, int(file.mtime_ns))
                for file in entry.files
                if os.path.lexists(path := self.store / file.path)
            ]
            item = by_files.get(frozenset(path for path, _size, _mtime in facts))
            if not facts:
                self._count(entry.kind).absent += 1
            elif (
                item is None
                or item.kind != entry.kind
                or not all(path.parent in directories and _same(*fact) for fact in facts)
            ):
                self._count(entry.kind).add("kept", "changed")
            else:
                # A lane unit's receipt goes last, so an interrupted run leaves it classifiable.
                facts.sort(key=lambda fact: "receipts" in fact[0].relative_to(self.store).parts)
                works.setdefault(entry.kind, []).append(Work(item, tuple(facts)))
        self.pending = [work.item for kind in works.values() for work in kind]
        chosen = set(self.pending)
        for item in fresh:
            if item not in chosen:
                self.closure.lend(item.paths)
        for item in [item for item in self.pending if not old(item)]:
            self._settle(item, "kept", "young")
        self._close({})
        return works

    def run(self, works: dict[str, list[Work]]) -> None:
        """Run each kind's batch in order, then make every deletion durable."""
        try:
            for kind in BATCHES:
                batch = [work for work in works.get(kind, ()) if work.item in self.pending]
                if not batch:
                    continue
                if not self.selected():
                    message = "record_retirement_runtime_unselected"
                    raise ValueError(message)
                lane = kind == "lane-retirement"
                lock = (
                    try_hold(self.store / "operations" / "lane-retirement.lock")
                    if lane
                    else hold_proof_slot(self.store)
                )
                if lock is None:
                    for work in batch:
                        self._settle(work.item, "deferred", "lane-lock" if lane else "slot")
                    continue
                try:
                    self._batch(batch)
                finally:
                    lock.release()
        finally:
            self._sync()

    def _batch(self, batch: list[Work]) -> None:
        stoned: dict[StoreItem, _Stones] = {}
        for work in batch:
            stones = self._tombstone(work)
            if stones is not None:
                stoned[work.item] = stones
        if not stoned:
            return
        try:
            commands = process_commands(self.repo, exclude_pid=os.getpid(), strict=True)
            roots = running_writers(commands, self.writer_roots())
            writers = tuple(path.as_posix() for path in roots)
        except (OSError, ValueError):
            writers = ("unknown",)
        self.writers.update(writers)
        if writers:
            for item, stones in stoned.items():
                _restore(stones)
                self._settle(item, "deferred", "writer")
            return
        self._compare(stoned)

    def _tombstone(self, work: Work) -> _Stones | None:
        """Rename one item's files to tombstones and recheck them; keep the item on a change."""
        stones: _Stones = []
        reason = ""
        for path, size, mtime in work.facts:
            try:
                stone = retire(path)
            except FileNotFoundError:
                reason = "changed"
                break
            if stone is None:
                reason = "in_use"
                break
            stones.append((path, stone))
            if not _same(stone, size, mtime):
                reason = "changed"
                break
        if not reason:
            return stones
        _restore(stones)
        self._settle(work.item, "kept", reason)
        return None

    def _compare(self, stoned: dict[StoreItem, _Stones]) -> None:
        """Unlink what the refreshed closure does not name, under the custody lock."""
        while stoned:
            for _hold in range(_HOLDS):
                self.closure.refresh()
                self._close(stoned)
                if not stoned:
                    return
                lock = custody_lock(self.repo)
                try:
                    lock.acquire(blocking=False)
                except Timeout:
                    continue
                try:
                    if self.closure.moved():
                        continue
                    self._unlink(stoned)
                finally:
                    lock.release()
                break
            else:
                for item, stones in stoned.items():
                    _restore(stones)
                    self._settle(item, "deferred", "custody")
                return

    def _unlink(self, stoned: dict[StoreItem, _Stones]) -> None:
        """Unlink whole items' tombstones, at most one hold's worth, the receipt last."""
        room = _PER_HOLD
        for item, stones in list(stoned.items()):
            if len(stones) > room and room < _PER_HOLD:
                return
            room -= len(stones)
            del stoned[item]
            if any(os.path.lexists(path) for path, _stone in stones):
                # A writer linked the record again; its name holds the same bytes.
                _restore(stones)
                self._settle(item, "kept", "adopted")
                continue
            size = sum(stone.lstat().st_size for _path, stone in stones)
            for index, (_path, stone) in enumerate(stones):
                try:
                    stone.unlink()
                except PermissionError:
                    left = [stone for _path, stone in stones[index:]]
                    self._settle(item, "deferred", "unlink", left)
                    break
                self.touched.add(stone.parent)
            else:
                tally = self._count(item.kind)
                tally.deleted += 1
                tally.deleted_bytes += size
                self.pending.remove(item)
                self.deleted.append(item)

    def _close(self, stoned: dict[StoreItem, _Stones]) -> None:
        """Keep every pending item that a root or staying item names, restoring its tombstones."""
        while reached := self.closure.reached(self.pending):
            for item in reached:
                if item in stoned:
                    _restore(stoned.pop(item))
                self._settle(item, "kept", "named")

    def _settle(
        self,
        item: StoreItem,
        outcome: Literal["kept", "deferred"],
        reason: str,
        files: Iterable[Path] | None = None,
    ) -> None:
        """Count one item that stays and lend its digests to the closure."""
        self.pending.remove(item)
        self.closure.lend(item.paths if files is None else files)
        self._count(item.kind).add(outcome, reason)

    def _count(self, kind: str) -> KindTally:
        return self.tally.setdefault(kind, KindTally())

    def _sync(self) -> None:
        """Make the deletions durable and remove each lane operation directory they emptied."""
        operations = self.store / "operations" / "lane-retirement"
        emptied = False
        for directory in sorted(self.touched):
            if directory.parent == operations and not any(directory.iterdir()):
                directory.rmdir()
                emptied = True
            else:
                sync_directory(directory)
        if emptied:
            sync_directory(operations)


def _same(path: Path, size: int, mtime: int) -> bool:
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and (info.st_size, info.st_mtime_ns) == (size, mtime)


def _restore(stones: _Stones) -> None:
    for _path, stone in stones:
        restore(stone)

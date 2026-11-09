"""Admit heavy local work through one host-wide queue of owned tickets.

A host that CI virtual machines, renders and several repositories' proofs share serves its heavy
work best a few runs at a time. Each waiter writes a ticket, named by its arrival time, pid and
nonce, under ETHOS's host root, and holds an OS lock on it for its lifetime. It is admitted once
fewer than the declared slots of live tickets precede its own. Testing another ticket's lock tells
a live holder from a dead one, so a holder that dies frees its place without any cleanup by age;
the record is written only after its lock is held, so no reader mistakes a new ticket for a dead
one. A ticket records the repository, the executable's name and the start time, never the
command's arguments, which can carry secrets. An admitted child receives the ticket's nonce and
pid, so work that it starts joins its admission instead of waiting for itself; a copied token
whose holder has exited admits nothing.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import subprocess
import time
import tomllib
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.repo.runtime.host_store import host_store_root

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

ADMISSION_ENV = "ETHOS_HOST_ADMISSION"
CPU_CAP = "ETHOS_HOST_CPU_CAP"
XDIST_WORKERS = "PYTEST_XDIST_AUTO_NUM_WORKERS"
CONTENDED = "host_admission_contended"
_FIELDS = frozenset(("slots", "reserved_cpus", "load_limit"))
_RECORD = ("repository", "executable", "since")
_POLL_SECONDS = 5.0


@dataclass(frozen=True)
class HostDeclaration:
    """How many heavy runs one host admits at once, and how many CPUs it keeps for others."""

    slots: int = 1
    reserved_cpus: int = 0
    load_limit: float | None = None

    def worker_cap(self, cpus: int) -> int:
        """The workers an admitted run may start: the CPUs not reserved, at least one."""
        return max(1, cpus - self.reserved_cpus)


def read_host_declaration(root: Path, *, cpus: int) -> HostDeclaration:
    """Read `host.toml` in ETHOS's host root; an absent declaration keeps the defaults."""
    try:
        declared = tomllib.loads((root / "host.toml").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HostDeclaration()
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        message = "host_declaration_unreadable"
        raise ValueError(message) from error
    if unknown := sorted(set(declared) - _FIELDS):
        message = f"host_declaration_invalid:{unknown[0]}"
        raise ValueError(message)
    slots, reserved = declared.get("slots", 1), declared.get("reserved_cpus", 0)
    if type(slots) is not int or not 1 <= slots <= cpus:
        message = "host_declaration_invalid:slots"
        raise ValueError(message)
    if type(reserved) is not int or not 0 <= reserved < cpus:
        message = "host_declaration_invalid:reserved_cpus"
        raise ValueError(message)
    limit = declared.get("load_limit")
    if limit is not None and (
        type(limit) not in {int, float} or not math.isfinite(limit) or limit <= 0
    ):
        message = "host_declaration_invalid:load_limit"
        raise ValueError(message)
    return HostDeclaration(slots, reserved, None if limit is None else float(limit))


@dataclass(frozen=True)
class Ticket:
    """One place in the queue: its name orders it, and its lock proves that its holder lives."""

    name: str

    @property
    def token(self) -> str:
        """The nonce and pid that an admitted child receives to join this admission."""
        _arrival, pid, nonce = self.name.split("-")
        return f"{nonce}:{pid}"


class HostQueue:
    """The tickets of one host's queue directory."""

    def __init__(self, directory: Path, slots: int) -> None:
        self.directory = directory
        self.slots = slots

    def enter(self, repository: Path, executable: str) -> tuple[Ticket, FileLock]:
        """Take a place behind every earlier arrival, holding its lock before recording it."""
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        ticket = Ticket(f"{time.time_ns():020d}-{os.getpid()}-{secrets.token_hex(8)}")
        lock = FileLock(self.directory / f"{ticket.name}.lock", mode=0o600)
        lock.acquire(blocking=False)
        record = {
            "repository": str(repository),
            "executable": executable,
            "since": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        partial = self.directory / f".{ticket.name}.partial"
        partial.write_text(json.dumps(record), encoding="utf-8")
        partial.replace(self.directory / f"{ticket.name}.json")
        return ticket, lock

    def live(self) -> list[Ticket]:
        """The tickets whose holders still hold their locks, in arrival order.

        A held lock counts even before its record exists, so two arrivals that enter at once are
        still ordered by their names. A free lock belongs to a holder that exited: its record and
        lock file go, the record first, so no reader takes the free lock for a live ticket.
        """
        tickets = []
        for path in sorted(self.directory.glob("*.lock")):
            probe = FileLock(path, mode=0o600)
            try:
                probe.acquire(blocking=False)
            except Timeout:
                tickets.append(Ticket(path.stem))
                continue
            (self.directory / f"{path.stem}.json").unlink(missing_ok=True)
            probe.release()
            path.unlink(missing_ok=True)
        return tickets

    def admitted(self, ticket: Ticket) -> bool:
        """Whether fewer than the declared slots of live tickets arrived before this one."""
        return sum(other.name < ticket.name for other in self.live()) < self.slots

    def holds(self, token: str) -> bool:
        """Whether a token names a live ticket of the process that it names."""
        return any(ticket.token == token for ticket in self.live())

    def ahead(self, ticket: Ticket) -> dict[str, str] | None:
        """The record of the earliest live ticket before this one, when it is readable."""
        for other in self.live():
            if other.name >= ticket.name:
                break
            with suppress(OSError, ValueError):
                held = json.loads((self.directory / f"{other.name}.json").read_text("utf-8"))
                if isinstance(held, dict) and all(
                    isinstance(held.get(key), str) for key in _RECORD
                ):
                    return {key: held[key] for key in _RECORD}
        return None

    def contention(self, ticket: Ticket) -> str:
        """The gap of a wait that reached its bound, naming the earliest live holder."""
        if (held := self.ahead(ticket)) is None:
            return CONTENDED
        return f"{CONTENDED}:{held['executable']}:{held['repository']}:{held['since']}"

    def leave(self, ticket: Ticket, lock: FileLock) -> None:
        """Give up a place: the record goes first, then the lock and its file."""
        (self.directory / f"{ticket.name}.json").unlink(missing_ok=True)
        lock.release()
        (self.directory / f"{ticket.name}.lock").unlink(missing_ok=True)


def host_queue(*, cpus: int | None = None) -> tuple[HostQueue, HostDeclaration, int]:
    """Open this host's queue under its own declaration."""
    root = host_store_root()
    if root is None:
        message = "host_root_unavailable"
        raise ValueError(message)
    selected = cpus or os.cpu_count() or 1
    declaration = read_host_declaration(root, cpus=selected)
    return HostQueue(root / "host-admission" / "v1", declaration.slots), declaration, selected


class HostPlace:
    """One heavy run's place in this host's queue, or the live admission that it joins."""

    def __init__(self, repository: Path, executable: str) -> None:
        self.queue, self.declaration, self.cpus = host_queue()
        inherited = os.environ.get(ADMISSION_ENV, "")
        self.joined = inherited if inherited and self.queue.holds(inherited) else ""
        self.repository = repository
        self.executable = executable
        self.ticket: tuple[Ticket, FileLock] | None = None

    def admitted(self) -> bool:
        """Whether the run may start; the first call takes its place behind earlier arrivals."""
        if self.joined:
            return True
        if self.ticket is None:
            self.ticket = self.queue.enter(self.repository, self.executable)
        return self.queue.admitted(self.ticket[0])

    def holder(self) -> dict[str, str] | None:
        """The record of the earliest live run ahead of this one."""
        return self.queue.ahead(self.ticket[0]) if self.ticket else None

    def contention(self) -> str:
        """The gap of a wait that reached its bound."""
        return self.queue.contention(self.ticket[0]) if self.ticket else CONTENDED

    def environment(self) -> dict[str, str]:
        """What an admitted child receives: the admission's token and the host's worker cap."""
        cap = str(self.declaration.worker_cap(self.cpus))
        token = self.joined or (self.ticket[0].token if self.ticket else "")
        return {ADMISSION_ENV: token, CPU_CAP: cap, XDIST_WORKERS: cap}

    def leave(self) -> None:
        """Give up the place, if this run took one."""
        if self.ticket is not None:
            self.queue.leave(*self.ticket)
            self.ticket = None


@contextmanager
def admitted_host_work(
    repository: Path,
    executable: str,
    *,
    seconds: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Generator[dict[str, str]]:
    """Hold a host slot for one heavy run, or join the live one; yield its child's environment."""
    place = HostPlace(repository, executable)
    try:
        started = clock()
        while not place.admitted():
            remaining = started + seconds - clock()
            if remaining <= 0:
                raise ValueError(place.contention())
            sleep(min(_POLL_SECONDS, remaining))
        yield place.environment()
    finally:
        place.leave()


def run_admitted(command: tuple[str, ...], *, repository: Path, seconds: float) -> int:
    """Run one command as the admitted child, inheriting this process's streams."""
    with admitted_host_work(repository, Path(command[0]).name, seconds=seconds) as environment:
        return subprocess.run(command, env=os.environ | environment, check=False).returncode

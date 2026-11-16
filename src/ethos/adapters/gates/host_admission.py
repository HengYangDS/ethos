"""Admit heavy local work through one host-wide queue of owned tickets.

A host that CI virtual machines, renders and several repositories' proofs share serves its heavy
work best a few runs at a time. Each waiter writes a ticket, named by its arrival time, pid and
nonce, under ETHOS's host root, and holds an OS lock on it for its lifetime. It is admitted once
fewer than the declared slots of live tickets precede its own. Testing another ticket's lock tells
a live holder from a dead one, so a holder that dies frees its place without any cleanup by age;
the record is written only after its lock is held, so no reader mistakes a new ticket for a dead
one. A ticket records the repository, the executable's name and the start time, never the
command's arguments, which can carry secrets, and this engine's records also name the operation
and the owner mark that the holder declared; the three older fields stay so engines of earlier
releases share the directory. Results print no path: a holder is projected as its operation, its
executable, its owner mark, its pid and its start time, with only whether it belongs to the
reading repository. An admitted child receives the ticket's nonce and pid, so work that it starts
joins its admission instead of waiting for itself; a copied token whose holder has exited admits
nothing.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import subprocess
import sys
import time
import tomllib
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.repository.paradigm.parameters import ceiling_seconds

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator

ADMISSION_ENV = "ETHOS_HOST_ADMISSION"
CPU_CAP = "ETHOS_HOST_CPU_CAP"
XDIST_WORKERS = "PYTEST_XDIST_AUTO_NUM_WORKERS"
CONTENDED = "host_admission_contended"
UNAVAILABLE = "host_admission_unavailable"
WAITING = "host_admission_waiting"
_FIELDS = frozenset(("slots", "reserved_cpus", "load_limit"))
# The fields every released engine wrote; a record without all three is unreadable to them.
_RECORD = ("repository", "executable", "since")
_POLL_SECONDS = 5.0


@dataclass(frozen=True)
class HostDeclaration:
    """How many heavy runs one host admits at once, and how many CPUs it keeps for others."""

    slots: int = 1
    reserved_cpus: int = 0
    load_limit: float | None = None

    def worker_cap(self, cpus: int) -> int:
        """The workers one admitted run may start: its slot's share of the CPUs not reserved.

        The slots run at once, so they share what the reservation leaves; each gets at least one.
        """
        return max(1, (cpus - self.reserved_cpus) // self.slots)


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

    def enter(
        self, repository: Path, executable: str, *, operation: str = "", owner: str = ""
    ) -> tuple[Ticket, FileLock]:
        """Take a place behind every earlier arrival, holding its lock before recording it."""
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        ticket = Ticket(f"{time.time_ns():020d}-{os.getpid()}-{secrets.token_hex(8)}")
        lock = FileLock(self.directory / f"{ticket.name}.lock", mode=0o600)
        lock.acquire(blocking=False)
        record = {
            "repository": str(repository),
            "executable": executable,
            "since": datetime.now(UTC).isoformat(timespec="seconds"),
            "operation": operation,
            "owner": owner,
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

    def ahead(self, ticket: Ticket, *, reader: Path) -> dict[str, object] | None:
        """The projection of the earliest live ticket before this one, when it is readable."""
        for other in self.live():
            if other.name >= ticket.name:
                break
            if (projected := self.project(other, reader=reader)) is not None:
                return projected
        return None

    def project(self, ticket: Ticket, *, reader: Path) -> dict[str, object] | None:
        """Project one live ticket without its repository path; None when no record is read.

        The owner mark is the identity the holder declared, which only the holder's own
        repository sees: another repository learns that the holder belongs elsewhere, and
        nothing more.
        """
        with suppress(OSError, ValueError):
            held = json.loads((self.directory / f"{ticket.name}.json").read_text("utf-8"))
            if not isinstance(held, dict) or not all(
                isinstance(held.get(key), str) for key in _RECORD
            ):
                return None
            same = same_repository(str(held["repository"]), reader)
            return {
                "operation": held.get("operation", ""),
                "executable": held["executable"],
                "owner": held.get("owner", "") if same else "",
                "pid": int(ticket.name.split("-")[1]),
                "since": held["since"],
                "same_repository": same,
            }
        return None

    def contention(self, ticket: Ticket, *, reader: Path) -> str:
        """The gap of a wait that reached its bound, naming the earliest live holder."""
        if (held := self.ahead(ticket, reader=reader)) is None:
            return CONTENDED
        operation = held["operation"] or held["executable"]
        return f"{CONTENDED}:{operation}:{held['pid']}:{held['since']}"

    def entries(self, *, reader: Path) -> list[dict[str, object]]:
        """Every live recorded ticket in arrival order, with its state, removing nothing.

        A read must not race an entrant, so unlike `live` this leaves a dead holder's record and
        lock file for the next waiter, and a ticket whose record is not written yet is skipped.
        """
        listed: list[dict[str, object]] = []
        for path in sorted(self.directory.glob("*.lock")):
            probe = FileLock(path, mode=0o600)
            try:
                probe.acquire(blocking=False)
            except Timeout:
                pass
            else:
                probe.release()
                continue
            if (projected := self.project(Ticket(path.stem), reader=reader)) is not None:
                state = "holding" if len(listed) < self.slots else "waiting"
                listed.append({"state": state, **projected})
        return listed

    def leave(self, ticket: Ticket, lock: FileLock) -> None:
        """Give up a place: the record goes first, then the lock and its file.

        The lock goes also when the record cannot be removed: a held lock is a live ticket.
        """
        try:
            (self.directory / f"{ticket.name}.json").unlink(missing_ok=True)
        finally:
            lock.release()
        (self.directory / f"{ticket.name}.lock").unlink(missing_ok=True)


def same_repository(holder: str, reader: Path) -> bool:
    """Whether a record's repository and the reader share one Git common directory.

    Identity comes from Git's own common directory on both sides, never from a printed path; a
    repository whose identity cannot be read is simply not the reader's.
    """
    if not holder:
        return False
    try:
        own, theirs = git_common_dir(Path(holder)), git_common_dir(reader)
    except (OSError, ValueError, ProcessExecutionError):
        return False
    return bool(own) and own == theirs


def host_queue(*, cpus: int | None = None) -> tuple[HostQueue, HostDeclaration, int]:
    """Open this host's queue under its own declaration."""
    root = host_store_root()
    if root is None:
        message = "host_root_unavailable"
        raise ValueError(message)
    selected = cpus or os.cpu_count() or 1
    declaration = read_host_declaration(root, cpus=selected)
    return HostQueue(root / "host-admission" / "v1", declaration.slots), declaration, selected


def _named[**P, T](read: Callable[P, T]) -> Callable[P, T]:
    """Answer the named gap where the host queue cannot be read or written, for every caller."""

    @wraps(read)
    def named(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return read(*args, **kwargs)
        except OSError as error:
            raise ValueError(UNAVAILABLE) from error

    return named


class HostPlace:
    """One heavy run's place in this host's queue, or the live admission that it joins.

    Opening the queue, taking the place and reading what is ahead each answer the named gap
    for an OS error, so no caller maps it again.
    """

    @_named
    def __init__(self, repository: Path, executable: str, *, operation: str, owner: str) -> None:
        self.queue, self.declaration, self.cpus = host_queue()
        inherited = os.environ.get(ADMISSION_ENV, "")
        self.joined = inherited if inherited and self.queue.holds(inherited) else ""
        self.repository = repository
        self.executable = executable
        self.operation = operation
        self.owner = owner
        self.ticket: tuple[Ticket, FileLock] | None = None

    @_named
    def admitted(self) -> bool:
        """Whether the run may start; the first call takes its place behind earlier arrivals."""
        if self.joined:
            return True
        if self.ticket is None:
            self.ticket = self.queue.enter(
                self.repository, self.executable, operation=self.operation, owner=self.owner
            )
        return self.queue.admitted(self.ticket[0])

    @_named
    def holder(self) -> dict[str, object] | None:
        """The projection of the earliest live run ahead of this one."""
        ticket = self.ticket[0] if self.ticket else None
        return self.queue.ahead(ticket, reader=self.repository) if ticket else None

    @_named
    def contention(self) -> str:
        """The gap of a wait that reached its bound."""
        ticket = self.ticket[0] if self.ticket else None
        return self.queue.contention(ticket, reader=self.repository) if ticket else CONTENDED

    def environment(self) -> dict[str, str]:
        """What an admitted child receives: the admission's token and the host's worker cap.

        The cap only lowers a count the caller already declares: a guest with more CPUs must not
        raise the worker count of the job it hosts.
        """
        cap = str(self.declaration.worker_cap(self.cpus))
        declared = os.environ.get(XDIST_WORKERS, "")
        workers = declared if declared.isdigit() and 0 < int(declared) < int(cap) else cap
        token = self.joined or (self.ticket[0].token if self.ticket else "")
        return {ADMISSION_ENV: token, CPU_CAP: cap, XDIST_WORKERS: workers}

    def leave(self) -> None:
        """Give up the place, if this run took one."""
        if self.ticket is not None:
            self.queue.leave(*self.ticket)
            self.ticket = None

    def leave_on_exit(
        self, _kind: type[BaseException] | None, exit_: BaseException | None, *_trace: object
    ) -> None:
        """Give up the place as an exit callback, never replacing an exit that is in flight.

        An OS error while leaving is the named gap after a normal end. An exit already in flight,
        such as the wait's own gap or an interrupt, survives it and carries a note of the error.
        """
        try:
            self.leave()
        except OSError as error:
            if exit_ is None:
                raise ValueError(UNAVAILABLE) from error
            exit_.add_note(f"{UNAVAILABLE}: {type(error).__name__}")


class AdmissionBound:
    """How long one wait may still last: its bound, under the ceiling of every admission wait."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self.clock = clock
        self.started = self.since = self.asked = clock()
        self.held = False
        self.ceiling = ceiling_seconds("admission")

    def remaining(self, seconds: float, *, held: bool) -> float:
        """The seconds left of a bound that does not run behind a live holder.

        A ticket's lock shows that its holder lives, and a holder that dies frees its place, so a
        waiter behind a live holder keeps its place however long that holder runs. The time from
        an answer behind a holder to the next question is left out of the bound, and no other
        time is: what the wait used before the holder stays used. Behind a holder only the
        ceiling runs, which counts the whole wait, so every wait ends.
        """
        now = self.clock()
        if self.held:
            self.since += now - self.asked
        self.asked, self.held = now, held
        left = self.started + self.ceiling - now
        return left if held else min(self.since + seconds - now, left)


@dataclass(frozen=True)
class HostWork:
    """One heavy run's admission: its child's environment, how long it waited, whether it joined."""

    environment: dict[str, str]
    waited_seconds: float
    joined: bool


def report_event(event: dict[str, object]) -> None:
    """Write one admission event as a diagnostic stderr line beside the run's own progress."""
    sys.stderr.write(json.dumps(event, sort_keys=True) + "\n")
    sys.stderr.flush()


@contextmanager
def exported(values: dict[str, str]) -> Generator[None]:
    """Give an admitted run's children its host admission, then restore the environment."""
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def admitted_host_work(
    repository: Path,
    executable: str,
    *,
    operation: str,
    owner: str = "",
    seconds: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    report: Callable[[dict[str, object]], None] = report_event,
) -> Generator[HostWork]:
    """Hold a host slot for one heavy run, or join the live one, and yield its admission.

    A run that must wait writes one event naming the earliest live holder; a host root that cannot
    be written is a named gap rather than a traceback. Every ticket ahead is live by its lock, so
    the run keeps its place behind them until its total: the caller's own `seconds`, and at most
    the declared ceiling of an admission wait. The place is given up on every exit, also one
    that ends the wait: its total, an OS error or an interrupt. A place that cannot be given up
    is the same named gap after a normal end, and never replaces an exit that is in flight.
    """
    started = clock()
    total = ceiling_seconds("admission", seconds)
    with ExitStack() as held:
        try:
            place = HostPlace(repository, executable, operation=operation, owner=owner)
            held.push(place.leave_on_exit)
            announced = False
            while not place.admitted():
                if not announced:
                    announced = True
                    report(
                        {
                            "event": WAITING,
                            "operation": operation,
                            "executable": executable,
                            "holder": place.holder(),
                        }
                    )
                remaining = started + total - clock()
                if remaining <= 0:
                    raise ValueError(place.contention())
                sleep(min(_POLL_SECONDS, remaining))
        except OSError as error:
            message = UNAVAILABLE
            raise ValueError(message) from error
        waited = round(clock() - started, 1)
        yield HostWork(place.environment(), waited, bool(place.joined))


def run_admitted(
    command: tuple[str, ...],
    *,
    repository: Path,
    operation: str,
    owner: str,
    seconds: float | None,
) -> int:
    """Run one command as the admitted child, inheriting this process's streams."""
    with admitted_host_work(
        repository, Path(command[0]).name, operation=operation, owner=owner, seconds=seconds
    ) as work:
        return subprocess.run(command, env=os.environ | work.environment, check=False).returncode

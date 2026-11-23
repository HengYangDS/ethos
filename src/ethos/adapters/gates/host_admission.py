"""Admit heavy local work through one host-wide queue of owned tickets.

A host that CI virtual machines, renders and several repositories' proofs share serves its heavy
work best a few runs at a time. Each waiter writes a ticket, named by its arrival time, pid and
nonce, under ETHOS's host root, and holds an OS lock on it. It is admitted once fewer than the
declared slots of live tickets precede its own. A place lasts exactly while its lock is held:
testing another ticket's lock tells a live place from a dead one, so a place frees without any
cleanup by age. The command that `ethos host run` admits inherits the lock where the platform
lets a child inherit a descriptor, so a holder that is killed leaves its place to that command,
and a holder that leaves releases the lock for every inheritor; the place that a proof takes for
itself stays with its holder. Entries take turns under one lock beside the
queue, and each names itself after every ticket present: when an entry ends, every ticket named
before it has taken its lock or is dead, so no arrival is ever counted ahead of an admitted run.

A ticket records the repository, the executable's name and the start time, never the command's
arguments, which can carry secrets, and this engine's records also name the operation and the
owner mark that the holder declared; the three older fields stay so engines of earlier releases
share the directory. Results print no path: a holder is projected as its operation, its
executable, its owner mark, its pid, its process state and its start time, with only whether it
belongs to the reading repository. An admitted child receives the ticket's nonce and pid, so work
that it starts joins its admission instead of waiting for itself; a copied token admits nothing
once its ticket's lock is free.
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

from filelock import lock_descriptor
from filelock import unlock_descriptor

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.repository.paradigm.parameters import ceiling_seconds

if sys.platform != "win32":
    import fcntl

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
# How often an entry asks again for a gate or a lock that another process holds for an instant,
# and how long it asks before it answers that it is not in the queue yet.
_GATE_POLL_SECONDS = 0.005
_GATE_GRACE_SECONDS = 1.0


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
    """One place in the queue: its name orders it, and its held lock proves that it is live.

    `descriptor` is the holder's own descriptor of the ticket's lock file, or -1 for a ticket that
    this process only reads. The lock belongs to the open file, not to the process: it lasts
    while any process that inherited the descriptor keeps it open, and an explicit release
    through one descriptor frees it for all.
    """

    name: str
    descriptor: int = -1

    @property
    def token(self) -> str:
        """The nonce and pid that an admitted child receives to join this admission."""
        _arrival, pid, nonce = self.name.split("-")
        return f"{nonce}:{pid}"


# A new ticket's lock file is created and locked under this suffix, then renamed to `.lock`, so
# a listed ticket name is always one whose lock was taken.
PENDING_SUFFIX = ".pending"
# The queue's entry gate: a lock file beside the queue directory, outside every listed name.
GATE_SUFFIX = ".gate"


def opened_descriptor(path: Path, *, create: bool) -> int:
    """Open one ticket's lock file, non-inheritable until an admitted child is given it."""
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    return os.open(path, flags | (os.O_CREAT if create else 0), 0o600)


class QueueBusyError(Exception):
    """The queue's gate or a new ticket's own lock stayed held: the arrival is not in yet."""


def _taken(descriptor: int, deadline: float) -> None:
    """Take a lock that is held for an instant, or raise `QueueBusyError` at the deadline.

    A deadline that has passed gives one attempt.
    """
    while not lock_descriptor(descriptor, blocking=False):
        if time.monotonic() >= deadline:
            raise QueueBusyError
        time.sleep(_GATE_POLL_SECONDS)


@contextmanager
def gated(directory: Path, deadline: float) -> Generator[None]:
    """Hold the queue's entry gate, or raise `QueueBusyError` when it stays held until the deadline.

    Entries take turns under this one lock, and a dead ticket's files are removed only under it.
    So no entry is half-made while another is made or while files are removed, and each entry
    can name itself after every name present. The gate is a lock file beside the queue
    directory: no listing of tickets meets it and an older release never sees it. It is held
    for a few filesystem operations, and it goes with its descriptor, so a killed process
    leaves no gate held; a process that is stopped inside it delays entries only, never a read.
    """
    descriptor = opened_descriptor(directory.with_name(directory.name + GATE_SUFFIX), create=True)
    try:
        _taken(descriptor, deadline)
        try:
            yield
        finally:
            # Explicit, so a process forked meanwhile does not keep the gate after this ends.
            unlock_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _free(path: Path) -> bool:
    """Whether no process holds a ticket's lock now, proven by one probe that creates nothing.

    A holder's lock is exclusive and a probe asks for a shared one, so a probe is refused
    exactly while a holder or the work that inherited its lock has it, and probes never refuse
    each other. Windows has no such probe here: there a probe takes the lock for an instant, as
    in every release, and a second probe in that instant reads a free lock as held. The probe
    is its own open file and creates nothing; a lock file that is gone is free. A probe in the
    holding process reads its own lock as held, as any other process does.
    """
    try:
        probe = opened_descriptor(path, create=False)
    except FileNotFoundError:
        return True
    try:
        if sys.platform == "win32":
            return lock_descriptor(probe, blocking=False)
        try:
            fcntl.flock(probe, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        # Let go explicitly: a process forked at this instant would keep the probe's lock.
        fcntl.flock(probe, fcntl.LOCK_UN)
        return True
    finally:
        os.close(probe)


class HostQueue:
    """The tickets of one host's queue directory."""

    def __init__(self, directory: Path, slots: int) -> None:
        self.directory = directory
        self.slots = slots

    def enter(
        self, repository: Path, executable: str, *, operation: str = "", owner: str = ""
    ) -> Ticket:
        """Take a place behind every arrival before this one, or raise `QueueBusyError`.

        Entries take turns under the queue's gate, and each names itself after every name
        present, by the clock or by one more than the latest name. So the name order is the
        entry order whatever the clock does, and when an entry ends, every ticket named before
        it has already taken its lock or is dead: no later arrival is ever counted ahead of a
        ticket that was admitted. The lock file is created under a pending name, locked and
        recorded, and only then renamed to `.lock`. Windows cannot rename an open file, so there
        it is named at once; the instant in which it is unlocked lies inside the gate, where
        only tickets named before it are being counted. An entry that fails removes what it
        made, its lock file last, so whatever a killed entry leaves is found by that file.
        """
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        deadline = time.monotonic() + _GATE_GRACE_SECONDS
        with gated(self.directory, deadline):
            present = (path.name[:20] for path in self.directory.glob("*.lock*"))
            latest = max((int(arrival) for arrival in present if arrival.isdigit()), default=0)
            arrival = max(time.time_ns(), latest + 1)
            ticket = Ticket(f"{arrival:020d}-{os.getpid()}-{secrets.token_hex(8)}")
            named = self.directory / f"{ticket.name}.lock"
            held = named.with_name(named.name + PENDING_SUFFIX) if os.name == "posix" else named
            partial = self.directory / f".{ticket.name}.partial"
            descriptor = -1
            try:
                descriptor = opened_descriptor(held, create=True)
                # Only a reader's probe can hold a new file's lock, and only for an instant.
                _taken(descriptor, deadline)
                record = {
                    "repository": str(repository),
                    "executable": executable,
                    "since": datetime.now(UTC).isoformat(timespec="seconds"),
                    "operation": operation,
                    "owner": owner,
                }
                partial.write_text(json.dumps(record), encoding="utf-8")
                partial.replace(self.directory / f"{ticket.name}.json")
                if held != named:
                    held.replace(named)
            except BaseException:
                # The gate is still held, so nothing has counted this file or will meet it.
                # A removal that fails stays silent: the caller hears the entry's own failure,
                # and what is left keeps its lock file, by which a later read removes it.
                if descriptor >= 0:
                    os.close(descriptor)
                with suppress(OSError):
                    for left in (partial, self.directory / f"{ticket.name}.json", held, named):
                        left.unlink(missing_ok=True)
                raise
        return Ticket(ticket.name, descriptor)

    def locked(self) -> list[Ticket]:
        """The tickets whose locks are held now, in arrival order: a read that removes nothing.

        It waits for nothing and never takes the gate. A ticket that an entry is still making is
        not listed, and need not be: it is named after every ticket that could be counting.
        """
        return [
            Ticket(path.stem) for path in sorted(self.directory.glob("*.lock")) if not _free(path)
        ]

    def live(self) -> list[Ticket]:
        """The tickets whose locks are held, after removing what dead tickets left behind.

        A free lock belongs to no live process. Its files go only under the gate, where no entry
        is half-made, and the lock file goes last: whatever a removal that was cut short leaves
        is found again by that file, also a pending one of an entry that was killed half-made.
        When the gate is held, or a file cannot be removed now, the next read removes it; the
        answer is the same either way.
        """
        with suppress(QueueBusyError, FileNotFoundError), gated(self.directory, 0.0):
            for path in sorted(self.directory.glob("*.lock*")):
                if not _free(path):
                    continue
                name = path.name.partition(".lock")[0]
                with suppress(OSError):
                    for left in (f"{name}.json", f".{name}.partial", path.name):
                        (self.directory / left).unlink(missing_ok=True)
        return self.locked()

    def admitted(self, ticket: Ticket) -> bool:
        """Whether fewer than the declared slots of live tickets arrived before this one."""
        return sum(other.name < ticket.name for other in self.live()) < self.slots

    def holds(self, token: str) -> bool:
        """Whether a token names a ticket whose lock is held, by its holder or by its work.

        The token is the nonce and the process number of one ticket, and nothing else. A name
        ends with a dash, a process number, a dash and a nonce, and neither part holds a dash,
        so only a ticket's own two parts match its tail: no other value admits anything. The
        answer is read from the locks alone and waits for nothing, so work that joins its own
        admission is never held up by the queue's gate.
        """
        nonce, _, pid = token.partition(":")
        return any(ticket.name.endswith(f"-{pid}-{nonce}") for ticket in self.locked())

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
        nothing more. The holder's process is read from its pid where the platform can tell one
        from a reused number, so a place kept by work that outlived its holder shows `gone`.
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
                "holder": holder_state(int(ticket.name.split("-")[1])),
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

        The read waits for nothing and leaves a dead holder's files for the next waiter. A ticket
        whose lock is held but whose holder is gone is listed as holding: its work, not its
        holder, keeps the place.
        """
        listed: list[dict[str, object]] = []
        for ticket in self.locked():
            if (projected := self.project(ticket, reader=reader)) is not None:
                state = "holding" if len(listed) < self.slots else "waiting"
                listed.append({"state": state, **projected})
        return listed

    def leave(self, ticket: Ticket) -> None:
        """Give up a place that this process entered: the record first, then the lock and its file.

        The release is explicit, so the place is free at once although a process that the
        admitted command started may still have the lock's descriptor open. The lock goes also
        when the record cannot be removed: a held lock is a live ticket. A ticket that this
        process only read holds no place, so nothing of it is touched.
        """
        if ticket.descriptor == -1:
            return
        try:
            (self.directory / f"{ticket.name}.json").unlink(missing_ok=True)
        finally:
            try:
                unlock_descriptor(ticket.descriptor)
            finally:
                os.close(ticket.descriptor)
        (self.directory / f"{ticket.name}.lock").unlink(missing_ok=True)


def holder_state(pid: int) -> str:
    """Whether the process that entered a ticket still exists: `present`, `gone`, or empty.

    A held lock says that the work lives, not that the process which entered it does; a place
    kept by work that outlived its holder is listed with its holder gone. A process number can
    be reused, so `present` is the best a liveness probe gives, never a proof of identity. Empty
    is the answer where the platform cannot ask, or where the process belongs to another user.
    """
    # Signal 0 only asks on POSIX. On Windows `os.kill` ends the process for every such number.
    if os.name != "posix":
        return ""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "gone"
    except OSError:
        return ""
    return "present"


def inherited_descriptors(descriptor: int) -> tuple[int, ...]:
    """The ticket's descriptor for the admitted child to inherit, on the platforms that can.

    `subprocess` refuses `pass_fds` on Windows, where a child would need its own handle
    duplication through `msvcrt.get_osfhandle` and the ticket's `LockFileEx` byte range; that
    form is not built, so there an admitted child keeps the place only by its holder's lock,
    as every earlier release did.
    """
    if os.name != "posix" or descriptor < 0:
        return ()
    return (descriptor,)


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
    for an OS error, so no caller maps a queue error again.
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
        self.ticket: Ticket | None = None

    @_named
    def admitted(self) -> bool:
        """Whether the run may start; the first call takes its place behind earlier arrivals.

        A run joins only an admission that is live when the run is admitted. The token it was
        built with may be free by the time it asks; it then joins nothing and takes a place.
        """
        if self.joined:
            if self.queue.holds(self.joined):
                return True
            self.joined = ""
        if self.ticket is None:
            try:
                self.ticket = self.queue.enter(
                    self.repository, self.executable, operation=self.operation, owner=self.owner
                )
            except QueueBusyError:
                # Another entry holds the queue's gate: this run is not in yet, and asks again.
                return False
        return self.queue.admitted(self.ticket)

    @property
    def entered(self) -> bool:
        """Whether this run is in the queue: it joined a live admission or took a place."""
        return bool(self.joined) or self.ticket is not None

    @_named
    def holder(self) -> dict[str, object] | None:
        """The projection of the earliest live run ahead of this one."""
        return self.queue.ahead(self.ticket, reader=self.repository) if self.ticket else None

    @_named
    def contention(self) -> str:
        """The gap of a wait that reached its bound."""
        ticket = self.ticket
        return self.queue.contention(ticket, reader=self.repository) if ticket else UNAVAILABLE

    def descriptor(self) -> int:
        """The ticket's lock descriptor for the admitted work to inherit, or -1 when joined.

        A joined run took no place, so it has no lock to pass: its work lasts under the place
        of the admission that it joined.
        """
        return self.ticket.descriptor if self.ticket is not None else -1

    def environment(self) -> dict[str, str]:
        """What an admitted child receives: the admission's token and the host's worker cap.

        The cap only lowers a count the caller already declares: a guest with more CPUs must not
        raise the worker count of the job it hosts.
        """
        cap = str(self.declaration.worker_cap(self.cpus))
        declared = os.environ.get(XDIST_WORKERS, "")
        workers = declared if declared.isdigit() and 0 < int(declared) < int(cap) else cap
        token = self.joined or (self.ticket.token if self.ticket else "")
        return {ADMISSION_ENV: token, CPU_CAP: cap, XDIST_WORKERS: workers}

    def leave(self) -> None:
        """Give up the place, if this run took one; inherited work may keep it after this ends."""
        if self.ticket is not None:
            ticket, self.ticket = self.ticket, None
            self.queue.leave(ticket)

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

        A ticket's held lock shows that its place is live, and a place whose lock is free is
        gone, so a waiter behind a live place keeps its own however long that work runs. The
        time from an answer behind a holder to the next question is left out of the bound, and
        no other time is: what the wait used before the holder stays used. Behind a holder only the
        ceiling runs, which counts the whole wait, so every wait ends.
        """
        now = self.clock()
        if self.held:
            self.since += now - self.asked
        self.asked, self.held = now, held
        left = self.started + self.ceiling - now
        # The ceiling stands first: a bound that is no number then leaves its remainder.
        return left if held else min(left, self.since + seconds - now)


@dataclass(frozen=True)
class HostWork:
    """One heavy run's admission: its child's environment, wait, join and lock descriptor."""

    environment: dict[str, str]
    waited_seconds: float
    joined: bool
    descriptor: int = -1


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
                # A run that is not in the queue yet is behind nobody that it could name.
                if not announced and place.entered:
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
            # The place names the gap for the queue itself. This handler owns what else the
            # wait does: the write of its event, its clock and its sleep.
            message = UNAVAILABLE
            raise ValueError(message) from error
        waited = round(clock() - started, 1)
        yield HostWork(place.environment(), waited, bool(place.joined), place.descriptor())


def run_admitted(
    command: tuple[str, ...],
    *,
    repository: Path,
    operation: str,
    owner: str,
    seconds: float | None,
) -> int:
    """Run one command as the admitted child, inheriting this process's streams and place.

    The child receives the ticket's lock descriptor, so the place stays held until the last
    process of the work that inherited it ends, also when this process ends first.
    """
    with admitted_host_work(
        repository, Path(command[0]).name, operation=operation, owner=owner, seconds=seconds
    ) as work:
        return subprocess.run(
            command,
            env=os.environ | work.environment,
            check=False,
            pass_fds=inherited_descriptors(work.descriptor),
        ).returncode

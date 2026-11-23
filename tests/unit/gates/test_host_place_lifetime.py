"""A place in the host queue lasts exactly while its lock is held, by its holder or its work."""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import time
from contextlib import suppress
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.host_admission as host_admission

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

posix = pytest.mark.skipif(os.name != "posix", reason="a child inherits the lock on POSIX only")
# The admitted command: it names itself, then outlives whoever started it.
_WORK = "import os, time; print(os.getpid(), flush=True); time.sleep(60)"
# A holder that admits the command through the product's own entry and is then killed.
_HOLDER = (
    "import sys; from pathlib import Path\n"
    "import ethos.adapters.gates.host_admission as h\n"
    f"h.run_admitted((sys.executable, '-c', {_WORK!r}), repository=Path(sys.argv[1]),\n"
    "    operation='host.run', owner='', seconds=5)\n"
)
# A later arrival in another process: it says that it is about to enter, then where it stands,
# and keeps its place until its input closes.
_ARRIVAL = (
    "import sys; from pathlib import Path\n"
    "import ethos.adapters.gates.host_admission as h\n"
    "queue = h.HostQueue(h.host_store_root() / 'host-admission/v1', 1)\n"
    "sys.stdout.write('arriving\\n'); sys.stdout.flush()\n"
    "ticket = queue.enter(Path(sys.argv[1]), 'proof')\n"
    "sys.stdout.write(f'{ticket.name} {queue.admitted(ticket)}\\n'); sys.stdout.flush()\n"
    "sys.stdin.read()\n"
)
# How long a half-made entry is held open for a later arrival to slip past it.
_HALF_MADE_SECONDS = 0.5


def _queue() -> host_admission.HostQueue:
    root = host_admission.host_store_root()
    assert root is not None
    return host_admission.HostQueue(root / "host-admission/v1", 1)


def _kept_except_lock_files(patch: pytest.MonkeyPatch) -> None:
    """Make `os.unlink` refuse every lock file, as a filesystem that keeps it would."""
    unlink = os.unlink

    def kept(path: object, *arguments: object, **options: object) -> None:
        if str(path).endswith(".lock"):
            raise PermissionError
        unlink(path, *arguments, **options)

    patch.setattr(os, "unlink", kept)


def _ended(pid: int) -> None:
    """End one process and wait until the system has let go of what it held."""
    os.kill(pid, signal.SIGKILL)
    for _ in range(500):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    pytest.fail(f"process {pid} did not end")


@pytest.fixture
def killed_holder(tmp_path: Path) -> Iterator[tuple[host_admission.HostQueue, int, int]]:
    """A queue whose holder was killed while the command it admitted still runs."""
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(tmp_path)],
        stdout=subprocess.PIPE,
        text=True,
        env=os.environ,
    )
    assert holder.stdout is not None
    try:
        line = holder.stdout.readline()
    finally:
        holder.kill()
        holder.wait()
        holder.stdout.close()
    assert line.strip().isdigit(), "the holder admitted no command"
    work = int(line)
    try:
        yield _queue(), holder.pid, work
    finally:
        with suppress(ProcessLookupError):
            _ended(work)


@posix
def test_a_killed_holder_leaves_its_place_to_the_work_it_admitted(
    killed_holder: tuple[host_admission.HostQueue, int, int], tmp_path: Path
) -> None:
    """The place stays held until the admitted command ends; the next waiter enters only then."""
    queue, holder, work = killed_holder
    (held,) = queue.live()
    waiter = queue.enter(tmp_path / "next", "proof")

    assert not queue.admitted(waiter)
    assert queue.holds(held.token)
    (listed, waiting) = queue.entries(reader=tmp_path)
    assert (listed["state"], listed["pid"], listed["holder"]) == ("holding", holder, "gone")
    assert (waiting["state"], waiting["holder"]) == ("waiting", "present")

    _ended(work)

    assert queue.admitted(waiter)
    assert not queue.holds(held.token)
    assert [path.stem for path in queue.directory.glob("*.lock")] == [waiter.name]
    queue.leave(waiter)
    assert not any(queue.directory.iterdir())


@posix
def test_a_holder_that_leaves_frees_its_place_for_every_inheritor(tmp_path: Path) -> None:
    """A command that returns frees its place at once, though a process it started lives on."""
    queue = _queue()
    ticket = queue.enter(tmp_path, "renderer")
    survivor = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        pass_fds=host_admission.inherited_descriptors(ticket.descriptor),
    )
    try:
        waiter = queue.enter(tmp_path / "next", "proof")
        assert not queue.admitted(waiter)
        queue.leave(ticket)

        assert queue.admitted(waiter)
        assert not queue.holds(ticket.token)
        assert [found.name for found in queue.live()] == [waiter.name]
        queue.leave(waiter)
        assert not any(queue.directory.iterdir())
    finally:
        survivor.kill()
        survivor.wait()


@posix
def test_a_place_is_free_although_its_lock_file_cannot_be_removed(tmp_path: Path) -> None:
    """The release is explicit: a process that outlives the command keeps no place it was left."""
    queue = _queue()
    ticket = queue.enter(tmp_path, "renderer")
    survivor = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        pass_fds=host_admission.inherited_descriptors(ticket.descriptor),
    )
    try:
        with pytest.MonkeyPatch.context() as patch:
            _kept_except_lock_files(patch)
            with pytest.raises(PermissionError):
                queue.leave(ticket)

        # The next reader finds a free lock and removes the file that the holder could not.
        assert queue.live() == []
        assert not any(queue.directory.iterdir())
    finally:
        survivor.kill()
        survivor.wait()


def test_a_reader_that_races_a_leaving_holder_creates_nothing(tmp_path: Path) -> None:
    """A lock file that goes between a reader's listing and its probe is free and stays gone."""
    queue = _queue()
    ticket = queue.enter(tmp_path, "renderer")
    opened = os.open

    def raced(path: object, flags: int, *arguments: object, **options: object) -> int:
        if str(path).endswith(".lock") and not flags & os.O_CREAT:
            queue.leave(ticket)
        return opened(path, flags, *arguments, **options)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "open", raced)
        listed = queue.entries(reader=tmp_path)

    assert listed == []
    assert queue.live() == []
    assert not any(queue.directory.iterdir())


def test_a_ticket_that_was_only_read_is_not_left(tmp_path: Path) -> None:
    """Only the process that entered a place gives it up: a reader's copy removes nothing.

    A copy of a ticket that is already gone removes nothing either, and creates no file.
    """
    queue = _queue()
    ticket = queue.enter(tmp_path, "renderer")
    (read,) = queue.live()

    queue.leave(read)

    assert [entry["state"] for entry in queue.entries(reader=tmp_path)] == ["holding"]
    assert sorted(path.suffix for path in queue.directory.iterdir()) == [".json", ".lock"]
    queue.leave(ticket)
    assert not any(queue.directory.iterdir())
    # The place is gone, so its token names nothing, and a copy of it removes nothing.
    assert not queue.holds(ticket.token)
    queue.leave(host_admission.Ticket(ticket.name))
    assert not any(queue.directory.iterdir())


@posix
@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_a_later_arrival_cannot_enter_while_an_entry_is_half_made(
    tmp_path: Path, platform: str
) -> None:
    """Two arrivals never both find the queue empty: the later one waits for the earlier entry.

    The earlier entry is stopped where its lock file exists and its lock is not yet taken, on
    POSIX under the pending name and on Windows under the listed one. A second process arrives
    then. It gets no place until the first entry is whole, so it is named after it and counted
    behind it: one slot admits one run.
    """
    queue = _queue()
    opened = os.open
    suffix = ".lock.pending" if platform == "posix" else ".lock"
    arrivals: list[subprocess.Popen[bytes]] = []
    early: list[bool] = []

    def half_made(path: object, flags: int, *arguments: object, **options: object) -> int:
        descriptor = opened(path, flags, *arguments, **options)
        if flags & os.O_CREAT and str(path).endswith(suffix) and not arrivals:
            later = subprocess.Popen(
                [sys.executable, "-c", _ARRIVAL, str(tmp_path / "next")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                bufsize=0,
                env=os.environ,
            )
            arrivals.append(later)
            assert later.stdout is not None
            assert later.stdout.readline() == b"arriving\n"
            early.append(bool(select.select([later.stdout], [], [], _HALF_MADE_SECONDS)[0]))
        return descriptor

    # Only the queue's own view of the platform changes: the entry names its file as that
    # platform would, and every other reader of `os` keeps the real one.
    seen = SimpleNamespace(**{**vars(os), "name": platform, "open": half_made})
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(host_admission, "os", seen)
        ticket = queue.enter(tmp_path, "renderer")
    (later,) = arrivals
    assert later.stdin is not None
    assert later.stdout is not None
    try:
        name, admitted = later.stdout.readline().decode().split()
        assert early == [False]
        assert (ticket.name < name, queue.admitted(ticket), admitted) == (True, True, "False")
    finally:
        later.stdin.close()
        later.wait()
        later.stdout.close()
    queue.leave(ticket)
    assert queue.live() == []
    assert not any(queue.directory.iterdir())


def test_a_read_during_an_entry_counts_nothing_half_made_and_removes_nothing(
    tmp_path: Path,
) -> None:
    """A read that runs while an entry holds the gate lists no half-made ticket and reaps none."""
    queue = _queue()
    opened = os.open
    reads: list[list[str]] = []

    def hooked(path: object, flags: int, *arguments: object, **options: object) -> int:
        made = bool(flags & os.O_CREAT) and ".lock" in str(path) and not reads
        descriptor = opened(path, flags, *arguments, **options)
        if made:
            reads.append([ticket.name for ticket in queue.live()])
        return descriptor

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "open", hooked)
        ticket = queue.enter(tmp_path, "renderer")

    assert reads == [[]]
    assert [listed.name for listed in queue.live()] == [ticket.name]
    assert sorted(path.suffix for path in queue.directory.iterdir()) == [".json", ".lock"]
    queue.leave(ticket)
    assert not any(queue.directory.iterdir())


def test_an_arrival_is_named_after_every_ticket_present_whatever_the_clock_says(
    tmp_path: Path,
) -> None:
    """A clock that steps back puts no arrival ahead of a ticket that was admitted."""
    queue = _queue()
    first = queue.enter(tmp_path, "renderer")
    assert queue.admitted(first)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(time, "time_ns", lambda: 1)
        second = queue.enter(tmp_path / "next", "proof")

    assert first.name < second.name
    assert (queue.admitted(first), queue.admitted(second)) == (True, False)
    queue.leave(first)
    assert queue.admitted(second)
    queue.leave(second)
    assert not any(queue.directory.iterdir())


def test_an_arrival_that_meets_a_held_gate_is_not_in_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that cannot take the queue's gate has no place, made nothing, and asks again."""
    monkeypatch.setattr(host_admission, "_POLL_SECONDS", 0.05)
    place = host_admission.HostPlace(tmp_path, "renderer", operation="host.run", owner="")
    queue = _queue()
    queue.directory.mkdir(parents=True, exist_ok=True)

    with host_admission.gated(queue.directory, seconds=0):
        assert not place.admitted()
        assert (place.descriptor(), place.contention()) == (-1, host_admission.UNAVAILABLE)
        assert not any(queue.directory.iterdir())

    assert place.admitted()
    place.leave()
    assert not any(queue.directory.iterdir())


def test_an_entry_that_fails_leaves_nothing_and_no_place(tmp_path: Path) -> None:
    """An entry that cannot write its record removes what it made before it lets the gate go."""
    queue = _queue()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(host_admission.json, "dumps", Mock(side_effect=OSError("disk full")))
        with pytest.raises(OSError, match=r"disk full"):
            queue.enter(tmp_path, "renderer")

    assert not any(queue.directory.iterdir())
    ticket = queue.enter(tmp_path, "renderer")
    assert queue.admitted(ticket)
    queue.leave(ticket)
    assert not any(queue.directory.iterdir())


def test_what_a_killed_entry_left_goes_at_the_next_read_that_holds_the_gate() -> None:
    """A half-made entry's files are removed under the gate only, where no entry is half-made."""
    queue = _queue()
    queue.directory.mkdir(parents=True, exist_ok=True)
    name = "00000000000000000001-1-0123456789abcdef"
    for left in (f"{name}.lock.pending", f"{name}.json", f".{name}.partial"):
        (queue.directory / left).write_bytes(b"{}")

    with host_admission.gated(queue.directory, seconds=0):
        assert queue.live() == []
        assert len(list(queue.directory.iterdir())) == 3

    assert queue.live() == []
    assert not any(queue.directory.iterdir())


@posix
def test_a_record_survives_a_reader_until_its_lock_file_goes(tmp_path: Path) -> None:
    """A record goes only after its lock file did: a file that cannot be removed keeps its record.

    Windows refuses to remove an open file, so the same order keeps a live ticket's record when
    its lock file stays.
    """
    queue = _queue()
    dead = queue.enter(tmp_path, "renderer")
    os.close(dead.descriptor)

    with pytest.MonkeyPatch.context() as patch:
        _kept_except_lock_files(patch)
        assert queue.live() == []

    assert sorted(path.suffix for path in queue.directory.iterdir()) == [".json", ".lock"]
    assert queue.entries(reader=tmp_path) == []
    (queue.directory / f"{dead.name}.lock").unlink()
    (queue.directory / f"{dead.name}.json").unlink()


def test_a_token_names_one_ticket_exactly(tmp_path: Path) -> None:
    """A token answers from the lock alone, and only its own ticket's: no pattern is a token."""
    queue = _queue()
    ticket = queue.enter(tmp_path, "renderer")

    assert queue.holds(ticket.token)
    for pattern in ("*:*", "?:*", "*", ticket.token + "*", "%-%-%", ticket.token.upper()):
        assert not queue.holds(pattern)
    os.close(ticket.descriptor)
    assert not queue.holds(ticket.token)


def test_a_place_that_could_not_be_given_up_is_not_given_up_twice(tmp_path: Path) -> None:
    """A leave that fails has still closed the lock, so the run keeps no ticket to leave again."""
    place = host_admission.HostPlace(tmp_path, "renderer", operation="host.run", owner="")
    assert place.admitted()

    with pytest.MonkeyPatch.context() as patch:
        _kept_except_lock_files(patch)
        with pytest.raises(PermissionError):
            place.leave()
        # The number is free for the next file the process opens; a second leave must not
        # close that file.
        (tmp_path / "other").touch()
        reused = os.open(tmp_path / "other", os.O_RDONLY)
        try:
            place.leave()
            assert place.descriptor() == -1
            os.fstat(reused)
        finally:
            with suppress(OSError):
                os.close(reused)

    assert _queue().live() == []


def test_no_process_is_signalled_where_the_platform_is_not_posix() -> None:
    """Signal 0 ends a process on Windows, so there the read names no holder state."""
    with pytest.MonkeyPatch.context() as patch:
        kill = Mock()
        patch.setattr(os, "kill", kill)
        patch.setattr(os, "name", "nt")
        state = host_admission.holder_state(os.getpid())
        passed = host_admission.inherited_descriptors(7)

    assert (state, passed) == ("", ())
    kill.assert_not_called()


def test_a_holder_of_another_user_has_no_named_state() -> None:
    """A process that exists and may not be signalled is neither present nor gone."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "kill", Mock(side_effect=PermissionError))
        patch.setattr(os, "name", "posix")
        state = host_admission.holder_state(1)

    assert state == ""

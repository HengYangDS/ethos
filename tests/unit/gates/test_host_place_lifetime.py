"""A place in the host queue lasts exactly while its lock is held, by its holder or its work."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from contextlib import suppress
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
def test_a_reader_that_finds_the_reaper_held_counts_the_ticket_as_live(tmp_path: Path) -> None:
    """A reader that cannot hold the reaper removes nothing; the next reader removes the file.

    The same process's second descriptor of the reaper's file contends like another process's.
    """
    queue = _queue()
    dead = queue.enter(tmp_path, "renderer")
    os.close(dead.descriptor)

    with host_admission.reaper(queue.directory) as held:
        assert held
        listed = queue.live()
        # A second descriptor of the same file contends only from another open file.
        second = queue.live()

    assert [ticket.name for ticket in listed] == [dead.name]
    assert [ticket.name for ticket in second] == [dead.name]
    assert sorted(path.suffix for path in queue.directory.iterdir()) == [".json", ".lock"]
    assert queue.live() == []
    assert not any(queue.directory.iterdir())
    assert [path.name for path in queue.directory.parent.glob("*.reap")] == ["v1.reap"]


@posix
def test_a_reader_cannot_remove_a_ticket_that_is_being_named(tmp_path: Path) -> None:
    """An entrant names and locks its file under the reaper, so a reader meets no bare file.

    The reader that runs at the instant the entrant has created its file and not yet locked it
    cannot hold the reaper, so it counts the ticket as live; without the reaper it would remove
    the file and the entrant would have to start over.
    """
    queue = _queue()
    opened = host_admission.opened_descriptor
    reads: list[list[host_admission.Ticket]] = []

    def hooked(path: object, *, create: bool) -> int:
        descriptor = opened(path, create=create)
        if create and str(path).endswith(".lock") and not reads:
            reads.append(queue.live())
        return descriptor

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(host_admission, "opened_descriptor", hooked)
        ticket = queue.enter(tmp_path, "renderer")

    assert len(reads) == 1
    assert [listed.name for listed in reads[0]] == [ticket.name]
    assert sorted(path.suffix for path in queue.directory.iterdir()) == [".json", ".lock"]
    queue.leave(ticket)


def test_a_locked_file_that_lost_its_name_takes_no_place(tmp_path: Path) -> None:
    """The second guard: a lock on a file with no name guards nothing, so the entry fails."""
    queue = _queue()
    gone = queue.directory / "00000000000000000001-1-nonce.lock"
    queue.directory.mkdir(parents=True, exist_ok=True)
    descriptor = host_admission.opened_descriptor(gone, create=True)
    try:
        gone.unlink()
        with pytest.raises(BlockingIOError):
            host_admission.record_ticket(
                queue.directory / "record.json",
                descriptor,
                repository=tmp_path,
                executable="renderer",
                operation="host.run",
                owner="",
            )
    finally:
        os.close(descriptor)

    assert not any(queue.directory.iterdir())


def test_the_reaper_is_not_taken_where_an_open_file_cannot_be_removed(tmp_path: Path) -> None:
    """On Windows a reader cannot remove a live file, so the reaper is never created."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "name", "nt")
        with host_admission.reaper(tmp_path) as held:
            assert held is False

    assert [path.name for path in tmp_path.parent.glob("*.reap")] == []


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

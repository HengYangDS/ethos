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
def test_a_reader_meeting_a_new_ticket_counts_it_and_leaves_it(tmp_path: Path) -> None:
    """A reader that runs the instant the entrant has created its pending file touches nothing.

    The file is younger than one poll, so it is not reaped; the entry then locks it and renames,
    and the ticket is listed under its own name.
    """
    queue = _queue()
    opened = os.open
    reads: list[list[str]] = []

    def hooked(path: object, flags: int, *arguments: object, **options: object) -> int:
        created = bool(flags & os.O_CREAT) and str(path).endswith(".lock.pending")
        descriptor = opened(path, flags, *arguments, **options)
        if created and not reads:
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


@posix
def test_a_locked_pending_ticket_counts_before_its_rename() -> None:
    """A ticket that holds its lock under the pending name counts, so it cannot be passed by."""
    queue = _queue()
    queue.directory.mkdir(parents=True, exist_ok=True)
    name = "00000000000000000001-1-0123456789abcdef"
    pending = queue.directory / f"{name}.lock.pending"
    descriptor = host_admission.opened_descriptor(pending, create=True)
    try:
        assert host_admission.lock_descriptor(descriptor, blocking=False)

        assert [ticket.name for ticket in queue.live()] == [name]
        assert not queue.admitted(host_admission.Ticket(f"{time.time_ns():020d}-2-x"))
    finally:
        host_admission.unlock_descriptor(descriptor)
        os.close(descriptor)
        pending.unlink()


@posix
def test_a_pending_file_older_than_a_poll_is_removed() -> None:
    """An entry that stopped before its rename leaves a pending file; a later reader removes it."""
    queue = _queue()
    queue.directory.mkdir(parents=True, exist_ok=True)
    orphan = queue.directory / "00000000000000000001-1-0123456789abcdef.lock.pending"
    orphan.write_bytes(b"")
    (queue.directory / "00000000000000000001-1-0123456789abcdef.json").write_text(
        "{}", encoding="utf-8"
    )
    old = time.time() - 3 * host_admission.POLL_SECONDS
    os.utime(orphan, (old, old))

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

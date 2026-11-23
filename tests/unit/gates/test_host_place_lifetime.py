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


def _ended(pid: int) -> None:
    """End one process and wait until the system has let go of what it held."""
    os.kill(pid, signal.SIGKILL)
    for _ in range(200):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)


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
    work = int(holder.stdout.readline())
    holder.kill()
    holder.wait()
    holder.stdout.close()
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
    unlink = os.unlink

    def kept(path: object, *arguments: object, **options: object) -> None:
        if str(path).endswith(".lock"):
            raise PermissionError
        unlink(path, *arguments, **options)

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(os, "unlink", kept)
            with pytest.raises(PermissionError):
                queue.leave(ticket)

        # The next reader finds a free lock and removes the file that the holder could not.
        assert queue.live() == []
        assert not any(queue.directory.iterdir())
    finally:
        survivor.kill()
        survivor.wait()


def test_a_probe_of_a_lock_file_that_is_gone_creates_nothing(tmp_path: Path) -> None:
    """A reader that races a leaving holder finds the place free and writes no file."""
    queue = _queue()
    gone = queue.enter(tmp_path, "renderer")
    queue.leave(gone)

    # The same ticket as a reader sees it: a name, and no descriptor of its own.
    queue.leave(host_admission.Ticket(gone.name))

    assert not queue.holds(gone.token)
    assert not any(queue.directory.iterdir())


def test_an_entry_that_meets_a_readers_probe_is_an_os_error_and_keeps_nothing(
    tmp_path: Path,
) -> None:
    """A probe holds a new lock for an instant; the entrant then takes no place and leaves none."""
    queue = _queue()
    opened = os.open
    probes: list[int] = []

    def probed(path: object, flags: int, *arguments: object, **options: object) -> int:
        descriptor = opened(path, flags, *arguments, **options)
        if flags & os.O_CREAT and str(path).endswith(".lock"):
            probes.append(opened(path, os.O_RDWR))
            assert host_admission.lock_descriptor(probes[-1], blocking=False)
        return descriptor

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(os, "open", probed)
            with pytest.raises(BlockingIOError):
                queue.enter(tmp_path, "renderer")
    finally:
        for probe in probes:
            os.close(probe)

    assert len(probes) == 1
    assert queue.live() == []
    assert not any(queue.directory.iterdir())


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

"""Arrivals enter the host queue one at a time, and no read mistakes a probe for a holder."""

from __future__ import annotations

import os
import select
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.gates.host_admission as host_admission

posix = pytest.mark.skipif(os.name != "posix", reason="the pending name and the shared probe")
# A later arrival in another process: it says that it is about to enter, asks until it is in, as
# a waiting run does, then says where it stands and keeps its place until its input closes.
_ARRIVAL = (
    "import sys; from pathlib import Path\n"
    "import ethos.adapters.gates.host_admission as h\n"
    "queue = h.host_queue()[0]\n"
    "sys.stdout.write('arriving\\n'); sys.stdout.flush()\n"
    "while True:\n"
    "    try:\n"
    "        ticket = queue.enter(Path(sys.argv[1]), 'proof')\n"
    "        break\n"
    "    except h.QueueBusyError:\n"
    "        pass\n"
    "sys.stdout.write(f'{ticket.name} {queue.admitted(ticket)}\\n'); sys.stdout.flush()\n"
    "sys.stdin.read()\n"
)
# How long a half-made entry is held open for a later arrival to slip past it.
_HALF_MADE_SECONDS = 0.5


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
    queue = host_admission.host_queue()[0]
    opened = os.open
    suffix = ".lock.pending" if platform == "posix" else ".lock"
    arrivals: list[subprocess.Popen[bytes]] = []
    early: list[bool] = []
    entered: list[host_admission.Ticket] = []

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
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(host_admission, "os", seen)
            entered.append(queue.enter(tmp_path, "renderer"))
        (ticket,), (later,) = entered, arrivals
        assert later.stdout is not None
        name, admitted = later.stdout.readline().decode().split()
        assert early == [False]
        assert (ticket.name < name, queue.admitted(ticket), admitted) == (True, True, "False")
    finally:
        for later in arrivals:
            for stream in (later.stdin, later.stdout):
                if stream is not None:
                    stream.close()
            later.wait()
        for ticket in entered:
            queue.leave(ticket)
    assert queue.live() == []
    assert not any(queue.directory.iterdir())


def test_a_read_during_an_entry_counts_nothing_half_made_and_removes_nothing(
    tmp_path: Path,
) -> None:
    """A read that runs while an entry holds the gate lists no half-made ticket and reaps none."""
    queue = host_admission.host_queue()[0]
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
    queue = host_admission.host_queue()[0]
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
    monkeypatch.setattr(host_admission, "_GATE_GRACE_SECONDS", 0.05)
    place = host_admission.HostPlace(tmp_path, "renderer", operation="host.run", owner="")
    queue = host_admission.host_queue()[0]
    queue.directory.mkdir(parents=True, exist_ok=True)

    with host_admission.gated(queue.directory, 0.0):
        assert not place.admitted()
        assert not place.entered
        assert (place.descriptor(), place.contention()) == (-1, host_admission.UNAVAILABLE)
        assert not any(queue.directory.iterdir())

    assert place.admitted()
    assert place.entered
    place.leave()
    assert not any(queue.directory.iterdir())


@posix
@pytest.mark.parametrize("failing", [1, 2])
def test_an_entry_that_fails_leaves_nothing_and_no_place(tmp_path: Path, failing: int) -> None:
    """An entry that fails removes what it made before it lets the gate go.

    The first rename fails while the partial record and the pending lock file exist; the second
    fails while the record and the pending lock file do.
    """
    queue = host_admission.host_queue()[0]
    replace = Path.replace
    renames: list[Path] = []

    def refused(source: Path, target: Path) -> Path:
        renames.append(source)
        if len(renames) == failing:
            message = "disk full"
            raise OSError(message)
        return replace(source, target)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "replace", refused)
        with pytest.raises(OSError, match=r"disk full"):
            queue.enter(tmp_path, "renderer")

    assert len(renames) == failing
    assert not any(queue.directory.iterdir())
    ticket = queue.enter(tmp_path, "renderer")
    assert queue.admitted(ticket)
    queue.leave(ticket)
    assert not any(queue.directory.iterdir())


def test_what_a_killed_entry_left_goes_at_the_next_read_that_holds_the_gate() -> None:
    """A half-made entry's files are removed under the gate only, where no entry is half-made."""
    queue = host_admission.host_queue()[0]
    queue.directory.mkdir(parents=True, exist_ok=True)
    name = "00000000000000000001-1-0123456789abcdef"
    for left in (f"{name}.lock.pending", f"{name}.json", f".{name}.partial"):
        (queue.directory / left).write_bytes(b"{}")

    with host_admission.gated(queue.directory, 0.0):
        assert queue.live() == []
        assert len(list(queue.directory.iterdir())) == 3

    assert queue.live() == []
    assert not any(queue.directory.iterdir())


def test_an_entry_whose_own_lock_stays_held_gives_up_and_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new ticket's lock that another process keeps is waited for no longer than the gate."""
    monkeypatch.setattr(host_admission, "_GATE_GRACE_SECONDS", 0.05)
    queue = host_admission.host_queue()[0]
    opened = os.open
    keepers: list[int] = []

    def kept(path: object, flags: int, *arguments: object, **options: object) -> int:
        descriptor = opened(path, flags, *arguments, **options)
        if flags & os.O_CREAT and str(path).endswith((".lock", ".lock.pending")) and not keepers:
            keepers.append(opened(path, os.O_RDWR))
            assert host_admission.lock_descriptor(keepers[0], blocking=False)
        return descriptor

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(os, "open", kept)
            with pytest.raises(host_admission.QueueBusyError):
                queue.enter(tmp_path, "renderer")
    finally:
        for keeper in keepers:
            os.close(keeper)

    assert not any(queue.directory.iterdir())
    ticket = queue.enter(tmp_path, "renderer")
    assert queue.admitted(ticket)
    queue.leave(ticket)
    assert not any(queue.directory.iterdir())


@posix
def test_probes_of_one_dead_ticket_do_not_refuse_each_other(tmp_path: Path) -> None:
    """A reader that is inside its probe makes no dead ticket live for anyone else.

    A probe asks for a shared lock, so a second reader, a token's check and the next arrival all
    read the dead ticket as free while the first probe still has the file.
    """
    fcntl = pytest.importorskip("fcntl")
    queue = host_admission.host_queue()[0]
    dead = queue.enter(tmp_path, "renderer")
    os.close(dead.descriptor)
    probing = host_admission.opened_descriptor(queue.directory / f"{dead.name}.lock", create=False)
    try:
        fcntl.flock(probing, fcntl.LOCK_SH | fcntl.LOCK_NB)

        assert queue.locked() == []
        assert not queue.holds(dead.token)
        place = host_admission.HostPlace(tmp_path / "next", "proof", operation="host.run", owner="")
        assert (place.admitted(), place.joined) == (True, "")
        place.leave()
    finally:
        os.close(probing)
    assert not any(queue.directory.iterdir())


def test_a_run_that_was_not_in_yet_names_the_holder_it_then_waits_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one waiting event is written when the run has a place, and names who is ahead."""
    monkeypatch.setattr(host_admission, "_GATE_GRACE_SECONDS", 0.0)
    queue = host_admission.host_queue()[0]
    holder = queue.enter(tmp_path / "busy", "renderer", operation="host.run")
    events: list[dict[str, object]] = []
    with ExitStack() as gate:
        gate.enter_context(host_admission.gated(queue.directory, 0.0))
        # The first poll finds the gate held; the second finds the holder; the third is admitted.
        steps = [gate.close, lambda: queue.leave(holder)]

        with host_admission.admitted_host_work(
            tmp_path,
            "proof",
            operation="host.run",
            seconds=600.0,
            sleep=lambda _seconds: steps.pop(0)(),
            report=events.append,
        ):
            pass

    assert steps == []
    assert [event["event"] for event in events] == [host_admission.WAITING]
    ahead = events[0]["holder"]
    assert isinstance(ahead, dict)
    assert ahead["executable"] == "renderer"
    assert not any(queue.directory.iterdir())

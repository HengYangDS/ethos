"""Heavy local work is admitted host-wide, in arrival order, by tickets whose holders live."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.host_admission as host_admission
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tests.support.clock import FakeClock
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def host_root(tmp_path: Path) -> Path:
    """The test's own ETHOS host root, which the suite binds through `XDG_DATA_HOME`."""
    root = host_admission.host_store_root()
    assert root is not None
    assert root.is_relative_to(tmp_path)
    return root


def _declare(root: Path, text: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "host.toml").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (None, (1, 0, 8)),
        ("slots = 2\nreserved_cpus = 2\n", (2, 2, 3)),
        ("slots = 3\n", (3, 0, 2)),
        ("slots = 2\nreserved_cpus = 6\n", (2, 6, 1)),
        ("reserved_cpus = 7\n", (1, 7, 1)),
    ],
)
def test_the_host_declaration_bounds_slots_and_workers(
    host_root: Path, text: str | None, expected: tuple[int, int, int]
) -> None:
    """One slot and no reserved CPUs by default; the slots share the CPUs left, at least one."""
    if text is not None:
        _declare(host_root, text)

    declared = host_admission.read_host_declaration(host_root, cpus=8)

    assert (declared.slots, declared.reserved_cpus, declared.worker_cap(8)) == expected


@pytest.mark.parametrize(
    ("text", "gap"),
    [
        ("slots = 0\n", "host_declaration_invalid:slots"),
        ("slots = true\n", "host_declaration_invalid:slots"),
        ("reserved_cpus = 8\n", "host_declaration_invalid:reserved_cpus"),
        ("reserved_cpus = -1\n", "host_declaration_invalid:reserved_cpus"),
        ("slot = 1\n", "host_declaration_invalid:slot"),
        ("slots = [\n", "host_declaration_unreadable"),
        ("load_limit = 0\n", "host_declaration_invalid:load_limit"),
        ("load_limit = true\n", "host_declaration_invalid:load_limit"),
        ("load_limit = -2.5\n", "host_declaration_invalid:load_limit"),
    ],
)
def test_an_out_of_range_declaration_is_refused_not_clamped(
    host_root: Path, text: str, gap: str
) -> None:
    """Zero slots, every CPU reserved or an unknown field names its gap."""
    _declare(host_root, text)

    with pytest.raises(ValueError, match=f"^{gap}$"):
        host_admission.read_host_declaration(host_root, cpus=8)


def _queue(root: Path, slots: int = 1) -> host_admission.HostQueue:
    return host_admission.HostQueue(root / "host-admission/v1", slots)


def held_pid(ticket_name: str) -> int:
    """The pid that a ticket's name records, which every projection shows for display."""
    return int(ticket_name.split("-")[1])


def test_heavy_runs_are_admitted_in_arrival_order(host_root: Path, tmp_path: Path) -> None:
    """With one slot the later run waits for the earlier, and a third follows both."""
    queue = _queue(host_root)
    first, second, third = (queue.enter(tmp_path, name) for name in ("one", "two", "three"))

    assert [queue.admitted(ticket) for ticket in (first, second, third)] == [
        True,
        False,
        False,
    ]
    queue.leave(first)
    assert [queue.admitted(ticket) for ticket in (second, third)] == [True, False]
    queue.leave(second)
    assert queue.admitted(third)
    queue.leave(third)
    assert not any(queue.directory.iterdir())


def test_two_declared_slots_admit_two_runs(host_root: Path, tmp_path: Path) -> None:
    """A host that declares two slots runs two heavy runs at once and queues the third."""
    queue = _queue(host_root, slots=2)
    tickets = [queue.enter(tmp_path, str(index)) for index in range(3)]

    assert [queue.admitted(ticket) for ticket in tickets] == [True, True, False]
    for ticket in tickets:
        queue.leave(ticket)
    assert not any(queue.directory.iterdir())


def test_a_dead_holder_frees_its_place_without_cleanup(host_root: Path, tmp_path: Path) -> None:
    """A holder that exits without leaving releases its lock, and the next waiter is admitted."""
    queue = _queue(host_root)
    script = (
        "import sys; from pathlib import Path\n"
        "import ethos.adapters.gates.host_admission as h\n"
        "h.HostQueue(Path(sys.argv[1]), 1).enter(Path(sys.argv[2]), 'gone')\n"
        "print('entered')\n"
    )
    subprocess.run(
        [sys.executable, "-c", script, str(queue.directory), str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ,
    )
    assert len(list(queue.directory.glob("*.json"))) == 1
    waiter = queue.enter(tmp_path, "next")

    assert queue.admitted(waiter)
    assert [path.stem for path in queue.directory.glob("*.json")] == [waiter.name]
    queue.leave(waiter)


def test_a_bounded_wait_names_the_holder(host_root: Path, tmp_path: Path) -> None:
    """A run that waits for the whole bound ends without running and names who holds the host."""
    queue = _queue(host_root)
    holder = queue.enter(
        tmp_path / "busy-repository", "renderer", operation="host.run", owner="agent:test:holder"
    )
    clock = FakeClock()

    with (
        pytest.raises(ValueError, match="host_admission_contended") as refused,
        host_admission.admitted_host_work(
            tmp_path,
            "proof",
            operation="proof.host",
            seconds=12,
            clock=lambda: clock.now,
            sleep=clock.sleep,
        ),
    ):
        pytest.fail("a contended run was admitted")

    recorded = json.loads((queue.directory / f"{holder.name}.json").read_text(encoding="utf-8"))
    assert str(refused.value) == (
        f"host_admission_contended:host.run:{held_pid(holder.name)}:{recorded['since']}"
    )
    assert recorded["executable"] == "renderer"
    assert str(tmp_path / "busy-repository") not in str(refused.value)
    assert sum(clock.sleeps) == 12
    assert [path.stem for path in queue.directory.glob("*.json")] == [holder.name]
    queue.leave(holder)


# How a contended wait ends: the exit it raises, that exit's message and its cause.
_ENDINGS = [
    ("bound", ValueError, "^host_admission_contended", type(None)),
    ("os_error", ValueError, "^host_admission_unavailable$", BrokenPipeError),
    ("interrupt", KeyboardInterrupt, "^$", type(None)),
]


def _admission(repository: Path, ending: str) -> None:
    """Ask for one admission; behind a holder, its wait ends the way `ending` names."""
    clock = FakeClock()

    def report(_event: dict[str, object]) -> None:
        if ending == "os_error":
            raise BrokenPipeError

    def sleep(seconds: float) -> None:
        if ending == "interrupt":
            raise KeyboardInterrupt
        clock.sleep(seconds)

    with host_admission.admitted_host_work(
        repository,
        "proof",
        operation="proof.host",
        seconds=5,
        clock=lambda: clock.now,
        sleep=sleep,
        report=report,
    ):
        pass


@pytest.mark.parametrize(("ending", "raised", "message", "cause"), _ENDINGS)
def test_a_wait_that_ends_unadmitted_gives_up_its_place(
    host_root: Path,
    tmp_path: Path,
    ending: str,
    raised: type[BaseException],
    message: str,
    cause: type,
) -> None:
    """The bound, an OS error while waiting and an interrupt each leave no ticket of the run."""
    queue = _queue(host_root)
    holder = queue.enter(tmp_path / "busy", "renderer")

    # The test keeps the raised error, so only the admission itself can give the place up.
    with pytest.raises(raised, match=message) as ended:
        _admission(tmp_path, ending)

    assert ended.type is raised
    assert isinstance(ended.value.__cause__, cause)
    assert [entry["executable"] for entry in queue.entries(reader=tmp_path)] == ["renderer"]
    assert {path.stem for path in queue.directory.iterdir()} == {holder.name}
    queue.leave(holder)
    with host_admission.admitted_host_work(
        tmp_path, "later", operation="host.run", seconds=0
    ) as later:
        assert not later.joined
    assert not any(queue.directory.iterdir())


@pytest.mark.parametrize(
    ("ending", "raised", "message", "cause"),
    [*_ENDINGS, ("admitted", ValueError, "^host_admission_unavailable$", PermissionError)],
)
def test_a_place_that_cannot_be_given_up_never_replaces_the_exit_in_flight(
    host_root: Path,
    tmp_path: Path,
    ending: str,
    raised: type[BaseException],
    message: str,
    cause: type,
) -> None:
    """An OS error while leaving keeps the wait's own ending; after a normal end it is the gap.

    The exit that stays in flight carries a note of the place that was not given up, and the run
    asks once to leave, for its own ticket.
    """
    queue = _queue(host_root)
    busy = [] if ending == "admitted" else [queue.enter(tmp_path / "busy", "renderer")]
    refused = Mock(side_effect=PermissionError)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(host_admission.HostQueue, "leave", refused)
        with pytest.raises(raised) as ended:
            _admission(tmp_path, ending)

    # The message alone is the gap that a caller reads; pytest's own match would read the note too.
    assert ended.type is raised
    assert re.search(message, str(ended.value)) is not None
    assert isinstance(ended.value.__cause__, cause)
    kept = [] if ending == "admitted" else ["host_admission_unavailable: PermissionError"]
    assert getattr(ended.value, "__notes__", []) == kept
    # The mock kept the run's own ticket; the real release then empties the queue.
    for holder in (*busy, *(call.args[0] for call in refused.call_args_list)):
        queue.leave(holder)
    assert refused.call_count == 1
    assert not any(queue.directory.iterdir())


def test_a_bound_that_is_no_number_leaves_the_ceilings_remainder() -> None:
    """Held or not, a bound of no number ends its wait at the ceiling, as a total does."""
    bound = host_admission.AdmissionBound(lambda: 0.0)
    ceiling = load_repository_paradigm().parameter_row("timeout", "admission_seconds").bound
    assert [bound.remaining(math.nan, held=held) for held in (False, True)] == [ceiling] * 2


def test_a_ticket_whose_record_cannot_be_removed_still_frees_its_place(
    host_root: Path, tmp_path: Path
) -> None:
    """A held lock is a live ticket, so the lock goes also when the record stays."""
    queue = _queue(host_root)
    ticket = queue.enter(tmp_path / "busy", "renderer")
    unlink = os.unlink

    def kept(path: object, *arguments: object, **options: object) -> None:
        if str(path).endswith(".json"):
            raise PermissionError
        unlink(path, *arguments, **options)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "unlink", kept)
        with pytest.raises(PermissionError):
            queue.leave(ticket)

    # The next reader finds a free lock and removes what the holder left.
    assert queue.live() == []
    assert not any(queue.directory.iterdir())


@pytest.mark.parametrize("total", [None, 40_000.0, math.nan])
def test_every_wait_ends_at_the_declared_ceiling(
    host_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, total: float | None
) -> None:
    """No total, one above the ceiling and one that is no number all end at the ceiling."""
    monkeypatch.setattr(host_admission, "_POLL_SECONDS", 600.0)
    ceiling = load_repository_paradigm().parameter_row("timeout", "admission_seconds").bound
    queue = _queue(host_root)
    holder = queue.enter(tmp_path, "renderer", operation="host.run")
    clock = FakeClock()

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        assert clock.now <= ceiling, "the wait outlasted the ceiling"

    with (
        pytest.raises(ValueError, match=r"^host_admission_contended:host\.run:"),
        host_admission.admitted_host_work(
            tmp_path,
            "proof",
            operation="proof.host",
            seconds=total,
            clock=lambda: clock.now,
            sleep=sleep,
        ),
    ):
        pytest.fail("a contended run was admitted")

    assert (ceiling, clock.now) == (36_000, 36_000.0)
    queue.leave(holder)


def test_a_record_names_its_operation_and_owner_and_keeps_the_three_old_fields(
    host_root: Path, tmp_path: Path
) -> None:
    """A new record adds the operation and the owner; readers that predate them still read it."""
    queue = _queue(host_root)

    ticket = queue.enter(tmp_path, "ethos", operation="proof.run", owner="agent:test:proof")
    queue.leave(ticket)
    older = queue.enter(tmp_path, "renderer")

    record = queue.directory / f"{older.name}.json"
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert set(recorded) >= {"repository", "executable", "since"}
    assert (recorded["operation"], recorded["owner"]) == ("", "")
    # An older engine wrote the three fields only; its ticket still projects, with both empty.
    three = {key: recorded[key] for key in ("repository", "executable", "since")}
    record.write_text(json.dumps(three), encoding="utf-8")
    projected = queue.project(older, reader=tmp_path)
    assert projected is not None
    assert (projected["operation"], projected["owner"]) == ("", "")
    assert projected["executable"] == "renderer"
    queue.leave(older)


def test_the_entries_read_lists_holders_and_waiters_without_removing(
    host_root: Path, tmp_path: Path
) -> None:
    """A holder and a waiter are listed; a dead ticket is left for the next waiter, not removed."""
    queue = _queue(host_root)
    busy = init_git_repo(tmp_path / "busy")
    holder = queue.enter(busy, "renderer", operation="host.run", owner="agent:test:h")
    script = (
        "import sys; from pathlib import Path\n"
        "import ethos.adapters.gates.host_admission as h\n"
        "h.HostQueue(Path(sys.argv[1]), 1).enter(Path(sys.argv[2]), 'gone')\n"
    )
    subprocess.run(
        [sys.executable, "-c", script, str(queue.directory), str(tmp_path / "dead")],
        check=True,
        capture_output=True,
        text=True,
        env=os.environ,
    )
    waiter = queue.enter(tmp_path / "next", "proof")

    entries = queue.entries(reader=busy)

    assert [(entry["state"], entry["executable"]) for entry in entries] == [
        ("holding", "renderer"),
        ("waiting", "proof"),
    ]
    assert set(entries[0]) == {
        "state",
        "operation",
        "executable",
        "owner",
        "pid",
        "since",
        "same_repository",
        "holder",
    }
    assert (entries[0]["operation"], entries[0]["owner"]) == ("host.run", "agent:test:h")
    assert entries[0]["pid"] == held_pid(holder.name)
    assert entries[0]["same_repository"] is True
    foreign = queue.entries(reader=init_git_repo(tmp_path / "elsewhere"))
    assert (foreign[0]["owner"], foreign[0]["same_repository"]) == ("", False)
    assert foreign[0]["operation"] == "host.run"
    # The path as JSON writes it: there a Windows path's backslashes are doubled.
    assert json.dumps(str(tmp_path))[1:-1] not in json.dumps(entries) + json.dumps(foreign)
    assert len(list(queue.directory.glob("*.json"))) == 3
    queue.leave(holder)
    queue.leave(waiter)


def test_an_unwritable_queue_directory_answers_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host root that cannot be written is a named gap, not a traceback."""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "host-admission").write_text("a file where the queue belongs", encoding="utf-8")
    monkeypatch.setattr(host_admission, "host_store_root", lambda: blocked)

    with (
        pytest.raises(ValueError, match=r"^host_admission_unavailable$"),
        host_admission.admitted_host_work(
            tmp_path, "proof", operation="proof.host", seconds=0, clock=lambda: 0.0
        ),
    ):
        pytest.fail("an unwritable queue admitted work")


def test_admitted_work_carries_one_token_and_worker_cap(
    host_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Work under a live admission joins it; a copied token whose holder left admits nothing."""
    # A suite that runs under a host ticket inherits that ticket's worker count.
    monkeypatch.delenv(host_admission.XDIST_WORKERS, raising=False)
    # The host's own CPU count is not the subject: one CPU would refuse the declaration.
    monkeypatch.setattr(host_admission.os, "cpu_count", lambda: 8)
    _declare(host_root, "reserved_cpus = 1\n")

    with host_admission.admitted_host_work(
        tmp_path, "outer", operation="host.run", seconds=0
    ) as outer:
        cap = str(max(1, (os.cpu_count() or 1) - 1))
        assert outer.environment[host_admission.CPU_CAP] == cap
        assert outer.environment[host_admission.XDIST_WORKERS] == cap
        assert outer.environment[host_admission.ADMISSION_ENV]
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(
                host_admission.ADMISSION_ENV, outer.environment[host_admission.ADMISSION_ENV]
            )
            patch.setenv(host_admission.XDIST_WORKERS, str(int(cap) + 5))
            with host_admission.admitted_host_work(
                tmp_path, "inner", operation="host.run", seconds=0
            ) as inner:
                assert inner.joined
                assert (
                    inner.environment[host_admission.ADMISSION_ENV]
                    == (outer.environment[host_admission.ADMISSION_ENV])
                )
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(host_admission.ADMISSION_ENV, outer.environment[host_admission.ADMISSION_ENV])
        patch.delenv(host_admission.XDIST_WORKERS, raising=False)
        with host_admission.admitted_host_work(
            tmp_path, "later", operation="host.run", seconds=0
        ) as later:
            assert (
                later.environment[host_admission.ADMISSION_ENV]
                != (outer.environment[host_admission.ADMISSION_ENV])
            )


@pytest.mark.parametrize(("caller", "expected"), [("3", "3"), ("99", None), ("two", None)])
def test_a_caller_that_declares_fewer_workers_keeps_its_count(
    host_root: Path, tmp_path: Path, caller: str, expected: str | None
) -> None:
    """The cap only lowers: a smaller count stays; a larger or non-numeric one is ignored."""
    _declare(host_root, "reserved_cpus = 1\n")

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(host_admission.XDIST_WORKERS, caller)
        # A count of three is smaller only on a host with more than four CPUs.
        patch.setattr(host_admission.os, "cpu_count", lambda: 8)
        with host_admission.admitted_host_work(
            tmp_path, "outer", operation="host.run", seconds=0
        ) as outer:
            cap = str(max(1, (os.cpu_count() or 1) - 1))
            assert outer.environment[host_admission.XDIST_WORKERS] == (expected or cap)
            assert outer.environment[host_admission.CPU_CAP] == cap


def test_a_waiting_run_reports_one_event_with_the_holder_projection(
    host_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A waiter writes one `host_admission_waiting` event whose holder carries no repository."""
    queue = _queue(host_root)
    busy = init_git_repo(tmp_path / "busy")
    holder = queue.enter(busy, "renderer", operation="host.run", owner="agent:test:h")
    clock = FakeClock()

    with (
        pytest.raises(ValueError, match="host_admission_contended"),
        host_admission.admitted_host_work(
            busy,
            "proof",
            operation="proof.host",
            seconds=5,
            clock=lambda: clock.now,
            sleep=clock.sleep,
        ),
    ):
        pass

    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    waiting = [event for event in events if event["event"] == "host_admission_waiting"]
    assert len(waiting) == 1
    assert waiting[0]["operation"] == "proof.host"
    assert waiting[0]["holder"] == {
        "operation": "host.run",
        "executable": "renderer",
        "owner": "agent:test:h",
        "pid": held_pid(holder.name),
        "since": json.loads((queue.directory / f"{holder.name}.json").read_text(encoding="utf-8"))[
            "since"
        ],
        "same_repository": True,
        # Whether a holder's process still runs is asked on POSIX alone.
        "holder": "present" if os.name == "posix" else "",
    }
    assert json.dumps(str(busy))[1:-1] not in json.dumps(waiting[0])
    queue.leave(holder)


def test_the_host_declaration_owns_the_load_limit(host_root: Path) -> None:
    """A declared positive limit is kept as declared; without one, none is declared."""
    assert host_admission.read_host_declaration(host_root, cpus=8).load_limit is None
    _declare(host_root, "load_limit = 14.5\n")

    assert host_admission.read_host_declaration(host_root, cpus=8).load_limit == pytest.approx(14.5)

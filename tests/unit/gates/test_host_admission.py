"""Heavy local work is admitted host-wide, in arrival order, by tickets whose holders live."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.host_admission as host_admission

if TYPE_CHECKING:
    from pathlib import Path


class _Clock:
    """A fake clock whose sleeps advance it by their own duration."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


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
        ("slots = 2\nreserved_cpus = 6\n", (2, 6, 2)),
        ("reserved_cpus = 7\n", (1, 7, 1)),
    ],
)
def test_the_host_declaration_bounds_slots_and_workers(
    host_root: Path, text: str | None, expected: tuple[int, int, int]
) -> None:
    """One slot and no reserved CPUs by default; the worker cap is the CPUs left, at least one."""
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


def test_heavy_runs_are_admitted_in_arrival_order(host_root: Path, tmp_path: Path) -> None:
    """With one slot the later run waits for the earlier, and a third follows both."""
    queue = _queue(host_root)
    first, second, third = (queue.enter(tmp_path, name) for name in ("one", "two", "three"))

    assert [queue.admitted(ticket) for ticket, _lock in (first, second, third)] == [
        True,
        False,
        False,
    ]
    queue.leave(*first)
    assert [queue.admitted(ticket) for ticket, _lock in (second, third)] == [True, False]
    queue.leave(*second)
    assert queue.admitted(third[0])
    queue.leave(*third)
    assert not any(queue.directory.iterdir())


def test_two_declared_slots_admit_two_runs(host_root: Path, tmp_path: Path) -> None:
    """A host that declares two slots runs two heavy runs at once and queues the third."""
    queue = _queue(host_root, slots=2)
    tickets = [queue.enter(tmp_path, str(index)) for index in range(3)]

    assert [queue.admitted(ticket) for ticket, _lock in tickets] == [True, True, False]


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

    assert queue.admitted(waiter[0])
    assert [path.stem for path in queue.directory.glob("*.json")] == [waiter[0].name]


def test_a_bounded_wait_names_the_holder(host_root: Path, tmp_path: Path) -> None:
    """A run that waits for the whole bound ends without running and names who holds the host."""
    queue = _queue(host_root)
    holder = queue.enter(tmp_path / "busy-repository", "renderer")
    clock = _Clock()

    with (
        pytest.raises(ValueError, match="host_admission_contended") as refused,
        host_admission.admitted_host_work(
            tmp_path, "proof", seconds=12, clock=lambda: clock.now, sleep=clock.sleep
        ),
    ):
        pytest.fail("a contended run was admitted")

    recorded = json.loads((queue.directory / f"{holder[0].name}.json").read_text(encoding="utf-8"))
    assert str(refused.value) == (
        f"host_admission_contended:{recorded['executable']}:{recorded['repository']}"
        f":{recorded['since']}"
    )
    assert recorded["executable"] == "renderer"
    assert sum(clock.sleeps) == 12
    assert [path.stem for path in queue.directory.glob("*.json")] == [holder[0].name]


def test_admitted_work_carries_one_token_and_worker_cap(host_root: Path, tmp_path: Path) -> None:
    """Work under a live admission joins it; a copied token whose holder left admits nothing."""
    _declare(host_root, "reserved_cpus = 1\n")

    with host_admission.admitted_host_work(tmp_path, "outer", seconds=0) as outer:
        cap = str(max(1, (os.cpu_count() or 1) - 1))
        assert outer[host_admission.CPU_CAP] == outer[host_admission.XDIST_WORKERS] == cap
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv(host_admission.ADMISSION_ENV, outer[host_admission.ADMISSION_ENV])
            with host_admission.admitted_host_work(tmp_path, "inner", seconds=0) as inner:
                assert inner[host_admission.ADMISSION_ENV] == outer[host_admission.ADMISSION_ENV]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(host_admission.ADMISSION_ENV, outer[host_admission.ADMISSION_ENV])
        with host_admission.admitted_host_work(tmp_path, "later", seconds=0) as later:
            assert later[host_admission.ADMISSION_ENV] != outer[host_admission.ADMISSION_ENV]


def test_the_host_declaration_owns_the_load_limit(host_root: Path) -> None:
    """A declared positive limit is kept as declared; without one, none is declared."""
    assert host_admission.read_host_declaration(host_root, cpus=8).load_limit is None
    _declare(host_root, "load_limit = 14.5\n")

    assert host_admission.read_host_declaration(host_root, cpus=8).load_limit == pytest.approx(14.5)

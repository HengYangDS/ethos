"""`ethos host run` admits one heavy command host-wide and returns its exit status unchanged."""

from __future__ import annotations

import json
import os
import sys
from functools import partial
from pathlib import Path

import pytest

import ethos.adapters.gates.host_admission as host_admission
import ethos.adapters.gates.host_work as host_work
from tests.support.clock import ReleasingClock
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw

_CHILD = """
import json, os, sys
from pathlib import Path
queue = Path(os.environ["XDG_DATA_HOME"]) / "ethos/host-admission/v1"
records = [json.loads(path.read_text()) for path in queue.glob("*.json")]
print(json.dumps({"cap": os.environ["ETHOS_HOST_CPU_CAP"], "records": records}))
sys.exit(7)
"""

_STATUS = """
import json, subprocess, sys
completed = subprocess.run(
    [sys.executable, "-m", "ethos.cli", "host", "status", *sys.argv[1:], "--json"],
    capture_output=True,
    text=True,
)
print(json.dumps({"returncode": completed.returncode, "payload": json.loads(completed.stdout)}))
"""

_EXCEEDED = "host_reservation_exceeded"
# The reference case: three guests of 4, 8 and 8 virtual CPUs on a host of 18.
_RESIZE = "resize the guests to 17 virtual CPUs or fewer in total: no reserved_cpus on 18 holds 20"
_NON_NEGATIVE = "pass the guests' count as a non-negative number"


def test_an_admitted_command_keeps_its_exit_status_and_records_no_arguments(tmp_path: Path) -> None:
    """The child runs with the worker cap; its ticket names the executable, never its arguments."""
    completed = run_ethos_raw(
        "host", "run", "--", sys.executable, "-c", _CHILD, "secret-argument", cwd=tmp_path
    )

    assert completed.returncode == 7
    seen = json.loads(completed.stdout.strip().splitlines()[-1])
    (record,) = seen["records"]
    assert set(record) == {"repository", "executable", "since", "operation", "owner"}
    assert (record["operation"], record["owner"]) == (
        "host.run",
        "agent:test:case:agent-test",
    )
    assert "secret-argument" not in json.dumps(record)
    assert int(seen["cap"]) >= 1


def test_work_under_a_live_admission_joins_it(tmp_path: Path) -> None:
    """A nested heavy command joins its parent's admission instead of waiting for itself."""
    nested = (
        "import subprocess, sys\n"
        "sys.exit(subprocess.run([sys.executable, '-m', 'ethos.cli', 'host', 'run', '--wait', '0',"
        " '--', sys.executable, '-c', 'pass']).returncode)\n"
    )

    completed = run_ethos_raw("host", "run", "--", sys.executable, "-c", nested, cwd=tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    ("wait", "returncode", "ended"),
    [
        ((), 0, 6400.0),  # no total of its own: a holder of 6,400 s ends no wait
        (("--wait", "12"), 1, 12.0),  # the caller's own total ends its wait behind a live holder
        (("--wait", "0"), 1, 0.0),  # a total of zero asks once
        (("--wait", "-1"), 1, 0.0),  # and so does one below zero, as it did before
    ],
)
def test_a_run_keeps_its_place_behind_a_live_holder_up_to_its_own_total(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wait: tuple[str, ...],
    returncode: int,
    ended: float,
) -> None:
    """Only the caller's own total ends a wait behind a holder whose lock shows that it lives."""
    queue = host_admission.host_queue()[0]
    held = queue.enter(tmp_path, "renderer", operation="host.run")
    clock = ReleasingClock(6400, lambda: queue.leave(*held))
    timed = partial(host_admission.admitted_host_work, clock=lambda: clock.now, sleep=clock.sleep)
    monkeypatch.setattr(host_admission, "admitted_host_work", timed)
    monkeypatch.setattr(host_admission, "_POLL_SECONDS", 400.0)

    argv = ("host", "run", *wait, "--json", "--", sys.executable, "-c", "pass")
    completed = run_ethos_raw(*argv, cwd=tmp_path)

    assert (completed.returncode, clock.now) == (returncode, ended), completed.stdout
    if returncode:
        (gap,) = json.loads(completed.stdout)["required_gaps"]
        assert gap.startswith("host_admission_contended:host.run:")
        queue.leave(*held)


def test_a_missing_command_is_refused(tmp_path: Path) -> None:
    """`ethos host run` without a command names the missing command."""
    payload = run_ethos_blocked("host", "run", "--json", cwd=tmp_path)

    assert (payload["command"], payload["required_gaps"]) == (
        "host run",
        ["host_run_command_missing"],
    )


@pytest.mark.parametrize(
    ("argv", "next_action"),
    [
        (("run", "--json", "--", "true"), "repair this host's root, or declare more host slots"),
        (("status", "--json"), "repair this host's root or its host.toml declaration"),
    ],
)
def test_an_invalid_declaration_refuses_the_run_and_the_read(
    tmp_path: Path, argv: tuple[str, ...], next_action: str
) -> None:
    """Neither the run nor the read guesses past a declaration that names an unknown key."""
    root = Path(os.environ["XDG_DATA_HOME"]) / "ethos"
    root.mkdir(parents=True, exist_ok=True)
    (root / "host.toml").write_text("slot = 2\n", encoding="utf-8")

    payload = json.loads(run_ethos_raw("host", *argv, cwd=tmp_path).stdout)

    assert payload["required_gaps"] == ["host_declaration_invalid:slot"]
    assert payload["next_action"] == next_action


def test_an_admitted_command_exits_with_its_status_and_prints_no_frame(tmp_path: Path) -> None:
    """The `process` exit replaces the result frame even under `--json`."""
    argv = ("host", "run", "--json", "--", sys.executable, "-c", "pass")
    completed = run_ethos_raw(*argv, cwd=tmp_path)
    assert (completed.returncode, completed.stdout) == (0, "")


def test_host_status_lists_the_holding_run_with_its_operation(tmp_path: Path) -> None:
    """A child of `host run` reads the queue and sees its parent holding it, with no path."""
    completed = run_ethos_raw("host", "run", "--", sys.executable, "-c", _STATUS, cwd=tmp_path)

    assert completed.returncode == 0, completed.stderr
    seen = json.loads(completed.stdout.strip().splitlines()[-1])
    assert seen["returncode"] == 0, seen
    payload = seen["payload"]
    (entry,) = payload["data"]["queue"]
    assert (entry["state"], entry["operation"]) == ("holding", "host.run")
    assert entry["same_repository"] is False
    assert "repository" not in entry
    assert str(tmp_path) not in json.dumps(payload)
    assert (payload["verdict"], payload["state"]) == ("pass", "observed")


@pytest.mark.parametrize(
    ("guest_cpus", "verdict", "gaps", "fits", "next_action"),
    [
        ("4", "pass", [], True, ""),
        ("12", "block", [_EXCEEDED], False, "raise reserved_cpus in host.toml to 12"),
        ("20", "block", [_EXCEEDED], False, _RESIZE),
        ("-1", "block", ["host_reservation_invalid"], None, _NON_NEGATIVE),
    ],
)
def test_the_guests_cpus_are_checked_against_the_reserved_cpus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    guest_cpus: str,
    verdict: str,
    gaps: list[str],
    *,
    fits: bool | None,
    next_action: str,
) -> None:
    """The repair is a value the declaration takes; guests no value holds are named themselves."""
    monkeypatch.setattr(host_admission.os, "cpu_count", lambda: 18)
    data_home = tmp_path / "user-data"
    (data_home / "ethos").mkdir(parents=True)
    (data_home / "ethos/host.toml").write_text("reserved_cpus = 4\n", encoding="utf-8")

    completed = run_ethos_raw("host", "status", "--guest-cpus", guest_cpus, "--json", cwd=tmp_path)

    payload = json.loads(completed.stdout)
    # A read exits 0 on every verdict; the gap names what does not fit.
    assert completed.returncode == 0
    assert (payload["verdict"], payload["required_gaps"]) == (verdict, gaps)
    assert payload["next_action"] == next_action
    reservation = payload["data"].get("reservation")
    if fits is None:
        assert reservation is None
    else:
        assert reservation == {
            "guest_cpus": int(guest_cpus),
            "reserved_cpus": 4,
            "reservable_cpus": 17,
            "fits": fits,
        }


def test_the_declaration_bounds_the_reads_worker_cap(tmp_path: Path) -> None:
    """The read reports the declaration's worker cap, and no reservation without a count."""
    payload = run_ethos("host", "status", "--json", cwd=tmp_path)

    declaration = payload["data"]["declaration"]
    assert set(declaration) >= {"slots", "reserved_cpus", "load_limit", "limit_source"}
    assert declaration["slots"] == 1
    assert declaration["worker_cap"] >= 1
    assert payload["data"]["queue"] == []
    assert "reservation" not in payload["data"]


def test_two_slots_share_the_cpus_that_the_reservation_leaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read and a child of one of two slots see one share: half of the CPUs left."""
    monkeypatch.setattr(host_admission.os, "cpu_count", lambda: 8)
    monkeypatch.delenv(host_admission.XDIST_WORKERS, raising=False)
    root = Path(os.environ["XDG_DATA_HOME"]) / "ethos"
    root.mkdir(parents=True, exist_ok=True)
    (root / "host.toml").write_text("slots = 2\nreserved_cpus = 2\n", encoding="utf-8")

    payload = run_ethos("host", "status", "--json", cwd=tmp_path)
    with host_admission.admitted_host_work(tmp_path, "one", operation="x", seconds=0) as work:
        child = work.environment

    assert payload["data"]["declaration"]["worker_cap"] == 3
    assert (child[host_admission.CPU_CAP], child[host_admission.XDIST_WORKERS]) == ("3", "3")


_ACTOR = "agent:test:case:agent-test"
_RENDER = f"{host_work.WORK_HOME}/render"
_MARK = f"{_RENDER}/{host_work.MARK}"
_FOREIGN = '{"owner": "agent:test:other"}'
_WORK = ("host", "run", "--work", "render", "--", sys.executable, "-c")
# The step that each refusal names; every case that raises its code can follow it.
_STEPS = {
    "host_work_invalid": (
        "name one lowercase directory of build/runtime/work, as in `--work render`"
    ),
    "host_work_owned": (
        "name another work directory, or set ETHOS_ACTOR to your own identity when the mark "
        "names it; a mark that names no owner is never taken over"
    ),
    "host_work_unavailable": (
        "make build/runtime/work/<name> a directory in which this run can create a file and "
        "hard-link it, or run without --work"
    ),
}


def test_a_run_marks_its_work_directory_with_its_owner_once(tmp_path: Path) -> None:
    """The child finds its work directory marked; a later run of the same owner keeps the mark."""
    child = f"print(open({_MARK!r}).read())"

    first = run_ethos_raw(*_WORK, child, cwd=tmp_path)
    assert first.returncode == 0, first.stdout + first.stderr
    seen = json.loads(first.stdout.strip().splitlines()[-1])
    earlier = seen | {"since": "2026-01-01T00:00:00+00:00"}
    (tmp_path / _MARK).write_text(json.dumps(earlier), encoding="utf-8")
    second = run_ethos_raw(*_WORK, child, cwd=tmp_path)

    assert set(seen) == {"owner", "operation", "since"}
    assert (seen["owner"], seen["operation"]) == (_ACTOR, "host.run")
    assert json.loads(second.stdout.strip().splitlines()[-1]) == earlier
    directory = tmp_path / host_work.WORK_HOME / "render"
    assert host_work.work_owner(directory) == _ACTOR
    assert [path.name for path in directory.iterdir()] == [host_work.MARK]


@pytest.mark.parametrize(
    ("work", "files", "actor", "gap"),
    [
        ("render", {_MARK: _FOREIGN}, _ACTOR, "host_work_owned:render"),
        ("render", {_MARK: "not a mark"}, _ACTOR, "host_work_owned:render"),
        ("render", {_MARK: _FOREIGN}, "", "host_work_owned:render"),
        ("render", {"build": "a file, not a tree"}, _ACTOR, "host_work_unavailable"),
        ("render", {_RENDER: "a file, not a directory"}, _ACTOR, "host_work_unavailable"),
        ("../render", {}, _ACTOR, "host_work_invalid"),
        ("render/frames", {}, _ACTOR, "host_work_invalid"),
        ("Render", {}, _ACTOR, "host_work_invalid"),
    ],
)
def test_a_work_directory_that_is_not_the_runs_refuses_it_before_the_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    work: str,
    files: dict[str, str],
    actor: str,
    gap: str,
) -> None:
    """Another owner's mark, an unreadable one, a path or an unwritable tree runs nothing."""
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    witness = tmp_path / "ran"
    child = (sys.executable, "-c", f"open({str(witness)!r}, 'w')")

    refused = run_ethos_raw("host", "run", "--work", work, "--json", "--", *child, cwd=tmp_path)

    payload = json.loads(refused.stdout)
    assert (refused.returncode, payload["required_gaps"]) == (1, [gap])
    assert payload["next_action"] == _STEPS[gap.partition(":")[0]]
    assert not witness.exists()
    assert (tmp_path / "build").exists() == bool(files)
    assert {name: (tmp_path / name).read_text(encoding="utf-8") for name in files} == files
    assert not list((Path(os.environ["XDG_DATA_HOME"]) / "ethos").glob("host-admission/v1/*"))


def test_of_two_owners_that_arrive_together_one_holds_the_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mark is linked exclusively: the later link loses, and its owner is refused."""
    link = os.link

    def late(source: Path, target: Path) -> None:
        target.write_text(_FOREIGN, encoding="utf-8")
        link(source, target)

    monkeypatch.setattr(host_work.os, "link", late)
    directory = tmp_path / host_work.WORK_HOME / "render"

    with pytest.raises(ValueError, match=r"^host_work_owned:render$"):
        host_work.claim_work_directory(tmp_path, "render", owner=_ACTOR, operation="host.run")

    assert [path.name for path in directory.iterdir()] == [host_work.MARK]
    assert host_work.work_owner(directory) == "agent:test:other"


def test_a_run_without_an_actor_marks_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An undeclared owner leaves the directory's owner unknown, and a declared one takes it."""
    monkeypatch.setenv("ETHOS_ACTOR", "")
    directory = tmp_path / host_work.WORK_HOME / "render"

    unmarked = run_ethos_raw(*_WORK, "pass", cwd=tmp_path)

    assert unmarked.returncode == 0, unmarked.stdout + unmarked.stderr
    assert (list(directory.iterdir()), host_work.work_owner(directory)) == ([], "")
    assert host_work.claim_work_directory(tmp_path, "render", owner=_ACTOR, operation="x")
    assert host_work.work_owner(directory) == _ACTOR


@pytest.mark.parametrize(
    ("marker", "tokens"),
    [
        (("--",), ["--help", "-h", "--json", "--version", "--root", "x", "--actor", "x"]),
        # Without the marker the child still keeps a flag that this command does not declare.
        ((), ["--actor", "x", "--other"]),
    ],
)
def test_every_token_after_the_end_marker_reaches_the_command(
    tmp_path: Path, marker: tuple[str, ...], tokens: list[str]
) -> None:
    """ETHOS reads its own options before `--` only, and a child's `--actor` is never its own."""
    child = "import json, sys; print(json.dumps(sys.argv[1:]))"
    argv = ("host", "run", *marker, sys.executable, "-c", child, *tokens)
    completed = run_ethos_raw(*argv, cwd=tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == tokens

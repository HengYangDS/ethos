"""`ethos host run` admits one heavy command host-wide and returns its exit status unchanged."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

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
    declaration = payload["data"]["declaration"]
    assert declaration["slots"] == 1
    assert declaration["worker_cap"] >= 1
    assert (payload["verdict"], payload["state"]) == ("pass", "observed")


@pytest.mark.parametrize(
    ("guest_cpus", "verdict", "gaps", "fits"),
    [
        ("2", "pass", [], True),
        ("99", "block", ["host_reservation_exceeded"], False),
        ("-1", "block", ["host_reservation_invalid"], None),
    ],
)
def test_the_guests_cpus_are_checked_against_the_reserved_cpus(
    tmp_path: Path, guest_cpus: str, verdict: str, gaps: list[str], *, fits: bool | None
) -> None:
    """A count that fits passes; one above the reservation or below zero is a named gap."""
    data_home = tmp_path / "user-data"
    (data_home / "ethos").mkdir(parents=True)
    (data_home / "ethos/host.toml").write_text("reserved_cpus = 2\n", encoding="utf-8")

    completed = run_ethos_raw("host", "status", "--guest-cpus", guest_cpus, "--json", cwd=tmp_path)

    payload = json.loads(completed.stdout)
    # A read exits 0 on every verdict; the gap names what does not fit.
    assert completed.returncode == 0
    assert (payload["verdict"], payload["required_gaps"]) == (verdict, gaps)
    reservation = payload["data"].get("reservation")
    if fits is None:
        assert reservation is None
    else:
        assert reservation["guest_cpus"] == int(guest_cpus)
        assert reservation["reserved_cpus"] == 2
        assert reservation["fits"] is fits


def test_the_declaration_bounds_the_reads_worker_cap(tmp_path: Path) -> None:
    """The read reports the declaration's worker cap, and no reservation without a count."""
    payload = run_ethos("host", "status", "--json", cwd=tmp_path)

    declaration = payload["data"]["declaration"]
    assert set(declaration) >= {"slots", "reserved_cpus", "load_limit", "limit_source"}
    assert declaration["slots"] == 1
    assert declaration["worker_cap"] >= 1
    assert payload["data"]["queue"] == []
    assert "reservation" not in payload["data"]


def test_every_token_after_the_end_marker_reaches_the_command(tmp_path: Path) -> None:
    """ETHOS reads its own options before `--` only; the command receives the rest unchanged."""
    tokens = ["--help", "-h", "--json", "--version", "--root", "elsewhere"]
    child = "import json, sys; print(json.dumps(sys.argv[1:]))"
    argv = ("host", "run", "--", sys.executable, "-c", child, *tokens)
    completed = run_ethos_raw(*argv, cwd=tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == tokens

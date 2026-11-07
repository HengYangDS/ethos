"""`ethos host run` admits one heavy command host-wide and returns its exit status unchanged."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path

_CHILD = """
import json, os, sys
from pathlib import Path
queue = Path(os.environ["XDG_DATA_HOME"]) / "ethos/host-admission/v1"
records = [json.loads(path.read_text()) for path in queue.glob("*.json")]
print(json.dumps({"cap": os.environ["ETHOS_HOST_CPU_CAP"], "records": records}))
sys.exit(7)
"""


def test_an_admitted_command_keeps_its_exit_status_and_records_no_arguments(tmp_path: Path) -> None:
    """The child runs with the worker cap; its ticket names the executable, never its arguments."""
    completed = run_ethos_raw(
        "host", "run", "--", sys.executable, "-c", _CHILD, "secret-argument", cwd=tmp_path
    )

    assert completed.returncode == 7
    seen = json.loads(completed.stdout.strip().splitlines()[-1])
    (record,) = seen["records"]
    assert set(record) == {"repository", "executable", "since"}
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

    assert payload["required_gaps"] == ["host_run_command_missing"]

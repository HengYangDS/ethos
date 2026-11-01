"""ETHOS's native pytest and coverage configuration keeps the suite's obligations."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from coverage.results import should_fail_under

from ethos.adapters.process import run_command

if TYPE_CHECKING:
    import subprocess

ROOT = Path(__file__).resolve().parents[2]
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.toml"
_QUEUE = """\
import os, time
from pathlib import Path
import pytest

@pytest.mark.parametrize("index", range(80))
def test_worker_loss(index):
    with (Path(__file__).parent / f"case-{{index}}").open("a") as stream:
        stream.write("after\\n" if Path(__file__).with_name("failed").exists() else "before\\n")
    if index == 0 and {failure!r} == 'crash':
        os._exit(86)
    assert index != 0 or {failure!r} != 'assertion'
    time.sleep(0.05)
"""


def _run_native_pytest(
    tmp_path: Path, case: Path, *, workers: int = 0
) -> subprocess.CompletedProcess[str]:
    """Run isolated cases under ETHOS's own pytest carrier."""
    return run_command(
        tmp_path,
        (
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(PYTEST_CONFIG),
            f"--rootdir={tmp_path}",
            f"--basetemp={tmp_path / 'owned-temp'}",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            f"--numprocesses={workers}",
            "-q",
            str(case),
        ),
        timeout=60,
        remove_env=(
            "PYTEST_ADDOPTS",
            "PYTEST_XDIST_WORKER",
            "PYTEST_XDIST_AUTO_NUM_WORKERS",
            "PYTHONPATH",
        ),
    )


def test_the_coverage_floor_rejects_below_95_percent_at_its_precision() -> None:
    """Coverage's own comparison rejects 94.99 and accepts 95.00 under the declared floor."""
    carrier = (ROOT / ".config/checks/coverage/coverage.toml").read_text(encoding="utf-8")
    report = tomllib.loads(carrier)["tool"]["coverage"]["report"]

    assert report["fail_under"] >= 95
    assert should_fail_under(94.99, report["fail_under"], report["precision"])
    assert not should_fail_under(95.00, report["fail_under"], report["precision"])


@pytest.mark.parametrize("failure", ["none", "cached", "crash", "assertion"])
def test_a_failed_parallel_run_stops_without_replay(tmp_path: Path, failure: str) -> None:
    """Workers stop at the first failure, never replay a lost case, and run failures first."""
    assert (
        "timeout_method" not in tomllib.loads(PYTEST_CONFIG.read_text(encoding="utf-8"))["pytest"]
    )
    if failure == "cached":
        (tmp_path / "cache/v/cache").mkdir(parents=True)
        (tmp_path / "cache/v/cache/lastfailed").write_text(
            '{"test_queue.py::test_worker_loss[79]": true}', encoding="utf-8"
        )
    (tmp_path / "conftest.py").write_text(
        "from pathlib import Path\ndef pytest_testnodedown(node, error):\n"
        "    if error: Path(__file__).with_name('failed').touch()\n"
        "def pytest_runtest_logreport(report):\n"
        "    if report.failed: Path(__file__).with_name('failed').touch()\n",
        encoding="utf-8",
    )
    test = tmp_path / "test_queue.py"
    test.write_text(_QUEUE.format(failure=failure), encoding="utf-8")

    result = _run_native_pytest(tmp_path, test, workers=2)

    failed = failure not in {"none", "cached"}
    assert (result.returncode != 0) is failed, result.stdout + result.stderr
    observations = [path.read_text().strip() for path in tmp_path.glob("case-*")]
    assert set(observations) <= {"before", "after"}
    assert (tmp_path / "case-0").read_text() == "before\n"
    assert observations.count("after") <= 3 if failed else len(observations) == 80, observations
    if failure == "cached":
        assert (tmp_path / "case-79").stat().st_mtime_ns < (tmp_path / "case-40").stat().st_mtime_ns
    if failure == "crash":
        for fragment in ("worker 'gw", "crashed while running", "::test_worker_loss[0]"):
            assert fragment in result.stdout + result.stderr


def test_native_tmp_path_policy_reclaims_passed_case_before_next_case(tmp_path: Path) -> None:
    """The pytest policy bounds scratch during the run, not only at session exit."""
    marker = tmp_path / "first-path.txt"
    case = tmp_path / "test_retention.py"
    case.write_text(
        "from pathlib import Path\n"
        f"MARKER = Path({marker.as_posix()!r})\n\n"
        "def test_create(tmp_path):\n"
        "    (tmp_path / 'payload').write_bytes(b'owned')\n"
        "    MARKER.write_text(str(tmp_path))\n\n"
        "def test_verify():\n"
        "    assert not Path(MARKER.read_text()).exists()\n",
        encoding="utf-8",
    )
    result = _run_native_pytest(tmp_path, case)
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.is_file()


def test_native_failure_report_never_renders_frame_arguments(tmp_path: Path) -> None:
    """A failure report stays bounded however large the interrupted state is."""
    marker = tmp_path / "rendered.txt"
    case = tmp_path / "test_report.py"
    case.write_text(
        "from pathlib import Path\n\n"
        "class State:\n"
        "    def __repr__(self):\n"
        f"        Path({marker.as_posix()!r}).touch()\n"
        "        return 'State()'\n\n"
        "def observe(state):\n"
        "    raise RuntimeError('interrupted')\n\n"
        "def test_interrupted():\n"
        "    observe(State())\n",
        encoding="utf-8",
    )
    result = _run_native_pytest(tmp_path, case)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "RuntimeError: interrupted" in result.stdout
    assert not marker.exists()

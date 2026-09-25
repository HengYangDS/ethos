"""One Python test attempt supplies reconstructable human and Agent reports."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from unittest.mock import Mock

import pytest

import tools.ci.python_test_gate as owner
import tools.ci.sessions as sessions
from ethos.adapters.process import run_command

if TYPE_CHECKING:
    from pathlib import Path

    import nox


def _gate(
    tmp_path: Path, *, node_package_supply: Path, head: str = "a" * 40
) -> owner.PythonTestGate:
    """Bind a disposable result root without copying an ETHOS runtime."""
    return owner.PythonTestGate(
        owner.Settings(
            head=head,
            evidence=tmp_path / "evidence",
            basetemp=tmp_path / "pytest",
            basetemp_owned=True,
            workers=None,
            shards=None,
            durations=0,
            timeout=None,
            lock_wait=0,
            uv_cache=None,
            node_package_supply=node_package_supply,
        )
    )


def test_test_gate_replaces_stale_allure_results_in_the_same_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A previous attempt's test result must never join the current JUnit population."""
    gate = _gate(tmp_path, node_package_supply=tmp_path / "node_modules")
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner, "_head", lambda: gate.s.head)
    result_dir = gate.s.evidence / "allure/results/single"
    result_dir.mkdir(parents=True)
    stale = result_dir / "old-result.json"
    stale.write_text("{}", encoding="utf-8")
    observed: list[tuple[str, ...]] = []

    def run(*args: str, **_kwargs: object) -> None:
        observed.append(args)
        assert f"--alluredir={result_dir}" in args
        assert not stale.exists()
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "new-result.json").write_text("{}", encoding="utf-8")

    gate.run_tests(cast("nox.Session", SimpleNamespace(run=run)))

    assert len(observed) == 1
    assert (result_dir / "new-result.json").is_file()
    assert (gate.s.evidence / "allure/head.txt").read_text().strip() == gate.s.head
    assert not gate.s.basetemp.exists()


def test_report_reconstruction_refuses_missing_and_stale_source(tmp_path: Path) -> None:
    """An old or absent result set cannot produce a current-source report."""
    gate = _gate(tmp_path, node_package_supply=tmp_path / "node_modules")
    with pytest.raises(RuntimeError, match="allure_results_missing"):
        gate.render_report()
    marker = gate.s.evidence / "allure/head.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("b" * 40 + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="allure_source_stale"):
        gate.render_report()


def test_report_rebuilds_from_one_failed_pytest_attempt_without_rerun(tmp_path: Path) -> None:
    """JUnit failure remains adverse while Allure renders every outcome class."""
    root = owner.ROOT
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    gate = _gate(tmp_path, node_package_supply=root / "node_modules", head=head)
    result_dir = gate.s.evidence / "allure/results/single"
    result_dir.mkdir(parents=True)
    (gate.s.evidence / "allure/head.txt").write_text(head + "\n", encoding="utf-8")
    trial = tmp_path / "test_outcomes.py"
    trial.write_text(
        "import pytest\n\n"
        "def test_pass(): assert True\n"
        "def test_fail(): assert False, 'deliberate'\n"
        "@pytest.mark.skip(reason='deliberate')\n"
        "def test_skip(): assert False\n"
        "@pytest.fixture\n"
        "def broken(): raise RuntimeError('deliberate setup error')\n"
        "def test_error(broken): assert broken\n",
        encoding="utf-8",
    )
    gate.pytest.mkdir(parents=True)
    executed = run_command(
        root,
        (
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(owner.PYTEST_CONFIG),
            "--rootdir=.",
            "-o",
            "addopts=",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            f"--basetemp={tmp_path / 'pytest'}",
            f"--junitxml={gate.pytest / 'junit.xml'}",
            f"--alluredir={result_dir}",
            str(trial),
        ),
        timeout=30,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        remove_env_prefixes=("COVERAGE",),
    )
    assert executed.returncode == 1
    raw = tuple(result_dir.glob("*-result.json"))
    assert len(raw) == 4
    before = {item.name: item.read_bytes() for item in raw}

    report = gate.render_report()

    assert report == gate.s.evidence / "allure/agent"
    manifest = json.loads((report / "manifest/human-report.json").read_text())
    run = json.loads((report / "manifest/run.json").read_text())
    assert (manifest["status"], manifest["result_count"]) == ("generated", 4)
    stats = run["summary"]["stats"]
    names = ("total", "passed", "failed", "skipped", "broken")
    assert {key: stats.get(key, 0) for key in names} == {
        "total": 4,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "broken": 1,
    }
    assert (report / "awesome/index.html").is_file()
    query = run_command(
        root,
        (
            str(owner.ProjectRuntime.discover(root).node_executable()),
            str(root / "node_modules/allure/cli.js"),
            "agent",
            "query",
            "--from",
            str(report),
            "tests",
            "--status",
            "failed",
        ),
        timeout=15,
        check=True,
    )
    assert json.loads(query.stdout)["total_matches"] == 1
    assert before == {item.name: item.read_bytes() for item in raw}
    assert executed.returncode == 1
    raw[0].unlink()
    with pytest.raises(RuntimeError, match="allure_report_incomplete"):
        gate.render_report()
    assert not report.exists()


def test_failing_test_session_still_renders_without_replacing_test_failure(monkeypatch) -> None:
    """A derivative report must not turn the pytest failure into success or another failure."""
    gate = Mock()
    gate.run_tests.side_effect = RuntimeError("original_test_failure")
    monkeypatch.setattr(owner.PythonTestGate, "from_environment", lambda **_kwargs: gate)
    monkeypatch.setattr(
        type(sessions.RUNTIME), "node_package_supply", lambda _self: owner.ROOT / "node_modules"
    )

    with pytest.raises(RuntimeError, match="original_test_failure"):
        sessions.tests(SimpleNamespace(log=lambda _message: None))

    gate.render_report.assert_called_once_with()

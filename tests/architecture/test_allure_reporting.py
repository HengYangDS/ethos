"""Hosted verification renders human and Agent Allure views from one test attempt."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import tools.ci.hosted_verification as hosted_verification
from ethos.adapters.process import run_command
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.toml"


def _attempt(tmp_path: Path, *arguments: str) -> tuple[Path, int]:
    """Run pytest once into a report root shaped like the probe's, and return its exit code."""
    reports = tmp_path / "reports"
    (reports / "pytest").mkdir(parents=True)
    executed = run_command(
        ROOT,
        (
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(PYTEST_CONFIG),
            f"--rootdir={ROOT}",
            "-o",
            "addopts=",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            f"--basetemp={tmp_path / 'pytest'}",
            f"--report-log={reports / 'pytest/events.jsonl'}",
            f"--alluredir={reports / 'allure/results'}",
            *arguments,
        ),
        timeout=60,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        remove_env=("ETHOS_NATIVE_OUTPUT_DIR",),
        remove_env_prefixes=("COVERAGE", "PYTEST_"),
    )
    return reports, executed.returncode


def test_report_rebuilds_from_one_failed_pytest_attempt_without_rerun(tmp_path: Path) -> None:
    """A failed attempt still renders every outcome class; a lost result is refused."""
    trial = tmp_path / "test_outcomes.py"
    trial.write_text(
        "import json\n"
        "import allure\n"
        "import pytest\n\n"
        "@allure.feature('Proof evidence')\n"
        "def test_pass():\n"
        "    with allure.step('Inspect a public proof summary'):\n"
        "        summary = {'verdict': 'pass', 'required_gaps': []}\n"
        "        allure.attach(json.dumps(summary), name='Public proof summary',\n"
        "                      attachment_type=allure.attachment_type.JSON)\n"
        "        assert summary['verdict'] == 'pass'\n"
        "def test_fail(): assert False, 'deliberate'\n"
        "@pytest.mark.skip(reason='deliberate')\n"
        "def test_skip(): assert False\n"
        "@pytest.fixture\n"
        "def broken(): raise RuntimeError('deliberate setup error')\n"
        "def test_error(broken): assert broken\n",
        encoding="utf-8",
    )
    reports, returncode = _attempt(tmp_path, str(trial))
    assert returncode == 1
    raw = tuple((reports / "allure/results").glob("*-result.json"))
    assert len(raw) == 4
    before = {item.name: item.read_bytes() for item in raw}

    hosted_verification.render_allure(ROOT, reports)

    report = reports / "allure/agent"
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
    results = [json.loads(path.read_bytes()) for path in raw]
    passed = next(result for result in results if result["name"] == "test_pass")
    assert {"name": "feature", "value": "Proof evidence"} in passed["labels"]
    assert passed["steps"][0]["name"] == "Inspect a public proof summary"
    attachment = passed["steps"][0]["attachments"][0]
    assert attachment["type"] == "application/json"
    assert json.loads((reports / "allure/results" / attachment["source"]).read_text()) == {
        "verdict": "pass",
        "required_gaps": [],
    }
    runtime = ProjectRuntime.discover(ROOT)
    query = run_command(
        ROOT,
        (
            str(runtime.node_executable()),
            str(runtime.node_package_supply() / "allure/cli.js"),
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
    raw[0].unlink()
    with pytest.raises(ValueError, match=r"allure_identities_differ:missing=\S*#test_"):
        hosted_verification.render_allure(ROOT, reports)


def test_a_parameter_id_with_the_node_separator_keeps_its_identity(tmp_path: Path) -> None:
    """A case whose parameter id holds `::` is named by its original function, as in Allure."""
    target = (
        "tests/unit/kernel/test_coordination_contract.py"
        "::test_holder_ref_rejects_provider_only_or_ambiguous_values"
    )
    reports, returncode = _attempt(tmp_path, "-q", target)
    assert returncode == 0
    hosted_verification.render_allure(ROOT, reports)


def test_binary_parameter_cases_remain_distinct_in_native_agent_report(tmp_path: Path) -> None:
    """Allure must not call distinct pytest node IDs retries of one binary case."""
    target = (
        "tests/unit/adapters/repo/commit/test_admission.py::test_indexed_policy_projection_matrix"
    )
    reports, returncode = _attempt(tmp_path, "-n", "2", "-q", target)
    assert returncode == 0
    assert len(tuple((reports / "allure/results").glob("*-result.json"))) == 7

    hosted_verification.render_allure(ROOT, reports)

    run = json.loads((reports / "allure/agent/manifest/run.json").read_text())
    assert run["summary"]["stats"].get("total") == 7
    assert run["summary"]["stats"].get("retries", 0) == 0

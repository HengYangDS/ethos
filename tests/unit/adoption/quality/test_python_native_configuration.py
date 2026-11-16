"""Run the Python behavior probe under the repository's native test configuration."""

from __future__ import annotations

import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from uv import find_uv_bin

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.python_quality as python_quality
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from types import ModuleType

_FIXTURE = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
_SOURCE = "def answer() -> int:\n    return 42\n"
_TEST = "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"
# A carrier whose floor the sample's one test cannot meet: the `zero` branch never runs.
_UNMET_FLOOR = {
    ".config/checks/coverage/coverage.toml": (
        '[tool.coverage.run]\nsource = ["src"]\n\n[tool.coverage.report]\nfail_under = 100\n'
    ),
    "src/sample/__init__.py": (
        "def answer(*, zero: bool = False) -> int:\n    if zero:\n        return 0\n    return 42\n"
    ),
    "tests/test_sample.py": _TEST,
}


def _sample(tmp_path: Path, files: dict[str, str]) -> Path:
    """Commit the locked sample project with the given sources, tests and carriers."""
    locked = {
        name: (_FIXTURE / name).read_text(encoding="utf-8")
        for name in ("pyproject.toml", "uv.lock")
    }
    return committed_source_repo(
        tmp_path,
        {**locked, ".gitignore": "__pycache__/\n", "src/sample/__init__.py": _SOURCE, **files},
    )


def test_probe_collects_with_the_repository_pytest_carrier(tmp_path: Path) -> None:
    """The paradigm pytest carrier decides collection, with node identities from the root."""
    repo = _sample(
        tmp_path,
        {
            ".config/checks/pytest/pytest.toml": '[pytest]\npython_functions = ["check_*"]\n',
            "tests/test_sample.py": _TEST.replace("def test_answer", "def check_answer"),
        },
    )

    report = python_quality.behavior_report(repo)

    assert report["verdict"] == "pass", report
    assert report["tests"] == {"total": 1, "failures": 0, "errors": 0, "skipped": 0}


def test_probe_measures_with_the_repository_coverage_carrier(tmp_path: Path) -> None:
    """The coverage carrier's floor decides the verdict of the execution that measured it."""
    repo = _sample(tmp_path, _UNMET_FLOOR)

    report = python_quality.behavior_report(repo)

    assert report["required_gaps"] == ["quality_behavior_coverage_below_floor"], report
    assert report["tests"] == {"total": 1, "failures": 0, "errors": 0, "skipped": 0}
    assert report["coverage"]["floor"] == {"fail_under": 100.0, "precision": 0}
    assert "fail-under=100" in report["native"]["stdout"]


@pytest.mark.parametrize("status", [0, 1], ids=["tests-pass", "run-fails"])
def test_a_leg_runs_on_its_callers_interpreter_and_never_decides_the_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """A leg leaves the locked interpreter and the floor to the gate's own run."""
    finish = f"def pytest_sessionfinish(session):\n    session.exitstatus = {status}\n"
    mise = {
        ".config/mise/config.toml": '[tools]\npython = "3.14.7"\n',
        ".config/mise/mise.lock": "",
    }
    repo = _sample(tmp_path, {**_UNMET_FLOOR, **mise, "tests/conftest.py": finish})
    monkeypatch.setattr(python_quality, "locked_environment", lambda *_a, **_k: nullcontext({}))
    locked = {"python": tmp_path / "locked-python", "uv": Path(find_uv_bin())}
    monkeypatch.setattr(python_quality, "locked_tool", lambda _root, name, **_k: locked[name])

    report = python_quality.behavior_report(repo, leg=True)

    command = report["native"]["command"]
    assert command[command.index("--python") + 1] == sys.executable
    assert report["required_gaps"] == (["quality_behavior_tests_failed"] if status else []), report
    assert report["coverage"]["combined_percent"] < 100
    assert "floor" not in report["coverage"]


def test_a_leg_fails_where_the_project_does_not_admit_its_interpreter(tmp_path: Path) -> None:
    """The leg names its caller to uv, which refuses that interpreter; uv selects no other one.

    The lock states the project's range too, so the interpreter is the only reason left.
    """
    ranges = {"pyproject.toml": ">=3.12,<3.15", "uv.lock": ">=3.12, <3.15"}
    excluded = {
        name: (_FIXTURE / name).read_text(encoding="utf-8").replace(f'"{declared}"', '">=3.99"')
        for name, declared in ranges.items()
    }
    repo = _sample(tmp_path, {**excluded, "tests/test_sample.py": _TEST})

    report = python_quality.behavior_report(repo, leg=True)

    command = report["native"]["command"]
    assert command[command.index("--python") + 1] == sys.executable
    assert report["required_gaps"] == ["quality_behavior_test_environment_sync_failed"], report
    # uv's own words: the named interpreter is refused, and no other one was looked for.
    assert "incompatible with the project's Python requirement" in report["native"]["stderr"]


@pytest.mark.parametrize("provider", [python_quality, native_quality], ids=["python", "code"])
@pytest.mark.parametrize("declared", [None, 1200], ids=["default", "declared"])
def test_probe_runs_within_the_gate_timeout(
    tmp_path: Path, provider: ModuleType, declared: float | None
) -> None:
    """A gate's declared timeout bounds the test run; otherwise 600 seconds do."""
    repo = _sample(tmp_path, {"tests/test_sample.py": _TEST})

    with patch.object(python_quality, "run_command", wraps=python_quality.run_command) as run:
        report = provider.behavior_report(repo, timeout_seconds=declared)

    assert report["verdict"] == "pass", report
    assert run.call_args.kwargs["timeout"] == (600 if declared is None else 1200)


@pytest.mark.parametrize("named", [True, False], ids=["native-root", "no-native-root"])
def test_probe_keeps_reports_and_tool_state_to_the_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, named: bool
) -> None:
    """Reports reach a named native root; bytecode and Hypothesis storage stay in scratch."""
    suite = (
        "import os\nfrom pathlib import Path\n\nfrom sample import answer\n\n\n"
        "def test_answer() -> None:\n"
        "    result = Path(os.environ['ETHOS_NATIVE_OUTPUT_DIR']) / 'suite/result.txt'\n"
        "    result.parent.mkdir()\n    result.write_text('ok', encoding='utf-8')\n"
        "    storage = Path(os.environ['HYPOTHESIS_STORAGE_DIRECTORY']) / 'constants'\n"
        "    storage.mkdir(parents=True)\n"
        "    (storage / 'cache').write_text('ok', encoding='utf-8')\n"
        "    assert answer() == 42\n"
    )
    repo = _sample(tmp_path, {"tests/test_sample.py": suite})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    native = tmp_path / "native"
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    monkeypatch.delenv("HYPOTHESIS_STORAGE_DIRECTORY", raising=False)
    if named:
        monkeypatch.setenv("ETHOS_NATIVE_OUTPUT_DIR", str(native))
    else:
        monkeypatch.delenv("ETHOS_NATIVE_OUTPUT_DIR", raising=False)

    report = python_quality.behavior_report(repo)

    assert report["verdict"] == "pass", report
    copied = sorted(
        path.relative_to(native).as_posix() for path in native.rglob("*") if path.is_file()
    )
    expected = [
        "coverage/coverage.xml",
        "pytest/events.jsonl",
        "pytest/junit.xml",
        "suite/result.txt",
    ]
    assert copied == (expected if named else [])
    assert list(scratch.iterdir()) == []
    assert git(repo, "status", "--porcelain", "--ignored") == ""

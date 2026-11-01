"""Run the Python behavior probe under the repository's native test configuration."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.python_quality as python_quality
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from types import ModuleType

_FIXTURE = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
_SOURCE = "def answer() -> int:\n    return 42\n"
_TEST = "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"


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
    repo = _sample(
        tmp_path,
        {
            ".config/checks/coverage/coverage.toml": (
                '[tool.coverage.run]\nsource = ["src"]\n\n'
                "[tool.coverage.report]\nfail_under = 100\n"
            ),
            "src/sample/__init__.py": (
                "def answer(*, zero: bool = False) -> int:\n"
                "    if zero:\n        return 0\n    return 42\n"
            ),
            "tests/test_sample.py": _TEST,
        },
    )

    report = python_quality.behavior_report(repo)

    assert report["required_gaps"] == ["quality_behavior_tests_failed"], report
    assert report["tests"] == {"total": 1, "failures": 0, "errors": 0, "skipped": 0}
    assert "fail-under=100" in report["native"]["stdout"]


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
def test_probe_keeps_reports_and_bytecode_to_the_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, named: bool
) -> None:
    """Reports reach a named native root; nothing else outlives the attempt's scratch."""
    suite = (
        "import os\nfrom pathlib import Path\n\nfrom sample import answer\n\n\n"
        "def test_answer() -> None:\n"
        "    result = Path(os.environ['ETHOS_NATIVE_OUTPUT_DIR']) / 'suite/result.txt'\n"
        "    result.parent.mkdir()\n    result.write_text('ok', encoding='utf-8')\n"
        "    assert answer() == 42\n"
    )
    repo = _sample(tmp_path, {"tests/test_sample.py": suite})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    native = tmp_path / "native"
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
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

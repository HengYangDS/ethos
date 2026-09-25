"""Product-owned native Python quality adapters for adopted repositories."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import junit_report


def _source(root: Path) -> tuple[str, tuple[str, ...]]:
    """Bind selected tracked Python files to the current committed tree."""
    head = current_tracked_head(root)
    if not head:
        message = "source_head_missing"
        raise ValueError(message)
    paths = tuple(sorted(path for path in git_files(root, "*.py") if (root / path).is_file()))
    if not paths:
        message = "python_sources_missing"
        raise ValueError(message)
    return current_tree(root, head), paths


def _failure(axis: str, reason: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "unproven",
        "required_gaps": [f"quality_{axis}_{reason}"],
    }


def static_report(root: Path) -> dict[str, object]:
    """Run product-pinned Ruff over every tracked Python file, not a profile argv."""
    try:
        tree, paths = _source(root)
    except (OSError, ValueError) as error:
        reason = str(error) if isinstance(error, ValueError) else "source_unavailable"
        return _failure("static", reason)
    command = (
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--isolated",
        "--no-cache",
        "--output-format",
        "json",
        "--select",
        "E,F,B,I,UP",
        *paths,
    )
    try:
        result = run_command(root, command, timeout=180, remove_env=("PYTHONPATH",))
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return _failure("static", f"tool_unavailable:{type(error).__name__}")
    try:
        findings = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return _failure("static", "report_invalid")
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        return _failure("static", "report_invalid")
    if result.returncode or findings:
        return _failure("static", "diagnostics")
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "quality_evidence": {
            "axis": "static-analysis",
            "source_tree": tree,
            "selected_paths": list(paths),
        },
    }


def _behavior_scope(root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Require the supported src/tests layout and a native locked toolchain."""
    source = tuple(path for path in paths if path.startswith("src/"))
    tests = tuple(path for path in paths if path.startswith("tests/"))
    if not source or not tests or len(source) + len(tests) != len(paths):
        message = "scope_unrecognized"
        raise ValueError(message)
    if not (root / "pyproject.toml").is_file() or not (root / "uv.lock").is_file():
        message = "locked_toolchain_missing"
        raise ValueError(message)
    return source


def _behavior_evidence(
    root: Path, source: tuple[str, ...]
) -> tuple[dict[str, int], dict[str, object]]:
    """Observe one locked native test run and its fresh reports."""
    with TemporaryDirectory(prefix="ethos-python-quality-") as temporary:
        output = Path(temporary)
        junit = output / "junit.xml"
        coverage = output / "coverage.xml"
        command = (
            sys.executable,
            "-m",
            "uv",
            "run",
            "--locked",
            "--offline",
            "python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={output / 'pytest'}",
            f"--junitxml={junit}",
            "--cov=src",
            f"--cov-report=xml:{coverage}",
            "--cov-fail-under=0",
            "tests",
        )
        result = run_command(
            root,
            command,
            timeout=600,
            env={"COVERAGE_FILE": str(output / ".coverage")},
            remove_env=("VIRTUAL_ENV", "PYTHONPATH", "PYTEST_ADDOPTS"),
        )
        counts, failed = junit_report((junit,))
        measured = coverage_report(coverage, include_files=True)
        files = measured["files"]
        if not isinstance(files, dict):
            message = "coverage_scope_invalid"
            raise TypeError(message)
        selected = tuple(path.removeprefix("src/") for path in source)
        if any(name not in files for name in selected):
            message = "coverage_scope_incomplete"
            raise ValueError(message)
        if any(
            isinstance(files[name], dict)
            and files[name]["lines"] > 0
            and files[name]["hit_lines"] == 0
            for name in selected
        ):
            message = "source_unexercised"
            raise ValueError(message)
        if result.returncode or failed or measured["covered"] == 0:
            message = "tests_failed"
            raise ValueError(message)
        return counts, measured


def behavior_report(root: Path) -> dict[str, object]:
    """Run locked pytest and verify fresh JUnit and source coverage evidence."""
    try:
        tree, paths = _source(root)
        source = _behavior_scope(root, paths)
        counts, measured = _behavior_evidence(root, source)
    except (
        OSError,
        TypeError,
        ValueError,
        ProcessExecutionError,
        subprocess.TimeoutExpired,
    ) as error:
        return _failure(
            "behavior", str(error) if isinstance(error, ValueError) else type(error).__name__
        )
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "tests": counts,
        "coverage": {key: value for key, value in measured.items() if key != "files"},
        "quality_evidence": {
            "axis": "behavior",
            "source_tree": tree,
            "selected_paths": list(source),
        },
    }

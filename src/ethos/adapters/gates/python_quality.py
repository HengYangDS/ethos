"""Product-owned native Python quality adapters for adopted repositories."""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.repository.policy.code_subjects import observed_code_subjects
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


def _behavior_scope(root: Path, paths: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Select production and test subjects from the common code classifier."""
    subjects = observed_code_subjects(paths)
    source = tuple(subject.path for subject in subjects if not subject.is_test)
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    if not source or not tests or len(subjects) != len(paths):
        message = "scope_unrecognized"
        raise ValueError(message)
    if not (root / "pyproject.toml").is_file() or not (root / "uv.lock").is_file():
        message = "locked_toolchain_missing"
        raise ValueError(message)
    return source, tests


def _behavior_evidence(
    root: Path, source: tuple[str, ...], tests: tuple[str, ...]
) -> tuple[dict[str, int], dict[str, object]]:
    """Observe one locked native test run and its fresh reports."""
    with TemporaryDirectory(prefix="ethos-python-quality-") as temporary, ExitStack() as scope:
        output = Path(temporary)
        junit = output / "junit.xml"
        coverage = output / "coverage.xml"
        targets = tuple(sorted({path.partition("/")[0] for path in tests}))
        mise_files = repository_mise_files(root)
        environment = {
            "COVERAGE_FILE": str(output / ".coverage"),
            "UV_PROJECT_ENVIRONMENT": str(output / "venv"),
        }
        if mise_files is not None:
            environment = {
                **scope.enter_context(locked_environment(root, mise_files)),
                **environment,
            }
            prefix = (
                str(locked_tool(root, "uv", files=mise_files)),
                "run",
                "--locked",
                "--offline",
                "--python",
                str(locked_tool(root, "python", files=mise_files)),
            )
        else:
            prefix = (sys.executable, "-m", "uv", "run", "--locked", "--offline")
        command = (
            *prefix,
            "python",
            "-m",
            "coverage",
            "run",
            "--branch",
            "--source=.",
            "-m",
            "pytest",
            "-q",
            "-o",
            f"cache_dir={output / 'pytest-cache'}",
            f"--basetemp={output / 'pytest'}",
            f"--junitxml={junit}",
            *targets,
        )
        removed = ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH", "PYTEST_ADDOPTS")
        result = run_command(
            root,
            command,
            timeout=600,
            env=environment,
            remove_env=removed,
            remove_env_prefixes=("MISE_",),
        )
        if not junit.is_file():
            message = "test_command_failed" if result.returncode else "test_report_missing"
            raise ValueError(message)
        report = run_command(
            root,
            (*prefix, "python", "-m", "coverage", "xml", "-o", str(coverage)),
            timeout=60,
            env=environment,
            remove_env=removed,
            remove_env_prefixes=("MISE_",),
        )
        if report.returncode or not coverage.is_file():
            message = "test_command_failed" if result.returncode else "coverage_report_missing"
            raise ValueError(message)
        counts, failed = junit_report((junit,))
        measured = coverage_report(coverage, include_files=True)
        files = measured["files"]
        if not isinstance(files, dict):
            message = "coverage_scope_invalid"
            raise TypeError(message)
        selected = source
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
        source, tests = _behavior_scope(root, paths)
        counts, measured = _behavior_evidence(root, source, tests)
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

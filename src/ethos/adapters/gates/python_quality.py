"""Product-owned native Python quality adapters for adopted repositories."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import junit_report


def _failure(axis: str, reason: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "unproven",
        "required_gaps": [f"quality_{axis}_{reason}"],
    }


def _native_fields(execution: NativeExecution) -> dict[str, object]:
    """Retain the original attempt independently of the provider verdict."""
    return {
        "command": list(execution.argv),
        "cwd": str(execution.cwd),
        "executable": execution.executable,
        "exit_code": execution.exit_code,
        "stdout": execution.stdout,
        "stderr": execution.stderr,
    }


def _static_execution(
    root: Path, paths: tuple[str, ...], execution: NativeExecution | None
) -> NativeExecution:
    """Select the native isolated command before execution or same-attempt consumption."""
    command = (
        sys.executable,
        "-I",
        "-m",
        "ruff",
        "check",
        "--isolated",
        "--no-cache",
        "--ignore-noqa",
        "--output-format",
        "json",
        "--select",
        "E,F,B,I,UP",
        *paths,
    )
    if execution is None:
        result = run_command(root, command, timeout=180, remove_env=("PYTHONPATH",))
        return NativeExecution(
            declared_identity=command,
            argv=command,
            cwd=root.resolve(),
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            executable=str(Path(sys.executable).absolute()),
        )
    if execution.cwd != root.resolve() or execution.argv[1:] != command[1:]:
        message = "python_native_selection_invalid"
        raise ValueError(message)
    if not execution.executable or os.path.normcase(
        str(Path(execution.executable).absolute())
    ) != os.path.normcase(str(Path(sys.executable).absolute())):
        message = "python_native_toolchain_unbound"
        raise ValueError(message)
    return execution


def _static_diagnostics(execution: NativeExecution) -> None:
    """Require readable native findings, clean exit and no stderr diagnostics."""
    try:
        findings = json.loads(execution.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        message = "report_invalid"
        raise ValueError(message) from error
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        message = "report_invalid"
        raise ValueError(message)
    if execution.exit_code or execution.stderr or findings:
        message = "diagnostics"
        raise ValueError(message)


def static_report(root: Path, *, execution: NativeExecution | None = None) -> dict[str, object]:
    """Qualify one isolated product-pinned Ruff attempt over exact Python subjects."""
    native = _native_fields(execution) if execution is not None else {}
    try:
        tree, subjects = observe_quality_subjects(root, language="python")
        paths = tuple(subject.path for subject in subjects)
        execution = _static_execution(root, paths, execution)
        native = _native_fields(execution)
        observe_quality_subjects(root, language="python", expected_tree=tree)
        _static_diagnostics(execution)
    except (OSError, ValueError, ProcessExecutionError, subprocess.TimeoutExpired) as error:
        reason = (
            str(error)
            if isinstance(error, ValueError)
            else f"tool_unavailable:{type(error).__name__}"
        )
        return {**_failure("static", reason), "native": native}
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "native": native,
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


def behavior_report(root: Path, *, execution: NativeExecution | None = None) -> dict[str, object]:
    """Run locked pytest and verify fresh JUnit and source coverage evidence."""
    if execution is not None:
        return {
            **_failure("behavior", "python_native_evidence_unavailable"),
            "native": _native_fields(execution),
        }
    try:
        tree, subjects = observe_quality_subjects(root, language="python")
        paths = tuple(subject.path for subject in subjects)
        source, tests = _behavior_scope(root, paths)
        counts, measured = _behavior_evidence(root, source, tests)
        observe_quality_subjects(root, language="python", expected_tree=tree)
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

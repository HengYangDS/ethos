"""Product-owned native Python quality adapters for adopted repositories."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tomllib
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import cast

from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from uv import find_uv_bin

from ethos.adapters.gates.native.python import report as native_python_report
from ethos.adapters.gates.python_target import compatibility_target
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import junit_stream_report

if TYPE_CHECKING:
    from ethos.repository.policy.code_subjects import CodeSubject

# The shared formatter width of governed repositories; isolation keeps it product-owned.
_FLEET_LINE_LENGTH = 100


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
    root: Path, paths: tuple[str, ...], target: str, execution: NativeExecution | None
) -> NativeExecution:
    """Select the native isolated command before execution or same-attempt consumption.

    Isolation keeps the product's rule floor; the explicit target keeps the subject's
    declared Python version rather than the checker's default.
    """
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
        "--line-length",
        str(_FLEET_LINE_LENGTH),
        "--target-version",
        target,
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
    """Qualify one isolated product-pinned Ruff attempt at the subjects' declared target."""
    native = _native_fields(execution) if execution is not None else {}
    try:
        if execution is not None and execution.evidence is not None:
            return native_python_report(root, execution, "static-analysis")
        tree, subjects = observe_quality_subjects(root, language="python")
        paths = tuple(subject.path for subject in subjects)
        authored = tuple(subject.path for subject in subjects if subject.requires_authored_analysis)
        artifacts = tuple(
            subject.path for subject in subjects if not subject.requires_authored_analysis
        )
        target = compatibility_target(root, tree, authored) if authored else None
        if target is not None:
            execution = _static_execution(root, authored, target.version, execution)
            native = _native_fields(execution)
        elif execution is not None:
            return {**_failure("static", "python_native_selection_invalid"), "native": native}
        observe_quality_subjects(root, language="python", expected_tree=tree)
        if execution is not None:
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
            **(
                {"authored_paths": list(authored), "artifact_paths": list(artifacts)}
                if artifacts
                else {}
            ),
            **({"python_target": target.evidence()} if target is not None else {}),
        },
    }


def _behavior_scope(
    root: Path, subjects: tuple[CodeSubject, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Select production and test subjects from the common code classifier."""
    source = tuple(subject.path for subject in subjects if subject.requires_behavior)
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    if not source or not tests:
        message = "scope_unrecognized"
        raise ValueError(message)
    if not (root / "pyproject.toml").is_file() or not (root / "uv.lock").is_file():
        message = "locked_toolchain_missing"
        raise ValueError(message)
    return source, tests


def _interpreter_pin(root: Path) -> tuple[str, ...]:
    """Pin the runtime interpreter only where the project's requires-python admits it.

    Otherwise uv, the project's own toolchain owner, selects an installed interpreter
    that the project declares.
    """
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return ()
    section = project.get("project")
    declared = section.get("requires-python") if isinstance(section, dict) else None
    if isinstance(declared, str):
        try:
            if platform.python_version() not in SpecifierSet(declared):
                return ()
        except InvalidSpecifier:
            return ()
    return ("--python", sys.executable)


def _behavior_evidence(
    root: Path, source: tuple[str, ...], tests: tuple[str, ...], bindable: tuple[str, ...]
) -> dict[str, object]:
    """Observe one locked native test run and its fresh reports."""
    with TemporaryDirectory(prefix="ethos-python-quality-") as temporary, ExitStack() as scope:
        output = Path(temporary)
        junit = output / "junit.xml"
        events = output / "events.jsonl"
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
            prefix = (find_uv_bin(), "run", "--locked", "--offline", *_interpreter_pin(root))
        command = (
            *prefix,
            "python",
            "-m",
            "pytest",
            "-q",
            "-W",
            "error",
            "-o",
            f"cache_dir={output / 'pytest-cache'}",
            f"--basetemp={output / 'pytest'}",
            f"--junitxml={junit}",
            f"--report-log={events}",
            "--cov=.",
            "--cov-branch",
            f"--cov-report=xml:{coverage}",
            *targets,
        )
        removed = (
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "PYTHONPATH",
            "PYTEST_ADDOPTS",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        )
        result = run_command(
            root,
            command,
            timeout=600,
            env=environment,
            remove_env=removed,
            remove_env_prefixes=("MISE_",),
        )
        evidence: dict[str, object] = {
            "native": _native_fields(
                NativeExecution(
                    command,
                    command,
                    root,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                    executable=command[0],
                )
            )
        }
        try:
            missing = next(
                (
                    name
                    for name, path in (("test_report", junit), ("test_event_report", events))
                    if not path.is_file()
                ),
                "",
            )
            if missing:
                reason = "test_command_failed" if result.returncode else f"{missing}_missing"
                return {**evidence, **_failure("behavior", reason)}
            counts, failed = junit_stream_report(
                junit.read_text(encoding="utf-8"),
                pytest_events=events.read_text(encoding="utf-8"),
            )
            evidence["tests"] = counts
            if not coverage.is_file():
                reason = "test_command_failed" if result.returncode else "coverage_report_missing"
                return {**evidence, **_failure("behavior", reason)}
            measured = coverage_report(
                coverage,
                include_files=True,
                repository_root=root.resolve(),
                source_paths=bindable,
            )
            evidence["coverage"] = {key: value for key, value in measured.items() if key != "files"}
            files = cast("dict[str, dict[str, int]]", measured["files"])
            if any(name not in files for name in source):
                reason = "coverage_scope_incomplete"
            elif any(files[name]["lines"] > 0 and files[name]["hit_lines"] == 0 for name in source):
                reason = "source_unexercised"
            elif result.returncode or failed or measured["covered"] == 0:
                reason = "tests_failed"
            else:
                reason = ""
            if reason:
                return {**evidence, **_failure("behavior", reason)}
        except (OSError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
            reason = str(error) if isinstance(error, ValueError) else type(error).__name__
            return {**evidence, **_failure("behavior", reason)}
        return {**evidence, "verdict": "pass", "state": "verified", "required_gaps": []}


def behavior_report(root: Path, *, execution: NativeExecution | None = None) -> dict[str, object]:
    """Run locked pytest and verify fresh JUnit and source coverage evidence."""
    if execution is not None and execution.evidence is None:
        return {
            **_failure("behavior", "python_native_evidence_unavailable"),
            "native": _native_fields(execution),
        }
    evidence: dict[str, object] = {}
    try:
        if execution is not None:
            return native_python_report(root, execution, "behavior")
        tree, subjects = observe_quality_subjects(root, language="python")
        source, tests = _behavior_scope(root, subjects)
        # Coverage may measure any committed Python subject; only product source owes coverage.
        bindable = tuple(subject.path for subject in subjects)
        evidence = _behavior_evidence(root, source, tests, bindable)
        observe_quality_subjects(root, language="python", expected_tree=tree)
    except ProcessExecutionError as error:
        return {**evidence, **_failure("behavior", error.code), "diagnostics": [error.evidence()]}
    except (
        OSError,
        TypeError,
        ValueError,
        subprocess.TimeoutExpired,
    ) as error:
        reason = str(error) if isinstance(error, ValueError) else type(error).__name__
        return {**evidence, **_failure("behavior", reason)}
    if evidence["verdict"] != "pass":
        return evidence
    return {
        **evidence,
        "quality_evidence": {
            "axis": "behavior",
            "source_tree": tree,
            "selected_paths": list(source),
        },
    }

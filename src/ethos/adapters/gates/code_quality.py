"""Product-owned native quality evidence for tracked code carriers."""

from __future__ import annotations

import shutil
import subprocess
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Never

import ethos.adapters.gates.go as native_go
import ethos.adapters.gates.reports as native_reports
from ethos.adapters.gates.execution import native_environment
from ethos.adapters.gates.execution import native_tool
from ethos.adapters.gates.python_quality import behavior_report as python_behavior_report
from ethos.adapters.gates.python_quality import static_report as python_static_report
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.code_subjects import CodeSubject
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import junit_report
from ethos.repository.policy.quality_reports import junit_stream_report
from ethos.repository.policy.quality_reports import lcov_covered_paths
from ethos.repository.policy.quality_reports import lcov_stream_covered_paths

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.contracts.gates import Gate


def _invalid(reason: str) -> Never:
    """Reject an unproved native quality observation."""
    raise ValueError(reason)


def _source(root: Path) -> tuple[str, tuple[CodeSubject, ...]]:
    """Bind observed code subjects to the exact committed source tree."""
    head = current_tracked_head(root)
    if not head:
        _invalid("source_head_missing")
    subjects = observed_code_subjects(tuple(git_files(root)))
    if not subjects:
        _invalid("code_sources_missing")
    if any(not (root / subject.path).is_file() for subject in subjects):
        _invalid("code_source_unavailable")
    return current_tree(root, head), subjects


def _failure(axis: str, reason: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "unproven",
        "required_gaps": [f"quality_{axis}_{reason}"],
    }


def _javascript_command(command: tuple[str, ...], tests: tuple[str, ...]) -> bool:
    """Validate native test and reporter selection before invoking repository code."""
    if not command:
        _invalid("javascript_native_test_selection_invalid")
    mise_wrapped = Path(command[0]).name in {"mise", "mise.exe"} and command[1:4] == (
        "exec",
        "--locked",
        "--",
    )
    if mise_wrapped:
        command = command[4:]
    if not command:
        _invalid("javascript_native_test_selection_invalid")
    if Path(command[0]).name not in {"node", "node.exe"}:
        _invalid("javascript_native_test_selection_invalid")
    required = (
        "--test",
        "--experimental-test-coverage",
        "--test-reporter=junit",
        "--test-reporter-destination=stdout",
        "--test-reporter=lcov",
        "--test-reporter-destination=stderr",
        *tests,
    )
    if command[1:] != required:
        _invalid("javascript_native_test_selection_invalid")
    return mise_wrapped


def _javascript_native_observation(
    root: Path,
    tests: tuple[str, ...],
    production: tuple[str, ...],
    native: dict[str, str],
    execution: NativeExecution,
) -> tuple[dict[str, int], set[str]]:
    """Consume a valid native test's original streams; never run a substitute."""
    mise_wrapped = _javascript_command(execution.argv, tests)
    command = execution.argv[4:] if mise_wrapped else execution.argv
    if execution.cwd != root.resolve() or execution.exit_code != 0:
        _invalid("javascript_native_test_selection_invalid")
    if "PATH" in native and not mise_wrapped:
        selected = shutil.which(command[0])
        locked = shutil.which("node", path=native["PATH"])
        if selected is None or locked is None or Path(selected).resolve() != Path(locked).resolve():
            _invalid("javascript_native_toolchain_unbound")
    counts, failed = junit_stream_report(execution.stdout)
    if failed:
        _invalid("javascript_tests_failed")
    return counts, lcov_stream_covered_paths(root, execution.stderr, production)


def _javascript_behavior(
    root: Path,
    subjects: tuple[CodeSubject, ...],
    native: dict[str, str],
    execution: NativeExecution | None,
) -> dict[str, object]:
    """Use one native Node test run for cases and per-module coverage."""
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not tests or not production:
        _invalid("javascript_tests_or_sources_missing")
    if execution is not None:
        counts, observed = _javascript_native_observation(
            root, tests, production, native, execution
        )
    else:
        with TemporaryDirectory(prefix="ethos-javascript-coverage-") as directory:
            junit = Path(directory) / "junit.xml"
            lcov = Path(directory) / "coverage.lcov"
            result = run_command(
                root,
                (
                    native_tool(root, "node"),
                    "--test",
                    "--experimental-test-coverage",
                    "--test-reporter=junit",
                    f"--test-reporter-destination={junit}",
                    "--test-reporter=lcov",
                    f"--test-reporter-destination={lcov}",
                    *tests,
                ),
                timeout=300,
                env=native,
                remove_env=("NODE_OPTIONS", "NODE_V8_COVERAGE"),
                remove_env_prefixes=("MISE_",),
            )
            if result.returncode:
                _invalid("javascript_tests_failed")
            counts, failed = junit_report((junit,))
            if failed:
                _invalid("javascript_tests_failed")
            observed = lcov_covered_paths(root, lcov, production)
    return {
        "language": "javascript",
        "tests_passed": counts["total"] - counts["skipped"],
        "covered_paths": sorted(observed),
    }


def _javascript_static(
    root: Path, paths: tuple[str, ...], native: dict[str, str]
) -> dict[str, object]:
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    node = native_tool(root, "node")
    for path in paths:
        result = run_command(
            root,
            (node, "--check", path),
            timeout=60,
            env=native,
            remove_env_prefixes=("MISE_",),
        )
        if result.returncode:
            _invalid("javascript_syntax_diagnostics")
    return {"language": "javascript", "checked_paths": len(paths)}


def _python_quality(
    root: Path,
    axis: str,
    subjects: tuple[CodeSubject, ...],
    execution: NativeExecution | None,
) -> dict[str, object]:
    """Preserve native judgment and bind its complete Python subject scope."""
    if execution is not None and execution.reports is None:
        return _failure(axis, "python_native_evidence_unavailable")
    report = (
        python_behavior_report(root, execution=execution)
        if axis == "behavior"
        else python_static_report(root, execution=execution)
    )
    if report.get("verdict") != "pass":
        return report
    selected = report.get("quality_evidence")
    expected = [
        subject.path
        for subject in subjects
        if subject.language == "python" and (axis != "behavior" or not subject.is_test)
    ]
    if not isinstance(selected, dict) or selected.get("selected_paths") != expected:
        return _failure(axis, "python_quality_unproven")
    return report


def _preflight(
    root: Path,
    axis: str,
    subjects: tuple[CodeSubject, ...],
    command: tuple[str, ...],
    gate: Gate | None,
) -> dict[str, object]:
    """Check every applicable native language before a declared command starts."""
    gaps: list[str] = []
    if gate is not None and gate.native_reports:
        native_reports.preflight(root, gate, {subject.language for subject in subjects}, axis)
        return {"verdict": "pass", "state": "ready", "required_gaps": []}
    for language in sorted({subject.language for subject in subjects}):
        if language == "python":
            report = (
                python_behavior_report(root, preflight=True, command=command)
                if axis == "behavior"
                else python_static_report(root, preflight=True, command=command)
            )
            gaps.extend(string_sequence(report.get("required_gaps"), drop_empty=True))
        elif axis != "behavior":
            gaps.append(f"quality_{axis}_{language}_native_evidence_unavailable")
        elif language == "go":
            native_go.preflight(root, command)
        elif language == "javascript":
            _javascript_command(
                command,
                tuple(
                    subject.path
                    for subject in subjects
                    if subject.language == language and subject.is_test
                ),
            )
        else:
            gaps.append(f"quality_{axis}_native_language_unsupported:{language}")
    return {
        "verdict": "block" if gaps else "pass",
        "state": "unproven" if gaps else "ready",
        "required_gaps": gaps,
    }


def _report(
    root: Path,
    axis: str,
    *,
    execution: NativeExecution | None = None,
    preflight: bool = False,
    command: tuple[str, ...] = (),
    gate: Gate | None = None,
) -> dict[str, object]:
    try:
        tree, subjects = _source(root)
        languages = {subject.language for subject in subjects}
        if preflight:
            return _preflight(root, axis, subjects, command, gate)
        if execution is not None and axis != "behavior" and languages & {"go", "javascript"}:
            _invalid("native_static_evidence_unavailable")
        with ExitStack() as scope:
            tool_environment = (
                native_environment(root, scope) if languages & {"go", "javascript"} else {}
            )
            native: list[dict[str, object]] = []
            for language in sorted(languages):
                language_subjects = tuple(
                    subject for subject in subjects if subject.language == language
                )
                paths = tuple(subject.path for subject in language_subjects)
                if language == "python":
                    report = _python_quality(root, axis, subjects, execution)
                    if report.get("verdict") != "pass":
                        return report
                    native.append({"language": language, "report": report})
                elif language == "go":
                    native.append(
                        native_go.behavior(
                            root,
                            language_subjects,
                            tool_environment,
                            execution,
                        )
                        if axis == "behavior"
                        else native_go.static_report(root, paths, tool_environment)
                    )
                elif language == "javascript":
                    native.append(
                        _javascript_behavior(root, language_subjects, tool_environment, execution)
                        if axis == "behavior"
                        else _javascript_static(root, paths, tool_environment)
                    )
                else:
                    _invalid(f"native_language_unsupported:{language}")
    except ProcessExecutionError as error:
        return {**_failure(axis, error.code), "diagnostics": [error.evidence()]}
    except (OSError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        return _failure(axis, str(error) if isinstance(error, ValueError) else type(error).__name__)
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "native": native,
        "quality_evidence": {
            "axis": axis,
            "source_tree": tree,
            "selected_paths": [
                subject.path for subject in subjects if axis != "behavior" or not subject.is_test
            ],
        },
    }


def behavior_report(
    root: Path,
    *,
    execution: NativeExecution | None = None,
    preflight: bool = False,
    command: tuple[str, ...] = (),
    gate: Gate | None = None,
) -> dict[str, object]:
    """Require non-vacuous native tests for every observed code language."""
    return _report(
        root, "behavior", execution=execution, preflight=preflight, command=command, gate=gate
    )


def static_report(
    root: Path,
    *,
    execution: NativeExecution | None = None,
    preflight: bool = False,
    command: tuple[str, ...] = (),
) -> dict[str, object]:
    """Require native static diagnostics for every observed code language."""
    return _report(
        root, "static-analysis", execution=execution, preflight=preflight, command=command
    )

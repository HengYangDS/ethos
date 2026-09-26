"""Product-owned native quality evidence for tracked code carriers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Never

from ethos.adapters.gates.python_quality import behavior_report as python_behavior_report
from ethos.adapters.gates.python_quality import static_report as python_static_report
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.code_subjects import CodeSubject
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import go_covered_paths
from ethos.repository.policy.quality_reports import junit_report
from ethos.repository.policy.quality_reports import v8_covered_paths


def _invalid(reason: str) -> Never:
    """Reject an unproved native quality observation."""
    raise ValueError(reason)


def source_subjects(root: Path) -> tuple[str, tuple[CodeSubject, ...]]:
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


def _executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        _invalid(f"native_tool_unavailable:{name}")
    return str(Path(path).resolve())


def _go_environment() -> dict[str, str]:
    """Use Go's content-addressed caches without network or toolchain downloads."""
    return {"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off"}


def _go_behavior(root: Path, subjects: tuple[CodeSubject, ...]) -> dict[str, object]:
    """Require an executed test and coverage of each production Go file."""
    if not (root / "go.mod").is_file() or not any(
        subject.path.endswith("_test.go") for subject in subjects
    ):
        _invalid("go_tests_or_module_missing")
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not production:
        _invalid("go_behavior_source_missing")
    with TemporaryDirectory(prefix="ethos-go-coverage-") as directory:
        coverage = Path(directory) / "coverage.out"
        result = run_command(
            root,
            (
                _executable("go"),
                "test",
                "-json",
                f"-coverprofile={coverage}",
                "-count=1",
                "./...",
            ),
            timeout=300,
            env=_go_environment(),
        )
        if result.returncode:
            _invalid("go_tests_failed")
        if not coverage.is_file():
            _invalid("go_coverage_missing")
        profile = coverage.read_text(encoding="utf-8").splitlines()
    try:
        events = [json.loads(line) for line in result.stdout.splitlines() if line]
    except json.JSONDecodeError as error:
        message = "go_test_report_invalid"
        raise ValueError(message) from error
    passes = sum(
        event.get("Action") == "pass" and bool(event.get("Test"))
        for event in events
        if isinstance(event, dict)
    )
    if passes == 0:
        _invalid("go_tests_unexecuted")
    return {
        "language": "go",
        "tests_passed": passes,
        "covered_paths": go_covered_paths(profile, production),
    }


def _go_static(root: Path, paths: tuple[str, ...]) -> dict[str, object]:
    if not (root / "go.mod").is_file():
        _invalid("go_module_missing")
    formatted = run_command(root, (_executable("gofmt"), "-l", *paths), timeout=60)
    if formatted.returncode or formatted.stdout.strip():
        _invalid("go_format_diagnostics")
    vetted = run_command(
        root,
        (_executable("go"), "vet", "./..."),
        timeout=300,
        env=_go_environment(),
    )
    if vetted.returncode:
        _invalid("go_vet_diagnostics")
    return {"language": "go", "checked_paths": len(paths)}


def _javascript_behavior(root: Path, subjects: tuple[CodeSubject, ...]) -> dict[str, object]:
    """Require native tests and V8 execution evidence for all production modules."""
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not tests or not production:
        _invalid("javascript_tests_or_sources_missing")
    with TemporaryDirectory(prefix="ethos-javascript-coverage-") as directory:
        result = run_command(
            root,
            (_executable("node"), "--test", "--test-reporter=junit", *tests),
            timeout=300,
            env={"NODE_V8_COVERAGE": directory},
        )
        if result.returncode:
            _invalid("javascript_tests_failed")
        junit = Path(directory) / "junit.xml"
        junit.write_text(result.stdout, encoding="utf-8")
        return javascript_test_evidence(root, Path(directory), junit, subjects)


def javascript_test_evidence(
    root: Path, directory: Path, junit: Path, subjects: tuple[CodeSubject, ...]
) -> dict[str, object]:
    """Qualify the same native JUnit and V8 materials for a tracked JS scope."""
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not tests or not production:
        _invalid("javascript_tests_or_sources_missing")
    counts, failed = junit_report((junit,))
    if failed:
        _invalid("javascript_tests_failed")
    observed = v8_covered_paths(root, directory, production)
    return {
        "language": "javascript",
        "tests_passed": counts["total"] - counts["skipped"],
        "covered_paths": sorted(observed),
    }


def _javascript_static(root: Path, paths: tuple[str, ...]) -> dict[str, object]:
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    node = _executable("node")
    for path in paths:
        result = run_command(root, (node, "--check", path), timeout=60)
        if result.returncode:
            _invalid("javascript_syntax_diagnostics")
    return {"language": "javascript", "checked_paths": len(paths)}


def _report(root: Path, axis: str) -> dict[str, object]:
    try:
        tree, subjects = source_subjects(root)
        languages = {subject.language for subject in subjects}
        native: list[dict[str, object]] = []
        for language in sorted(languages):
            language_subjects = tuple(
                subject for subject in subjects if subject.language == language
            )
            paths = tuple(subject.path for subject in language_subjects)
            if language == "python":
                report = (
                    python_behavior_report(root)
                    if axis == "behavior"
                    else python_static_report(root)
                )
                selected = report.get("quality_evidence")
                expected = [
                    subject.path
                    for subject in subjects
                    if subject.language == language and (axis != "behavior" or not subject.is_test)
                ]
                if (
                    report.get("verdict") != "pass"
                    or not isinstance(selected, dict)
                    or selected.get("selected_paths") != expected
                ):
                    _invalid("python_quality_unproven")
                native.append({"language": language, "report": report})
            elif language == "go":
                native.append(
                    _go_behavior(root, language_subjects)
                    if axis == "behavior"
                    else _go_static(root, paths)
                )
            elif language == "javascript":
                native.append(
                    _javascript_behavior(root, language_subjects)
                    if axis == "behavior"
                    else _javascript_static(root, paths)
                )
            else:
                _invalid(f"native_language_unsupported:{language}")
    except (
        OSError,
        TypeError,
        ValueError,
        ProcessExecutionError,
        subprocess.TimeoutExpired,
    ) as error:
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


def behavior_report(root: Path) -> dict[str, object]:
    """Require non-vacuous native tests for every observed code language."""
    return _report(root, "behavior")


def static_report(root: Path) -> dict[str, object]:
    """Require native static diagnostics for every observed code language."""
    return _report(root, "static-analysis")

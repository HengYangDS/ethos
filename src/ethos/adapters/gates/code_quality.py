"""Product-owned native quality evidence for tracked code carriers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Never
from urllib.parse import urlparse
from urllib.request import url2pathname

from ethos.adapters.gates.python_quality import behavior_report as python_behavior_report
from ethos.adapters.gates.python_quality import static_report as python_static_report
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.code_subjects import CodeSubject
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import junit_report


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


def _executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        _invalid(f"native_tool_unavailable:{name}")
    return str(Path(path).resolve())


def _go_environment() -> dict[str, str]:
    """Use Go's content-addressed caches without network or toolchain downloads."""
    return {"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off"}


def _go_covered_paths(profile: list[str], production: tuple[str, ...]) -> list[str]:
    """Interpret Go's structured coverage profile against exact tracked paths."""
    if not profile or not profile[0].startswith("mode: "):
        _invalid("go_coverage_invalid")
    hits = dict.fromkeys(production, 0)
    for line in profile[1:]:
        fields = line.split()
        if len(fields) != 3:
            _invalid("go_coverage_invalid")
        source = fields[0].split(":", maxsplit=1)[0]
        try:
            count = int(fields[2])
        except ValueError as error:
            message = "go_coverage_invalid"
            raise ValueError(message) from error
        candidate = source
        while candidate:
            if candidate in hits:
                hits[candidate] += count
                break
            _, separator, candidate = candidate.partition("/")
            if not separator:
                break
    if any(count == 0 for count in hits.values()):
        _invalid("go_source_unexercised")
    return list(hits)


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
        "covered_paths": _go_covered_paths(profile, production),
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


def _v8_entry_executed(entry: dict[str, object]) -> bool:
    """Read positive execution counts from one V8 script record."""
    functions = entry.get("functions")
    if not isinstance(functions, list):
        _invalid("javascript_coverage_invalid")
    return any(
        isinstance(function, dict)
        and any(
            isinstance(block, dict) and isinstance(block.get("count"), int) and block["count"] > 0
            for block in function.get("ranges", [])
        )
        for function in functions
    )


def _javascript_covered_paths(root: Path, directory: str, production: tuple[str, ...]) -> set[str]:
    """Match owned V8 coverage artifacts to every committed production module."""
    expected = {(root / path).resolve(): path for path in production}
    observed: set[str] = set()
    artifacts = list(Path(directory).glob("coverage-*.json"))
    if not artifacts:
        _invalid("javascript_coverage_missing")
    for artifact in artifacts:
        document = json.loads(artifact.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or not isinstance(document.get("result"), list):
            _invalid("javascript_coverage_invalid")
        for entry in document["result"]:
            if not isinstance(entry, dict) or not str(entry.get("url", "")).startswith("file:"):
                continue
            path = Path(url2pathname(urlparse(entry["url"]).path)).resolve()
            if path in expected and _v8_entry_executed(entry):
                observed.add(expected[path])
    if observed != set(production):
        _invalid("javascript_source_unexercised")
    return observed


def _javascript_behavior(root: Path, subjects: tuple[CodeSubject, ...]) -> dict[str, object]:
    """Require native tests and V8 execution evidence for all production modules."""
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    tests = tuple(
        subject.path
        for subject in subjects
        if subject.is_test
        and Path(subject.path).name.endswith((".test.js", ".test.mjs", ".test.cjs"))
    )
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
        counts, failed = junit_report((junit,))
        if failed:
            _invalid("javascript_tests_failed")
        observed = _javascript_covered_paths(root, directory, production)
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
        tree, subjects = _source(root)
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

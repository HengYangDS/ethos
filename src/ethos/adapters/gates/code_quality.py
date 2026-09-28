"""Product-owned native quality evidence for tracked code carriers."""

from __future__ import annotations

import json
import re
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
from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.repository.policy.code_subjects import CodeSubject
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import go_covered_paths
from ethos.repository.policy.quality_reports import junit_report
from ethos.repository.policy.quality_reports import lcov_covered_paths


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


def _executable(root: Path, name: str) -> str:
    if (files := repository_mise_files(root)) is not None:
        return str(locked_tool(root, name, files=files))
    path = shutil.which(name)
    if path is None:
        _invalid(f"native_tool_unavailable:{name}")
    return str(Path(path).resolve())


def _native_environment(root: Path) -> dict[str, str]:
    """Enter the repository's complete locked native tool graph once per gate."""
    files = repository_mise_files(root)
    return locked_environment(root, files) if files is not None else {}


def _go_environment(native: dict[str, str]) -> dict[str, str]:
    """Use Go's content-addressed caches without network or toolchain downloads."""
    return {
        **native,
        "GOTOOLCHAIN": "local",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GOWORK": "off",
    }


def _go_packages(root: Path, native: dict[str, str]) -> list[dict[str, object]]:
    """Decode Go's concatenated package observations without a parallel parser."""
    result = run_command(
        root,
        (_executable(root, "go"), "list", "-json", "./..."),
        timeout=120,
        env=_go_environment(native),
    )
    if result.returncode:
        _invalid("go_package_scope_unavailable")
    decoder = json.JSONDecoder()
    position = 0
    packages: list[dict[str, object]] = []
    while position < len(result.stdout):
        while position < len(result.stdout) and result.stdout[position].isspace():
            position += 1
        if position == len(result.stdout):
            break
        try:
            package, position = decoder.raw_decode(result.stdout, position)
        except json.JSONDecodeError:
            _invalid("go_package_scope_invalid")
        if not isinstance(package, dict) or package.get("Error") or package.get("Incomplete"):
            _invalid("go_package_scope_invalid")
        packages.append(package)
    return packages


def _go_file_names(package: dict[str, object], key: str) -> list[str]:
    """Reject invalid native package file identities before coverage mapping."""
    files = package.get(key, [])
    if not isinstance(files, list) or any(
        not isinstance(name, str) or Path(name).name != name for name in files
    ):
        _invalid("go_package_scope_invalid")
    if key != "IgnoredGoFiles" and any(name.endswith("_test.go") for name in files):
        _invalid("go_package_scope_invalid")
    return files


def _go_package_identity(root: Path, package: dict[str, object]) -> tuple[Path, str]:
    """Bind a native package import path to a directory inside this repository."""
    directory, import_path = package.get("Dir"), package.get("ImportPath")
    if not isinstance(directory, str) or not isinstance(import_path, str) or not import_path:
        _invalid("go_package_scope_invalid")
    try:
        return Path(directory).resolve().relative_to(root.resolve()), import_path
    except ValueError:
        _invalid("go_package_scope_invalid")


def _go_package_sources(
    root: Path, production: tuple[str, ...], native: dict[str, str]
) -> dict[str, str]:
    """Use Go's selected packages, not file suffixes, as the build-scope owner."""
    sources: dict[str, str] = {}
    ignored: set[str] = set()
    tracked = set(production)
    for package in _go_packages(root, native):
        prefix, import_path = _go_package_identity(root, package)
        for key in ("GoFiles", "CgoFiles", "IgnoredGoFiles"):
            for name in _go_file_names(package, key):
                path = (prefix / name).as_posix()
                if key == "IgnoredGoFiles":
                    ignored.add(path)
                    continue
                if path not in tracked:
                    _invalid("go_package_source_untracked")
                source = f"{import_path}/{name}"
                if source in sources and sources[source] != path:
                    _invalid("go_package_scope_invalid")
                sources[source] = path
    if not sources:
        _invalid("go_behavior_source_missing")
    unlisted = tracked - set(sources.values()) - ignored
    if any(
        not any(part.startswith(("_", ".")) or part == "testdata" for part in Path(path).parts[:-1])
        for path in unlisted
    ):
        _invalid("go_source_scope_unknown")
    return sources


def _go_zero_statement_source(root: Path, path: str, output: Path, native: dict[str, str]) -> bool:
    """Ask Go's coverage instrumenter whether an omitted selected file has blocks."""
    result = run_command(
        root,
        (
            _executable(root, "go"),
            "tool",
            "cover",
            "-mode=set",
            "-var=EthosCoverageProbe",
            "-o",
            str(output),
            path,
        ),
        timeout=60,
        env=_go_environment(native),
    )
    if result.returncode or not output.is_file():
        _invalid("go_coverage_applicability_unknown")
    marker = "var EthosCoverageProbe = struct {"
    generated = output.read_text(encoding="utf-8")
    if marker not in generated:
        _invalid("go_coverage_applicability_unknown")
    match = re.match(r"\s*Count\s+\[(\d+)\]uint32", generated.rsplit(marker, 1)[1])
    if match is None:
        _invalid("go_coverage_applicability_unknown")
    return int(match.group(1)) == 0


def _go_behavior(
    root: Path, subjects: tuple[CodeSubject, ...], native: dict[str, str]
) -> dict[str, object]:
    """Require an executed test and coverage of each production Go file."""
    if not (root / "go.mod").is_file() or not any(
        subject.path.endswith("_test.go") for subject in subjects
    ):
        _invalid("go_tests_or_module_missing")
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not production:
        _invalid("go_behavior_source_missing")
    source_paths = _go_package_sources(root, production, native)
    with TemporaryDirectory(prefix="ethos-go-coverage-") as directory:
        coverage = Path(directory) / "coverage.out"
        command = (
            _executable(root, "go"),
            "test",
            "-json",
            "-coverpkg=./...",
            f"-coverprofile={coverage}",
            "-count=1",
            "./...",
        )
        result = run_command(
            root,
            command,
            timeout=300,
            env=_go_environment(native),
        )
        if result.returncode:
            message = "go_tests_failed"
            raise ProcessExecutionError(
                message,
                reason="native_test_failed",
                command=command,
                cwd=root.as_posix(),
                cause=result.stderr[-4096:],
                observation={
                    "exit_code": result.returncode,
                    "stdout_tail": result.stdout[-4096:],
                },
            )
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
        observed_sources = {line.partition(":")[0] for line in profile[1:]}
        missing = [path for source, path in source_paths.items() if source not in observed_sources]
        zero_statement_paths = frozenset(
            path
            for index, path in enumerate(missing)
            if _go_zero_statement_source(root, path, Path(directory) / f"scope-{index}.go", native)
        )
        covered = go_covered_paths(
            profile, production, source_paths, zero_statement_paths=zero_statement_paths
        )
    return {
        "language": "go",
        "tests_passed": passes,
        "covered_paths": covered,
        "non_applicable_paths": [path for path in production if path not in covered],
    }


def _go_static(root: Path, paths: tuple[str, ...], native: dict[str, str]) -> dict[str, object]:
    if not (root / "go.mod").is_file():
        _invalid("go_module_missing")
    formatted = run_command(
        root, (_executable(root, "gofmt"), "-l", *paths), timeout=60, env=native
    )
    if formatted.returncode or formatted.stdout.strip():
        _invalid("go_format_diagnostics")
    vetted = run_command(
        root,
        (_executable(root, "go"), "vet", "./..."),
        timeout=300,
        env=_go_environment(native),
    )
    if vetted.returncode:
        _invalid("go_vet_diagnostics")
    return {"language": "go", "checked_paths": len(paths)}


def _javascript_behavior(
    root: Path, subjects: tuple[CodeSubject, ...], native: dict[str, str]
) -> dict[str, object]:
    """Use one product-owned Node test run for cases and per-module coverage."""
    if not (root / "package.json").is_file():
        _invalid("javascript_package_missing")
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not tests or not production:
        _invalid("javascript_tests_or_sources_missing")
    with TemporaryDirectory(prefix="ethos-javascript-coverage-") as directory:
        junit = Path(directory) / "junit.xml"
        lcov = Path(directory) / "coverage.lcov"
        result = run_command(
            root,
            (
                _executable(root, "node"),
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
    node = _executable(root, "node")
    for path in paths:
        result = run_command(root, (node, "--check", path), timeout=60, env=native)
        if result.returncode:
            _invalid("javascript_syntax_diagnostics")
    return {"language": "javascript", "checked_paths": len(paths)}


def _report(root: Path, axis: str) -> dict[str, object]:
    try:
        tree, subjects = _source(root)
        languages = {subject.language for subject in subjects}
        tool_environment = _native_environment(root) if languages & {"go", "javascript"} else {}
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
                    _go_behavior(root, language_subjects, tool_environment)
                    if axis == "behavior"
                    else _go_static(root, paths, tool_environment)
                )
            elif language == "javascript":
                native.append(
                    _javascript_behavior(root, language_subjects, tool_environment)
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


def behavior_report(root: Path) -> dict[str, object]:
    """Require non-vacuous native tests for every observed code language."""
    return _report(root, "behavior")


def static_report(root: Path) -> dict[str, object]:
    """Require native static diagnostics for every observed code language."""
    return _report(root, "static-analysis")

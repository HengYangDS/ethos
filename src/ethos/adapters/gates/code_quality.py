"""Product-owned native quality evidence for tracked code carriers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Never

from ethos.adapters.gates.javascript.analysis import static_observation
from ethos.adapters.gates.javascript.behavior import behavior_observation
from ethos.adapters.gates.native.evidence import native_report
from ethos.adapters.gates.python_quality import behavior_report as python_behavior_report
from ethos.adapters.gates.python_quality import static_report as python_static_report
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.quality_reports import go_covered_paths

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.repository.policy.code_subjects import CodeSubject


# Languages each axis can judge with ETHOS's own native checks.
_CHECKED = {
    "behavior": frozenset({"python", "go", "javascript"}),
    "static-analysis": frozenset({"python", "go", "javascript", "script"}),
}


def _invalid(reason: str) -> Never:
    """Reject an unproved native quality observation."""
    raise ValueError(reason)


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


def _native_environment(root: Path, scope: ExitStack) -> dict[str, str]:
    """Enter the repository's complete locked native tool graph once per gate."""
    files = repository_mise_files(root)
    return scope.enter_context(locked_environment(root, files)) if files is not None else {}


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
        remove_env_prefixes=("MISE_",),
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
        remove_env_prefixes=("MISE_",),
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
            remove_env_prefixes=("MISE_",),
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
        root,
        (_executable(root, "gofmt"), "-l", *paths),
        timeout=60,
        env=native,
        remove_env_prefixes=("MISE_",),
    )
    if formatted.returncode or formatted.stdout.strip():
        _invalid("go_format_diagnostics")
    vetted = run_command(
        root,
        (_executable(root, "go"), "vet", "./..."),
        timeout=300,
        env=_go_environment(native),
        remove_env_prefixes=("MISE_",),
    )
    if vetted.returncode:
        _invalid("go_vet_diagnostics")
    return {"language": "go", "checked_paths": len(paths)}


def _script_static(root: Path, paths: tuple[str, ...], native: dict[str, str]) -> dict[str, object]:
    """Observe supported script dialects with native ShellCheck, without running source."""
    command = (_executable(root, "shellcheck"), "--norc", "--format=json1", "--", *paths)
    result = run_command(root, command, timeout=60, env=native)
    document = json.loads(result.stdout)
    if not isinstance(document, dict) or not isinstance(document.get("comments"), list):
        _invalid("script_static_report_invalid")
    findings = document["comments"]
    if any(
        not isinstance(finding, dict)
        or finding.get("file") not in paths
        or not isinstance(finding.get("code"), int)
        or not isinstance(finding.get("message"), str)
        for finding in findings
    ):
        _invalid("script_static_report_invalid")
    return {
        "language": "script",
        "tool": "shellcheck",
        "verdict": "block" if result.returncode or result.stderr or findings else "pass",
        "checked_paths": list(paths),
        "argv": list(command),
        "cwd": str(root),
        "findings": findings,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


def _python_observation(
    root: Path,
    subjects: tuple[CodeSubject, ...],
    axis: str,
    execution: NativeExecution | None,
) -> dict[str, object]:
    """Bind a native Python result to the exact scope selected by the common classifier."""
    report = (
        python_behavior_report(root, execution=execution)
        if axis == "behavior"
        else python_static_report(root, execution=execution)
    )
    expected = [
        subject.path for subject in subjects if axis != "behavior" or subject.requires_behavior
    ]
    selected = report.get("quality_evidence")
    if report.get("verdict") == "pass" and (
        not isinstance(selected, dict) or selected.get("selected_paths") != expected
    ):
        _invalid("python_quality_unproven")
    return {"language": "python", **report}


def _claims(axis: str, tree: str, subjects: tuple[CodeSubject, ...]) -> dict[str, object]:
    """Claim the applicable files in languages ETHOS checked; list the rest as unclaimed."""
    applicable = tuple(
        subject for subject in subjects if axis != "behavior" or subject.requires_behavior
    )
    claimed = tuple(subject for subject in applicable if subject.language in _CHECKED[axis])
    unclaimed = [subject.path for subject in applicable if subject not in claimed]
    authored = [subject.path for subject in claimed if subject.requires_authored_analysis]
    artifacts = [subject.path for subject in claimed if not subject.requires_authored_analysis]
    return {
        "quality_evidence": {
            "axis": axis,
            "source_tree": tree,
            "selected_paths": [subject.path for subject in claimed],
            **(
                {"authored_paths": authored, "artifact_paths": artifacts}
                if axis == "static-analysis" and artifacts
                else {}
            ),
        },
        **({"unclaimed_paths": unclaimed} if unclaimed else {}),
    }


def _checked_languages(axis: str, subjects: tuple[CodeSubject, ...]) -> set[str]:
    """Select the observed languages ETHOS checks; the rest stay for a native contributor."""
    if not subjects:
        _invalid("code_sources_missing")
    observed = (
        {subject.language for subject in subjects if subject.requires_behavior or subject.is_test}
        if axis == "behavior"
        else {subject.language for subject in subjects if subject.requires_authored_analysis}
    )
    languages = observed & _CHECKED[axis]
    if observed and not languages:
        _invalid(f"native_language_unsupported:{min(observed)}")
    return languages


def _report(
    root: Path,
    axis: str,
    *,
    execution: NativeExecution | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    try:
        if execution is not None and execution.evidence is not None:
            return native_report(root, execution, axis)
        tree, subjects = observe_quality_subjects(root)
        languages = _checked_languages(axis, subjects)
        with ExitStack() as scope:
            scope.enter_context(command_scope(timeout_seconds=timeout_seconds))
            tool_environment = (
                _native_environment(root, scope)
                if languages & {"go", "javascript", "script"}
                else {}
            )
            native: list[dict[str, object]] = []
            for language in sorted(languages):
                language_subjects = tuple(
                    subject for subject in subjects if subject.language == language
                )
                authored = tuple(
                    subject.path
                    for subject in language_subjects
                    if subject.requires_authored_analysis
                )
                if language == "python":
                    native.append(_python_observation(root, language_subjects, axis, execution))
                elif language == "go":
                    native.append(
                        _go_behavior(root, language_subjects, tool_environment)
                        if axis == "behavior"
                        else _go_static(root, authored, tool_environment)
                    )
                elif language == "javascript":
                    native.append(
                        behavior_observation(
                            root,
                            language_subjects,
                            execution,
                            _executable(root, "node"),
                            tool_environment,
                            timeout_seconds=timeout_seconds,
                        )
                        if axis == "behavior"
                        else static_observation(
                            root,
                            authored,
                            node=_executable(root, "node"),
                            native=tool_environment,
                        )
                    )
                else:
                    native.append(_script_static(root, authored, tool_environment))
            observe_quality_subjects(root, expected_tree=tree)
    except ProcessExecutionError as error:
        return {**_failure(axis, error.code), "diagnostics": [error.evidence()]}
    except (OSError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        return _failure(axis, str(error) if isinstance(error, ValueError) else type(error).__name__)
    if any(report.get("verdict") in {"block", "unknown"} for report in native):
        gaps = tuple(
            gap for report in native for gap in string_sequence(report.get("required_gaps"))
        )
        return {
            "verdict": "block",
            "state": "unproven",
            "required_gaps": list(
                dict.fromkeys(
                    gap if gap.startswith("quality_") else f"quality_{axis}_{gap}" for gap in gaps
                )
            )
            or [f"quality_{axis}_native_diagnostics"],
            "native": native,
        }
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "native": native,
        **_claims(axis, tree, subjects),
    }


def behavior_report(
    root: Path, *, execution: NativeExecution | None = None, timeout_seconds: float | None = None
) -> dict[str, object]:
    """Require non-vacuous native tests for every observed code language."""
    return _report(root, "behavior", execution=execution, timeout_seconds=timeout_seconds)


def static_report(root: Path, *, execution: NativeExecution | None = None) -> dict[str, object]:
    """Require native static diagnostics for every observed code language."""
    return _report(root, "static-analysis", execution=execution)

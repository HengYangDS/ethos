"""Observe Go-native package, execution and coverage identities at one owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Never

from ethos.adapters.gates.execution import native_tool
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.gates.verification import NativeGoReports
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import go_covered_paths
from ethos.repository.policy.quality_reports import go_test_report

if TYPE_CHECKING:
    from ethos.repository.policy.code_subjects import CodeSubject


def _invalid(reason: str) -> Never:
    """Reject missing or inconsistent native observation evidence."""
    raise ValueError(reason)


def _environment(native: dict[str, str]) -> dict[str, str]:
    """Use Go's content-addressed caches without network or toolchain downloads."""
    return {
        **native,
        "GOTOOLCHAIN": "local",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GOWORK": "off",
    }


def _packages(root: Path, native: dict[str, str]) -> list[dict[str, object]]:
    """Decode Go's concatenated package observations without a parallel parser."""
    result = run_command(
        root,
        (native_tool(root, "go"), "list", "-json", "./..."),
        timeout=120,
        env=_environment(native),
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


def _file_names(package: dict[str, object], key: str) -> list[str]:
    """Reject invalid native package file identities before coverage mapping."""
    files = package.get(key, [])
    if not isinstance(files, list) or any(
        not isinstance(name, str) or Path(name).name != name for name in files
    ):
        _invalid("go_package_scope_invalid")
    if key != "IgnoredGoFiles" and any(name.endswith("_test.go") for name in files):
        _invalid("go_package_scope_invalid")
    return files


def _package_identity(root: Path, package: dict[str, object]) -> tuple[Path, str]:
    """Bind a native package import path to a directory inside this repository."""
    directory, import_path = package.get("Dir"), package.get("ImportPath")
    if not isinstance(directory, str) or not isinstance(import_path, str) or not import_path:
        _invalid("go_package_scope_invalid")
    try:
        return Path(directory).resolve().relative_to(root.resolve()), import_path
    except ValueError:
        _invalid("go_package_scope_invalid")


def _package_sources(
    root: Path, production: tuple[str, ...], native: dict[str, str]
) -> dict[str, str]:
    """Use Go's selected packages, not file suffixes, as the build-scope owner."""
    sources: dict[str, str] = {}
    ignored: set[str] = set()
    tracked = set(production)
    for package in _packages(root, native):
        prefix, import_path = _package_identity(root, package)
        for key in ("GoFiles", "CgoFiles", "IgnoredGoFiles"):
            for name in _file_names(package, key):
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


def _zero_statement_source(root: Path, path: str, output: Path, native: dict[str, str]) -> bool:
    """Ask Go's coverage instrumenter whether an omitted selected file has blocks."""
    result = run_command(
        root,
        (
            native_tool(root, "go"),
            "tool",
            "cover",
            "-mode=set",
            "-var=EthosCoverageProbe",
            "-o",
            str(output),
            path,
        ),
        timeout=60,
        env=_environment(native),
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


def _test_frame(command: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Recognize a native test command without guessing an opaque producer's effects."""
    offset = 0
    if command and Path(command[0]).name in {"mise", "mise.exe"}:
        if command[1:4] != ("exec", "--locked", "--"):
            _invalid("go_native_command_unsupported")
        offset = 4
    selected = command[offset:]
    if len(selected) < 2 or Path(selected[0]).name not in {"go", "go.exe"} or selected[1] != "test":
        _invalid("go_native_command_unsupported")
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    for flag in ("-json", "-v", "-race", "-short", "-failfast"):
        parser.add_argument(flag, action="store_true")
    for flag in ("-count", "-covermode", "-parallel", "-timeout", "-run", "-shuffle"):
        parser.add_argument(flag)
    parser.add_argument("packages", nargs="*")
    try:
        arguments, unknown = parser.parse_known_args(selected[2:])
    except argparse.ArgumentError as error:
        _invalid(f"go_native_command_unsupported:{error}")
    if unknown or arguments.packages != ["./..."] or arguments.count not in {None, "1"}:
        _invalid("go_native_command_unsupported")
    return command[: offset + 1], selected[2:]


def preflight(root: Path, command: tuple[str, ...]) -> None:
    """Reject unbound tools and unsupported producers before the native test starts."""
    prefix, _ = _test_frame(command)
    actual = shutil.which(prefix[-1])
    expected = native_tool(root, "go")
    if actual is None or Path(actual).resolve() != Path(expected).resolve():
        _invalid("go_native_toolchain_unbound")


def prepare(
    root: Path, command: tuple[str, ...], output: Path, native: dict[str, str]
) -> tuple[tuple[str, ...], dict[str, str], NativeGoReports]:
    """Bind native package scope and instrument the declared single attempt."""
    prefix, arguments = _test_frame(command)
    production = tuple(
        subject.path
        for subject in observed_code_subjects(tuple(git_files(root)))
        if subject.language == "go" and not subject.is_test
    )
    source_paths = _package_sources(root, production, native)
    output.mkdir(exist_ok=True)
    argv = (
        *prefix,
        "test",
        "-json",
        "-coverpkg=./...",
        f"-coverprofile={output / 'coverage.out'}",
        "-count=1",
        *arguments,
    )
    paths = tuple(git_files(root, "*.go"))
    paths += tuple(
        path for path in ("go.mod", "go.sum", "go.work", "go.work.sum") if (root / path).is_file()
    )
    return (
        argv,
        _environment(native),
        NativeGoReports(
            root=output,
            source_digests=tuple(
                (path, hashlib.sha256((root / path).read_bytes()).hexdigest()) for path in paths
            ),
            command=argv,
            source_paths=tuple(source_paths.items()),
        ),
    )


def _evidence(
    root: Path, production: tuple[str, ...], native: dict[str, str], execution: NativeExecution
) -> dict[str, object]:
    """Consume held test output and coverage; the verifier never replays the attempt."""
    inputs = execution.reports
    if not isinstance(inputs, NativeGoReports):
        _invalid("go_native_evidence_unavailable")
    if execution.cwd != root.resolve() or execution.argv != inputs.command:
        _invalid("go_native_execution_frame_invalid")
    if inputs.root.is_symlink() or not inputs.root.is_dir():
        _invalid("go_native_report_root_invalid")
    if any(
        hashlib.sha256((root / path).read_bytes()).hexdigest() != digest
        for path, digest in inputs.source_digests
    ):
        _invalid("go_native_source_inputs_changed")
    tests = go_test_report(execution.stdout)
    if execution.exit_code or tests.failures:
        message = "go_tests_failed"
        raise ProcessExecutionError(
            message,
            reason="native_test_failed",
            command=execution.argv,
            cwd=root.as_posix(),
            cause=execution.stderr[-4096:],
            observation={
                "exit_code": execution.exit_code,
                "stdout_tail": execution.stdout[-4096:],
                "go_test_report_valid": tests.valid,
                "go_test_failures": [asdict(failure) for failure in tests.failures],
            },
        )
    coverage = inputs.root / "coverage.out"
    if coverage.is_symlink() or not coverage.is_file():
        _invalid("go_coverage_missing")
    if not tests.valid:
        _invalid("go_test_report_invalid")
    if tests.passed == 0:
        _invalid("go_tests_unexecuted")
    source_paths = dict(inputs.source_paths)
    profile = coverage.read_text(encoding="utf-8").splitlines()
    observed_sources = {line.partition(":")[0] for line in profile[1:]}
    missing = [path for source, path in source_paths.items() if source not in observed_sources]
    zero_statement_paths = frozenset(
        path
        for index, path in enumerate(missing)
        if _zero_statement_source(root, path, inputs.root / f"scope-{index}.go", native)
    )
    covered = go_covered_paths(
        profile, production, source_paths, zero_statement_paths=zero_statement_paths
    )
    return {
        "language": "go",
        "tests_passed": tests.passed,
        "covered_paths": covered,
        "non_applicable_paths": [path for path in production if path not in covered],
    }


def behavior(
    root: Path,
    subjects: tuple[CodeSubject, ...],
    native: dict[str, str],
    execution: NativeExecution | None = None,
) -> dict[str, object]:
    """Execute only for a provider-owned gate; otherwise observe its single native attempt."""
    if not (root / "go.mod").is_file() or not any(
        subject.path.endswith("_test.go") for subject in subjects
    ):
        _invalid("go_tests_or_module_missing")
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not production:
        _invalid("go_behavior_source_missing")
    if execution is not None:
        return _evidence(root, production, native, execution)
    with TemporaryDirectory(prefix="ethos-go-coverage-") as directory:
        command, environment, inputs = prepare(
            root, (native_tool(root, "go"), "test", "-count=1", "./..."), Path(directory), native
        )
        result = run_command(
            root,
            command,
            timeout=300,
            env=environment,
            remove_env_prefixes=("MISE_",),
        )
        return _evidence(
            root,
            production,
            native,
            NativeExecution(
                declared_identity=command,
                argv=command,
                cwd=root.resolve(),
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                reports=inputs,
            ),
        )


def static_report(root: Path, paths: tuple[str, ...], native: dict[str, str]) -> dict[str, object]:
    if not (root / "go.mod").is_file():
        _invalid("go_module_missing")
    formatted = run_command(
        root,
        (native_tool(root, "gofmt"), "-l", *paths),
        timeout=60,
        env=native,
        remove_env_prefixes=("MISE_",),
    )
    if formatted.returncode or formatted.stdout.strip():
        _invalid("go_format_diagnostics")
    vetted = run_command(
        root,
        (native_tool(root, "go"), "vet", "./..."),
        timeout=300,
        env=_environment(native),
        remove_env_prefixes=("MISE_",),
    )
    if vetted.returncode:
        _invalid("go_vet_diagnostics")
    return {"language": "go", "checked_paths": len(paths)}

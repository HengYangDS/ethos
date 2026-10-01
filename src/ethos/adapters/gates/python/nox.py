"""Prepare and consume Nox's native same-attempt test evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Never

import ethos.adapters.gates.python.coverage as native_coverage
from ethos.adapters.gates.python.static import prepare_capture
from ethos.adapters.gates.verification import NativePythonReports
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import junit_report

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution


_NATIVE_ATTEMPT = """
import inspect,json,runpy,sys
from pathlib import Path
import coverage
from nox import tasks
from nox import command as native_command
from nox.sessions import SessionRunner

selection = Path(sys.argv.pop(1))
capture_static = sys.argv.pop(1) == 'static'
native_run_manifest = tasks.run_manifest
native_execute = SessionRunner.execute
native_popen = native_command.popen
command_records = []


def capture_command(args, **kwargs):
    code, output = native_popen(args, **kwargs)
    command_records.append({'argv': list(args), 'cwd': str(Path.cwd().resolve()),
                            'session': kwargs.get('env', {}).get('NOX_CURRENT_SESSION', ''),
                            'exit_code': code})
    (selection.parent / 'commands.json').write_text(json.dumps(command_records))
    return code, output


def measure_session(session):
    collector = coverage.Coverage.current()
    previous = collector.switch_context(session.friendly_name) if collector is not None else None
    try:
        return native_execute(session)
    finally:
        if collector is not None:
            collector.switch_context(previous or '')


def retain_scope(manifest, global_config):
    selected = [session for session, included in manifest.list_all_sessions() if included]
    root = Path.cwd().resolve()
    origins = [global_config.noxfile, *(inspect.getsourcefile(inspect.unwrap(session.func))
                for session in selected)]
    orchestrators = sorted({str(Path(origin).resolve().relative_to(root))
                           for origin in origins
                           if origin and Path(origin).resolve().is_relative_to(root)})
    selection.write_text(json.dumps({
        'names': [session.friendly_name for session in selected],
        'signatures': [signature for session in selected for signature in session.signatures],
        'orchestrators': orchestrators,
    }))
    return native_run_manifest(manifest, global_config=global_config)


tasks.run_manifest = retain_scope
SessionRunner.execute = measure_session
if capture_static:
    native_command.popen = capture_command
    import runpy as native_runpy
    static = native_runpy.run_path(str(selection.parent / 'static-adapter.py'))
    native_command.run = static['capture_run'](native_command.run, selection.parent)
runpy.run_module('nox', run_name='__main__')
"""


_NATIVE_PREREQUISITES = """
import json,sys
import nox,coverage
from nox._options import options
from coverage.tracer import CTracer
try:
    config = options.parse_args(sys.argv[1:])
    provenance = config.provenance('envdir')
    conflict = (config.report is not None or provenance != type(provenance).DEFAULT
                or config.install_only or config.list_sessions or config.usage
                or config.help or config.version or (config.parallel or 1) > 1)
    print(json.dumps({'conflict': bool(conflict), 'coverage': coverage.__version__}))
except SystemExit:
    print(json.dumps({'invalid': True}))
"""


def _invalid(reason: str) -> Never:
    """Reject an unsupported or inconsistent native evidence contract."""
    raise ValueError(reason)


def requires_reports(root: Path, references: tuple[str, ...]) -> bool:
    """Select report preparation for the existing native Python verifier entries."""
    return bool(
        set(references)
        & {
            "ethos.adapters.gates.python_quality:behavior_report",
            "ethos.adapters.gates.code_quality:behavior_report",
            "ethos.adapters.gates.python_quality:static_report",
            "ethos.adapters.gates.code_quality:static_report",
        }
    ) and any(
        subject.language == "python" for subject in observed_code_subjects(tuple(git_files(root)))
    )


def _prefix(command: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Resolve supported native Nox entry forms without searching command text."""
    offset = 0
    if command and Path(command[0]).name in {"mise", "mise.exe"}:
        if command[1:4] != ("exec", "--locked", "--"):
            _invalid("python_nox_command_unsupported")
        offset = 4
    if offset < len(command) and Path(command[offset]).name in {"uv", "uv.exe"}:
        return _uv_prefix(command, offset)
    if command[offset + 1 : offset + 3] == ("-m", "nox"):
        return command[: offset + 1], command[offset + 3 :]
    _invalid("python_nox_command_unsupported")


def _uv_prefix(command: tuple[str, ...], offset: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Resolve supported uv argv grammar while preserving option values and module selection."""
    if command[offset + 1 : offset + 2] != ("run",):
        _invalid("python_nox_command_unsupported")
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False, exit_on_error=False)
    for flag in ("--locked", "--frozen", "--no-sync", "--offline", "--no-dev", "--no-editable"):
        parser.add_argument(flag, action="store_true")
    for flag in ("--python", "--group", "--extra"):
        parser.add_argument(flag)
    parser.add_argument("entry", nargs=argparse.REMAINDER)
    try:
        selected, unknown = parser.parse_known_args(command[offset + 2 :])
    except argparse.ArgumentError as error:
        _invalid(f"python_nox_command_unsupported:{error}")
    if unknown or not selected.entry:
        _invalid("python_nox_command_unsupported")
    if not selected.locked:
        _invalid("python_nox_command_unlocked")
    entry = tuple(selected.entry)
    start = len(command) - len(entry)
    if entry[0] == "nox":
        return (*command[:start], "python"), entry[1:]
    if entry[1:3] == ("-m", "nox"):
        return command[: start + 1], entry[3:]
    _invalid("python_nox_command_unsupported")


def preflight(root: Path, command: tuple[str, ...]) -> None:
    """Verify native measurement supply before the selected test command starts."""
    prefix, arguments = _prefix(command)
    result = run_command(
        root,
        (*prefix, "-B", "-I", "-c", _NATIVE_PREREQUISITES, *arguments),
        timeout=30,
    )
    if result.returncode:
        _invalid("python_nox_measurement_supply_unavailable")
    observation = json.loads(result.stdout)
    if not isinstance(observation, dict) or observation.get("invalid"):
        _invalid("python_nox_command_unsupported")
    if observation.get("conflict"):
        _invalid("python_nox_output_selection_conflict")


def prepare(
    root: Path, command: tuple[str, ...], output: Path, *, references: tuple[str, ...] = ()
) -> tuple[tuple[str, ...], dict[str, str], NativePythonReports]:
    """Use native Nox session and Coverage process mechanisms in one owned root."""
    prefix, arguments = _prefix(command)
    output.mkdir(exist_ok=True)
    attempt = output / "nox-attempt.py"
    attempt.write_text(_NATIVE_ATTEMPT, encoding="utf-8")
    config = output / "coverage.toml"
    config.write_text(
        "[tool.coverage.run]\nbranch = true\nparallel = true\n"
        "core = 'ctrace'\ncontext = '${NOX_CURRENT_SESSION-}'\n"
        f"data_file = {json.dumps(str(output / '.coverage'))}\n",
        encoding="utf-8",
    )
    report_argument = shlex.join((f"--junitxml={output}/${{NOX_CURRENT_SESSION}}.xml",))
    environment = {
        "PYTEST_ADDOPTS": f"{os.environ.get('PYTEST_ADDOPTS', '')} {report_argument}".strip(),
        "COVERAGE_FILE": str(output / ".coverage"),
        "COVERAGE_RCFILE": str(config),
        "COVERAGE_PROCESS_START": str(config),
    }
    capture_static = any(reference.endswith(":static_report") for reference in references)
    if capture_static:
        prepare_capture(output)
    return (
        (
            *prefix,
            "-B",
            str(attempt),
            str(output / "selection.json"),
            "static" if capture_static else "behavior",
            "--envdir",
            str(output / "environments"),
            "--report",
            str(output / "nox.json"),
            *arguments,
        ),
        environment,
        NativePythonReports(
            root=output,
            source_digests=tuple(
                (path, hashlib.sha256((root / path).read_bytes()).hexdigest())
                for path in git_files(root)
                if capture_static or path.endswith(".py")
            ),
            python_prefix=prefix,
            packaged_sources=native_coverage.artifact_sources(root, prefix),
        ),
    )


def session_evidence(
    output: Path,
    expected: tuple[str, ...],
    exit_code: int,
    *,
    names: tuple[str, ...] = (),
    require_tests: bool = True,
) -> dict[str, object]:
    """Reduce each native session and JUnit once without replaying test commands."""
    native_report = output / "nox.json"
    if native_report.is_symlink() or not native_report.is_file():
        _invalid("python_nox_session_report_missing")
    report = json.loads(native_report.read_text())
    sessions = report.get("sessions") if isinstance(report, dict) else None
    if (
        not isinstance(sessions, list)
        or not sessions
        or any(not isinstance(item, dict) for item in sessions)
    ):
        _invalid("python_nox_session_report_invalid")
    signatures = [item.get("signatures") for item in sessions]
    if any(
        not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or not value for value in values)
        for values in signatures
    ):
        _invalid("python_nox_session_report_invalid")
    actual = [signature for values in signatures for signature in values]
    identities = [values[0] for values in signatures]
    if (
        len(identities) != len(set(identities))
        or sorted(actual) != sorted(expected)
        or (names and sorted(identities) != sorted(names))
    ):
        _invalid("python_nox_session_scope_incomplete")
    if any(item.get("result") != "success" for item in sessions) or exit_code:
        _invalid("python_nox_session_failed")
    if not require_tests:
        return {"sessions": actual}
    return {"tests": _test_counts(output, names or expected), "sessions": actual}


def _test_counts(output: Path, names: tuple[str, ...]) -> dict[str, int]:
    """Observe complete native test-session reports after session identity admission."""
    junit = tuple(output / f"{name}.xml" for name in names)
    if any(not path.is_file() or path.is_symlink() for path in junit):
        _invalid("python_nox_junit_missing")
    counts: dict[str, int] = {}
    for path in junit:
        session_counts, failed = junit_report((path,))
        if failed:
            _invalid("python_nox_tests_failed")
        for key, value in session_counts.items():
            counts[key] = counts.get(key, 0) + value
    return counts


def selection(output: Path) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Read the native selected manifest retained in the same process before execution."""
    path = output / "selection.json"
    if path.is_symlink() or not path.is_file():
        _invalid("python_nox_session_selection_missing")
    selection = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(selection, dict):
        _invalid("python_nox_session_selection_invalid")
    result: list[tuple[str, ...]] = []
    for key in ("signatures", "names"):
        values = selection.get(key)
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) or not value for value in values)
            or (key == "names" and len(values) != len(set(values)))
            or any(value in {".", ".."} or any(c in value for c in "/\\\x00") for value in values)
        ):
            _invalid("python_nox_session_selection_invalid")
        result.append(tuple(values))
    orchestrators = selection.get("orchestrators")
    if not isinstance(orchestrators, list) or any(
        not isinstance(path, str)
        or Path(path).is_absolute()
        or any(part in {"", ".", ".."} for part in path.split("/"))
        for path in orchestrators
    ):
        _invalid("python_nox_session_selection_invalid")
    return result[0], result[1], tuple(orchestrators)


def evidence(root: Path, execution: NativeExecution, source: tuple[str, ...]) -> dict[str, object]:
    """Require fresh native session results, JUnit and positive source execution."""
    inputs = execution.reports
    if not isinstance(inputs, NativePythonReports):
        _invalid("python_native_evidence_unavailable")
    output = inputs.root
    if output.is_symlink() or not output.is_dir() or execution.cwd != root.resolve():
        _invalid("python_nox_report_root_invalid")
    if execution.argv[: len(inputs.python_prefix)] != inputs.python_prefix:
        _invalid("python_nox_execution_frame_invalid")
    expected, names, orchestrators = selection(output)
    sessions = session_evidence(output, expected, execution.exit_code, names=names)
    coverage = native_coverage.observe(
        root, inputs, source, sessions=names, orchestrators=orchestrators
    )
    source_digests = dict(inputs.source_digests)
    return {
        **sessions,
        "coverage": {key: value for key, value in coverage.items() if key != "files"},
        "source_digests": {path: source_digests[path] for path in source},
    }

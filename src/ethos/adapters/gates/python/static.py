"""Capture native Ruff observations within one Nox attempt, never a replacement check."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.verification import NativePythonReports

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution


def capture_run(native_run, output):
    """Decorate the native command seam only for a recognized Ruff lint command."""
    observations = []

    def capture(args, **kwargs):
        arguments = tuple(map(str, args))
        offset = 1 if Path(arguments[0]).name in {"ruff", "ruff.exe"} else 3
        if (offset == 3 and arguments[1:3] != ("-m", "ruff")) or arguments[offset : offset + 1] != (
            "check",
        ):
            return native_run(args, **kwargs)
        if any(
            argument.partition("=")[0]
            in {
                "--fix",
                "--fix-only",
                "--diff",
                "--watch",
                "-w",
                "--statistics",
                "--show-files",
                "--show-settings",
                "--add-noqa",
                "--add-ignore",
                "--silent",
                "-s",
                "--output-file",
                "-o",
                "--output-format",
            }
            for argument in arguments
        ):
            message = "python_static_command_unsupported"
            raise ValueError(message)
        index = len(observations)
        report = output / f"ruff-{index}.json"
        files = output / f"ruff-{index}.files"
        settings = output / f"ruff-{index}.settings"
        record = {
            "argv": list(arguments),
            "cwd": str(Path.cwd().resolve()),
            "report": report.name,
            "files": files.name,
            "settings": settings.name,
            "completed": False,
        }
        observations.append(record)
        command = (*args, "--no-fix", "--no-fix-only")

        def retain():
            (output / "static.json").write_text(json.dumps(observations))

        retain()
        try:
            invocation = {**kwargs, "silent": True}
            result = native_run(
                (*command, "--output-format=json", f"--output-file={report}"), **invocation
            )
            record["diagnostic_output"] = result
            if isinstance(result, str) and result:
                print(result, end="", file=sys.stderr)
            record["completed"] = True
            return result
        finally:
            if report.is_file():
                options = {**kwargs, "success_codes": (0,), "silent": True}
                native_run((*command, "--show-files", f"--output-file={files}"), **options)
                configuration = native_run((*command, "--show-settings"), **options)
                settings.write_text(configuration)
                record["digests"] = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (report, files, settings)
                }
            retain()

    return capture


def prepare_capture(output: Path) -> None:
    """Materialize the installed capture implementation, not a copied interpreter."""
    (output / "static-adapter.py").write_text(
        "from pathlib import Path\nimport json,hashlib,sys\n\n" + inspect.getsource(capture_run),
        encoding="utf-8",
    )


def _report_paths(output: Path, record: dict[str, object]) -> tuple[Path, Path, Path]:
    """Keep every recorded report inside the exact owned attempt root."""
    paths = []
    for key in ("report", "files", "settings"):
        name = record.get(key)
        if not isinstance(name, str) or Path(name).name != name:
            message = "python_static_report_invalid"
            raise ValueError(message)
        candidate = output / name
        if candidate.is_symlink() or not candidate.is_file():
            message = "python_static_report_invalid"
            raise ValueError(message)
        paths.append(candidate)
    return paths[0], paths[1], paths[2]


def _checked_paths(root: Path, output: Path, record: dict[str, object]) -> set[str]:
    """Native diagnostics and effective rules qualify the native selected paths."""
    if record.get("completed") is not True or record.get("cwd") != str(root.resolve()):
        message = "python_static_execution_invalid"
        raise ValueError(message)
    if record.get("diagnostic_output") not in (None, ""):
        message = "python_static_native_warning"
        raise ValueError(message)
    report, files, settings = _report_paths(output, record)
    digests = record.get("digests")
    if not isinstance(digests, dict) or any(
        hashlib.sha256(path.read_bytes()).hexdigest() != digests.get(path.name)
        for path in (report, files, settings)
    ):
        message = "python_static_report_changed"
        raise ValueError(message)
    findings = json.loads(report.read_text())
    if not isinstance(findings, list) or findings:
        message = "python_static_diagnostics"
        raise ValueError(message)
    configuration = settings.read_text()
    if "linter.rules.enabled = [" not in configuration or re.search(
        r"linter\.rules\.enabled = \[\s*\]", configuration
    ):
        message = "python_static_rules_disabled"
        raise ValueError(message)
    return {
        candidate.relative_to(root.resolve()).as_posix()
        for name in files.read_text().splitlines()
        if (candidate := Path(name).resolve()).is_relative_to(root.resolve())
    }


def _command_evidence(output: Path) -> None:
    """Native child return codes survive a session's relaxed success-code policy."""
    path = output / "commands.json"
    if path.is_symlink() or not path.is_file():
        message = "python_static_command_evidence_missing"
        raise ValueError(message)
    commands = json.loads(path.read_text())
    if (
        not isinstance(commands, list)
        or not commands
        or any(
            not isinstance(command, dict) or command.get("exit_code") != 0 for command in commands
        )
    ):
        message = "python_static_native_command_failed"
        raise ValueError(message)


def evidence(root: Path, execution: NativeExecution, paths: tuple[str, ...]) -> dict[str, object]:
    """Validate actual native diagnostics, selection and source freshness without replay."""
    inputs = execution.reports
    if not isinstance(inputs, NativePythonReports) or execution.cwd != root.resolve():
        message = "python_native_evidence_unavailable"
        raise ValueError(message)
    output = inputs.root
    if execution.argv[: len(inputs.python_prefix)] != inputs.python_prefix:
        message = "python_static_execution_frame_invalid"
        raise ValueError(message)
    record_path = output / "static.json"
    if output.is_symlink() or record_path.is_symlink() or not record_path.is_file():
        message = "python_static_evidence_missing"
        raise ValueError(message)
    records = json.loads(record_path.read_text())
    _command_evidence(output)
    if (
        not isinstance(records, list)
        or not records
        or execution.exit_code
        or any(not isinstance(record, dict) for record in records)
    ):
        message = "python_static_attempt_failed"
        raise ValueError(message)
    selected = set().union(*(_checked_paths(root, output, record) for record in records))
    if not set(paths) <= selected:
        message = "python_static_scope_incomplete"
        raise ValueError(message)
    digests = dict(inputs.source_digests)
    if any(
        hashlib.sha256((root / path).read_bytes()).hexdigest() != digests.get(path)
        for path in digests
    ):
        message = "python_static_source_changed"
        raise ValueError(message)
    return {"checked_paths": list(paths), "native_commands": [record["argv"] for record in records]}

"""Interpret original native Python reports under exact producer custody."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.git import current_tracked_head
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.quality_reports import coverage_stream_report
from ethos.repository.policy.quality_reports import junit_stream_report

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.contracts.gates import NativeOutput


class NoxSession(BaseModel):
    """Official Nox result fields retain concrete native session signatures."""

    model_config = ConfigDict(strict=True, extra="forbid")
    args: dict[str, object]
    name: str = Field(min_length=1)
    result: Literal["aborted", "failed", "success", "skipped"]
    result_code: int
    reason: str | None
    signatures: list[str] = Field(min_length=1)
    duration: float = Field(ge=0)


class NoxReport(BaseModel):
    """Nox's result is a success bit, not the subprocess return code."""

    model_config = ConfigDict(strict=True, extra="forbid")
    result: Literal[0, 1]
    sessions: list[NoxSession] = Field(min_length=1)


class PytestInvocation(BaseModel):
    """The actual checker, config and terminal result from one pytest session."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    session: str = Field(min_length=1)
    argv: list[str] = Field(min_length=1)
    root: str = Field(min_length=1)
    configuration: str = Field(min_length=1)
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    version: str = Field(min_length=1)
    warnings: list[str]
    exitstatus: int | None = Field(ge=0, le=5)

    def require(self, root: Path, output: NativeOutput) -> None:
        """Match the declared exact config, not another identical-looking file."""
        selected = root / output.configuration
        if (
            self.session != output.sessions[0]
            or Path(self.root).resolve() != root.resolve()
            or Path(self.configuration).resolve() != selected.resolve()
            or self.configuration_sha256 != hashlib.sha256(selected.read_bytes()).hexdigest()
            or self.exitstatus != 0
        ):
            msg = "python_native_pytest_invocation_unbound"
            raise ValueError(msg)


class RuffInvocation(BaseModel):
    """One original direct Ruff launch, config and terminal native output."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    session: str
    executable: str
    argv: list[str]
    cwd: str
    configuration: str
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed: bool
    launches: int = Field(ge=0)
    stdout: str
    stderr: str

    def require(self, runtime: PythonRuntime, root: Path, output: NativeOutput) -> None:
        """Explicit native config and binary must belong to the observed child."""
        selected = root / output.configuration
        expected = Path(runtime.prefix) / ("Scripts/ruff.exe" if os.name == "nt" else "bin/ruff")
        try:
            arguments = self.argv
            config = arguments[arguments.index("--config") + 1]
            used_config = Path(config) if Path(config).is_absolute() else root / config
            subjects: set[str] = set()
            for line in self.stderr.splitlines():
                _prefix, separator, path = line.partition("[ruff::diagnostics][DEBUG] Checking: ")
                if separator:
                    observed = Path(path).resolve()
                    if observed.is_relative_to(root.resolve()):
                        subjects.add(observed.relative_to(root.resolve()).as_posix())
            _, selected_subjects = observe_quality_subjects(root, language="python")
            required = {subject.path for subject in selected_subjects}
            valid = (
                self.completed
                and self.launches == 1
                and self.session == output.sessions[0]
                and Path(self.cwd).resolve() == root.resolve()
                and Path(self.executable).absolute() == expected.absolute()
                and arguments[0] == self.executable
                and arguments[1] == "check"
                and used_config.resolve() == selected.resolve()
                and Path(self.configuration).resolve() == selected.resolve()
                and self.configuration_sha256 == hashlib.sha256(selected.read_bytes()).hexdigest()
                and "--verbose" in arguments
                and f"Using user-specified configuration file at: {config}" in self.stderr
            )
        except (ValueError, IndexError, OSError):
            valid = False
        if not valid:
            msg = "python_native_static_invocation_unbound"
            raise ValueError(msg)
        if not required <= subjects:
            msg = "python_native_static_scope_incomplete"
            raise ValueError(msg)


class PythonRuntime(BaseModel):
    """Native child identity distinguishes an actual interpreter from a signature."""

    model_config = ConfigDict(strict=True, extra="forbid")
    executable: str = Field(min_length=1)
    version: list[int] = Field(min_length=3, max_length=3)
    prefix: str = Field(min_length=1)
    pytest: PytestInvocation | None = None
    ruff: RuffInvocation | None = None

    def require_checks(
        self, root: Path, output: NativeOutput, outputs: tuple[NativeOutput, ...]
    ) -> None:
        """Each selected evidence kind requires its actual same-session checker."""
        formats = {item.format for item in outputs if item.sessions == output.sessions}
        for kind, required, report in (
            ("pytest", "junit-xml", self.pytest),
            ("static", "ruff-json", self.ruff),
        ):
            if required not in formats:
                continue
            if report is None:
                msg = f"python_native_{kind}_invocation_unbound"
                raise ValueError(msg)
            if isinstance(report, PytestInvocation):
                report.require(root, output)
            else:
                report.require(self, root, output)

    def observe(self) -> None:
        """Qualify interpreter liveness before its owned environment is released."""
        executable, prefix = Path(self.executable), Path(self.prefix)
        if (
            not executable.is_absolute()
            or not prefix.is_absolute()
            or not executable.is_file()
            or not os.access(executable, os.X_OK)
            or not prefix.is_dir()
            or not executable.is_relative_to(prefix)
        ):
            msg = "python_native_toolchain_unbound"
            raise ValueError(msg)

    def qualify(self, root: Path, output: NativeOutput, *, deadline: float) -> bytes:
        """Observe the locked dependency floor; do not authenticate extra product bytes."""
        self.observe()
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired((self.executable,), 0)
        groups = output.dependency_groups
        if groups is None:
            msg = "python_native_dependency_floor_unbound"
            raise ValueError(msg)
        if not (root / "pyproject.toml").is_file() or not (root / "uv.lock").is_file():
            msg = "python_native_lock_missing"
            raise ValueError(msg)
        command = (
            sys.executable,
            "-B",
            "-I",
            "-m",
            "uv",
            "sync",
            "--check",
            "--frozen",
            "--offline",
            "--no-config",
            "--no-python-downloads",
            "--no-default-groups",
            "--no-install-project",
            "--inexact",
            "--project",
            str(root),
            "--python",
            self.executable,
            "--output-format",
            "json",
            *(argument for group in groups for argument in ("--group", group)),
        )
        completed = run_command(
            root,
            command,
            timeout=min(15, remaining),
            env={"UV_PROJECT_ENVIRONMENT": self.prefix, "PYTHONDONTWRITEBYTECODE": "1"},
            remove_env=("VIRTUAL_ENV",),
            remove_env_prefixes=("UV_", "PYTHON"),
        )
        return json.dumps(
            {
                "argv": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        ).encode()

    def require_floor(self, root: Path, content: bytes) -> None:
        """Validate the native check's actual target and zero-change observation."""
        try:
            attempt = json.loads(content)
            result = json.loads(attempt["stdout"])
            environment = result["sync"]["environment"]
            python = environment["python"]
            valid = (
                attempt.get("returncode") == 0
                and result["schema"] == {"version": "preview"}
                and result["target"] == "project"
                and Path(result["project"]["path"]).resolve() == root.resolve()
                and Path(result["lock"]["path"]).resolve() == (root / "uv.lock").resolve()
                and result["lock"]["action"] == "use"
                and result["dry_run"] is True
                and result["sync"]["action"] == "check"
                and result["sync"]["changes"] == []
                and Path(environment["path"]).resolve() == Path(self.prefix).resolve()
                and os.path.normcase(str(Path(python["path"]).absolute()))
                == os.path.normcase(str(Path(self.executable).absolute()))
                and tuple(int(part) for part in python["version"].split(".")) == tuple(self.version)
            )
        except (KeyError, TypeError, AttributeError, ValueError) as error:
            msg = "python_native_dependency_floor_unbound"
            raise ValueError(msg) from error
        if not valid:
            msg = "python_native_dependency_floor_unbound"
            raise ValueError(msg)


def _outputs(execution: NativeExecution, kind: str) -> tuple[tuple[NativeOutput, bytes], ...]:
    evidence = execution.evidence
    if evidence is None:
        msg = "python_native_evidence_unavailable"
        raise ValueError(msg)
    return tuple(item for item in evidence.outputs if item[0].format == kind)


def _producer(root: Path, execution: NativeExecution) -> tuple[NoxReport, tuple[str, ...]]:
    """Require complete source-bound output and terminal status from this invocation."""
    evidence = execution.evidence
    if evidence is None:
        msg = "python_native_evidence_unavailable"
        raise ValueError(msg)
    type(evidence.gate).model_validate(evidence.gate.to_dict())
    if evidence.gaps:
        raise ValueError(evidence.gaps[0])
    if execution.cwd != root.resolve() or not evidence.artifact:
        msg = "python_native_custody_missing"
        raise ValueError(msg)
    expected_argv = tuple(
        item.replace("{native_output}", evidence.output_root) for item in evidence.gate.command[1:]
    )
    if (
        execution.declared_identity != gate_execution_identity(evidence.gate)
        or execution.argv[1:] != expected_argv
        or execution.executable != execution.argv[0]
        or tuple(output for output, _ in evidence.outputs) != evidence.gate.native_outputs
    ):
        msg = "python_native_selection_invalid"
        raise ValueError(msg)
    tree, subjects = observe_quality_subjects(root, expected_tree=evidence.tree)
    if (
        tree != evidence.tree
        or current_tracked_head(root) != evidence.head
        or tuple(subject.path for subject in subjects) != evidence.subjects
    ):
        msg = "python_native_source_changed"
        raise ValueError(msg)
    reports = _outputs(execution, "nox-json")
    if len(reports) != 1:
        msg = "python_native_report_missing"
        raise ValueError(msg)
    contract, payload = reports[0]
    report = NoxReport.model_validate_json(payload)
    selected = tuple(
        set(session.signatures).intersection(contract.sessions) for session in report.sessions
    )
    found = tuple(next(iter(matches)) for matches in selected if len(matches) == 1)
    if (
        len(found) != len(report.sessions)
        or len(set(found)) != len(found)
        or set(found) != set(contract.sessions)
    ):
        msg = "python_native_sessions_incomplete"
        raise ValueError(msg)
    if (
        execution.exit_code != 0
        or report.result != 1
        or any(
            session.result != "success" or session.result_code != 1 or session.reason
            for session in report.sessions
        )
    ):
        msg = "python_native_execution_failed"
        raise ValueError(msg)
    _runtimes(execution, found)
    return report, tuple(subject.path for subject in subjects if subject.language == "python")


def _runtimes(execution: NativeExecution, found: tuple[str, ...]) -> None:
    """Each required native session has one actual interpreter observation."""
    runtimes = _outputs(execution, "python-runtime-json")
    runtime_sessions: set[str] = set()
    for output, content in runtimes:
        runtime = PythonRuntime.model_validate_json(content)
        version = tuple(int(part) for part in output.python.split("."))
        if (
            tuple(runtime.version[: len(version)]) != version
            or any(part < 0 for part in runtime.version)
            or not Path(runtime.executable).is_absolute()
            or not Path(runtime.prefix).is_absolute()
            or runtime_sessions.intersection(output.sessions)
            or len(output.sessions) != 1
        ):
            msg = "python_native_toolchain_unbound"
            raise ValueError(msg)
        runtime_sessions.update(output.sessions)
    evidence = execution.evidence
    checks = evidence.dependency_checks if evidence is not None else ()
    if tuple(output for output, _ in checks) != tuple(output for output, _ in runtimes):
        msg = "python_native_dependency_floor_unbound"
        raise ValueError(msg)
    for (output, content), (_, check) in zip(runtimes, checks, strict=True):
        runtime = PythonRuntime.model_validate_json(content)
        runtime.require_floor(root=execution.cwd, content=check)
        if evidence is None:
            msg = "python_native_evidence_unavailable"
            raise ValueError(msg)
        runtime.require_checks(execution.cwd, output, evidence.gate.native_outputs)
    if runtime_sessions != set(found):
        msg = "python_native_toolchain_unbound"
        raise ValueError(msg)


def report(root: Path, execution: NativeExecution, axis: str) -> dict[str, object]:
    """Consume the sole native attempt; never invoke another test or static tool."""
    producer, selected = _producer(root, execution)
    evidence = execution.evidence
    if evidence is None:
        msg = "python_native_evidence_unavailable"
        raise ValueError(msg)
    native: dict[str, object] = {
        "declared_identity": list(execution.declared_identity),
        "argv": list(execution.argv),
        "cwd": str(execution.cwd),
        "exit_code": execution.exit_code,
        "stdout": execution.stdout,
        "stderr": execution.stderr,
        "same_attempt": True,
        "artifact": evidence.artifact,
        "sessions": [session.model_dump() for session in producer.sessions],
        "structural_validation_is_authentication": False,
    }
    observation: dict[str, object] = {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "native": native,
        "quality_evidence": {
            "axis": axis,
            "source_tree": evidence.tree,
            "selected_paths": list(selected),
        },
    }
    if axis == "static-analysis":
        findings = _outputs(execution, "ruff-json")
        if not findings:
            msg = "python_native_static_missing"
            raise ValueError(msg)
        for _, content in findings:
            if json.loads(content) != []:
                msg = "python_native_static_diagnostics"
                raise ValueError(msg)
        return observation
    return _behavior(root, execution, observation)


def _behavior(
    root: Path, execution: NativeExecution, observation: dict[str, object]
) -> dict[str, object]:
    """Conjoin native JUnit and coverage for every declared behavior producer."""
    evidence = execution.evidence
    if evidence is None:
        msg = "python_native_evidence_unavailable"
        raise ValueError(msg)
    _, subjects = observe_quality_subjects(root, language="python", expected_tree=evidence.tree)
    source = tuple(subject.path for subject in subjects if subject.requires_behavior)
    cast("dict[str, object]", observation["quality_evidence"])["selected_paths"] = list(source)
    tests = _outputs(execution, "junit-xml")
    events = _outputs(execution, "pytest-jsonl")
    coverage = _outputs(execution, "coverage-xml")
    if not source or not tests or not coverage:
        msg = "python_native_behavior_missing"
        raise ValueError(msg)
    counts = {"total": 0, "failures": 0, "errors": 0, "skipped": 0}
    covered, total = 0, 0
    observed_tests: set[str] = set()
    observed_coverage: set[str] = set()
    for output, content in tests:
        selected_events = tuple(
            event for event_output, event in events if event_output.sessions == output.sessions
        )
        measured, failed = junit_stream_report(
            content.decode("utf-8"),
            pytest_events=selected_events[0].decode("utf-8") if selected_events else None,
        )
        if failed or observed_tests.intersection(output.sessions):
            msg = "python_native_tests_failed"
            raise ValueError(msg)
        observed_tests.update(output.sessions)
        for key in counts:
            counts[key] += measured[key]
    if any(not set(output.sessions) <= observed_tests for output, _ in events):
        msg = "python_native_pytest_scope_invalid"
        raise ValueError(msg)
    for output, content in coverage:
        measured = coverage_stream_report(
            content,
            include_files=True,
            repository_root=root.resolve(),
            source_paths=tuple(subject.path for subject in subjects),
        )
        files = cast("dict[str, dict[str, int]]", measured["files"])
        if (
            observed_coverage.intersection(output.sessions)
            or any(path not in files for path in source)
            or any(files[path]["lines"] > 0 and not files[path]["hit_lines"] for path in source)
        ):
            msg = "python_native_coverage_scope_incomplete"
            raise ValueError(msg)
        observed_coverage.update(output.sessions)
        covered += cast("int", measured["covered"])
        total += cast("int", measured["total"])
    if observed_tests != observed_coverage or not covered:
        msg = "python_native_coverage_scope_incomplete"
        raise ValueError(msg)
    observation["tests"] = counts
    observation["coverage"] = {
        "covered": covered,
        "total": total,
        "combined_percent": 100 * covered / total,
    }
    return observation

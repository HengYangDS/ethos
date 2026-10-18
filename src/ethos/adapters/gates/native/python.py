"""Qualify optional native Python producer reports under exact attempt custody."""

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

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import observe_quality_subjects

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeEvidence
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

    def checked_paths(self, root: Path) -> frozenset[str]:
        """Repository files this launch's verbose diagnostics report it checked."""
        subjects: set[str] = set()
        for line in self.stderr.splitlines():
            _prefix, separator, path = line.partition("[ruff::diagnostics][DEBUG] Checking: ")
            if separator:
                observed = Path(path).resolve()
                if observed.is_relative_to(root.resolve()):
                    subjects.add(observed.relative_to(root.resolve()).as_posix())
        return frozenset(subjects)

    def require(self, runtime: PythonRuntime, root: Path, output: NativeOutput) -> None:
        """Explicit native config and binary must belong to the observed child."""
        selected = root / output.configuration
        expected = Path(runtime.prefix) / ("Scripts/ruff.exe" if os.name == "nt" else "bin/ruff")
        try:
            arguments = self.argv
            config = arguments[arguments.index("--config") + 1]
            used_config = Path(config) if Path(config).is_absolute() else root / config
            subjects = self.checked_paths(root)
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
            ("static", "sarif", self.ruff),
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


def nox_sessions(evidence: NativeEvidence) -> list[dict[str, object]]:
    """Require a declared Nox report to show every selected session succeeded."""
    reports = tuple(item for item in evidence.outputs if item[0].format == "nox-json")
    if not reports:
        return []
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
    if report.result != 1 or any(
        session.result != "success" or session.result_code != 1 or session.reason
        for session in report.sessions
    ):
        msg = "python_native_execution_failed"
        raise ValueError(msg)
    return [session.model_dump() for session in report.sessions]


def runtime_scopes(root: Path, evidence: NativeEvidence) -> dict[str, frozenset[str]]:
    """Qualify each declared session runtime; return the files its Ruff launch checked."""
    runtimes = tuple(item for item in evidence.outputs if item[0].format == "python-runtime-json")
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
    checks = evidence.dependency_checks
    if tuple(output for output, _ in checks) != tuple(output for output, _ in runtimes):
        msg = "python_native_dependency_floor_unbound"
        raise ValueError(msg)
    scopes: dict[str, frozenset[str]] = {}
    for (output, content), (_, check) in zip(runtimes, checks, strict=True):
        runtime = PythonRuntime.model_validate_json(content)
        runtime.require_floor(root=root, content=check)
        runtime.require_checks(root, output, evidence.gate.native_outputs)
        if runtime.ruff is not None:
            scopes[output.sessions[0]] = runtime.ruff.checked_paths(root)
    return scopes

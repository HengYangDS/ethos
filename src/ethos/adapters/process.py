"""Provider-neutral external process execution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Mapping

PROCESS_CREATION_FAILED = "process_creation_failed"
NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE = "native_windows_powershell_unavailable"
NATIVE_PROCESS_OBSERVER_UNAVAILABLE = "native_process_observer_unavailable"


class ProcessExecutionError(ValueError):
    """Preserve the exact boundary of a failed process creation."""

    def __init__(
        self,
        code: str,
        *,
        reason: str,
        command: tuple[str, ...] = (),
        cwd: str = "",
        cause: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.reason = reason
        self.command = command
        self.cwd = cwd
        self.cause = cause

    def evidence(self) -> dict[str, object]:
        """Return the stable machine-readable failure evidence."""
        return {
            "code": self.code,
            "reason": self.reason,
            "command": list(self.command),
            "cwd": self.cwd,
            "cause": self.cause,
        }


def windows_powershell(*, environment: Mapping[str, str] | None = None) -> str:
    """Resolve native Windows PowerShell without consulting ambient PATH."""
    values = os.environ if environment is None else environment
    system_root = values.get("SYSTEMROOT", "")
    if not system_root:
        raise ProcessExecutionError(
            NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE,
            reason="system_root_missing",
        )
    executable = Path(system_root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    if not executable.is_file():
        raise ProcessExecutionError(
            NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE,
            reason="native_executable_missing",
            command=(executable.as_posix(),),
        )
    return executable.resolve().as_posix()


def process_listing_command(*, platform_name: str | None = None) -> tuple[str, ...]:
    """Return the native process-listing command without consulting ambient PATH."""
    windows = "Get-CimInstance Win32_Process | % CommandLine"
    if (platform_name or os.name) == "nt":
        return (
            windows_powershell(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            windows,
        )
    executable = shutil.which("ps", path=os.defpath)
    if executable is None or not Path(executable).is_file():
        raise ProcessExecutionError(
            NATIVE_PROCESS_OBSERVER_UNAVAILABLE,
            reason="native_executable_missing",
        )
    return (Path(executable).resolve().as_posix(), "-axo", "command=")


def _file_observation_failure(reason: str) -> None:
    raise ValueError(reason)


def _file_identities(payload: bytes) -> frozenset[tuple[int, int]]:
    if not payload.endswith(b"\0\n"):
        _file_observation_failure("file_observation_incomplete")
    identities: set[tuple[int, int]] = set()
    process_seen = False
    for frame in payload[:-2].split(b"\0\n"):
        pairs = [(item[:1], item[1:]) for item in frame.split(b"\0")]
        fields = dict(pairs)
        if len(fields) != len(pairs):
            _file_observation_failure("file_observation_duplicate_field")
        if b"p" in fields:
            if set(fields) != {b"p"} or not fields[b"p"].isdigit():
                _file_observation_failure("file_observation_process_invalid")
            process_seen = True
            continue
        if (
            sys.platform == "darwin"
            and process_seen
            and set(fields) == {b"f", b"n"}
            and fields[b"f"].isdigit()
            and re.fullmatch(
                rb"(?:kqueue|pipe|semaphore|POSIX shared memory|vnode|socket): "
                rb"(?:FD unavailable|process unavailable)",
                fields[b"n"],
            )
        ):
            continue
        fields.pop(b"n", None)
        if (
            not process_seen
            or set(fields) not in ({b"f", b"t"}, {b"f", b"t", b"D", b"i"})
            or not all(fields.values())
            or fields.get(b"f", b"NOFD") == b"NOFD"
            or fields.get(b"t", b"unknown") == b"unknown"
            or (b"i" in fields and not fields[b"i"].isdigit())
            or (fields[b"t"] in {b"REG", b"DIR"} and b"i" not in fields)
        ):
            _file_observation_failure(f"file_observation_unreadable:{frame[:256]!r}")
        if b"D" in fields:
            identities.add((int(fields[b"D"], 16), int(fields[b"i"])))
    if not identities:
        _file_observation_failure("file_observation_empty")
    return frozenset(identities)


def process_file_identities(root: Path) -> frozenset[tuple[int, int]]:
    """Observe native process file references; unavailable evidence is never empty."""
    command: tuple[str, ...] = ()
    try:
        executable = shutil.which("lsof", path=os.defpath + os.pathsep + "/usr/sbin")
        if os.name != "posix" or executable is None:
            _file_observation_failure("native_file_observer_missing")
        command = (str(executable), "-nP", "-F0pftDin")
        result = run_command(root, command, text=False, timeout=10, remove_env_prefixes=("GIT_",))
        if result.returncode or result.stderr:
            _file_observation_failure(
                result.stderr.decode(errors="replace") or "file_observation_incomplete"
            )
        return _file_identities(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise ProcessExecutionError(
            NATIVE_PROCESS_OBSERVER_UNAVAILABLE,
            reason="file_references_unavailable",
            command=command,
            cwd=root.as_posix(),
            cause=str(error),
        ) from error


def run_command(
    root: Path,
    command: tuple[str, ...],
    *,
    text: bool = True,
    check: bool = False,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
    remove_env: tuple[str, ...] = (),
    remove_env_prefixes: tuple[str, ...] = (),
    inherit_environment: bool = True,
    stdin: str | bytes | None = None,
) -> subprocess.CompletedProcess[Any]:
    """Run one exact argv command and preserve process-creation evidence."""
    resolved_root = root.resolve()
    if not root.is_dir():
        raise ProcessExecutionError(
            PROCESS_CREATION_FAILED,
            reason="working_directory_unavailable",
            command=command,
            cwd=resolved_root.as_posix(),
        )
    removed = {key.casefold() for key in remove_env}
    removed_prefixes = tuple(prefix.casefold() for prefix in remove_env_prefixes)
    effective_env = dict(os.environ) if inherit_environment else {}
    for key in tuple(effective_env):
        folded = key.casefold()
        if folded in removed or folded.startswith(removed_prefixes):
            effective_env.pop(key)
    effective_env.update(env or {})
    try:
        return subprocess.run(
            command,
            cwd=resolved_root,
            check=check,
            text=text,
            capture_output=True,
            env=effective_env,
            input=stdin,
            timeout=timeout,
            shell=False,
        )
    except OSError as error:
        raise ProcessExecutionError(
            PROCESS_CREATION_FAILED,
            reason="operating_system_rejected_process_creation",
            command=command,
            cwd=resolved_root.as_posix(),
            cause=f"{error.__class__.__name__}: {error}",
        ) from error

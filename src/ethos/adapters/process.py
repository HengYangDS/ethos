"""Provider-neutral external process execution."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Mapping

PROCESS_CREATION_FAILED = "process_creation_failed"
NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE = "native_windows_powershell_unavailable"


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

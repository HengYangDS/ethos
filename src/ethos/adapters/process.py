"""Provider-neutral external process execution."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
from contextlib import contextmanager
from contextlib import suppress
from contextvars import ContextVar
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping

PROCESS_CREATION_FAILED = "process_creation_failed"
NATIVE_WINDOWS_POWERSHELL_UNAVAILABLE = "native_windows_powershell_unavailable"
NATIVE_PROCESS_OBSERVER_UNAVAILABLE = "native_process_observer_unavailable"


class ProcessExecutionError(ValueError):
    """Preserve a failed process boundary and any bounded observation evidence."""

    def __init__(
        self,
        code: str,
        *,
        reason: str,
        command: tuple[str, ...] = (),
        cwd: str = "",
        cause: str = "",
        observation: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.reason = reason
        self.command = command
        self.cwd = cwd
        self.cause = cause
        self.observation = dict(observation or {})

    def evidence(self) -> dict[str, object]:
        """Return the stable machine-readable failure evidence."""
        return {
            "code": self.code,
            "reason": self.reason,
            "command": list(self.command),
            "cwd": self.cwd,
            "cause": self.cause,
            **({"observation": self.observation} if self.observation else {}),
        }


class CommandScope:
    """Own commands across one caller and its context-propagating worker threads."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._processes: set[subprocess.Popen[Any]] = set()
        self._cancelled = False

    def start(self, command: tuple[str, ...], **kwargs: Any) -> subprocess.Popen[Any]:
        """Fence creation against cancellation, retaining the actual process handle."""
        with self._lock:
            if self._cancelled:
                message = "process_cancelled"
                raise ProcessExecutionError(
                    message,
                    reason="command_scope_cancelled",
                    command=command,
                    cwd=str(kwargs.get("cwd", "")),
                )
            process = subprocess.Popen(command, **kwargs)
            self._processes.add(process)
            return process

    def discard(self, process: subprocess.Popen[Any]) -> None:
        """Release a completed command without retaining historical process IDs."""
        with self._lock:
            self._processes.discard(process)

    def terminate(self, process: subprocess.Popen[Any]) -> None:
        """Fence both cleanup initiators; the command caller still owns reaping."""
        with self._lock:
            if process in self._processes:
                _terminate_command(process)
                self._processes.discard(process)

    def cancel(self) -> None:
        """Stop owned groups before thread-pool shutdown waits on their callers."""
        errors: list[OSError] = []
        with self._lock:
            self._cancelled = True
            processes = tuple(self._processes)
        for process in processes:
            try:
                self.terminate(process)
            except OSError as error:
                errors.append(error)
        if errors:
            message = "command_scope_cleanup_failed"
            raise ExceptionGroup(message, errors)


_COMMAND_SCOPE: ContextVar[CommandScope | None] = ContextVar("command_scope", default=None)


@contextmanager
def command_scope() -> Iterator[CommandScope]:
    """Propagate caller interruption through one transient native command owner."""
    scope = _COMMAND_SCOPE.get() or CommandScope()
    token = _COMMAND_SCOPE.set(scope)
    try:
        yield scope
    except BaseException:
        scope.cancel()
        raise
    finally:
        _COMMAND_SCOPE.reset(token)


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
    """Observe full native command text, independent of PATH or display width."""
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
    return (Path(executable).resolve().as_posix(), "-axww", "-o", "command=")


def _file_observation_failure(reason: str) -> None:
    raise ValueError(reason)


def _file_identities(payload: bytes) -> frozenset[tuple[int, int]]:
    if not payload.endswith(b"\0\n"):
        _file_observation_failure("file_observation_incomplete")
    identities: set[tuple[int, int]] = set()
    process_seen = False
    for frame in payload[:-2].split(b"\0\n"):
        fields = {item[:1]: item[1:] for item in frame.split(b"\0")}
        if len(fields) != frame.count(b"\0") + 1:
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
            or set(fields) not in ({b"f", b"t"}, {b"f", b"t", b"D", b"i"}, {b"f", b"t", b"i"})
            or not all(fields.values())
            or fields.get(b"f", b"NOFD") == b"NOFD"
            or fields.get(b"t", b"unknown") == b"unknown"
            or (b"i" in fields and not fields[b"i"].isdigit())
            or (b"i" in fields and b"D" not in fields and fields[b"t"] != b"unix")
            or (fields[b"t"] in {b"REG", b"DIR"} and b"i" not in fields)
        ):
            _file_observation_failure(f"file_observation_unreadable:{frame[:256]!r}")
        if b"D" in fields:
            identities.add((int(fields[b"D"], 16), int(fields[b"i"])))
    if not identities:
        _file_observation_failure("file_observation_empty")
    return frozenset(identities)


def process_file_identities(root: Path, *, tree: Path, index: Path) -> frozenset[tuple[int, int]]:
    """Observe references to one selected worktree and its external Git index."""
    command: tuple[str, ...] = ()
    try:
        executable = shutil.which("lsof", path=os.defpath + os.pathsep + "/usr/sbin")
        if os.name != "posix" or executable is None:
            _file_observation_failure("native_file_observer_missing")
        if (
            not tree.is_absolute()
            or not index.is_absolute()
            or tree.is_symlink()
            or index.is_symlink()
            or not tree.is_dir()
            or not index.is_file()
        ):
            _file_observation_failure("file_observation_scope_unavailable")
        command = (str(executable), "-nP", "-F0pftDin", "+D", str(tree), str(index))
        result = run_command(root, command, text=False, timeout=10, remove_env_prefixes=("GIT_",))
        # Scoped lsof exits 1 when a selected path has no open match.
        if result.returncode not in {0, 1} or result.stderr:
            _file_observation_failure(
                result.stderr.decode(errors="replace") or "file_observation_incomplete"
            )
        if not result.stdout:
            if result.returncode == 1:
                return frozenset()
            _file_observation_failure("file_observation_empty_success")
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
    return _execute_command(
        command,
        cwd=resolved_root,
        check=check,
        text=text,
        env=effective_env,
        input=stdin,
        timeout=timeout,
    )


def _execute_command(
    command: tuple[str, ...], *, check: bool, timeout: float | None, **kwargs: Any
) -> subprocess.CompletedProcess[Any]:
    """Separate creation failures from communication and owned-process cleanup."""
    stdin = kwargs.pop("input")
    scope = _COMMAND_SCOPE.get()
    try:
        process = (scope.start if scope is not None else subprocess.Popen)(
            command,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **({"process_group": 0} if os.name == "posix" else {}),
            **kwargs,
        )
    except OSError as error:
        raise ProcessExecutionError(
            PROCESS_CREATION_FAILED,
            reason="operating_system_rejected_process_creation",
            command=command,
            cwd=kwargs["cwd"].as_posix(),
            cause=f"{error.__class__.__name__}: {error}",
        ) from error
    with process:
        try:
            stdout, stderr = process.communicate(stdin, timeout=timeout)
        except BaseException as error:
            (scope.terminate if scope is not None else _terminate_command)(process)
            if os.name == "nt" and isinstance(error, subprocess.TimeoutExpired):
                error.stdout, error.stderr = process.communicate()
            process.wait()
            raise
        finally:
            if scope is not None and process.returncode is not None:
                scope.discard(process)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result


def _terminate_command(process: subprocess.Popen[Any]) -> None:
    """Terminate owned processes; only observed group absence resolves a kill race."""
    with suppress(ProcessLookupError):
        if os.name != "posix":
            process.kill()
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except PermissionError:
            if process.poll() is None:
                raise
            # An unreaped exited leader can leave an unsignalable group on Darwin.
            # Reaping is insufficient: surviving members must not be ignored.
            os.killpg(process.pid, 0)
            raise

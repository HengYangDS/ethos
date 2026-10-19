"""Provider-neutral external process execution."""

from __future__ import annotations

import locale
import os
import shutil
import signal
import subprocess
import sys
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from contextvars import ContextVar
from functools import partial
from pathlib import Path
from tempfile import TemporaryFile
from threading import Lock
from threading import current_thread
from threading import main_thread
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Mapping
    from types import FrameType
    from types import TracebackType
    from typing import BinaryIO

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

    def start(
        self, command: tuple[str, ...], *, resources: ExitStack, **kwargs: Any
    ) -> subprocess.Popen[Any]:
        """Bind caller cleanup before a created child can leave its owning scope."""
        with self._lock:
            if self._cancelled:
                message = "process_cancelled"
                raise ProcessExecutionError(
                    message,
                    reason="command_scope_cancelled",
                    command=command,
                    cwd=str(kwargs.get("cwd", "")),
                )
            process: subprocess.Popen[Any] | None = None
            try:
                with defer_interruptions():
                    process = subprocess.Popen(command, **kwargs)
                    self._processes.add(process)
                    resources.push(partial(self.release, process))
            except BaseException:
                if process is not None:
                    with defer_interruptions():
                        _terminate_command(process)
                        process.__exit__(None, None, None)
                        self._processes.discard(process)
                raise
        return process

    def release(
        self,
        process: subprocess.Popen[Any],
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """Finish the registered native lifetime even when handle handoff is interrupted."""
        with defer_interruptions():
            if exc_type is not None or process.returncode is None:
                self.terminate(
                    process, grace_seconds=0.5 if isinstance(exc, KeyboardInterrupt) else 1
                )
            try:
                if os.name == "nt" and isinstance(exc, subprocess.TimeoutExpired):
                    exc.stdout, exc.stderr = process.communicate()
                process.__exit__(None, None, None)
            finally:
                self.discard(process)

    def discard(self, process: subprocess.Popen[Any]) -> None:
        """Release a completed command without retaining historical process IDs."""
        with self._lock:
            self._processes.discard(process)

    def terminate(self, process: subprocess.Popen[Any], *, grace_seconds: float = 1) -> None:
        """Fence both cleanup initiators; the command caller still owns reaping."""
        with self._lock:
            if process in self._processes:
                _terminate_commands((process,), grace_seconds=grace_seconds)
                self._processes.discard(process)

    def cancel(self) -> None:
        """Fan out cancellation within one budget before thread-pool shutdown waits."""
        with self._lock:
            self._cancelled = True
            processes = tuple(self._processes)
            _terminate_commands(processes, grace_seconds=0.5)
            self._processes.difference_update(processes)


_COMMAND_SCOPE: ContextVar[CommandScope | None] = ContextVar("command_scope", default=None)
_COMMAND_DEADLINE: ContextVar[float | None] = ContextVar("command_deadline", default=None)


@contextmanager
def defer_interruptions() -> Generator[None]:
    """Finish one critical effect before replaying an already-owned signal."""
    if current_thread() is not main_thread():
        yield
        return
    pending: tuple[int, FrameType | None] | None = None
    handlers: dict[int, Callable[[int, FrameType | None], object]] = {}

    def postpone(signum: int, frame: FrameType | None) -> None:
        nonlocal pending
        pending = signum, frame

    with ExitStack() as restoration:
        for signum in (signal.SIGINT, signal.SIGTERM):
            handler = signal.getsignal(signum)
            if callable(handler):
                handlers[signum] = handler
                restoration.callback(signal.signal, signum, handler)
                signal.signal(signum, postpone)
        yield
    if pending is not None:
        handlers[pending[0]](*pending)


@contextmanager
def command_scope(
    *, timeout_seconds: float | None = None, handle_termination: bool = False
) -> Generator[CommandScope]:
    """Propagate interruption, optionally owning SIGTERM on the caller's main thread."""
    if handle_termination and current_thread() is not main_thread():
        message = "command_scope_signal_requires_main_thread"
        raise ValueError(message)
    scope = _COMMAND_SCOPE.get() or CommandScope()
    token = _COMMAND_SCOPE.set(scope)
    deadline = _COMMAND_DEADLINE.get()
    if timeout_seconds is not None:
        proposed = monotonic() + timeout_seconds
        deadline = min(deadline, proposed) if deadline is not None else proposed
    deadline_token = _COMMAND_DEADLINE.set(deadline)

    def interrupt(_signum: int, _frame: FrameType | None) -> None:
        raise KeyboardInterrupt

    try:
        with ExitStack() as restoration:
            if handle_termination:
                handler = signal.getsignal(signal.SIGTERM)
                restoration.callback(signal.signal, signal.SIGTERM, handler)
                signal.signal(signal.SIGTERM, interrupt)
            try:
                yield scope
            except BaseException:
                with defer_interruptions():
                    scope.cancel()
                raise
    finally:
        _COMMAND_DEADLINE.reset(deadline_token)
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
    spool_stdout: bool = False,
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
        spool_stdout=spool_stdout,
    )


def _execute_command(
    command: tuple[str, ...],
    *,
    check: bool,
    timeout: float | None,
    spool_stdout: bool,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    """Separate creation failures from communication and owned-process cleanup."""
    deadline = _COMMAND_DEADLINE.get()
    if deadline is not None:
        remaining = max(0, deadline - monotonic())
        timeout = remaining if timeout is None else min(timeout, remaining)
        if timeout <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
    stdin = kwargs.pop("input")
    text_mode = kwargs["text"]
    scope = _COMMAND_SCOPE.get() or CommandScope()
    with (
        ExitStack() as resources,
        _finite_output(enabled=spool_stdout and os.name == "posix") as (output, diagnostic),
    ):
        finite_input = None
        if stdin is not None:
            finite_input = resources.enter_context(
                TemporaryFile(mode="w+" if kwargs["text"] else "w+b")
            )
            finite_input.write(stdin)
            finite_input.seek(0)
        kwargs["text"] = text_mode and diagnostic is None
        try:
            process = scope.start(
                command,
                resources=resources,
                stdin=finite_input if finite_input is not None else subprocess.DEVNULL,
                stdout=output,
                stderr=diagnostic if diagnostic is not None else subprocess.PIPE,
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
        _unpiped, stderr = process.communicate(timeout=timeout)
        if diagnostic is not None:
            scope.terminate(process)
            stderr = _decoded(_written(diagnostic), text=text_mode)
        stdout = _decoded(_written(output), text=text_mode)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result


@contextmanager
def _finite_output(*, enabled: bool) -> Generator[tuple[BinaryIO, BinaryIO | None]]:
    """Snapshot timeout bytes before cleanup; preserve optional stderr pipe semantics."""
    with ExitStack() as resources:
        output = resources.enter_context(TemporaryFile(mode="w+b"))
        diagnostic = resources.enter_context(TemporaryFile(mode="w+b")) if enabled else None
        try:
            yield output, diagnostic
        except subprocess.TimeoutExpired as error:
            error.stdout = _written(output)
            if diagnostic is not None:
                error.stderr = _written(diagnostic)
            raise


def _written(output: BinaryIO) -> bytes:
    """Read one captured native stream from its start."""
    output.seek(0)
    return output.read()


def _decoded(data: bytes, *, text: bool) -> str | bytes:
    """Decode captured output exactly as a default text-mode pipe would."""
    if not text:
        return data
    encoding = "utf-8" if sys.flags.utf8_mode else locale.getencoding()
    return data.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")


def _terminate_commands(
    processes: tuple[subprocess.Popen[Any], ...], *, grace_seconds: float
) -> None:
    """Interrupt all owned leaders, then close their groups within one cleanup budget."""
    errors: list[OSError] = []
    for process in processes:
        try:
            if os.name == "posix" and process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
        except ProcessLookupError:
            pass
        except OSError as error:
            errors.append(error)
    deadline = monotonic() + grace_seconds
    for process in processes:
        try:
            _terminate_command(process, deadline=deadline)
        except OSError as error:
            errors.append(error)
    if len(errors) == 1:
        raise errors[0]
    if errors:
        message = "command_scope_cleanup_failed"
        raise ExceptionGroup(message, errors)


def _terminate_command(process: subprocess.Popen[Any], *, deadline: float | None = None) -> None:
    """Close an owned group; only observed absence resolves a native kill race."""
    with suppress(ProcessLookupError):
        if os.name != "posix":
            process.kill()
            return
        try:
            try:
                if deadline is not None:
                    with suppress(subprocess.TimeoutExpired):
                        process.wait(timeout=max(0, deadline - monotonic()))
            finally:
                os.killpg(process.pid, signal.SIGKILL)
        except PermissionError:
            if process.poll() is None:
                raise
            # An unreaped exited leader can leave an unsignalable group on Darwin.
            # Reaping is insufficient: surviving members must not be ignored.
            os.killpg(process.pid, 0)
            raise

"""Bounded nonblocking exchange and process-group cleanup."""

from __future__ import annotations

import os
import selectors
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    CleanupCause,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    CleanupWait,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    ProcessGroupProbe,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    WorkerExchangeContext,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    WorkerExchangeState,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    WorkerLifecycleBoundary,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    WorkerLifecycleContext,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    WorkerLifecycleOwner,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    acquire_worker_selector,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    finish_worker_process,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    wait_for_cleanup_timeout,
)

if TYPE_CHECKING:
    import subprocess

    from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerTelemetry
    from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
        WorkerExchangeCause,
    )
    from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
        WorkerProtocolDescriptor,
    )
    from ethos_core.contracts.source_budget.measurement.worker.resource import (
        WorkerResourceProfileDescriptor,
    )

_SelectFactory = Callable[[], selectors.BaseSelector]
_Monotonic = Callable[[], float]
_GroupSignal = Callable[[int, int], None]
_RemoveDirectory = Callable[[Path], None]
_IO_CHUNK_BYTES = 64 * 1024
_PIPE_CAPABILITY_ERROR = "worker pipe capability unavailable"
_TELEMETRY_ERROR = "worker telemetry unavailable"
_VIRTUAL_TELEMETRY_ERROR = "worker virtual telemetry unavailable"
_EXIT_OBSERVATION_ERROR = "worker exit observation unavailable"


@dataclass(frozen=True, slots=True)
class WorkerExchangeConfig:
    """Immutable process, protocol, and policy inputs for one worker exchange."""

    request_frame: bytes
    telemetry: WorkerTelemetry | None
    profile: WorkerResourceProfileDescriptor
    protocol: WorkerProtocolDescriptor
    wall_deadline: float
    darwin_vms_baseline: int | None = None
    resource_sampled_at: float | None = None
    request_permitted: bool = True
    initial_cause: WorkerExchangeCause | None = None


@dataclass(frozen=True, slots=True)
class WorkerExchangeHooks:
    """Explicit operating-system and deterministic-test seams for an exchange."""

    send_group_signal: _GroupSignal
    probe_process_group: ProcessGroupProbe
    monotonic: _Monotonic = time.monotonic
    selector_factory: _SelectFactory = selectors.DefaultSelector
    wait_for: CleanupWait = wait_for_cleanup_timeout
    remove_directory: _RemoveDirectory = shutil.rmtree


@dataclass(frozen=True, slots=True)
class WorkerExchangeResult:
    """Bounded raw process outcome before protocol interpretation."""

    stdout: bytes
    stdout_eof: bool
    returncode: int | None
    first_cause: WorkerExchangeCause | None
    cleanup_failed: bool
    cleanup_cause: CleanupCause | None = None


@dataclass(frozen=True, slots=True)
class WorkerExchangeSession:
    """Pre-spawn exchange state and its single idempotent lifecycle owner."""

    state: WorkerExchangeState
    lifecycle: WorkerLifecycleContext

    def bind_process(self, process: subprocess.Popen[bytes]) -> None:
        """Bind the sole spawned process identity to the lifecycle owner."""
        self.lifecycle.owner.bind_process(process)

    def finish(self, active_error: BaseException | None = None) -> None:
        """Attempt lifecycle cleanup once."""
        finish_worker_process(self.lifecycle, active_error)


def exchange_worker_process(
    config: WorkerExchangeConfig,
    hooks: WorkerExchangeHooks,
    session: WorkerExchangeSession,
) -> WorkerExchangeResult:
    """Exchange one frame and unconditionally terminate, close, reap, and remove."""
    state = session.state
    process = session.lifecycle.owner.process
    if config.initial_cause is not None:
        state.trigger(config.initial_cause)
    if process is None:
        state.trigger("pipe_failed")
    active_error: BaseException | None = None
    try:
        if process is not None:
            _run_exchange(config, hooks, state, session, process)
    except BaseException as error:
        active_error = error
        raise
    finally:
        session.finish(active_error)
    return _freeze_exchange(state)


def prepare_worker_exchange(
    private_directory: Path,
    profile: WorkerResourceProfileDescriptor,
    hooks: WorkerExchangeHooks,
) -> WorkerExchangeSession:
    """Allocate every cleanup-critical carrier before worker spawn."""
    state = WorkerExchangeState()
    owner = WorkerLifecycleOwner(private_directory=private_directory)
    boundary = WorkerLifecycleBoundary(owner, state)
    lifecycle = WorkerLifecycleContext(
        owner=owner,
        state=state,
        boundary=boundary,
        grace_seconds=profile.term_grace_ms / 1000,
        send_group_signal=hooks.send_group_signal,
        probe_process_group=hooks.probe_process_group,
        observe_direct_child=_observe_direct_child,
        monotonic=hooks.monotonic,
        wait_for=hooks.wait_for,
        remove_directory=hooks.remove_directory,
    )
    return WorkerExchangeSession(state, lifecycle)


def _run_exchange(
    config: WorkerExchangeConfig,
    hooks: WorkerExchangeHooks,
    state: WorkerExchangeState,
    session: WorkerExchangeSession,
    process: subprocess.Popen[bytes],
) -> None:
    try:
        if state.triggered():
            return
        if hooks.monotonic() >= config.wall_deadline:
            state.trigger("timeout")
            return
        selector = acquire_worker_selector(session.lifecycle, hooks.selector_factory)
        context = WorkerExchangeContext(
            process,
            selector,
            state,
            config,
            hooks.monotonic,
        )
        _prepare_pipes(context)
        if not state.triggered():
            _drive_exchange(context)
    except MemoryError:
        _trigger_parent_failure(state, hooks, config.wall_deadline, "pipe_failed")
    except WorkerIsolationUnsupportedError:
        _trigger_parent_failure(state, hooks, config.wall_deadline, "capability_failed")
    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        _trigger_parent_failure(state, hooks, config.wall_deadline, "pipe_failed")


def _trigger_parent_failure(
    state: WorkerExchangeState,
    hooks: WorkerExchangeHooks,
    wall_deadline: float,
    cause: WorkerExchangeCause,
) -> None:
    expired = not state.triggered() and hooks.monotonic() >= wall_deadline
    state.trigger("timeout" if expired else cause)


def _prepare_pipes(context: WorkerExchangeContext) -> None:
    process = context.process
    if _expire_exchange(context):
        return
    if (
        type(context.request_frame) is not bytes
        or len(context.request_frame) > context.protocol.stdin_max_bytes
        or process.stdin is None
        or process.stdout is None
    ):
        raise WorkerIsolationUnsupportedError(_PIPE_CAPABILITY_ERROR)
    os.set_blocking(process.stdin.fileno(), False)
    if _expire_exchange(context):
        return
    os.set_blocking(process.stdout.fileno(), False)
    if _expire_exchange(context):
        return
    context.selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    if context.request_permitted:
        if context.telemetry is None:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        if _expire_exchange(context):
            return
        context.selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
    else:
        try:
            process.stdin.close()
        except OSError:
            context.state.trigger("pipe_failed")


def _drive_exchange(context: WorkerExchangeContext) -> None:
    state = context.state
    interval = context.profile.sample_interval_ms / 1000
    telemetry_active = context.request_permitted
    while not state.triggered():
        if _expire_exchange(context):
            return
        _handle_events(context, _select_events(context, None), allow_write=True)
        if state.triggered() or _exchange_complete(context):
            return
        now = context.monotonic()
        if now >= context.wall_deadline:
            state.trigger("timeout")
            return
        telemetry_active = _sample_if_due(
            context,
            telemetry_active=telemetry_active,
            now=now,
            interval=interval,
        )
        if state.triggered():
            return
        wait_deadline = min(context.wall_deadline, context.next_sample)
        _handle_events(context, _select_events(context, wait_deadline), allow_write=True)


def _exchange_complete(context: WorkerExchangeContext) -> bool:
    state = context.state
    if (returncode := _observe_direct_child(context.process)) is not None:
        state.returncode = returncode
    if (
        state.returncode is not None
        and context.request_permitted
        and state.request_offset < len(context.request_frame)
    ):
        state.trigger("pipe_failed")
    return state.triggered() or (state.stdout_eof and state.returncode is not None)


def _sample_if_due(
    context: WorkerExchangeContext,
    *,
    telemetry_active: bool,
    now: float,
    interval: float,
) -> bool:
    if not telemetry_active or context.state.returncode is not None or now < context.next_sample:
        return telemetry_active
    try:
        _sample_resources(context)
    except WorkerIsolationUnsupportedError:
        if _expire_exchange(context):
            return telemetry_active
        telemetry_active = False
        if not _reconcile_terminal_after_telemetry_loss(
            context,
            min(context.wall_deadline, now + interval),
        ):
            context.state.trigger("capability_failed")
    context.next_sample = now + interval
    return telemetry_active


def _expire_exchange(context: WorkerExchangeContext) -> bool:
    if context.monotonic() < context.wall_deadline:
        return False
    context.state.trigger("timeout")
    return True


def _select_events(
    context: WorkerExchangeContext,
    wait_deadline: float | None,
) -> list[tuple[selectors.SelectorKey, int]]:
    while not context.state.triggered():
        now = context.monotonic()
        if now >= context.wall_deadline:
            context.state.trigger("timeout")
            return []
        if wait_deadline is None:
            timeout = 0.0
        else:
            if now >= wait_deadline:
                return []
            timeout = min(context.wall_deadline, wait_deadline) - now
        try:
            return context.selector.select(timeout)
        except InterruptedError:
            continue
    return []


def _sample_resources(context: WorkerExchangeContext) -> None:
    telemetry = context.telemetry
    if telemetry is None:
        raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
    sample = telemetry.sample()
    if _expire_exchange(context):
        return
    if sample.rss_bytes > context.profile.rss_bytes:
        context.state.trigger("resource_exhausted")
    if sample.virtual_bytes is None:
        raise WorkerIsolationUnsupportedError(_VIRTUAL_TELEMETRY_ERROR)
    baseline = context.darwin_vms_baseline
    if (
        baseline is not None
        and sample.virtual_bytes > baseline + context.profile.darwin_vms_growth_bytes
    ):
        context.state.trigger("resource_exhausted")


def _reconcile_terminal_after_telemetry_loss(
    context: WorkerExchangeContext,
    race_deadline: float,
) -> bool:
    while True:
        _handle_events(context, _select_events(context, None), allow_write=False)
        if context.state.triggered():
            return False
        if (returncode := _observe_direct_child(context.process)) is not None:
            context.state.returncode = returncode
        if context.state.returncode is not None and context.state.stdout_eof:
            return True
        now = context.monotonic()
        if now >= race_deadline:
            return False
        _handle_events(
            context,
            _select_events(context, race_deadline),
            allow_write=False,
        )


def _handle_events(
    context: WorkerExchangeContext,
    events: list[tuple[selectors.SelectorKey, int]],
    *,
    allow_write: bool,
) -> None:
    for key, mask in events:
        if key.data == "stdin" and mask & selectors.EVENT_WRITE and allow_write:
            _write_request(context)
        elif key.data == "stdout" and mask & selectors.EVENT_READ:
            _read_stdout(context)
        if context.state.triggered():
            break


def _write_request(context: WorkerExchangeContext) -> None:
    process = context.process
    state = context.state
    if process.stdin is None:
        state.trigger("pipe_failed")
        return
    remaining = context.request_frame[state.request_offset :]
    written = _write_nonblocking(context, process.stdin.fileno(), remaining)
    if written is None:
        return
    if written <= 0 or written > len(remaining):
        state.trigger("pipe_failed")
        return
    state.request_offset += written
    if _expire_exchange(context):
        return
    if state.request_offset == len(context.request_frame):
        try:
            context.selector.unregister(process.stdin)
            process.stdin.close()
        except (KeyError, OSError, ValueError):
            state.trigger("pipe_failed")


def _write_nonblocking(
    context: WorkerExchangeContext,
    descriptor: int,
    payload: bytes,
) -> int | None:
    while not _expire_exchange(context):
        try:
            return os.write(descriptor, payload)
        except InterruptedError:
            continue
        except BlockingIOError:
            return None
        except OSError:
            context.state.trigger("pipe_failed")
            return None
    return None


def _read_stdout(context: WorkerExchangeContext) -> None:
    process = context.process
    state = context.state
    if process.stdout is None:
        state.trigger("pipe_failed")
        return
    remaining = context.protocol.result_max_bytes + 1 - len(state.stdout)
    if remaining <= 0:
        state.trigger("output_exceeded")
        return
    chunk = _read_nonblocking(
        context,
        process.stdout.fileno(),
        min(_IO_CHUNK_BYTES, remaining),
    )
    if chunk is None:
        return
    if not chunk:
        state.stdout_eof = True
        if _expire_exchange(context):
            return
        try:
            context.selector.unregister(process.stdout)
        except (KeyError, ValueError):
            state.trigger("pipe_failed")
        return
    state.stdout.extend(chunk)
    if _expire_exchange(context):
        return
    if len(state.stdout) > context.protocol.result_max_bytes:
        state.trigger("output_exceeded")


def _read_nonblocking(
    context: WorkerExchangeContext,
    descriptor: int,
    maximum: int,
) -> bytes | None:
    while not _expire_exchange(context):
        try:
            return os.read(descriptor, maximum)
        except InterruptedError:
            continue
        except BlockingIOError:
            return None
        except OSError:
            context.state.trigger("pipe_failed")
            return None
    return None


def _observe_direct_child(process: subprocess.Popen[bytes]) -> int | None:
    required = ("P_PID", "WEXITED", "WNOHANG", "WNOWAIT")
    if not hasattr(os, "waitid") or any(not hasattr(os, name) for name in required):
        raise WorkerIsolationUnsupportedError(_EXIT_OBSERVATION_ERROR)
    try:
        observed = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except InterruptedError:
        return None
    except (ChildProcessError, OSError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_EXIT_OBSERVATION_ERROR) from exc
    if observed is None or observed.si_pid == 0:
        return None
    if observed.si_code == getattr(os, "CLD_EXITED", -1):
        return observed.si_status
    if observed.si_code in {
        getattr(os, "CLD_KILLED", -1),
        getattr(os, "CLD_DUMPED", -1),
    }:
        return -observed.si_status
    raise WorkerIsolationUnsupportedError(_EXIT_OBSERVATION_ERROR)


def _freeze_exchange(state: WorkerExchangeState) -> WorkerExchangeResult:
    try:
        return _frozen_exchange(state, bytes(state.stdout))
    except MemoryError:
        if state.first_cause is None:
            raise
        return _frozen_exchange(state, b"")


def _frozen_exchange(state: WorkerExchangeState, stdout: bytes) -> WorkerExchangeResult:
    return WorkerExchangeResult(
        stdout=stdout,
        stdout_eof=state.stdout_eof,
        returncode=state.returncode,
        first_cause=state.first_cause,
        cleanup_failed=state.cleanup_failed,
        cleanup_cause=state.cleanup_cause,
    )

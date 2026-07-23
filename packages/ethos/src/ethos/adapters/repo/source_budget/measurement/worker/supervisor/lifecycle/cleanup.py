"""Bounded process-group termination and carrier cleanup algorithms."""

from __future__ import annotations

import signal
import subprocess
from typing import TYPE_CHECKING
from typing import Protocol

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)

if TYPE_CHECKING:
    import selectors
    from collections.abc import Callable
    from pathlib import Path

    from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
        CleanupCause,
    )
    from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
        WorkerLifecycleContext,
    )

_MAX_INTERRUPTED_ATTEMPTS = 3
_MAX_REAP_ATTEMPTS = 2
_ACCEPTED_STATES = frozenset(
    {WorkerProcessGroupState.TERMINAL_ONLY, WorkerProcessGroupState.ABSENT}
)


class _CleanupState(Protocol):
    returncode: int | None
    cleanup_cause: CleanupCause | None
    cleanup_failed: bool


def cleanup_owned_resources(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes] | None,
    selector: selectors.BaseSelector | None,
    *,
    safe_to_remove_directory: bool,
    no_live_proved: bool = False,
) -> None:
    with context.boundary:
        no_live_proved = process is None
        _checkpoint_cleanup_progress()
    try:
        if process is not None:
            no_live_proved = _attempt_owned_termination(context, process)
    finally:
        try:
            _run_cleanup_phase(context, _close_selector, context, selector)
        finally:
            try:
                if process is not None:
                    _run_cleanup_phase(context, _close_parent_pipes, context, process)
            finally:
                try:
                    if process is not None:
                        _run_cleanup_phase(context, _reap_direct_child, context, process)
                finally:
                    if process is not None and not no_live_proved:
                        with context.boundary:
                            no_live_proved = _final_no_live_proof(context, process)
                            _checkpoint_cleanup_progress()
                    if safe_to_remove_directory and no_live_proved:
                        _run_cleanup_phase(
                            context,
                            _remove_private_directory,
                            context,
                            context.owner.private_directory,
                        )
                    else:
                        context.state.cleanup_failed = True


def cleanup_unbound_process(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
    *,
    no_live_proved: bool = False,
) -> bool:
    with context.boundary:
        no_live_proved = _attempt_owned_termination(context, process)
        _checkpoint_cleanup_progress()
    try:
        _run_cleanup_phase(context, _close_parent_pipes, context, process)
    finally:
        _run_cleanup_phase(context, _reap_direct_child, context, process)
    if not no_live_proved:
        with context.boundary:
            no_live_proved = _final_no_live_proof(context, process)
            _checkpoint_cleanup_progress()
    return no_live_proved


def _attempt_owned_termination(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> bool:
    with context.boundary:
        return _terminate_process_group(context, process)
    return False


def _final_no_live_proof(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> bool:
    _observe_child(context, process)
    return _no_live_proved(context.state, _probe_group(context, process))


def _run_cleanup_phase(
    context: WorkerLifecycleContext,
    action: Callable[..., object],
    *args: object,
) -> None:
    with context.boundary:
        action(*args)


def _checkpoint_cleanup_progress() -> None:
    """Keep post-store control injection inside the active cleanup boundary."""


def _terminate_process_group(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> bool:
    term_deadline: float | None = None
    term_delivered = False
    term_proved = False
    with context.boundary:
        started = _read_clock(context)
        term_deadline = None if started is None else started + context.grace_seconds
        term_delivered = _attempt_signal(
            context,
            process,
            signal.SIGTERM,
            deadline=term_deadline,
            retry_failures=False,
        )
        _checkpoint_cleanup_progress()
    if term_delivered and term_deadline is not None:
        with context.boundary:
            if _wait_until(term_deadline, context):
                _observe_child(context, process)
                term_proved = _no_live_proved(context.state, _probe_group(context, process))
                _checkpoint_cleanup_progress()
    if term_proved:
        return True
    kill_deadline: float | None = None
    with context.boundary:
        started = _read_clock(context)
        kill_deadline = None if started is None else started + context.grace_seconds
        _attempt_signal(
            context,
            process,
            signal.SIGKILL,
            deadline=kill_deadline,
            retry_failures=True,
        )
        _checkpoint_cleanup_progress()
    no_live_proved = False
    with context.boundary:
        if kill_deadline is None:
            _observe_child(context, process)
            no_live_proved = _no_live_proved(context.state, _probe_group(context, process))
            if not no_live_proved:
                context.state.cleanup_failed = True
        else:
            no_live_proved = _prove_after_kill(context, process, kill_deadline)
        _checkpoint_cleanup_progress()
    return no_live_proved


def _attempt_signal(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
    signal_number: int,
    *,
    deadline: float | None,
    retry_failures: bool,
) -> bool:
    for attempt in range(_MAX_INTERRUPTED_ATTEMPTS):
        outcome = _send_signal_once(context, process, signal_number)
        if outcome in {"delivered", "absent"}:
            return True
        if outcome == "denied":
            if _probe_group(context, process) not in _ACCEPTED_STATES:
                context.state.cleanup_failed = True
                break
            return True
        if outcome == "failed" and not retry_failures:
            break
        if not _retry_before_deadline(context, deadline, attempt):
            break
    context.state.cleanup_failed = True
    return False


def _record_cleanup_capability_failure(
    context: WorkerLifecycleContext,
    error: Exception,
) -> None:
    context.state.cleanup_cause = "capability_failed"
    context.owner.record_failure(context.state, error)


def _send_signal_once(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
    signal_number: int,
) -> str:
    outcome = "failed"
    with context.boundary:
        try:
            context.send_group_signal(process.pid, signal_number)
        except InterruptedError:
            outcome = "interrupted"
        except ProcessLookupError:
            outcome = "absent"
        except PermissionError:
            outcome = "denied"
        except (WorkerIsolationUnsupportedError, AttributeError, OSError, ValueError) as error:
            _record_cleanup_capability_failure(context, error)
        else:
            outcome = "delivered"
    return outcome


def _retry_before_deadline(
    context: WorkerLifecycleContext,
    deadline: float | None,
    attempt: int,
) -> bool:
    if attempt + 1 >= _MAX_INTERRUPTED_ATTEMPTS or deadline is None:
        context.state.cleanup_failed = True
        return False
    now = _read_clock(context)
    if now is None or now >= deadline:
        context.state.cleanup_failed = True
        return False
    return True


def _prove_after_kill(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
    deadline: float,
) -> bool:
    while True:
        _observe_child(context, process)
        if _no_live_proved(context.state, _probe_group(context, process)):
            return True
        now = _read_clock(context)
        if now is None or now >= deadline:
            context.state.cleanup_failed = True
            return False
        if not _wait_until(deadline, context):
            return False


def _probe_group(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> WorkerProcessGroupState | None:
    observed: WorkerProcessGroupState | None = None
    with context.boundary:
        try:
            observed = context.probe_process_group(
                process.pid,
                direct_child_terminal=context.state.returncode is not None,
            )
        except (WorkerIsolationUnsupportedError, AttributeError, OSError, ValueError) as error:
            _record_cleanup_capability_failure(context, error)
    return observed


def _observe_child(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> None:
    returncode = None
    with context.boundary:
        try:
            returncode = context.observe_direct_child(process)
        except (WorkerIsolationUnsupportedError, AttributeError, OSError, ValueError) as error:
            _record_cleanup_capability_failure(context, error)
    if returncode is not None:
        if context.state.returncode is not None and context.state.returncode != returncode:
            context.state.cleanup_failed = True
        context.state.returncode = returncode


def _no_live_proved(
    state: _CleanupState,
    observed: WorkerProcessGroupState | None,
) -> bool:
    return observed is WorkerProcessGroupState.ABSENT or (
        state.returncode is not None and observed is WorkerProcessGroupState.TERMINAL_ONLY
    )


def _wait_until(deadline: float, context: WorkerLifecycleContext) -> bool:
    for _attempt in range(_MAX_INTERRUPTED_ATTEMPTS):
        result = _wait_once(deadline, context)
        if result is not None:
            return result
    context.state.cleanup_failed = True
    return False


def _wait_once(deadline: float, context: WorkerLifecycleContext) -> bool | None:
    before = _read_clock(context)
    if before is None:
        return False
    remaining = deadline - before
    if remaining <= 0:
        return True
    interrupted = False
    waited = False
    with context.boundary:
        try:
            context.wait_for(remaining)
        except InterruptedError:
            interrupted = True
        else:
            waited = True
    if interrupted:
        return None
    if not waited:
        return False
    after = _read_clock(context)
    if after is None or after <= before:
        if after is not None:
            context.state.cleanup_failed = True
        return False
    return True if after >= deadline else None


def _read_clock(context: WorkerLifecycleContext) -> float | None:
    with context.boundary:
        return context.monotonic()
    return None


def _close_selector(
    context: WorkerLifecycleContext,
    selector: selectors.BaseSelector | None,
) -> None:
    if selector is None:
        return
    with context.boundary:
        selector.close()


def _close_parent_pipes(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> None:
    for pipe in (process.stdin, process.stdout):
        if pipe is None or pipe.closed:
            continue
        with context.boundary:
            pipe.close()


def _reap_direct_child(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> None:
    started = _read_clock(context)
    deadline = None if started is None else started + context.grace_seconds * _MAX_REAP_ATTEMPTS
    for _attempt in range(_MAX_REAP_ATTEMPTS):
        timeout = _remaining_reap_timeout(context, deadline)
        if timeout is None:
            return
        completed = False
        returncode = 0
        with context.boundary:
            try:
                returncode = process.wait(timeout=timeout)
            except InterruptedError:
                pass
            except subprocess.TimeoutExpired as error:
                context.owner.record_failure(context.state, error)
            except (WorkerIsolationUnsupportedError, AttributeError, OSError, ValueError) as error:
                _record_cleanup_capability_failure(context, error)
            else:
                completed = True
        if completed:
            if context.state.returncode is not None and context.state.returncode != returncode:
                context.state.cleanup_failed = True
            context.state.returncode = returncode
            return
    context.state.cleanup_failed = True


def _remaining_reap_timeout(
    context: WorkerLifecycleContext,
    deadline: float | None,
) -> float | None:
    if deadline is None:
        context.state.cleanup_failed = True
        return None
    now = _read_clock(context)
    if now is None or now >= deadline:
        context.state.cleanup_failed = True
        return None
    return min(context.grace_seconds, deadline - now)


def _remove_private_directory(
    context: WorkerLifecycleContext,
    private_directory: Path,
) -> None:
    with context.boundary:
        context.remove_directory(private_directory)

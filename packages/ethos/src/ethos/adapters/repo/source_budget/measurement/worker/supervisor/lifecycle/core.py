"""Ordered process-group cleanup for one isolated worker."""

from __future__ import annotations

import shutil
import stat
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import Protocol

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.cleanup import (
    cleanup_owned_resources,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.cleanup import (
    cleanup_unbound_process,
)

if TYPE_CHECKING:
    import selectors
    from contextlib import AbstractContextManager
    from types import TracebackType

_Monotonic = Callable[[], float]
_GroupSignal = Callable[[int, int], None]
_PRIVATE_DIRECTORY_PREFIX = "ethos-source-budget-worker-"
_PRIVATE_DIRECTORY_MODE = 0o700
_PRIVATE_MODE_ERROR = "worker private directory mode unavailable"
_PROCESS_RESOURCE = "process"
_SELECTOR_RESOURCE = "selector"
_EXCHANGE_RESOURCE = "exchange"
_CLEANUP_WAIT_MULTIPLIER = 8
_MAX_STATE_PUBLICATION_ATTEMPTS = 2
_MAX_PRE_ACTION_ATTEMPTS = 2
_ProcessAcquisitionState = Literal[
    "idle",
    "pending",
    "published",
    "resolved_safe",
    "resolved_unsafe",
]
_FinishAction = Literal[
    "retry",
    "return",
    "cleanup",
    "wait_cleanup",
    "wait_acquisition",
]

CleanupCause = Literal["capability_failed"]
CleanupWait = Callable[[float], None]
ProcessGroupProbe = Callable[..., WorkerProcessGroupState]


def bind_worker_process(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes],
) -> None:
    """Publish a spawned process, retrying same-identity completion once."""
    try:
        context.owner.bind_process(process)
    except BaseException:
        with context.boundary:
            context.owner.bind_process(process)
        raise


def resolve_worker_process_acquisition(
    context: WorkerLifecycleContext,
    process: subprocess.Popen[bytes] | None,
    *,
    no_process_is_safe: bool,
    active_error: BaseException | None = None,
) -> None:
    """Settle failed publication without losing destructive-cleanup proof."""
    owner = context.owner
    if process is not None and owner.process is process:
        with context.boundary:
            owner.bind_process(process)
        return
    if owner.process_acquisition_state != "pending":
        return
    safe_to_remove_directory = no_process_is_safe
    if process is not None:
        try:
            safe_to_remove_directory = cleanup_unbound_process(context, process)
            _checkpoint_lifecycle_progress()
        except BaseException as error:
            owner.record_failure(context.state, error)
            with context.boundary:
                owner.resolve_process_acquisition(
                    safe_to_remove_directory=safe_to_remove_directory,
                )
            if active_error is None:
                raise
            return
    try:
        owner.resolve_process_acquisition(
            safe_to_remove_directory=safe_to_remove_directory,
        )
    except BaseException as error:
        owner.record_failure(context.state, error)
        expected_state = "resolved_safe" if safe_to_remove_directory else "resolved_unsafe"
        with context.boundary:
            if owner.process_acquisition_state != expected_state and owner.process is None:
                owner.resolve_process_acquisition(
                    safe_to_remove_directory=safe_to_remove_directory,
                )
        if active_error is None:
            raise


def acquire_worker_selector(
    context: WorkerLifecycleContext,
    selector_factory: Callable[[], selectors.BaseSelector],
) -> selectors.BaseSelector:
    """Claim, allocate, and publish one selector or close its local handle."""
    selector: selectors.BaseSelector | None = None
    try:
        context.owner.claim_exchange()
        selector = selector_factory()
        context.owner.bind_selector(selector)
    except BaseException:
        if selector is not None and context.owner.selector is not selector:
            _close_unbound_selector(context, selector)
        raise
    return selector


def _close_unbound_selector(
    context: WorkerLifecycleContext,
    selector: selectors.BaseSelector,
) -> None:
    with context.boundary:
        selector.close()


def create_private_directory() -> Path:
    """Create and verify the private worker directory before lifecycle allocation."""
    directory = Path(tempfile.mkdtemp(prefix=_PRIVATE_DIRECTORY_PREFIX))
    try:
        directory.chmod(_PRIVATE_DIRECTORY_MODE)
        mode = stat.S_IMODE(directory.stat().st_mode)
    except OSError:
        discard_unstarted_directory(directory)
        raise
    if mode != _PRIVATE_DIRECTORY_MODE:
        discard_unstarted_directory(directory)
        raise RuntimeError(_PRIVATE_MODE_ERROR)
    return directory


def discard_unstarted_directory(directory: Path) -> None:
    """Remove a private directory that never entered lifecycle ownership."""
    with suppress(OSError):
        shutil.rmtree(directory)


class _CleanupState(Protocol):
    returncode: int | None
    cleanup_cause: CleanupCause | None
    cleanup_failed: bool


_ObserveChild = Callable[[subprocess.Popen[bytes]], int | None]


class _LifecycleCleanupStartedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("worker lifecycle cleanup already started")


class _LifecycleAlreadyBoundError(RuntimeError):
    def __init__(self, resource: str) -> None:
        super().__init__(f"worker {resource} already bound")


class _LifecycleCleanupIncompleteError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("worker lifecycle cleanup did not complete")


class _LifecycleAcquisitionIncompleteError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("worker process acquisition did not complete")


@dataclass(slots=True)
class WorkerLifecycleOwner:
    """Pre-spawn bind-once resources owned by one serialized cleanup sequence."""

    private_directory: Path
    _process: subprocess.Popen[bytes] | None = None
    _selector: selectors.BaseSelector | None = None
    _process_acquisition_state: _ProcessAcquisitionState = "idle"
    _process_acquisition_thread: int | None = None
    _cleanup_state: str = "open"
    _exchange_claimed: bool = False
    _cleanup_lock: AbstractContextManager[object] = field(
        default_factory=threading.RLock,
        repr=False,
    )
    _cleanup_complete: threading.Event = field(default_factory=threading.Event, repr=False)
    _process_acquisition_complete: threading.Event = field(
        default_factory=threading.Event,
        repr=False,
    )
    _cleanup_thread: int | None = None
    _control_error: BaseException | None = None

    @property
    def process(self) -> subprocess.Popen[bytes] | None:
        """Return the exact process owned by this lifecycle."""
        return self._process

    @property
    def selector(self) -> selectors.BaseSelector | None:
        """Return the exact selector owned by this lifecycle."""
        return self._selector

    @property
    def process_acquisition_state(self) -> _ProcessAcquisitionState:
        """Return the spawn/publication state used by destructive cleanup."""
        return self._process_acquisition_state

    def begin_process_acquisition(self) -> None:
        """Declare one in-flight process acquisition before invoking Popen."""
        with self._cleanup_lock:
            if self._cleanup_state != "open":
                raise _LifecycleCleanupStartedError
            if self._process_acquisition_state != "idle":
                raise _LifecycleAlreadyBoundError(_PROCESS_RESOURCE)
            self._process_acquisition_state = "pending"
            self._process_acquisition_thread = threading.get_ident()
            self._process_acquisition_complete.clear()

    def bind_process(self, process: subprocess.Popen[bytes]) -> None:
        """Bind one process identity before later process-dependent allocation."""
        with self._cleanup_lock:
            if self._cleanup_state != "open":
                raise _LifecycleCleanupStartedError
            if self._process is not None and self._process is not process:
                raise _LifecycleAlreadyBoundError(_PROCESS_RESOURCE)
            if self._process_acquisition_state in {"resolved_safe", "resolved_unsafe"}:
                raise _LifecycleAlreadyBoundError(_PROCESS_RESOURCE)
            self._process = process
            self._process_acquisition_state = "published"
            self._process_acquisition_thread = None
            self._process_acquisition_complete.set()

    def publish_process(self, process: subprocess.Popen[bytes]) -> None:
        """Complete process publication; same-identity retries are idempotent."""
        self.bind_process(process)

    def resolve_process_acquisition(self, *, safe_to_remove_directory: bool) -> None:
        """Resolve an unbound acquisition with its final no-live proof."""
        with self._cleanup_lock:
            if self._cleanup_state != "open":
                raise _LifecycleCleanupStartedError
            if self._process_acquisition_state != "pending" or self._process is not None:
                raise _LifecycleAlreadyBoundError(_PROCESS_RESOURCE)
            self._process_acquisition_state = (
                "resolved_safe" if safe_to_remove_directory else "resolved_unsafe"
            )
            self._process_acquisition_thread = None
            self._process_acquisition_complete.set()

    def bind_selector(self, selector: selectors.BaseSelector) -> None:
        """Bind one selector identity before allocating exchange context."""
        with self._cleanup_lock:
            if self._cleanup_state != "open":
                raise _LifecycleCleanupStartedError
            if self._selector is not None and self._selector is not selector:
                raise _LifecycleAlreadyBoundError(_SELECTOR_RESOURCE)
            self._selector = selector

    def claim_exchange(self) -> None:
        """Claim this one-shot session before allocating an exchange selector."""
        with self._cleanup_lock:
            if self._cleanup_state != "open":
                raise _LifecycleCleanupStartedError
            if self._exchange_claimed:
                raise _LifecycleAlreadyBoundError(_EXCHANGE_RESOURCE)
            self._exchange_claimed = True

    def _mark_cleanup_running(self, thread_id: int) -> None:
        self._cleanup_thread = thread_id
        self._cleanup_state = "running"

    def record_failure(self, state: _CleanupState, error: BaseException) -> None:
        """Record one cleanup failure and preserve the first control exception."""
        state.cleanup_failed = True
        if not isinstance(error, Exception) and self._control_error is None:
            self._control_error = error

    def _finish_action(
        self,
        current_thread: int,
        state: _CleanupState,
    ) -> _FinishAction:
        if self._cleanup_state == "done":
            return "return"
        if self._cleanup_state == "running":
            return "return" if self._cleanup_thread == current_thread else "wait_cleanup"
        if self._process_acquisition_state == "pending" and self._process is None:
            if self._process_acquisition_thread == current_thread:
                state.cleanup_failed = True
                raise _LifecycleAcquisitionIncompleteError
            return "wait_acquisition"
        if self._process_acquisition_state == "pending":
            self._process_acquisition_state = "published"
            self._process_acquisition_thread = None
            self._process_acquisition_complete.set()
        return "cleanup"

    def _await_process_acquisition(self, context: WorkerLifecycleContext) -> None:
        completed = self._process_acquisition_complete.wait(_process_acquisition_timeout(context))
        if completed:
            return
        with self._cleanup_lock:
            unresolved = self._process_acquisition_state == "pending" and self._process is None
        if unresolved:
            context.state.cleanup_failed = True
            raise _LifecycleAcquisitionIncompleteError

    def _await_cleanup(self, context: WorkerLifecycleContext) -> None:
        completed = self._cleanup_complete.wait(_cleanup_completion_timeout(context))
        if completed:
            return
        with self._cleanup_lock:
            incomplete = self._cleanup_state != "done"
        if incomplete:
            context.state.cleanup_failed = True
            raise _LifecycleCleanupIncompleteError

    def _publish_cleanup_terminal(
        self,
        context: WorkerLifecycleContext,
    ) -> BaseException | None:
        published = False
        control_error: BaseException | None = None
        for _attempt in range(_MAX_STATE_PUBLICATION_ATTEMPTS):
            with context.boundary, self._cleanup_lock:
                self._cleanup_state = "done"
                _checkpoint_lifecycle_progress()
                self._cleanup_thread = None
                control_error = self._control_error
                published = True
                _checkpoint_lifecycle_progress()
            if published:
                break
        if published:
            self._cleanup_complete.set()
            return control_error
        context.state.cleanup_failed = True
        return self._control_error or _LifecycleCleanupIncompleteError()

    def finish(self, context: WorkerLifecycleContext) -> None:
        """Serialize and complete this owner's cleanup order exactly once."""
        current_thread = threading.get_ident()
        pre_action_attempts = 0
        while True:
            process: subprocess.Popen[bytes] | None = None
            selector: selectors.BaseSelector | None = None
            cleanup_runner = False
            action: _FinishAction = "retry"
            control_error: BaseException | None = None
            safe_to_remove_directory = False
            try:
                with self._cleanup_lock:
                    with context.boundary:
                        action = self._finish_action(current_thread, context.state)
                        _checkpoint_lifecycle_progress()
                    if action == "return":
                        return
                    if action == "cleanup":
                        process, selector = self._process, self._selector
                        safe_to_remove_directory = process is not None or (
                            self._process_acquisition_state in {"idle", "resolved_safe"}
                        )
                        cleanup_runner = True
                        self._mark_cleanup_running(current_thread)
            finally:
                if cleanup_runner:
                    try:
                        cleanup_owned_resources(
                            context,
                            process,
                            selector,
                            safe_to_remove_directory=safe_to_remove_directory,
                        )
                    finally:
                        control_error = self._publish_cleanup_terminal(context)
            if action == "retry":
                pre_action_attempts += 1
                if pre_action_attempts >= _MAX_PRE_ACTION_ATTEMPTS:
                    context.state.cleanup_failed = True
                    raise self._control_error or _LifecycleCleanupIncompleteError()
                continue
            if action == "wait_acquisition":
                self._await_process_acquisition(context)
                continue
            if action == "wait_cleanup":
                self._await_cleanup(context)
                return
            if control_error is not None:
                raise control_error
            return


@dataclass(frozen=True, slots=True)
class WorkerLifecycleBoundary:
    """Preallocated exception-total boundary reused by every cleanup phase."""

    owner: WorkerLifecycleOwner
    state: _CleanupState

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        t: type[BaseException] | None,
        v: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        del t, tb
        if v is None:
            return False
        self.owner.record_failure(self.state, v)
        return True


@dataclass(frozen=True, slots=True)
class WorkerLifecycleContext:
    """Pre-spawn immutable cleanup policy around one mutable resource owner."""

    owner: WorkerLifecycleOwner
    state: _CleanupState
    boundary: WorkerLifecycleBoundary
    grace_seconds: float
    send_group_signal: _GroupSignal
    probe_process_group: ProcessGroupProbe
    observe_direct_child: _ObserveChild
    monotonic: _Monotonic
    wait_for: CleanupWait
    remove_directory: Callable[[Path], None]


def wait_for_cleanup_timeout(seconds: float) -> None:
    """Yield without file descriptors for one bounded cleanup interval."""
    time.sleep(max(0.0, seconds))


def _checkpoint_lifecycle_progress() -> None:
    """Keep post-store control injection inside the active lifecycle boundary."""


def _cleanup_completion_timeout(context: WorkerLifecycleContext) -> float:
    return context.grace_seconds * _CLEANUP_WAIT_MULTIPLIER


def _process_acquisition_timeout(context: WorkerLifecycleContext) -> float:
    return _cleanup_completion_timeout(context)


def finish_worker_process(
    context: WorkerLifecycleContext,
    active_error: BaseException | None = None,
) -> None:
    """Serialize and complete the full cleanup order exactly once."""
    try:
        context.owner.finish(context)
    except BaseException:
        if active_error is None:
            raise

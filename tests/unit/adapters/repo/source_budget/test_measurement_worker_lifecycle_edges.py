"""Deterministic edge coverage for worker cleanup and lifecycle ownership."""

from __future__ import annotations

import signal
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import Protocol
from typing import cast

import pytest

import ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.cleanup as cleanup
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core as lifecycle
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from tests.support.source_budget_worker import WorkerProcess

if TYPE_CHECKING:
    import selectors
    from collections.abc import Callable
    from subprocess import Popen

_SPIN_ERROR = "finish pre-action spin detected"
_PUBLISH_ERROR = "publish"
_RETRY_ERROR = "retry"
_PERMANENT_PRE_ACTION_ERROR = "permanent pre-action failure"
_CLEANUP_STATE_ATTR = "_cleanup_state"
_PROCESS_ATTR = "_process"
_CLEANUP_LOCK_ATTR = "_cleanup_lock"


def _raise(error: BaseException) -> NoReturn:
    raise error


def _process(events: list[str] | None = None) -> Popen[bytes]:
    return cast("Popen[bytes]", WorkerProcess([] if events is None else events))


class _LoopGuard:
    def __init__(self, limit: int = 3) -> None:
        self.entries = 0
        self.limit = limit

    def __enter__(self) -> _LoopGuard:
        self.entries += 1
        if self.entries > self.limit:
            raise _SpinDetectedError
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


class _SpinDetectedError(AssertionError):
    def __init__(self) -> None:
        super().__init__(_SPIN_ERROR)


class _CleanupStateView(Protocol):
    returncode: int | None
    cleanup_cause: lifecycle.CleanupCause | None
    cleanup_failed: bool


@dataclass(frozen=True, slots=True)
class _LifecycleCase:
    context: lifecycle.WorkerLifecycleContext
    state: _CleanupStateView
    owner: lifecycle.WorkerLifecycleOwner


@dataclass(frozen=True, slots=True)
class _CaseOptions:
    monotonic: Callable[[], float] = lambda: 0.0
    send: Callable[[int, int], None] = lambda _pid, _signal: None
    probe: Callable[..., WorkerProcessGroupState] = lambda _pid, **_kwargs: (
        WorkerProcessGroupState.ABSENT
    )
    observe: Callable[[Popen[bytes]], int | None] = lambda _process: 0
    wait: Callable[[float], None] = lambda _seconds: None
    grace_seconds: float = 0.1


_DEFAULT_CASE_OPTIONS = _CaseOptions()


def _case(
    private: Path,
    options: _CaseOptions = _DEFAULT_CASE_OPTIONS,
) -> _LifecycleCase:
    private.mkdir(exist_ok=True)
    state = cast("_CleanupStateView", lifecycle.WorkerExchangeState())
    owner = lifecycle.WorkerLifecycleOwner(private)
    boundary = lifecycle.WorkerLifecycleBoundary(owner, state)
    context = lifecycle.WorkerLifecycleContext(
        owner=owner,
        state=state,
        boundary=boundary,
        grace_seconds=options.grace_seconds,
        send_group_signal=options.send,
        probe_process_group=options.probe,
        observe_direct_child=options.observe,
        monotonic=options.monotonic,
        wait_for=options.wait,
        remove_directory=lambda path: path.rmdir(),
    )
    return _LifecycleCase(context=context, state=state, owner=owner)


@pytest.mark.parametrize(
    ("observed", "proved"),
    [(WorkerProcessGroupState.ABSENT, True), (WorkerProcessGroupState.LIVE, False)],
)
def test_termination_handles_missing_clock_with_final_probe(
    tmp_path: Path,
    observed: WorkerProcessGroupState,
    proved: object,
) -> None:
    signals: list[int] = []
    case = _case(
        tmp_path / observed.value,
        _CaseOptions(
            monotonic=lambda: _raise(RuntimeError("clock")),
            send=lambda _pid, number: signals.append(number),
            probe=lambda *_args, **_kwargs: observed,
        ),
    )

    result = vars(cleanup)["_terminate_process_group"](case.context, _process())

    assert result is proved
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert case.state.cleanup_failed is True


def test_signal_denial_with_live_group_fails_cleanup(tmp_path: Path) -> None:
    case = _case(
        tmp_path / "denied",
        _CaseOptions(
            send=lambda *_args: _raise(PermissionError()),
            probe=lambda *_args, **_kwargs: WorkerProcessGroupState.LIVE,
        ),
    )
    delivered = vars(cleanup)["_attempt_signal"](
        case.context,
        _process(),
        signal.SIGTERM,
        deadline=1.0,
        retry_failures=False,
    )
    assert delivered is False
    assert case.state.cleanup_failed is True


def test_signal_attempt_has_a_natural_finite_loop_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "signal-loop")
    monkeypatch.setattr(cleanup, "_send_signal_once", lambda *_args: "interrupted")
    monkeypatch.setattr(cleanup, "_retry_before_deadline", lambda *_args: True)
    delivered = vars(cleanup)["_attempt_signal"](
        case.context,
        _process(),
        signal.SIGKILL,
        deadline=1.0,
        retry_failures=True,
    )
    assert delivered is False
    assert case.state.cleanup_failed is True


def test_process_lookup_signal_is_already_absent(tmp_path: Path) -> None:
    case = _case(
        tmp_path / "absent",
        _CaseOptions(send=lambda *_args: _raise(ProcessLookupError())),
    )
    outcome = vars(cleanup)["_send_signal_once"](case.context, _process(), signal.SIGTERM)
    assert outcome == "absent"


def test_retry_rejects_an_expired_deadline(tmp_path: Path) -> None:
    case = _case(tmp_path / "retry-expired", _CaseOptions(monotonic=lambda: 2.0))
    assert vars(cleanup)["_retry_before_deadline"](case.context, 1.0, 0) is False
    assert case.state.cleanup_failed is True


def test_child_observation_maps_capability_failure_and_conflicting_status(
    tmp_path: Path,
) -> None:
    probe_failed = _case(
        tmp_path / "probe-failed",
        _CaseOptions(probe=lambda *_args, **_kwargs: _raise(OSError("probe"))),
    )
    assert vars(cleanup)["_probe_group"](probe_failed.context, _process()) is None
    assert probe_failed.state.cleanup_cause == "capability_failed"

    failed = _case(
        tmp_path / "observe-failed",
        _CaseOptions(observe=lambda _process: _raise(OSError("observe"))),
    )
    vars(cleanup)["_observe_child"](failed.context, _process())
    assert failed.state.cleanup_cause == "capability_failed"

    conflict = _case(
        tmp_path / "observe-conflict",
        _CaseOptions(observe=lambda _process: 2),
    )
    conflict.state.returncode = 1
    vars(cleanup)["_observe_child"](conflict.context, _process())
    assert conflict.state.returncode == 2
    assert conflict.state.cleanup_failed is True


def test_wait_until_exhausts_exact_interrupted_attempt_budget(tmp_path: Path) -> None:
    case = _case(
        tmp_path / "wait-interrupted",
        _CaseOptions(wait=lambda _seconds: _raise(InterruptedError())),
    )
    assert vars(cleanup)["_wait_until"](1.0, case.context) is False
    assert case.state.cleanup_failed is True


def test_wait_once_handles_missing_expired_interrupted_and_stalled_clocks(
    tmp_path: Path,
) -> None:
    missing = _case(
        tmp_path / "clock-missing",
        _CaseOptions(monotonic=lambda: _raise(RuntimeError("clock"))),
    )
    assert vars(cleanup)["_wait_once"](1.0, missing.context) is False

    expired = _case(tmp_path / "clock-expired", _CaseOptions(monotonic=lambda: 1.0))
    assert vars(cleanup)["_wait_once"](1.0, expired.context) is True

    interrupted = _case(
        tmp_path / "wait-once-interrupted",
        _CaseOptions(wait=lambda _seconds: _raise(InterruptedError())),
    )
    assert vars(cleanup)["_wait_once"](1.0, interrupted.context) is None

    stalled = _case(tmp_path / "clock-stalled", _CaseOptions(monotonic=lambda: 0.0))
    assert vars(cleanup)["_wait_once"](1.0, stalled.context) is False
    assert stalled.state.cleanup_failed is True

    ticks = iter((0.0, RuntimeError("after")))
    missing_after = _case(
        tmp_path / "clock-after-missing",
        _CaseOptions(
            monotonic=lambda: (
                _raise(value) if isinstance((value := next(ticks)), BaseException) else value
            )
        ),
    )
    assert vars(cleanup)["_wait_once"](1.0, missing_after.context) is False


@pytest.mark.parametrize("failure", [InterruptedError(), OSError("wait")])
def test_reap_retries_interrupt_or_capability_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: Exception,
) -> None:
    case = _case(tmp_path / type(failure).__name__.lower())
    process = cast("Popen[bytes]", WorkerProcess([]))
    attempts = 0

    def wait(timeout: float | None = None) -> int:
        del timeout
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise failure
        return 0

    monkeypatch.setattr(process, "wait", wait)
    vars(cleanup)["_reap_direct_child"](case.context, process)
    assert attempts == 2
    if type(failure) is OSError:
        assert case.state.cleanup_cause == "capability_failed"


def test_reap_handles_missing_clock_conflict_and_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = _case(
        tmp_path / "reap-clock-missing",
        _CaseOptions(monotonic=lambda: _raise(RuntimeError("clock"))),
    )
    vars(cleanup)["_reap_direct_child"](missing.context, _process())
    assert missing.state.cleanup_failed is True

    conflict = _case(tmp_path / "reap-conflict")
    conflict.state.returncode = 1
    process = _process()

    def conflicting_wait(timeout: float | None = None) -> int:
        del timeout
        return 2

    monkeypatch.setattr(process, "wait", conflicting_wait)
    vars(cleanup)["_reap_direct_child"](conflict.context, process)
    assert conflict.state.returncode == 2
    assert conflict.state.cleanup_failed is True

    exhausted = _case(tmp_path / "reap-exhausted")
    timed_out = _process()
    timed_out.wait = lambda timeout=None: _raise(subprocess.TimeoutExpired("worker", timeout))
    vars(cleanup)["_reap_direct_child"](exhausted.context, timed_out)
    assert exhausted.state.cleanup_failed is True


def test_remaining_reap_timeout_rejects_absent_or_expired_deadline(tmp_path: Path) -> None:
    absent = _case(tmp_path / "reap-no-deadline")
    assert vars(cleanup)["_remaining_reap_timeout"](absent.context, None) is None
    expired = _case(tmp_path / "reap-deadline", _CaseOptions(monotonic=lambda: 2.0))
    assert vars(cleanup)["_remaining_reap_timeout"](expired.context, 1.0) is None


def test_resolve_acquisition_returns_when_no_publication_is_pending(tmp_path: Path) -> None:
    case = _case(tmp_path / "resolve-idle")
    lifecycle.resolve_worker_process_acquisition(
        case.context,
        None,
        no_process_is_safe=True,
    )
    assert case.owner.process_acquisition_state == "idle"


def test_unbound_cleanup_failure_is_settled_then_reraised(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "resolve-cleanup-failure")
    case.owner.begin_process_acquisition()
    monkeypatch.setattr(
        lifecycle,
        "cleanup_unbound_process",
        lambda *_args: _raise(KeyboardInterrupt("cleanup")),
    )
    with pytest.raises(KeyboardInterrupt, match="cleanup"):
        lifecycle.resolve_worker_process_acquisition(
            case.context,
            _process(),
            no_process_is_safe=False,
        )
    assert case.owner.process_acquisition_state == "resolved_unsafe"


def test_resolution_publication_retry_preserves_primary_or_reraises_control(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = lifecycle.WorkerLifecycleOwner.resolve_process_acquisition
    reraised = _case(tmp_path / "resolve-reraise")
    reraised.owner.begin_process_acquisition()
    calls = 0

    def fail_then_publish(
        owner: lifecycle.WorkerLifecycleOwner,
        *,
        safe_to_remove_directory: bool,
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise KeyboardInterrupt(_PUBLISH_ERROR)
        original(owner, safe_to_remove_directory=safe_to_remove_directory)

    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "resolve_process_acquisition",
        fail_then_publish,
    )
    with pytest.raises(KeyboardInterrupt, match="publish"):
        lifecycle.resolve_worker_process_acquisition(
            reraised.context,
            None,
            no_process_is_safe=True,
        )
    assert reraised.owner.process_acquisition_state == "resolved_safe"

    preserved = _case(tmp_path / "resolve-primary")
    preserved.owner.begin_process_acquisition()

    def publish_then_fail(
        owner: lifecycle.WorkerLifecycleOwner,
        *,
        safe_to_remove_directory: bool,
    ) -> None:
        original(owner, safe_to_remove_directory=safe_to_remove_directory)
        raise KeyboardInterrupt(_PUBLISH_ERROR)

    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "resolve_process_acquisition",
        publish_then_fail,
    )
    lifecycle.resolve_worker_process_acquisition(
        preserved.context,
        None,
        no_process_is_safe=True,
        active_error=SystemExit("primary"),
    )
    assert preserved.owner.process_acquisition_state == "resolved_safe"


def test_private_directory_creation_removes_chmod_or_mode_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    chmod_failed = tmp_path / "chmod-failed"
    chmod_failed.mkdir()
    monkeypatch.setattr(lifecycle.tempfile, "mkdtemp", lambda **_kwargs: str(chmod_failed))
    monkeypatch.setattr(Path, "chmod", lambda *_args, **_kwargs: _raise(OSError("chmod")))
    with pytest.raises(OSError, match="chmod"):
        lifecycle.create_private_directory()
    assert not chmod_failed.exists()

    monkeypatch.undo()
    mode_failed = tmp_path / "mode-failed"
    mode_failed.mkdir()
    monkeypatch.setattr(lifecycle.tempfile, "mkdtemp", lambda **_kwargs: str(mode_failed))
    monkeypatch.setattr(lifecycle.stat, "S_IMODE", lambda _mode: 0)
    with pytest.raises(RuntimeError, match="mode unavailable"):
        lifecycle.create_private_directory()
    assert not mode_failed.exists()


def test_lifecycle_owner_rejects_invalid_binding_transitions(tmp_path: Path) -> None:
    started = lifecycle.WorkerLifecycleOwner(tmp_path / "started")
    setattr(started, _CLEANUP_STATE_ATTR, "done")
    with pytest.raises(RuntimeError, match="cleanup already started"):
        started.begin_process_acquisition()
    with pytest.raises(RuntimeError, match="cleanup already started"):
        started.bind_process(_process())
    with pytest.raises(RuntimeError, match="cleanup already started"):
        started.resolve_process_acquisition(safe_to_remove_directory=True)

    repeated = lifecycle.WorkerLifecycleOwner(tmp_path / "repeated")
    repeated.begin_process_acquisition()
    with pytest.raises(RuntimeError, match="already bound"):
        repeated.begin_process_acquisition()

    resolved = lifecycle.WorkerLifecycleOwner(tmp_path / "resolved")
    resolved.begin_process_acquisition()
    resolved.resolve_process_acquisition(safe_to_remove_directory=True)
    with pytest.raises(RuntimeError, match="already bound"):
        resolved.bind_process(_process())
    with pytest.raises(RuntimeError, match="already bound"):
        resolved.resolve_process_acquisition(safe_to_remove_directory=True)

    selector = lifecycle.WorkerLifecycleOwner(tmp_path / "selector")
    selector.bind_selector(cast("selectors.BaseSelector", object()))
    with pytest.raises(RuntimeError, match="already bound"):
        selector.bind_selector(cast("selectors.BaseSelector", object()))
    selector.claim_exchange()
    with pytest.raises(RuntimeError, match="already bound"):
        selector.claim_exchange()


def test_finish_action_rejects_same_thread_gap_and_publishes_visible_process(
    tmp_path: Path,
) -> None:
    incomplete = _case(tmp_path / "same-thread")
    incomplete.owner.begin_process_acquisition()
    finish_action = vars(type(incomplete.owner))["_finish_action"]
    with pytest.raises(RuntimeError, match="did not complete"):
        finish_action(incomplete.owner, threading.get_ident(), incomplete.state)

    published = _case(tmp_path / "visible-process")
    published.owner.begin_process_acquisition()
    setattr(published.owner, _PROCESS_ATTR, _process())
    action = finish_action(published.owner, threading.get_ident() + 1, published.state)
    assert action == "cleanup"
    assert published.owner.process_acquisition_state == "published"


def test_cleanup_wait_and_terminal_publication_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    waiting = _case(tmp_path / "cleanup-wait", _CaseOptions(grace_seconds=0.0))
    setattr(waiting.owner, _CLEANUP_STATE_ATTR, "running")
    await_cleanup = vars(type(waiting.owner))["_await_cleanup"]
    with pytest.raises(RuntimeError, match="cleanup did not complete"):
        await_cleanup(waiting.owner, waiting.context)

    publication = _case(tmp_path / "publish-terminal")
    monkeypatch.setattr(
        lifecycle,
        "_checkpoint_lifecycle_progress",
        lambda: _raise(KeyboardInterrupt(_PUBLISH_ERROR)),
    )
    publish_terminal = vars(type(publication.owner))["_publish_cleanup_terminal"]
    error = publish_terminal(publication.owner, publication.context)
    assert isinstance(error, KeyboardInterrupt)
    assert publication.state.cleanup_failed is True


def test_finish_rejects_same_thread_unpublished_acquisition_without_spin(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "finish-same-thread")
    case.owner.begin_process_acquisition()
    guard = _LoopGuard()
    setattr(case.owner, _CLEANUP_LOCK_ATTR, guard)

    with pytest.raises(RuntimeError, match="cleanup did not complete"):
        case.owner.finish(case.context)

    assert guard.entries <= 2
    assert case.state.cleanup_failed is True


def test_finish_exhausts_permanent_pre_action_failure_without_spin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "finish-permanent-failure")
    guard = _LoopGuard()
    setattr(case.owner, _CLEANUP_LOCK_ATTR, guard)
    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "_finish_action",
        lambda *_args: _raise(RuntimeError(_PERMANENT_PRE_ACTION_ERROR)),
    )

    with pytest.raises(RuntimeError, match="cleanup did not complete"):
        case.owner.finish(case.context)

    assert guard.entries <= 2
    assert case.state.cleanup_failed is True


def test_finish_retries_after_pre_action_boundary_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "finish-retry")
    original = vars(lifecycle.WorkerLifecycleOwner)["_finish_action"]
    calls = 0

    def fail_once(
        owner: lifecycle.WorkerLifecycleOwner,
        current_thread: int,
        state: object,
    ) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError(_RETRY_ERROR)
        return original(owner, current_thread, state)

    monkeypatch.setattr(lifecycle.WorkerLifecycleOwner, "_finish_action", fail_once)
    case.owner.finish(case.context)
    assert calls >= 2
    assert not (tmp_path / "finish-retry").exists()


def test_cleanup_incomplete_error_has_stable_message() -> None:
    error_type = vars(lifecycle)["_LifecycleCleanupIncompleteError"]
    assert str(error_type()) == "worker lifecycle cleanup did not complete"

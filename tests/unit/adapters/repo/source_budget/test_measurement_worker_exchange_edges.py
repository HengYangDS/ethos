"""Deterministic edge coverage for worker supervision and lifecycle helpers."""

from __future__ import annotations

import os
import signal
import types
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import Protocol
from typing import cast

import pytest

import ethos.adapters.repo.source_budget.measurement.worker.supervisor.core as supervisor
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.io as exchange
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core as lifecycle
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerResourceSample
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    worker_protocol_descriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)
from tests.support.source_budget_worker import WorkerClock
from tests.support.source_budget_worker import WorkerProcess
from tests.support.source_budget_worker import WorkerSelector

if TYPE_CHECKING:
    import selectors
    from collections.abc import Callable
    from pathlib import Path
    from subprocess import Popen

    from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerTelemetry

PROFILE = worker_resource_profile_descriptor()
PROTOCOL = worker_protocol_descriptor()


def _raise(error: BaseException) -> NoReturn:
    raise error


def _process(events: list[str] | None = None) -> Popen[bytes]:
    return cast("Popen[bytes]", WorkerProcess([] if events is None else events))


class _ExchangeStateView(Protocol):
    first_cause: str | None
    stdout: bytearray
    stdout_eof: bool

    def trigger(self, cause: str) -> None: ...


class _ExchangeContextView(Protocol):
    process: Popen[bytes]
    state: _ExchangeStateView


def _lifecycle_case(private: Path) -> types.SimpleNamespace:
    private.mkdir(exist_ok=True)
    state = lifecycle.WorkerExchangeState()
    owner = lifecycle.WorkerLifecycleOwner(private)
    boundary = lifecycle.WorkerLifecycleBoundary(owner, state)
    context = lifecycle.WorkerLifecycleContext(
        owner=owner,
        state=state,
        boundary=boundary,
        grace_seconds=0.1,
        send_group_signal=lambda _pid, _signal: None,
        probe_process_group=lambda _pid, **_kwargs: WorkerProcessGroupState.ABSENT,
        observe_direct_child=lambda _process: 0,
        monotonic=lambda: 0.0,
        wait_for=lambda _seconds: None,
        remove_directory=lambda path: path.rmdir(),
    )
    return types.SimpleNamespace(context=context, state=state, owner=owner)


def _default_telemetry() -> object:
    return types.SimpleNamespace(sample=lambda: WorkerResourceSample(rss_bytes=1, virtual_bytes=2))


@dataclass(frozen=True, slots=True)
class _ExchangeOptions:
    process: Popen[bytes] | None = None
    request_frame: object = b"request"
    telemetry: object | None = field(default_factory=_default_telemetry)
    selector: object | None = None
    state: _ExchangeStateView | None = None
    monotonic: Callable[[], float] = lambda: 0.0
    wall_deadline: float = 10.0
    request_permitted: bool = True


_DEFAULT_EXCHANGE_OPTIONS = _ExchangeOptions()


def _exchange_context(
    options: _ExchangeOptions = _DEFAULT_EXCHANGE_OPTIONS,
) -> _ExchangeContextView:
    events: list[str] = []
    config = exchange.WorkerExchangeConfig(
        request_frame=cast("bytes", options.request_frame),
        telemetry=cast("WorkerTelemetry | None", options.telemetry),
        profile=PROFILE,
        protocol=PROTOCOL,
        wall_deadline=options.wall_deadline,
        resource_sampled_at=1.0 - PROFILE.sample_interval_ms / 1000,
        request_permitted=options.request_permitted,
    )
    context = lifecycle.WorkerExchangeContext(
        _process(events) if options.process is None else options.process,
        cast(
            "selectors.BaseSelector",
            WorkerSelector(WorkerClock(), (), events)
            if options.selector is None
            else options.selector,
        ),
        cast(
            "lifecycle.WorkerExchangeState",
            lifecycle.WorkerExchangeState() if options.state is None else options.state,
        ),
        config,
        options.monotonic,
    )
    return cast("_ExchangeContextView", context)


def _wait_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    for index, name in enumerate(
        (
            "P_PID",
            "WEXITED",
            "WSTOPPED",
            "WNOHANG",
            "WNOWAIT",
            "CLD_STOPPED",
            "CLD_EXITED",
            "CLD_KILLED",
            "CLD_DUMPED",
        ),
        start=1,
    ):
        monkeypatch.setattr(supervisor.os, name, index, raising=False)
        monkeypatch.setattr(exchange.os, name, index, raising=False)


def test_supervisor_rejects_content_digest_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    canonical = types.SimpleNamespace(content_sha256="0" * 64)
    monkeypatch.setattr(supervisor, "_canonical_request", lambda _request: canonical)

    with pytest.raises(ValueError, match="content digest mismatch"):
        vars(supervisor)["_admit_parent_request"](object(), b"content")


@pytest.mark.parametrize(
    ("bootstrap", "runtime", "expected"),
    [
        (False, object(), "source_budget_worker_unavailable"),
        (True, None, "source_budget_worker_isolation_unsupported"),
    ],
)
def test_supervisor_rejects_unavailable_bootstrap_or_runtime(
    monkeypatch: pytest.MonkeyPatch,
    bootstrap: object,
    runtime: object,
    expected: str,
) -> None:
    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: bool(bootstrap))
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Other")
    monkeypatch.setattr(supervisor, "_worker_runtime", lambda _platform: runtime)

    load = vars(supervisor)["_run_admitted_worker"](types.SimpleNamespace())

    assert load.required_gaps == (expected,)


def test_supervisor_directory_creation_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hooks = types.SimpleNamespace()
    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: True)
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(supervisor, "_worker_runtime", lambda _platform: (object(), hooks))
    monkeypatch.setattr(
        supervisor,
        "create_private_directory",
        lambda: _raise(OSError("private")),
    )

    load = vars(supervisor)["_run_admitted_worker"](types.SimpleNamespace(profile=PROFILE))

    assert load.required_gaps == ("source_budget_worker_unavailable",)


def test_supervisor_discards_directory_when_session_preparation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = tmp_path / "private"
    private.mkdir()
    discarded: list[Path] = []
    hooks = types.SimpleNamespace()
    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: True)
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(supervisor, "_worker_runtime", lambda _platform: (object(), hooks))
    monkeypatch.setattr(supervisor, "create_private_directory", lambda: private)
    monkeypatch.setattr(
        supervisor,
        "prepare_worker_exchange",
        lambda *_args: _raise(MemoryError("session")),
    )
    monkeypatch.setattr(supervisor, "discard_unstarted_directory", discarded.append)

    with pytest.raises(MemoryError, match="session"):
        vars(supervisor)["_run_admitted_worker"](types.SimpleNamespace(profile=PROFILE))

    assert discarded == [private]


@pytest.mark.parametrize("failure", [AttributeError("backend"), WorkerIsolationUnsupportedError()])
def test_worker_runtime_rejects_backend_lookup_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    monkeypatch.setattr(supervisor, "worker_backend", lambda _platform: _raise(failure))
    assert vars(supervisor)["_worker_runtime"]("Other") is None


def test_worker_runtime_rejects_noncallable_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = types.SimpleNamespace(signal_process_group=None, probe_process_group=None)
    monkeypatch.setattr(supervisor, "worker_backend", lambda _platform: backend)
    assert vars(supervisor)["_worker_runtime"]("Linux") is None


@pytest.mark.parametrize(
    "failure", [AttributeError("spec"), ImportError("spec"), ValueError("spec")]
)
def test_bootstrap_availability_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    monkeypatch.setattr(
        supervisor.importlib.util,
        "find_spec",
        lambda _name: _raise(failure),
    )
    assert vars(supervisor)["_bootstrap_available"]() is False


def test_prepare_worker_rejects_unready_or_over_rss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launch = vars(supervisor)["_WorkerLaunch"](_process(), 10.0)
    monkeypatch.setattr(
        supervisor,
        "_await_resource_ready",
        lambda *_args: types.SimpleNamespace(ready=False, initial_cause="capability_failed"),
    )
    unready = vars(supervisor)["_prepare_worker"](
        launch,
        object(),
        PROFILE,
        "Linux",
        lambda *_args: None,
    )
    assert unready.initial_cause == "capability_failed"

    monkeypatch.setattr(
        supervisor,
        "_await_resource_ready",
        lambda *_args: types.SimpleNamespace(ready=True, initial_cause=None),
    )
    sample = WorkerResourceSample(rss_bytes=PROFILE.rss_bytes + 1, virtual_bytes=2)
    initial = (object(), sample, None, 1.0)
    monkeypatch.setattr(supervisor, "_prepare_initial_telemetry", lambda *_args: initial)
    exceeded = vars(supervisor)["_prepare_worker"](
        launch,
        object(),
        PROFILE,
        "Linux",
        lambda *_args: None,
    )
    assert exceeded.initial_cause == "resource_exhausted"


def test_prepare_initial_telemetry_maps_memory_error_after_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = types.SimpleNamespace(sample=lambda: _raise(MemoryError("sample")))
    backend = types.SimpleNamespace(open_parent_telemetry=lambda *_args: telemetry)
    launch = vars(supervisor)["_WorkerLaunch"](_process(), 10.0)
    calls = 0

    def timeout(*_args: object, **_kwargs: object) -> object | None:
        nonlocal calls
        calls += 1
        return None if calls < 3 else types.SimpleNamespace(initial_cause="timeout")

    monkeypatch.setattr(supervisor, "_timeout_worker", timeout)
    prepared = vars(supervisor)["_prepare_initial_telemetry"](
        launch,
        backend,
        PROFILE,
        "Linux",
    )
    assert prepared.initial_cause == "timeout"


@pytest.mark.parametrize(
    ("timeouts", "signal_error", "expected", "raises"),
    [
        (("timeout",), None, "timeout", None),
        ((None, "timeout"), MemoryError("signal"), "timeout", None),
        ((None, None), MemoryError("signal"), None, MemoryError),
        ((None, None), OSError("signal"), "capability_failed", None),
        ((None, "timeout"), None, "timeout", None),
    ],
)
def test_continue_worker_handles_deadlines_and_signal_failures(
    monkeypatch: pytest.MonkeyPatch,
    timeouts: tuple[str | None, ...],
    signal_error: BaseException | None,
    expected: str | None,
    raises: type[BaseException] | None,
) -> None:
    launch = vars(supervisor)["_WorkerLaunch"](_process(), 10.0)
    initial = (
        object(),
        WorkerResourceSample(rss_bytes=1, virtual_bytes=2),
        None,
        1.0,
    )
    results = deque(timeouts)

    def timeout(*_args: object) -> object | None:
        value = results.popleft() if results else None
        return None if value is None else types.SimpleNamespace(initial_cause=value)

    def send(*_args: object) -> None:
        if signal_error is not None:
            raise signal_error

    monkeypatch.setattr(supervisor, "_timeout_from_initial", timeout)
    if raises is not None:
        with pytest.raises(raises):
            vars(supervisor)["_continue_worker"](launch, send, initial)
        return
    prepared = vars(supervisor)["_continue_worker"](launch, send, initial)
    assert prepared.initial_cause == expected


def test_canonical_request_rejects_subclasses_or_other_types() -> None:
    assert vars(supervisor)["_canonical_request"](object()) is None


def test_resource_readiness_requires_waitid_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(supervisor.os, "waitid", raising=False)
    result = vars(supervisor)["_await_resource_ready"](_process(), 1.0)
    assert result.initial_cause == "capability_failed"


def test_resource_readiness_retries_interrupt_then_exhausts_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wait_capabilities(monkeypatch)
    ticks = iter((0.0, 1.0))
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        supervisor.os,
        "waitid",
        lambda *_args: _raise(InterruptedError()),
    )
    result = vars(supervisor)["_await_resource_ready"](_process(), 0.5)
    assert result.initial_cause == "timeout"


@pytest.mark.parametrize(
    ("ticks", "expected"), [((0.0, 0.0), "capability_failed"), ((0.0, 1.0), "timeout")]
)
def test_resource_readiness_classifies_waitid_failure_by_deadline(
    monkeypatch: pytest.MonkeyPatch,
    ticks: tuple[float, float],
    expected: str,
) -> None:
    _wait_capabilities(monkeypatch)
    clock = iter(ticks)
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(supervisor.os, "waitid", lambda *_args: _raise(OSError("waitid")))
    result = vars(supervisor)["_await_resource_ready"](_process(), 0.5)
    assert result.initial_cause == expected


def test_resource_readiness_rejects_observation_after_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wait_capabilities(monkeypatch)
    ticks = iter((0.0, 1.0))
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(
        supervisor.os,
        "waitid",
        lambda *_args: types.SimpleNamespace(
            si_pid=1,
            si_code=supervisor.os.CLD_STOPPED,
            si_status=signal.SIGSTOP,
        ),
    )
    result = vars(supervisor)["_await_resource_ready"](_process(), 0.5)
    assert result.initial_cause == "timeout"


@pytest.mark.parametrize(
    ("code", "expected"),
    [(os.CLD_EXITED, None), (99999, "capability_failed")],
)
def test_resource_readiness_classifies_terminal_and_unknown_observations(
    code: int,
    expected: str | None,
) -> None:
    observed = types.SimpleNamespace(si_code=code, si_status=0, si_pid=1)
    result = vars(supervisor)["_classify_readiness_observation"](observed)
    assert result.initial_cause == expected


def test_initial_sample_rejects_unknown_platform() -> None:
    sample = WorkerResourceSample(rss_bytes=1, virtual_bytes=2)
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(supervisor)["_admit_initial_sample"]("Other", sample)


def test_outcome_memory_failure_and_pipe_gap_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outcome = exchange.WorkerExchangeResult(
        stdout=b"x",
        stdout_eof=True,
        returncode=0,
        first_cause=None,
        cleanup_failed=False,
    )
    monkeypatch.setattr(supervisor, "decode_result_frame", lambda _stdout: _raise(MemoryError()))
    load = vars(supervisor)["_interpret_worker_outcome"](object(), outcome)
    assert load.required_gaps == ("source_budget_worker_failed",)
    piped = exchange.WorkerExchangeResult(
        stdout=b"",
        stdout_eof=False,
        returncode=None,
        first_cause="pipe_failed",
        cleanup_failed=False,
    )
    assert vars(supervisor)["_parent_gap"](piped) == "source_budget_worker_failed"


def test_cleanup_capability_failure_precedes_nonzero_returncode_mapping() -> None:
    outcome = exchange.WorkerExchangeResult(
        stdout=b"",
        stdout_eof=False,
        returncode=3,
        first_cause=None,
        cleanup_failed=True,
        cleanup_cause="capability_failed",
    )

    assert vars(supervisor)["_parent_gap"](outcome) == (
        "source_budget_worker_isolation_unsupported"
    )


def test_exchange_state_preserves_first_cause() -> None:
    state = lifecycle.WorkerExchangeState()
    state.trigger("timeout")
    state.trigger("pipe_failed")
    assert state.first_cause == "timeout"


def test_exchange_without_bound_process_freezes_pipe_failure(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir()
    hooks = exchange.WorkerExchangeHooks(
        send_group_signal=lambda *_args: None,
        probe_process_group=lambda *_args, **_kwargs: WorkerProcessGroupState.ABSENT,
        monotonic=lambda: 0.0,
        remove_directory=lambda path: path.rmdir(),
    )
    session = exchange.prepare_worker_exchange(private, PROFILE, hooks)
    result = exchange.exchange_worker_process(
        exchange.WorkerExchangeConfig(b"request", None, PROFILE, PROTOCOL, 1.0),
        hooks,
        session,
    )
    assert result.first_cause == "pipe_failed"


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (MemoryError("exchange"), "pipe_failed"),
        (WorkerIsolationUnsupportedError(), "capability_failed"),
    ],
)
def test_run_exchange_maps_parent_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: BaseException,
    expected: str,
) -> None:
    case = _lifecycle_case(tmp_path / expected)
    process = _process()
    case.owner.bind_process(process)
    session = exchange.WorkerExchangeSession(case.state, case.context)
    monkeypatch.setattr(exchange, "acquire_worker_selector", lambda *_args: _raise(failure))
    vars(exchange)["_run_exchange"](
        exchange.WorkerExchangeConfig(b"request", None, PROFILE, PROTOCOL, 10.0),
        exchange.WorkerExchangeHooks(
            send_group_signal=case.context.send_group_signal,
            probe_process_group=case.context.probe_process_group,
            monotonic=lambda: 0.0,
        ),
        case.state,
        session,
        process,
    )
    assert case.state.first_cause == expected


def test_run_exchange_skips_drive_after_pipe_preparation_triggers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case = _lifecycle_case(tmp_path / "skip-drive")
    process = _process()
    case.owner.bind_process(process)
    session = exchange.WorkerExchangeSession(case.state, case.context)
    selector = WorkerSelector(WorkerClock(), (), [])
    monkeypatch.setattr(exchange, "acquire_worker_selector", lambda *_args: selector)
    monkeypatch.setattr(
        exchange, "_prepare_pipes", lambda context: context.state.trigger("pipe_failed")
    )
    monkeypatch.setattr(exchange, "_drive_exchange", lambda _context: pytest.fail("drive called"))
    vars(exchange)["_run_exchange"](
        exchange.WorkerExchangeConfig(b"request", None, PROFILE, PROTOCOL, 10.0),
        exchange.WorkerExchangeHooks(
            send_group_signal=case.context.send_group_signal,
            probe_process_group=case.context.probe_process_group,
            monotonic=lambda: 0.0,
        ),
        case.state,
        session,
        process,
    )
    assert case.state.first_cause == "pipe_failed"


def test_trigger_parent_failure_prefers_expired_deadline() -> None:
    state = lifecycle.WorkerExchangeState()
    hooks = types.SimpleNamespace(monotonic=lambda: 2.0)
    vars(exchange)["_trigger_parent_failure"](state, hooks, 1.0, "pipe_failed")
    assert state.first_cause == "timeout"


@pytest.mark.parametrize(
    "expiry", [(True,), (False, True), (False, False, True), (False, False, False, True)]
)
def test_prepare_pipes_stops_at_each_deadline_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    expiry: tuple[bool, ...],
) -> None:
    context = _exchange_context()
    states = iter(expiry)
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: next(states, True))
    monkeypatch.setattr(exchange.os, "set_blocking", lambda *_args: None)
    vars(exchange)["_prepare_pipes"](context)


def test_prepare_pipes_rejects_invalid_frame_or_missing_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    with pytest.raises(WorkerIsolationUnsupportedError, match="pipe"):
        vars(exchange)["_prepare_pipes"](
            _exchange_context(_ExchangeOptions(request_frame="not-bytes"))
        )
    monkeypatch.setattr(exchange.os, "set_blocking", lambda *_args: None)
    with pytest.raises(WorkerIsolationUnsupportedError, match="telemetry"):
        vars(exchange)["_prepare_pipes"](_exchange_context(_ExchangeOptions(telemetry=None)))


def test_prepare_pipes_maps_unpermitted_stdin_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = cast("Popen[bytes]", WorkerProcess([]))
    monkeypatch.setattr(process.stdin, "close", lambda: _raise(OSError("close")))
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    monkeypatch.setattr(exchange.os, "set_blocking", lambda *_args: None)
    context = _exchange_context(_ExchangeOptions(process=process, request_permitted=False))
    vars(exchange)["_prepare_pipes"](context)
    assert context.state.first_cause == "pipe_failed"


def test_drive_exchange_stops_on_expiry_or_wall_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired = _exchange_context()
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    vars(exchange)["_drive_exchange"](expired)

    deadline = _exchange_context(_ExchangeOptions(monotonic=lambda: 2.0, wall_deadline=1.0))
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    monkeypatch.setattr(exchange, "_select_events", lambda *_args: [])
    monkeypatch.setattr(exchange, "_exchange_complete", lambda _context: False)
    vars(exchange)["_drive_exchange"](deadline)
    assert deadline.state.first_cause == "timeout"


def test_exchange_complete_rejects_exit_before_request_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _exchange_context()
    monkeypatch.setattr(exchange, "_observe_direct_child", lambda _process: 0)
    assert vars(exchange)["_exchange_complete"](context) is True
    assert context.state.first_cause == "pipe_failed"


def test_sample_due_handles_expiry_and_unreconciled_capability_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _exchange_context()
    monkeypatch.setattr(
        exchange,
        "_sample_resources",
        lambda _context: _raise(WorkerIsolationUnsupportedError()),
    )
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    assert (
        vars(exchange)["_sample_if_due"](
            context,
            telemetry_active=True,
            now=2.0,
            interval=0.1,
        )
        is True
    )
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    monkeypatch.setattr(
        exchange,
        "_reconcile_terminal_after_telemetry_loss",
        lambda *_args: False,
    )
    assert (
        vars(exchange)["_sample_if_due"](
            context,
            telemetry_active=True,
            now=2.0,
            interval=0.1,
        )
        is False
    )
    assert context.state.first_cause == "capability_failed"


def test_expire_exchange_records_timeout() -> None:
    context = _exchange_context(_ExchangeOptions(monotonic=lambda: 1.0, wall_deadline=1.0))
    assert vars(exchange)["_expire_exchange"](context) is True
    assert context.state.first_cause == "timeout"


def test_select_events_returns_when_already_triggered() -> None:
    state = lifecycle.WorkerExchangeState()
    state.trigger("pipe_failed")
    context = _exchange_context(_ExchangeOptions(state=cast("_ExchangeStateView", state)))
    assert vars(exchange)["_select_events"](context, None) == []


def test_sample_resources_rejects_missing_or_invalid_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(WorkerIsolationUnsupportedError, match="telemetry"):
        vars(exchange)["_sample_resources"](_exchange_context(_ExchangeOptions(telemetry=None)))
    context = _exchange_context(
        _ExchangeOptions(
            telemetry=types.SimpleNamespace(
                sample=lambda: WorkerResourceSample(rss_bytes=1, virtual_bytes=None)
            )
        )
    )
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    with pytest.raises(WorkerIsolationUnsupportedError, match="virtual"):
        vars(exchange)["_sample_resources"](context)
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    vars(exchange)["_sample_resources"](context)


def test_reconcile_telemetry_loss_stops_on_trigger_or_race_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triggered = _exchange_context()
    monkeypatch.setattr(
        exchange,
        "_handle_events",
        lambda context, *_args, **_kwargs: context.state.trigger("pipe_failed"),
    )
    monkeypatch.setattr(exchange, "_select_events", lambda *_args: [])
    assert vars(exchange)["_reconcile_terminal_after_telemetry_loss"](triggered, 1.0) is False

    deadline = _exchange_context(_ExchangeOptions(monotonic=lambda: 2.0))
    monkeypatch.setattr(exchange, "_handle_events", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(exchange, "_observe_direct_child", lambda _process: None)
    assert vars(exchange)["_reconcile_terminal_after_telemetry_loss"](deadline, 1.0) is False


def test_handle_events_ignores_unactionable_stdout_event() -> None:
    context = _exchange_context()
    key = types.SimpleNamespace(data="stdout")
    vars(exchange)["_handle_events"](context, [(key, 0)], allow_write=True)
    assert context.state.first_cause is None


def test_write_request_rejects_missing_pipe_invalid_write_and_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = _exchange_context()
    missing.process.stdin = None
    vars(exchange)["_write_request"](missing)
    assert missing.state.first_cause == "pipe_failed"

    invalid = _exchange_context()
    monkeypatch.setattr(exchange, "_write_nonblocking", lambda *_args: 0)
    vars(exchange)["_write_request"](invalid)
    assert invalid.state.first_cause == "pipe_failed"

    expired = _exchange_context()
    monkeypatch.setattr(exchange, "_write_nonblocking", lambda *_args: 1)
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    vars(exchange)["_write_request"](expired)

    selector = types.SimpleNamespace(unregister=lambda _pipe: _raise(KeyError("pipe")))
    closing = _exchange_context(_ExchangeOptions(request_frame=b"x", selector=selector))
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    vars(exchange)["_write_request"](closing)
    assert closing.state.first_cause == "pipe_failed"


def test_nonblocking_write_handles_os_error_and_expired_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _exchange_context()
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    monkeypatch.setattr(exchange.os, "write", lambda *_args: _raise(OSError("write")))
    assert vars(exchange)["_write_nonblocking"](context, 1, b"x") is None
    assert context.state.first_cause == "pipe_failed"
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    assert vars(exchange)["_write_nonblocking"](context, 1, b"x") is None


def test_read_stdout_handles_missing_pipe_limit_eof_and_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = _exchange_context()
    missing.process.stdout = None
    vars(exchange)["_read_stdout"](missing)
    assert missing.state.first_cause == "pipe_failed"

    limited = _exchange_context()
    limited.state.stdout.extend(b"x" * (PROTOCOL.result_max_bytes + 1))
    vars(exchange)["_read_stdout"](limited)
    assert limited.state.first_cause == "output_exceeded"

    eof = _exchange_context()
    monkeypatch.setattr(exchange, "_read_nonblocking", lambda *_args: b"")
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    vars(exchange)["_read_stdout"](eof)
    assert eof.state.stdout_eof is True

    selector = types.SimpleNamespace(unregister=lambda _pipe: _raise(KeyError("pipe")))
    rejected = _exchange_context(_ExchangeOptions(selector=selector))
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    vars(exchange)["_read_stdout"](rejected)
    assert rejected.state.first_cause == "pipe_failed"

    chunk = _exchange_context()
    monkeypatch.setattr(exchange, "_read_nonblocking", lambda *_args: b"x")
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    vars(exchange)["_read_stdout"](chunk)


def test_nonblocking_read_handles_os_error_and_expired_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _exchange_context()
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: False)
    monkeypatch.setattr(exchange.os, "read", lambda *_args: _raise(OSError("read")))
    assert vars(exchange)["_read_nonblocking"](context, 1, 1) is None
    assert context.state.first_cause == "pipe_failed"
    monkeypatch.setattr(exchange, "_expire_exchange", lambda _context: True)
    assert vars(exchange)["_read_nonblocking"](context, 1, 1) is None


def test_direct_child_observation_requires_capability_and_known_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _process()
    monkeypatch.delattr(exchange.os, "waitid", raising=False)
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(exchange)["_observe_direct_child"](process)

    _wait_capabilities(monkeypatch)
    monkeypatch.setattr(
        exchange.os,
        "waitid",
        lambda *_args: _raise(InterruptedError()),
        raising=False,
    )
    assert vars(exchange)["_observe_direct_child"](process) is None
    monkeypatch.setattr(exchange.os, "waitid", lambda *_args: _raise(OSError("waitid")))
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(exchange)["_observe_direct_child"](process)
    monkeypatch.setattr(
        exchange.os,
        "waitid",
        lambda *_args: types.SimpleNamespace(si_pid=1, si_code=99999, si_status=0),
    )
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(exchange)["_observe_direct_child"](process)

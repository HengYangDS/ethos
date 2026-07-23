"""Reusable lifecycle-session fixtures for source-budget worker tests."""

from __future__ import annotations

import dataclasses
import signal
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.source_budget.measurement.worker.supervisor.io as exchange
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    worker_protocol_descriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)
from tests.support.source_budget_worker import WorkerProcess
from tests.support.source_budget_worker import WorkerSelector

if TYPE_CHECKING:
    import selectors
    import threading
    from collections.abc import Callable
    from pathlib import Path
    from subprocess import Popen

    import pytest

PROFILE = worker_resource_profile_descriptor()


@dataclasses.dataclass(frozen=True, slots=True)
class LifecycleSessionOptions:
    """Deterministic failure and concurrency switches for one worker session."""

    signal_error: BaseException | None = None
    kill_errors: list[BaseException] | None = None
    remove_before_delete: bool = False
    bind_process: bool = True
    signal_gate: tuple[threading.Event, threading.Event] | None = None
    term_ignored: bool = False


_DEFAULT_OPTIONS = LifecycleSessionOptions()


def worker_exchange_config(*, wall_deadline: float = 2.0) -> exchange.WorkerExchangeConfig:
    """Return the canonical deterministic exchange configuration."""
    return exchange.WorkerExchangeConfig(
        request_frame=b"request",
        telemetry=None,
        profile=PROFILE,
        protocol=worker_protocol_descriptor(),
        wall_deadline=wall_deadline,
    )


def worker_exchange_hooks(
    session: exchange.WorkerExchangeSession,
    selector_factory: Callable[[], object],
) -> exchange.WorkerExchangeHooks:
    """Project a prepared session into deterministic exchange hooks."""
    context = session.lifecycle
    return exchange.WorkerExchangeHooks(
        send_group_signal=context.send_group_signal,
        probe_process_group=context.probe_process_group,
        monotonic=context.monotonic,
        selector_factory=cast("Callable[[], selectors.BaseSelector]", selector_factory),
        wait_for=context.wait_for,
        remove_directory=context.remove_directory,
    )


def bind_worker_process(
    session: exchange.WorkerExchangeSession,
    process: WorkerProcess,
) -> None:
    """Bind one deterministic process double to a prepared session."""
    session.bind_process(cast("Popen[bytes]", process))


def bind_worker_selector(
    session: exchange.WorkerExchangeSession,
    selector: WorkerSelector,
) -> None:
    """Bind one deterministic selector double to a prepared session."""
    session.lifecycle.owner.bind_selector(cast("selectors.BaseSelector", selector))


def worker_session(
    monkeypatch: pytest.MonkeyPatch,
    private: Path,
    events: list[str],
    options: LifecycleSessionOptions = _DEFAULT_OPTIONS,
) -> tuple[exchange.WorkerExchangeSession, WorkerProcess]:
    """Create one pre-spawn lifecycle session with deterministic OS seams."""
    private.mkdir()
    process = WorkerProcess(events)
    alive = {"value": True}
    send_group_signal = _group_signal(events, alive, options)

    def probe_group(
        process_group: int,
        *,
        direct_child_terminal: bool,
    ) -> WorkerProcessGroupState:
        assert process_group == process.pid
        events.append("group-probe")
        if alive["value"]:
            return WorkerProcessGroupState.LIVE
        return (
            WorkerProcessGroupState.TERMINAL_ONLY
            if direct_child_terminal
            else WorkerProcessGroupState.ABSENT
        )

    def observe(child: WorkerProcess) -> int:
        events.append("observe")
        child.returncode = 0
        return 0

    def remove(path: Path) -> None:
        events.append("remove")
        if options.remove_before_delete:
            raise OSError
        path.rmdir()

    monkeypatch.setattr(exchange, "_observe_direct_child", observe)
    hooks = exchange.WorkerExchangeHooks(
        send_group_signal=send_group_signal,
        probe_process_group=probe_group,
        monotonic=lambda: 1.0,
        wait_for=lambda seconds: events.append(f"wait:{seconds}"),
        remove_directory=remove,
    )
    session = exchange.prepare_worker_exchange(private, PROFILE, hooks)
    if options.bind_process:
        bind_worker_process(session, process)
    return session, process


def _group_signal(
    events: list[str],
    alive: dict[str, bool],
    options: LifecycleSessionOptions,
) -> Callable[[int, int], None]:
    def send_group_signal(_pid: int, number: int) -> None:
        events.append(f"signal:{number}")
        if options.signal_gate is not None and number == signal.SIGTERM:
            entered, release = options.signal_gate
            entered.set()
            assert release.wait(timeout=2)
        if options.signal_error is not None and number == signal.SIGTERM:
            raise options.signal_error
        if options.kill_errors and number == signal.SIGKILL:
            raise options.kill_errors.pop(0)
        if options.term_ignored and number == signal.SIGTERM:
            return
        alive["value"] = False

    return send_group_signal

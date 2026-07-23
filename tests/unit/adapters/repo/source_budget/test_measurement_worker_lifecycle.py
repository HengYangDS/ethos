"""Failure-atomic ownership contract for the isolated measurement worker."""

from __future__ import annotations

import dataclasses
import selectors
import signal
import subprocess
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.repo.source_budget.measurement.worker.supervisor.core as supervisor
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.io as exchange
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.cleanup as cleanup
import ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core as lifecycle
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from tests.support.source_budget_worker import WorkerClock
from tests.support.source_budget_worker import WorkerProcess
from tests.support.source_budget_worker import WorkerSelector
from tests.support.source_budget_worker_lifecycle import PROFILE
from tests.support.source_budget_worker_lifecycle import LifecycleSessionOptions as _SessionOptions
from tests.support.source_budget_worker_lifecycle import bind_worker_selector as _bind_selector
from tests.support.source_budget_worker_lifecycle import worker_exchange_config as _config
from tests.support.source_budget_worker_lifecycle import worker_exchange_hooks as _hooks
from tests.support.source_budget_worker_lifecycle import worker_session as _session

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import Popen

_AMBIENT_MESSAGE = "ambient"
_BIND_MESSAGE = "bind"
_EXCHANGE_MESSAGE = "exchange-primary"
_ELECTION_MESSAGE = "cleanup-election"

_DEFAULT_SESSION_OPTIONS = _SessionOptions()


def _raise_ambient_error() -> None:
    raise ValueError(_AMBIENT_MESSAGE)


def test_cleanup_control_exception_still_kills_closes_reaps_and_removes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(signal_error=KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        session.finish()

    assert events.count(f"signal:{signal.SIGTERM}") == 1
    assert events.count(f"signal:{signal.SIGKILL}") == 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert events.count(f"reap:{PROFILE.term_grace_ms / 1000}") == 1
    assert not (tmp_path / "private").exists()
    frozen = tuple(events)
    session.finish()
    assert tuple(events) == frozen


def test_cleanup_is_exactly_once_under_concurrent_finish(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    entered, release = threading.Event(), threading.Event()
    session, _process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(signal_gate=(entered, release)),
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(session.finish)
            assert entered.wait(timeout=2)
            second = executor.submit(session.finish)
            with pytest.raises(TimeoutError):
                second.result(timeout=0.05)
            release.set()
            first.result(timeout=2)
            second.result(timeout=2)
    finally:
        release.set()

    assert events.count(f"signal:{signal.SIGTERM}") == 1
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1


def test_cleanup_election_control_exception_still_runs_owned_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, process = _session(monkeypatch, tmp_path / "private", events)
    mark_running = vars(lifecycle.WorkerLifecycleOwner)["_mark_cleanup_running"]

    def interrupt_after_election(
        owner: lifecycle.WorkerLifecycleOwner,
        thread_id: int,
    ) -> None:
        mark_running(owner, thread_id)
        raise KeyboardInterrupt(_ELECTION_MESSAGE)

    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "_mark_cleanup_running",
        interrupt_after_election,
    )
    with pytest.raises(KeyboardInterrupt, match=_ELECTION_MESSAGE):
        session.finish()

    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert not (tmp_path / "private").exists()


def test_owner_binding_is_single_identity_and_config_has_no_duplicate_resources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session, process = _session(monkeypatch, tmp_path / "private", [])
    replacement = WorkerProcess([])

    assert hasattr(session, "bind_process")
    with pytest.raises(RuntimeError, match="already bound"):
        session.bind_process(cast("Popen[bytes]", replacement))
    assert session.lifecycle.owner.process is process
    config_fields = {item.name for item in dataclasses.fields(exchange.WorkerExchangeConfig)}
    assert config_fields.isdisjoint({"process", "private_directory"})
    session.finish()


def test_spawned_process_is_cleaned_when_first_bind_attempt_is_interrupted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(bind_process=False),
    )
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *_args, **_kwargs: process)
    original_bind = lifecycle.WorkerLifecycleOwner.bind_process
    attempts = 0

    def interrupt_before_bind(
        owner: lifecycle.WorkerLifecycleOwner,
        child: Popen[bytes],
    ) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise KeyboardInterrupt(_BIND_MESSAGE)
        original_bind(owner, child)

    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "bind_process",
        interrupt_before_bind,
    )
    with pytest.raises(KeyboardInterrupt, match="bind"):
        vars(supervisor)["_launch_worker"](PROFILE, 1.0, session)
    session.finish()

    assert attempts >= 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert not private.exists()


def test_finished_session_reuse_rejects_before_selector_allocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, _process = _session(monkeypatch, tmp_path / "private", events)
    session.finish()
    allocations: list[WorkerSelector] = []

    def allocate() -> WorkerSelector:
        selector = WorkerSelector(WorkerClock(), (), events)
        allocations.append(selector)
        return selector

    exchange.exchange_worker_process(_config(), _hooks(session, allocate), session)

    assert allocations == []


def test_allocated_selector_is_closed_when_bind_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, _process = _session(monkeypatch, tmp_path / "private", events)
    selector = WorkerSelector(WorkerClock(), (), events)

    def allocate_then_finish() -> WorkerSelector:
        session.finish()
        return selector

    exchange.exchange_worker_process(
        _config(),
        _hooks(session, allocate_then_finish),
        session,
    )

    assert events.count("selector-close") == 1


def test_exchange_preserves_primary_system_exit_over_cleanup_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(signal_error=KeyboardInterrupt("cleanup")),
    )

    def interrupt_exchange() -> WorkerSelector:
        raise SystemExit(_EXCHANGE_MESSAGE)

    with pytest.raises(BaseException, match=r"exchange-primary|cleanup") as raised:
        exchange.exchange_worker_process(
            _config(),
            _hooks(session, interrupt_exchange),
            session,
        )

    assert type(raised.value) is SystemExit
    assert str(raised.value) == "exchange-primary"
    assert process.stdin.closed
    assert process.stdout.closed
    assert not (tmp_path / "private").exists()


def test_explicit_finish_does_not_treat_an_ambient_exception_as_primary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session, _process = _session(
        monkeypatch,
        tmp_path / "private",
        [],
        _SessionOptions(signal_error=KeyboardInterrupt("cleanup")),
    )

    try:
        _raise_ambient_error()
    except ValueError:
        with pytest.raises(KeyboardInterrupt, match="cleanup"):
            session.finish()


def test_interrupted_kill_is_retried_before_cleanup_control_is_reraised(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    kill_errors: list[BaseException] = [KeyboardInterrupt("kill")]
    session, process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(kill_errors=kill_errors, term_ignored=True),
    )

    with pytest.raises(KeyboardInterrupt, match="kill"):
        session.finish()

    assert events.count(f"signal:{signal.SIGKILL}") == 2
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert not (tmp_path / "private").exists()


def test_permanently_interrupted_kill_has_a_finite_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    kill_errors: list[BaseException] = [InterruptedError() for _ in range(32)]
    session, _process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(kill_errors=kill_errors, term_ignored=True),
    )

    session.finish()

    assert events.count(f"signal:{signal.SIGKILL}") < 32
    assert kill_errors
    assert session.state.cleanup_failed is True
    assert (tmp_path / "private").exists()


@pytest.mark.parametrize(
    ("phase", "later_event"),
    [
        ("_terminate_process_group", "selector-close"),
        ("_close_selector", "close:31"),
        ("_close_parent_pipes", f"reap:{PROFILE.term_grace_ms / 1000}"),
        ("_reap_direct_child", "remove"),
    ],
)
def test_control_exception_between_cleanup_phases_does_not_skip_later_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    phase: str,
    later_event: str,
) -> None:
    events: list[str] = []
    session, _process = _session(monkeypatch, tmp_path / "private", events)
    _bind_selector(session, WorkerSelector(WorkerClock(), (), events))
    original = getattr(cleanup, phase)

    def interrupt_after_phase(*args: object) -> None:
        original(*args)
        raise KeyboardInterrupt(phase)

    monkeypatch.setattr(cleanup, phase, interrupt_after_phase)

    with pytest.raises(KeyboardInterrupt, match=phase):
        session.finish()

    assert later_event in events
    assert not (tmp_path / "private").exists()


@pytest.mark.parametrize(
    "first_error",
    [KeyboardInterrupt("reap"), subprocess.TimeoutExpired("worker", 0.1)],
)
def test_reap_retries_after_interruption_before_owner_becomes_done(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    first_error: BaseException,
) -> None:
    events: list[str] = []
    session, process = _session(monkeypatch, tmp_path / "private", events)
    calls = 0

    def wait(timeout: float | None = None) -> int:
        nonlocal calls
        calls += 1
        events.append(f"reap:{timeout}")
        if calls == 1:
            raise first_error
        process.returncode = 0
        return 0

    monkeypatch.setattr(process, "wait", wait)

    if isinstance(first_error, Exception):
        session.finish()
    else:
        with pytest.raises(type(first_error)):
            session.finish()

    assert calls == 2
    assert process.returncode == 0
    assert not (tmp_path / "private").exists()


def test_cleanup_wait_does_not_allocate_a_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        selectors,
        "DefaultSelector",
        lambda: pytest.fail("cleanup wait allocated a selector"),
    )
    monkeypatch.setattr(time, "sleep", sleeps.append)

    lifecycle.wait_for_cleanup_timeout(0.125)

    assert sleeps == [0.125]


def test_deadline_failure_after_directory_creation_still_removes_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    private = tmp_path / "private"
    backend = types.SimpleNamespace(
        signal_process_group=lambda _pid, _number: None,
        probe_process_group=lambda _pid, *, direct_child_terminal: (
            WorkerProcessGroupState.TERMINAL_ONLY
            if direct_child_terminal
            else WorkerProcessGroupState.ABSENT
        ),
    )

    def create_private_directory() -> Path:
        private.mkdir()
        return private

    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: True)
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(supervisor, "worker_backend", lambda _name: backend)
    monkeypatch.setattr(supervisor, "create_private_directory", create_private_directory)
    monkeypatch.setattr(
        supervisor.time,
        "monotonic",
        lambda: (_ for _ in ()).throw(MemoryError("deadline")),
    )

    with pytest.raises(MemoryError, match="deadline"):
        vars(supervisor)["_run_admitted_worker"](types.SimpleNamespace(profile=PROFILE))
    assert not private.exists()


@pytest.mark.parametrize("stage", ["pipe", "wait", "remove"])
def test_cleanup_attempts_later_phases_after_each_ordinary_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage: str,
) -> None:
    events: list[str] = []
    session, process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(remove_before_delete=stage == "remove"),
    )
    selector = WorkerSelector(WorkerClock(), (), events)
    _bind_selector(session, selector)
    if stage == "pipe":
        monkeypatch.setattr(
            process.stdin,
            "close",
            lambda: (_ for _ in ()).throw(RuntimeError("pipe")),
        )
    if stage == "wait":
        monkeypatch.setattr(
            process,
            "wait",
            lambda _timeout=None: (_ for _ in ()).throw(RuntimeError("wait")),
        )

    session.finish()

    assert session.state.cleanup_failed is True
    assert "selector-close" in events
    assert "remove" in events
    if stage != "remove":
        assert not (tmp_path / "private").exists()

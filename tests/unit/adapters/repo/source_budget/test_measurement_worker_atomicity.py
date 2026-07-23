"""Failure-atomic publication boundaries for the isolated measurement worker."""

from __future__ import annotations

import dataclasses
import dis
import inspect
import signal
import sys
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
    WorkerIsolationUnsupportedError,
)
from tests.support.source_budget_worker import WorkerClock
from tests.support.source_budget_worker import WorkerSelector
from tests.support.source_budget_worker_lifecycle import PROFILE
from tests.support.source_budget_worker_lifecycle import LifecycleSessionOptions as _SessionOptions
from tests.support.source_budget_worker_lifecycle import worker_exchange_config as _config
from tests.support.source_budget_worker_lifecycle import worker_exchange_hooks as _hooks
from tests.support.source_budget_worker_lifecycle import worker_session as _session

_AMBIENT_MESSAGE = "ambient"
_PUBLICATION_MESSAGE = "publication"

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable
    from pathlib import Path
    from subprocess import Popen
    from types import FrameType


def _opcode_after_store(
    function: types.FunctionType,
    name: str,
    *,
    last: bool = False,
) -> int:
    instructions = list(dis.get_instructions(function))
    indexes = [
        index
        for index, instruction in enumerate(instructions)
        if instruction.opname == "STORE_FAST" and instruction.argval == name
    ]
    selected = indexes[-1] if last else indexes[0]
    return instructions[selected + 1].offset


def _interrupt_once(
    function: types.FunctionType,
    offset: int,
    *,
    local_name: str,
    expected: object,
    error: BaseException,
) -> Callable[[FrameType, str, object], object]:
    armed = True

    def trace(frame: FrameType, event: str, _arg: object) -> object:
        nonlocal armed
        if frame.f_code is function.__code__:
            frame.f_trace_opcodes = True
            if armed and event == "opcode" and frame.f_lasti == offset:
                assert frame.f_locals.get(local_name) is expected
                armed = False
                raise error
            return trace
        return None

    return trace


def test_owned_cleanup_post_store_interrupt_completes_before_control_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(monkeypatch, private, events)
    cleanup_function = cleanup.cleanup_owned_resources
    offset = _opcode_after_store(cleanup_function, "no_live_proved")
    trace = _interrupt_once(
        cleanup_function,
        offset,
        local_name="no_live_proved",
        expected=False,
        error=KeyboardInterrupt("pre-cleanup"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="pre-cleanup"):
            session.finish()
    finally:
        sys.settrace(previous)

    assert events.count(f"signal:{signal.SIGTERM}") == 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()
    frozen = tuple(events)
    session.finish()
    assert tuple(events) == frozen


def test_popen_post_store_interrupt_enters_publication_fallback(
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
    offset = _opcode_after_store(
        vars(supervisor)["_launch_worker"],
        "process",
        last=True,
    )
    trace = _interrupt_once(
        vars(supervisor)["_launch_worker"],
        offset,
        local_name="process",
        expected=process,
        error=KeyboardInterrupt("post-store"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="post-store"):
            vars(supervisor)["_launch_worker"](PROFILE, 1.0, session)
    finally:
        sys.settrace(previous)

    published = session.lifecycle.owner.process is process
    locally_cleaned = (
        process.stdin.closed
        and process.stdout.closed
        and sum(event.startswith("reap:") for event in events) == 1
    )
    assert published or locally_cleaned

    session.finish()
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


def test_selector_post_store_interrupt_closes_local_selector(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, process = _session(monkeypatch, tmp_path / "private", events)
    selector = WorkerSelector(WorkerClock(), (), events)
    offset = _opcode_after_store(
        lifecycle.acquire_worker_selector,
        "selector",
        last=True,
    )
    trace = _interrupt_once(
        lifecycle.acquire_worker_selector,
        offset,
        local_name="selector",
        expected=selector,
        error=KeyboardInterrupt("selector-post-store"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="selector-post-store"):
            exchange.exchange_worker_process(
                _config(),
                _hooks(session, lambda: selector),
                session,
            )
    finally:
        sys.settrace(previous)

    assert events.count("selector-close") == 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert not (tmp_path / "private").exists()


def test_unpublished_process_live_group_retains_private_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    kill_errors: list[BaseException] = [InterruptedError() for _ in range(32)]
    private = tmp_path / "private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(
            bind_process=False,
            term_ignored=True,
            kill_errors=kill_errors,
        ),
    )
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *_args, **_kwargs: process)

    def reject_publication(
        _owner: lifecycle.WorkerLifecycleOwner,
        _process: Popen[bytes],
    ) -> None:
        raise KeyboardInterrupt(_PUBLICATION_MESSAGE)

    monkeypatch.setattr(
        lifecycle.WorkerLifecycleOwner,
        "bind_process",
        reject_publication,
    )

    with pytest.raises(KeyboardInterrupt, match="publication") as raised:
        vars(supervisor)["_launch_worker"](PROFILE, 1.0, session)
    session.finish(raised.value)

    assert session.lifecycle.owner.process is None
    assert session.state.cleanup_failed is True
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert "group-probe" in events
    assert 0 < events.count(f"signal:{signal.SIGKILL}") < 32
    assert kill_errors
    assert "remove" not in events
    assert private.exists()


def test_unbound_cleanup_post_store_interrupt_preserves_publication_primary(
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

    def reject_publication(
        _owner: lifecycle.WorkerLifecycleOwner,
        _process: Popen[bytes],
    ) -> None:
        raise KeyboardInterrupt(_PUBLICATION_MESSAGE)

    monkeypatch.setattr(lifecycle.WorkerLifecycleOwner, "bind_process", reject_publication)
    cleanup_function = cleanup.cleanup_unbound_process
    offset = _opcode_after_store(cleanup_function, "no_live_proved")
    trace = _interrupt_once(
        cleanup_function,
        offset,
        local_name="no_live_proved",
        expected=True,
        error=KeyboardInterrupt("cleanup-post-store"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="publication") as raised:
            vars(supervisor)["_launch_worker"](PROFILE, 1.0, session)
    finally:
        sys.settrace(previous)
    session.finish(raised.value)

    assert session.lifecycle.owner.process_acquisition_state in {
        "resolved_safe",
        "resolved_unsafe",
    }
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


@pytest.mark.parametrize("resolution", ["publish", "timeout"])
def test_concurrent_finish_during_process_acquisition_waits_or_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolution: str,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(bind_process=False),
    )
    owner = session.lifecycle.owner
    owner.begin_process_acquisition()
    if resolution == "timeout":
        monkeypatch.setattr(
            lifecycle,
            "_process_acquisition_timeout",
            lambda _context: 0.01,
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(session.finish)
        if resolution == "publish":
            with pytest.raises(TimeoutError):
                future.result(timeout=0.05)
            assert not events
            assert private.exists()

            owner.publish_process(cast("Popen[bytes]", process))
            future.result(timeout=2)

            assert events.count(f"signal:{signal.SIGTERM}") == 1
            assert sum(event.startswith("reap:") for event in events) == 1
            assert events.count("remove") == 1
            assert not private.exists()
        else:
            acquisition_error = vars(lifecycle)["_LifecycleAcquisitionIncompleteError"]
            with pytest.raises(acquisition_error):
                future.result(timeout=2)

            assert not any(event.startswith("signal:") for event in events)
            assert "remove" not in events
            assert private.exists()

            owner.resolve_process_acquisition(safe_to_remove_directory=False)
            session.finish()
            assert session.state.cleanup_failed is True
            assert "remove" not in events
            assert private.exists()


def test_acquisition_timeout_rechecks_published_state_before_failing(
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
    owner = session.lifecycle.owner
    owner.begin_process_acquisition()

    class TimeoutRaceEvent:
        def wait(self, timeout: float | None = None) -> bool:
            assert timeout is not None
            assert timeout > 0
            owner.publish_process(cast("Popen[bytes]", process))
            return False

        def set(self) -> None:
            events.append("acquisition-set")

    monkeypatch.setattr(owner, "_process_acquisition_complete", TimeoutRaceEvent())

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(session.finish).result(timeout=2)

    assert "acquisition-set" in events
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


def _opcode_for_store_attribute(
    function: types.FunctionType,
    name: str,
) -> frozenset[int]:
    instructions = list(dis.get_instructions(function))
    return frozenset(
        instruction.offset
        for instruction in instructions
        if instruction.opname == "STORE_ATTR" and instruction.argval == name
    )


def _cleanup_state(owner: lifecycle.WorkerLifecycleOwner) -> str:
    return cast("str", object.__getattribute__(owner, "_cleanup_state"))


def _cleanup_thread(owner: lifecycle.WorkerLifecycleOwner) -> int | None:
    return cast("int | None", object.__getattribute__(owner, "_cleanup_thread"))


def _cleanup_complete(owner: lifecycle.WorkerLifecycleOwner) -> threading.Event:
    return cast("threading.Event", object.__getattribute__(owner, "_cleanup_complete"))


def _interrupt_before_attribute_store(
    function: types.FunctionType,
    offsets: frozenset[int],
    *,
    owner: lifecycle.WorkerLifecycleOwner,
    error: BaseException,
) -> Callable[[FrameType, str, object], object]:
    armed = True

    def trace(frame: FrameType, event: str, _arg: object) -> object:
        nonlocal armed
        if frame.f_code is function.__code__:
            frame.f_trace_opcodes = True
            if armed and event == "opcode" and frame.f_lasti in offsets:
                assert _cleanup_state(owner) == "running"
                armed = False
                raise error
            return trace
        return None

    return trace


def _raise_ambient_error() -> None:
    raise ValueError(_AMBIENT_MESSAGE)


def test_finish_action_post_store_interrupt_still_completes_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(monkeypatch, private, events)
    finish = vars(lifecycle.WorkerLifecycleOwner)["finish"]
    offset = _opcode_after_store(finish, "action", last=True)
    trace = _interrupt_once(
        finish,
        offset,
        local_name="action",
        expected="cleanup",
        error=KeyboardInterrupt("finish-action"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="finish-action"):
            session.finish()
    finally:
        sys.settrace(previous)

    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert _cleanup_state(session.lifecycle.owner) == "done"
    assert _cleanup_complete(session.lifecycle.owner).is_set()
    frozen = tuple(events)
    session.finish()
    assert tuple(events) == frozen


def test_cleanup_finalization_interrupt_publishes_terminal_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, _process = _session(monkeypatch, private, events)
    owner = session.lifecycle.owner
    finalizer = vars(lifecycle.WorkerLifecycleOwner)["_publish_cleanup_terminal"]
    offsets = _opcode_for_store_attribute(finalizer, "_cleanup_state")
    trace = _interrupt_before_attribute_store(
        finalizer,
        offsets,
        owner=owner,
        error=KeyboardInterrupt("cleanup-finalization"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="cleanup-finalization"):
            session.finish()
    finally:
        sys.settrace(previous)

    assert _cleanup_state(owner) == "done"
    assert _cleanup_thread(owner) is None
    assert _cleanup_complete(owner).is_set()
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    frozen = tuple(events)
    session.finish()
    assert tuple(events) == frozen


def test_cleanup_timeout_rechecks_done_state_before_failing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, _process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(bind_process=False),
    )
    owner = session.lifecycle.owner
    object.__setattr__(owner, "_cleanup_state", "running")
    object.__setattr__(owner, "_cleanup_thread", -1)

    class TimeoutRaceEvent:
        def wait(self, timeout: float | None = None) -> bool:
            assert timeout is not None
            assert timeout > 0
            private.rmdir()
            object.__setattr__(owner, "_cleanup_state", "done")
            return False

    monkeypatch.setattr(owner, "_cleanup_complete", TimeoutRaceEvent())

    session.finish()

    assert _cleanup_state(owner) == "done"
    assert not private.exists()


def test_exchange_ignores_ambient_exception_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session, _process = _session(
        monkeypatch,
        tmp_path / "private",
        [],
        _SessionOptions(signal_error=KeyboardInterrupt("cleanup")),
    )
    config = dataclasses.replace(_config(), initial_cause="pipe_failed")

    try:
        _raise_ambient_error()
    except ValueError:
        with pytest.raises(KeyboardInterrupt, match="cleanup"):
            exchange.exchange_worker_process(
                config,
                _hooks(session, lambda: WorkerSelector(WorkerClock(), (), [])),
                session,
            )


def test_supervisor_ignores_ambient_exception_when_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(signal_error=KeyboardInterrupt("cleanup")),
    )
    hooks = _hooks(session, lambda: WorkerSelector(WorkerClock(), (), events))
    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: True)
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(supervisor, "_worker_runtime", lambda _name: (object(), hooks))
    monkeypatch.setattr(supervisor, "create_private_directory", lambda: private)
    monkeypatch.setattr(supervisor, "prepare_worker_exchange", lambda *_args: session)
    monkeypatch.setattr(supervisor.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(
        supervisor,
        "_launch_worker",
        lambda *_args: types.SimpleNamespace(process=process, wall_deadline=2.0),
    )
    monkeypatch.setattr(
        supervisor,
        "_prepare_worker",
        lambda *_args: types.SimpleNamespace(
            telemetry=None,
            baseline=None,
            sampled_at=None,
            request_permitted=False,
            initial_cause="pipe_failed",
        ),
    )
    monkeypatch.setattr(
        supervisor,
        "exchange_worker_process",
        lambda *_args: exchange.WorkerExchangeResult(
            stdout=b"",
            stdout_eof=True,
            returncode=0,
            first_cause=None,
            cleanup_failed=False,
        ),
    )
    monkeypatch.setattr(supervisor, "_interpret_worker_outcome", lambda *_args: object())
    admitted = types.SimpleNamespace(
        profile=PROFILE,
        request_frame=b"request",
        protocol=_config().protocol,
        request=object(),
    )

    try:
        _raise_ambient_error()
    except ValueError:
        with pytest.raises(KeyboardInterrupt, match="cleanup"):
            vars(supervisor)["_run_admitted_worker"](admitted)


def test_worker_launch_does_not_duplicate_private_directory_identity() -> None:
    fields = {item.name for item in dataclasses.fields(vars(supervisor)["_WorkerLaunch"])}

    assert fields == {"process", "wall_deadline"}


def test_session_cleanup_is_active_immediately_after_publication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(monkeypatch, private, events)
    hooks = _hooks(session, lambda: WorkerSelector(WorkerClock(), (), events))
    monkeypatch.setattr(supervisor, "_bootstrap_available", lambda: True)
    monkeypatch.setattr(supervisor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(supervisor, "_worker_runtime", lambda _name: (object(), hooks))
    monkeypatch.setattr(supervisor, "create_private_directory", lambda: private)
    monkeypatch.setattr(supervisor, "prepare_worker_exchange", lambda *_args: session)
    admitted = types.SimpleNamespace(
        profile=PROFILE,
        request_frame=b"request",
        protocol=_config().protocol,
        request=object(),
    )
    run = vars(supervisor)["_run_admitted_worker"]
    offset = _opcode_after_store(run, "exchange", last=True)
    trace = _interrupt_once(
        run,
        offset,
        local_name="exchange",
        expected=session,
        error=KeyboardInterrupt("owner-window"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="owner-window"):
            run(admitted)
    finally:
        sys.settrace(previous)

    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


def test_term_post_store_interrupt_still_runs_kill_and_reap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    private = tmp_path / "private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(term_ignored=True),
    )
    terminate = vars(cleanup)["_terminate_process_group"]
    offset = _opcode_after_store(terminate, "term_delivered", last=True)
    trace = _interrupt_once(
        terminate,
        offset,
        local_name="term_delivered",
        expected=True,
        error=KeyboardInterrupt("term-post-store"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="term-post-store"):
            session.finish()
    finally:
        sys.settrace(previous)

    assert events.count(f"signal:{signal.SIGTERM}") == 1
    assert events.count(f"signal:{signal.SIGKILL}") == 1
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


def test_unbound_resolution_post_store_preserves_publication_primary(
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

    def reject_publication(
        _owner: lifecycle.WorkerLifecycleOwner,
        _process: Popen[bytes],
    ) -> None:
        raise KeyboardInterrupt(_PUBLICATION_MESSAGE)

    monkeypatch.setattr(lifecycle.WorkerLifecycleOwner, "bind_process", reject_publication)
    resolve = lifecycle.resolve_worker_process_acquisition
    offset = _opcode_after_store(resolve, "safe_to_remove_directory", last=True)
    trace = _interrupt_once(
        resolve,
        offset,
        local_name="safe_to_remove_directory",
        expected=True,
        error=KeyboardInterrupt("resolution-post-store"),
    )

    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt, match="publication") as raised:
            vars(supervisor)["_launch_worker"](PROFILE, 1.0, session)
    finally:
        sys.settrace(previous)
    session.finish(raised.value)

    assert session.lifecycle.owner.process_acquisition_state == "resolved_safe"
    assert process.stdin.closed
    assert process.stdout.closed
    assert sum(event.startswith("reap:") for event in events) == 1
    assert events.count("remove") == 1
    assert not private.exists()


def test_worker_launch_uses_only_owner_private_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launch = vars(supervisor)["_launch_worker"]
    assert tuple(inspect.signature(launch).parameters) == (
        "profile",
        "wall_deadline",
        "exchange",
    )
    events: list[str] = []
    private = tmp_path / "owner-private"
    session, process = _session(
        monkeypatch,
        private,
        events,
        _SessionOptions(bind_process=False),
    )
    observed: dict[str, object] = {}

    def spawn(*_args: object, **kwargs: object) -> Popen[bytes]:
        observed.update(kwargs)
        return cast("Popen[bytes]", process)

    monkeypatch.setattr(supervisor.subprocess, "Popen", spawn)
    result = launch(PROFILE, 1.0, session)

    assert result is not None
    assert observed["cwd"] == str(private)
    assert observed["env"] == {
        "HOME": str(private),
        "TMPDIR": str(private),
        "TMP": str(private),
        "TEMP": str(private),
    }
    session.finish()
    assert not private.exists()


def test_cleanup_capability_cause_does_not_replace_existing_first_cause(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    session, _process = _session(
        monkeypatch,
        tmp_path / "private",
        events,
        _SessionOptions(
            signal_error=WorkerIsolationUnsupportedError("missing signal capability"),
        ),
    )
    session.state.trigger("timeout")

    session.finish()

    assert session.state.first_cause == "timeout"
    assert session.state.cleanup_cause == "capability_failed"
    assert session.state.cleanup_failed is True

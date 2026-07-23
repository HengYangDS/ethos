"""Behavioral RED contract for one-shot source-budget worker supervision."""

from __future__ import annotations

import ast
import contextlib
import ctypes
import dataclasses
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import resource
import signal
import struct
import subprocess
import sys
import time
import types
import typing as t
from collections import deque
from pathlib import Path

import pytest

import ethos_core.contracts.source_budget.measurement.worker.protocol.core as worker_protocol
import ethos_core.contracts.source_budget.measurement.worker.protocol.frame as worker_frame
import ethos_core.contracts.source_budget.measurement.worker.resource as worker_resource
import ethos_core.contracts.source_budget.measurements as measurements
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement.native.identity import resolve_native_provider
from tests.support.source_budget_worker import UnexpectedCleanupError as _UnexpectedCleanupError
from tests.support.source_budget_worker import WorkerClock as _Clock
from tests.support.source_budget_worker import WorkerGroupProbe as _GroupProbe
from tests.support.source_budget_worker import WorkerProcess as _Process
from tests.support.source_budget_worker import WorkerRawIO as _RawIO
from tests.support.source_budget_worker import WorkerSelector as _Selector
from tests.support.source_budget_worker import WorkerTelemetry as _Telemetry
from tests.support.source_budget_worker import (
    assert_emergency_exchange as _assert_emergency_exchange,
)
from tests.support.source_budget_worker import step as _step

BACKEND = "ethos.adapters.repo.source_budget.measurement.worker.backend.core"
LINUX = "ethos.adapters.repo.source_budget.measurement.worker.backend.linux.core"
DARWIN = "ethos.adapters.repo.source_budget.measurement.worker.backend.darwin.core"
BOOTSTRAP = "ethos.adapters.repo.source_budget.measurement.worker.bootstrap.core"
SUPERVISOR = "ethos.adapters.repo.source_budget.measurement.worker.supervisor.core"
EXCHANGE = "ethos.adapters.repo.source_budget.measurement.worker.supervisor.io"
LIFECYCLE = "ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core"
ISOLATED = "ethos.adapters.repo.source_budget.measurement.native.isolated.core"
PROFILE = worker_resource.worker_resource_profile_descriptor()
PROTOCOL = worker_protocol.worker_protocol_descriptor()
_Cause = t.Literal[
    "timeout", "resource_exhausted", "output_exceeded", "pipe_failed", "capability_failed"
]

# fmt: off

def _module(name: str) -> types.ModuleType:
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"required Task 4 module is missing: {name}: {exc}", pytrace=False)


def _root() -> Path:
    local = Path(__file__).resolve().parents[5]
    if (local / "system/authority.toml").is_file():
        return local
    origin = getattr(importlib.util.find_spec("ethos"), "origin", None)
    assert origin is not None
    return Path(origin).resolve().parents[4]


@pytest.fixture(scope="module")
def worker_case() -> types.SimpleNamespace:
    load = load_metric_contracts(_root())
    assert load.required_gaps == ()
    assert load.contracts is not None
    contracts = tuple(sorted((item for item in load.contracts.contracts if item.metric_profile == "json-source-v2"), key=lambda item: (item.metric_id, item.unit, item.contract_id)))
    content = b'{"name":"ethos"}\n'
    resolved = resolve_native_provider(contracts, load.contracts)
    request = worker_protocol.WorkerRequest.create(content=content, contracts=resolved.contracts, provider_descriptor=resolved.provider_descriptor, execution_descriptor=resolved.execution_descriptor)
    values = tuple(measurements.MetricValue(contract_id=item.contract_id, metric_id=item.metric_id, unit=item.unit, value=1) for item in request.contracts)
    measurement = measurements.NativeMeasurement.create(content_sha256=request.content_sha256, normalized_digest=hashlib.sha256(b"normalized").hexdigest(), contracts=request.contracts, values=values)
    success = worker_protocol.WorkerResult.from_measurement(request=request, measurement=measurement)
    gap = worker_protocol.WorkerResult.from_gap(request=request, gap="source_budget_native_runtime_unsupported")
    return types.SimpleNamespace(resolved=resolved, request=request, content=content, success=success, success_frame=worker_frame.encode_result_frame(success), gap_frame=worker_frame.encode_result_frame(gap))



@dataclasses.dataclass(frozen=True, slots=True)
class _SuperviseOptions:
    system: str = "Linux"
    spawn_error: BaseException | None = None
    sample_value: object | None = None
    real_readiness: bool = False
    exchange_error: BaseException | None = None
    ticks: tuple[float, ...] = (100.0, 101.0, 102.0, 103.0)


@dataclasses.dataclass(frozen=True, slots=True)
class _ExchangeOptions:
    frame: bytes = b"x"
    actions: tuple[str | BaseException, ...] = ("stdin", "stdout", "stdout")
    writes: tuple[int | BaseException, ...] = (1,)
    reads: tuple[bytes | BaseException, ...] = (b"",)
    polls: tuple[int | None, ...] = (None, 0)
    samples: tuple[object, ...] | None = None
    baseline: int | None = None
    group_alive: bool = False
    cleanup_error_stage: str | None = None
    wall_deadline: float = PROFILE.wall_seconds
    initial_cause: _Cause | None = None


_DEFAULT_SUPERVISE_OPTIONS = _SuperviseOptions()
_DEFAULT_EXCHANGE_OPTIONS = _ExchangeOptions()


class _SupervisorBackend:
    def __init__(self, process: _Process, telemetry: _Telemetry, events: list[str]) -> None:
        self.process, self.telemetry, self.events = process, telemetry, events

    def open_parent_telemetry(self, pid: int, profile: object) -> _Telemetry:
        self.events.append("telemetry")
        assert (pid, profile) == (self.process.pid, PROFILE)
        return self.telemetry

    def signal_process_group(self, _pid: int, sig: int) -> None:
        self.events.append(f"signal:{sig}")

    def probe_process_group(self, _pid: int, *, direct_child_terminal: bool) -> object:
        self.events.append("group-probe")
        states = _module(BACKEND).WorkerProcessGroupState
        return states.TERMINAL_ONLY if direct_child_terminal else states.ABSENT



def _limits() -> dict[int, tuple[int, int]]:
    same = ((resource.RLIMIT_NOFILE, PROFILE.nofile), (resource.RLIMIT_NPROC, PROFILE.nproc), (resource.RLIMIT_CORE, PROFILE.core_bytes), (resource.RLIMIT_FSIZE, PROFILE.regular_file_bytes))
    return {resource.RLIMIT_CPU: (PROFILE.cpu_soft_seconds, PROFILE.cpu_hard_seconds), **{key: (value, value) for key, value in same}}


def _outcome(**changes: object) -> object:
    values = {"stdout": b"", "stdout_eof": True, "returncode": 0, "first_cause": None, "cleanup_failed": False}
    return _module(EXCHANGE).WorkerExchangeResult(**(values | changes))


def _bootstrap(monkeypatch: pytest.MonkeyPatch, case: types.SimpleNamespace, frame: bytes, error=None, *, io_steps: tuple[tuple[bytes | BaseException, ...], tuple[int | BaseException, ...]] | None = None):
    module, events = _module(BOOTSTRAP), []
    read_steps, write_steps = io_steps or ((), ())
    chunks, output, maximums = deque(read_steps or (frame, b"")), bytearray(), []
    writes, write_attempts = deque[int | BaseException](write_steps), []

    class Backend:
        def apply_child_limits(self, profile: object) -> None:
            events.append("limits")
            assert profile == PROFILE
            if error is not None:
                raise error

    def read(fd: int, maximum: int) -> bytes:
        events.append("read")
        maximums.append(maximum)
        assert fd == 0
        return _step(chunks, b"")

    def write(fd: int, payload: bytes | memoryview) -> int:
        events.append("write")
        write_attempts.append(bytes(payload))
        count = min(_step(writes, 5), len(payload))
        output.extend(bytes(payload[:count]))
        assert fd == 1
        return count

    def importer(name: str) -> object:
        events.append("import")
        assert name == ISOLATED
        return types.SimpleNamespace(measure_isolated=lambda _request, _content: case.success)

    monkeypatch.setattr(module, "worker_backend", Backend)
    monkeypatch.setattr(module.os, "getpid", lambda: 9)
    monkeypatch.setattr(module.os, "kill", lambda pid, sig: events.append(f"stop:{pid}:{sig}"))
    monkeypatch.setattr(module.os, "read", read)
    monkeypatch.setattr(module.os, "write", write)
    monkeypatch.setattr(module.os, "close", lambda fd: events.append(f"close:{fd}"))
    monkeypatch.setattr(module, "importlib", types.SimpleNamespace(import_module=importer))
    code = module.main()
    return types.SimpleNamespace(code=code, events=events, output=bytes(output), maximums=maximums, write_attempts=write_attempts)


def _patch_readiness(monkeypatch: pytest.MonkeyPatch, module: types.ModuleType, events: list[str], *, real: bool) -> None:
    if not real:
        monkeypatch.setattr(module, "_await_resource_ready", lambda *_args: types.SimpleNamespace(ready=True, initial_cause=None))
        return
    def waitid(_kind: int, pid: int, options: int) -> object:
        events.append(f"readiness-waitid:{options}")
        return types.SimpleNamespace(si_pid=pid, si_code=module.os.CLD_STOPPED, si_status=signal.SIGSTOP)
    monkeypatch.setattr(module.os, "waitid", waitid)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: pytest.fail("arbitrary readiness sleep"))


def _supervise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: types.SimpleNamespace,
    outcome: object,
    options: _SuperviseOptions = _DEFAULT_SUPERVISE_OPTIONS,
):
    module, events, calls = _module(SUPERVISOR), [], []
    process, private = _Process(events), tmp_path / "worker-private"
    sample = _module(BACKEND).WorkerResourceSample(1, 2) if options.sample_value is None else options.sample_value
    telemetry = _Telemetry((sample,), events)
    backend = _SupervisorBackend(process, telemetry, events)

    def popen(*args: object, **kwargs: object) -> _Process:
        calls.append((args, kwargs))
        events.append("spawn")
        if options.spawn_error is not None:
            raise options.spawn_error
        return process

    def exchange(config, hooks, session) -> object:
        events.append(f"deadline:{config.wall_deadline}")
        events.append(f"exchange-config:{config.request_permitted}:{config.initial_cause}")
        assert session.lifecycle.owner.process is process
        assert (config.profile, config.protocol) == (PROFILE, PROTOCOL)
        assert hooks.send_group_signal == backend.signal_process_group
        assert hooks.probe_process_group == backend.probe_process_group
        if config.request_frame == b"":
            _assert_emergency_exchange(config, process, events, PROFILE.term_grace_ms / 1000)
        else:
            events.append("exchange")
            assert config.request_frame == worker_frame.encode_request_frame(case.request, case.content)
        if options.exchange_error is not None:
            raise options.exchange_error
        return _outcome(first_cause=config.initial_cause) if config.initial_cause is not None else outcome

    def mkdtemp(**_kwargs: object) -> str:
        private.mkdir(mode=0o700)
        return str(private)

    ticks = deque(options.ticks)
    monkeypatch.setattr(module.time, "monotonic", lambda: (events.append("clock"), ticks[0] if len(ticks) == 1 else ticks.popleft())[1])
    cleanup_clock = _Clock(0.001)

    def wait_for(seconds: float) -> None:
        events.append("cleanup-wait")
        cleanup_clock.now += seconds

    def remove_directory(path: Path) -> None:
        events.append("remove")
        path.rmdir()

    hooks_type = _module(EXCHANGE).WorkerExchangeHooks
    monkeypatch.setattr(
        module,
        "WorkerExchangeHooks",
        lambda **values: hooks_type(
            **values,
            monotonic=cleanup_clock.monotonic,
            wait_for=wait_for,
            remove_directory=remove_directory,
        ),
    )
    def observe_direct_child(child: _Process) -> int | None:
        events.append("observe")
        value = child.returncodes.popleft() if child.returncodes else child.returncode
        child.returncode = value if value is not None else child.returncode
        return value

    monkeypatch.setattr(_module(EXCHANGE), "_observe_direct_child", observe_direct_child)
    monkeypatch.setattr(module, "importlib", types.SimpleNamespace(util=types.SimpleNamespace(find_spec=lambda _name: object())))
    monkeypatch.setattr(module.platform, "system", lambda: options.system)
    monkeypatch.setattr(_module(LIFECYCLE).tempfile, "mkdtemp", mkdtemp)
    monkeypatch.setattr(module.subprocess, "Popen", popen)
    monkeypatch.setattr(module, "worker_backend", lambda _name: backend)
    _patch_readiness(monkeypatch, module, events, real=options.real_readiness)
    monkeypatch.setattr(module.os, "killpg", lambda _pid, sig: events.append(f"signal:{sig}"))
    monkeypatch.setattr(module, "exchange_worker_process", exchange)
    return types.SimpleNamespace(load=module.run_isolated_worker(case.request, case.content), calls=calls, events=events, private=private, process=process)


def _exchange(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    options: _ExchangeOptions = _DEFAULT_EXCHANGE_OPTIONS,
):
    module, events, clock = _module(EXCHANGE), [], _Clock(0.0 if options.cleanup_error_stage == "wait-live" else 0.001)
    process = _Process(events, options.polls)
    raw = _RawIO(options.writes, options.reads, events)
    selector = _Selector(clock, options.actions, events, fail_close=options.cleanup_error_stage == "close")
    sample = _module(BACKEND).WorkerResourceSample(1, 2)
    telemetry = _Telemetry(options.samples or (sample,), events)
    signals, alive = [], {"value": options.group_alive}
    private = tmp_path / "private"
    private.mkdir()

    def waitid(_kind: int, pid: int, options: int) -> object | None:
        events.append(f"waitid:{options}")
        value = process.returncodes.popleft() if process.returncodes else process.returncode
        if value is None:
            return None
        process.returncode = value
        code = module.os.CLD_EXITED if value >= 0 else module.os.CLD_KILLED
        return types.SimpleNamespace(si_pid=pid, si_code=code, si_status=abs(value))

    monkeypatch.setattr(module.os, "set_blocking", raw.set_blocking)
    monkeypatch.setattr(module.os, "write", raw.write)
    monkeypatch.setattr(module.os, "read", raw.read)
    monkeypatch.setattr(module.os, "waitid", waitid)

    def send_group_signal(_pgid: int, sig: int) -> None:
        events.append(f"signal:{sig}")
        signals.append((clock.now, sig))
        if options.cleanup_error_stage in {"signal", "memory"}:
            raise MemoryError() if options.cleanup_error_stage == "memory" else _UnexpectedCleanupError()
        if sig == signal.SIGKILL and options.cleanup_error_stage != "wait-live":
            alive["value"] = False

    def wait_for(seconds: float) -> None:
        events.append("cleanup-wait")
        if options.cleanup_error_stage in {"wait", "wait-live"}:
            raise _UnexpectedCleanupError
        clock.now += seconds

    def remove_directory(path: Path) -> None:
        events.append("remove")
        path.rmdir()
        if options.cleanup_error_stage == "remove":
            raise _UnexpectedCleanupError

    config = module.WorkerExchangeConfig(request_frame=options.frame, telemetry=telemetry, profile=PROFILE, protocol=PROTOCOL, wall_deadline=options.wall_deadline, darwin_vms_baseline=options.baseline, initial_cause=options.initial_cause)
    hooks = module.WorkerExchangeHooks(
        send_group_signal=send_group_signal,
        probe_process_group=_GroupProbe(alive, events, fail=options.cleanup_error_stage == "probe"),
        monotonic=clock.monotonic,
        selector_factory=lambda: selector,
        wait_for=wait_for,
        remove_directory=remove_directory,
    )
    session = module.prepare_worker_exchange(private, PROFILE, hooks)
    session.bind_process(process)
    try:
        result = module.exchange_worker_process(config, hooks, session)
    finally:
        session.finish()
    return types.SimpleNamespace(result=result, events=events, process=process, private=private, raw=raw, signals=signals, selector=selector, session=session)


def _raw_result(result: worker_protocol.WorkerResult, gap: str) -> bytes:
    payload = result.model_dump(mode="json", by_alias=True)
    payload.update(success=None, gap=gap)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return PROTOCOL.result_magic.encode() + struct.pack(">I", len(encoded)) + encoded


def test_worker_backend_admits_only_linux_and_darwin() -> None:
    module = _module(BACKEND)
    assert module.worker_backend("Linux").__class__.__module__ == LINUX
    assert module.worker_backend("Darwin").__class__.__module__ == DARWIN
    for name in ("FreeBSD", "POSIX", "Windows"):
        with pytest.raises(module.WorkerIsolationUnsupportedError):
            module.worker_backend(name)


def test_linux_child_limits_apply_every_exact_resource_value(monkeypatch: pytest.MonkeyPatch) -> None:
    module, calls, reads = _module(LINUX), [], []
    monkeypatch.setattr(module.resource, "setrlimit", lambda key, value: calls.append((key, value)))
    monkeypatch.setattr(module.resource, "getrlimit", lambda key: (reads.append(key), dict(calls)[key])[1])
    module.LinuxWorkerBackend().apply_child_limits(PROFILE)
    expected = {**_limits(), resource.RLIMIT_AS: (PROFILE.linux_address_space_bytes,) * 2}
    assert dict(calls) == expected
    assert reads == list(expected)


def test_darwin_child_limits_omit_false_absolute_as_rss_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    module, calls, reads = _module(DARWIN), [], []
    monkeypatch.setattr(module.resource, "setrlimit", lambda key, value: calls.append((key, value)))
    monkeypatch.setattr(module.resource, "getrlimit", lambda key: (reads.append(key), dict(calls)[key])[1])
    module.DarwinWorkerBackend().apply_child_limits(PROFILE)
    assert dict(calls) == _limits()
    assert reads == list(_limits())
    assert resource.RLIMIT_AS not in dict(calls)
    assert resource.RLIMIT_RSS not in dict(calls)


def test_child_limit_failure_is_isolation_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    backend, module = _module(BACKEND), _module(LINUX)
    monkeypatch.setattr(module.resource, "setrlimit", lambda *_args: None)
    monkeypatch.setattr(module.resource, "getrlimit", lambda _key: (-1, -1))
    with pytest.raises(backend.WorkerIsolationUnsupportedError):
        module.LinuxWorkerBackend().apply_child_limits(PROFILE)
    def status(uid: str = "1000 1000 1000 1000", eff: str = "0", prm: str = "0") -> str:
        return f"Uid: {uid}\nCapEff: {eff}\nCapPrm: {prm}\n"
    accepted = (status(), status("1000 0 0 0"), status(eff="2"))
    rejected = (status("0 1000 1000 1000"), status(eff=f"{1 << 21:x}"), status(prm=f"{1 << 24:x}"), status().replace("CapPrm: 0\n", ""), status() + "CapEff: 0\n", status(eff="xyz"), status(eff="1" * 17), "CapEff: 0\nCapPrm: 0\n", status("1000 nope 1000 1000"))
    for payload in accepted:
        paths: list[Path] = []
        monkeypatch.setattr(module, "_read_status", lambda path, value=payload, seen=paths: (seen.append(path), value)[1])
        assert module.LinuxWorkerBackend().open_parent_telemetry(4242, PROFILE).pid == 4242
        assert paths == [Path("/proc/4242/status")]
    for payload in rejected:
        paths = []
        monkeypatch.setattr(module, "_read_status", lambda path, value=payload, seen=paths: (seen.append(path), value)[1])
        with pytest.raises(backend.WorkerIsolationUnsupportedError):
            module.LinuxWorkerBackend().open_parent_telemetry(4242, PROFILE)
        assert paths == [Path("/proc/4242/status")]
    assert all(token not in Path(t.cast("str", module.__file__)).read_text() for token in ("getuid(", "geteuid(", "/proc/self/status"))


def test_linux_telemetry_parses_exact_rss_and_vms_without_defaulting() -> None:
    module = _module(LINUX)
    text = "Name:\tworker\nVmSize:\t4096 kB\nVmRSS:\t2048 kB\n"
    sample = module.LinuxWorkerTelemetry(7, lambda _path: text).sample()
    assert sample == _module(BACKEND).WorkerResourceSample(2048 << 10, 4096 << 10)


def test_linux_missing_or_malformed_proc_telemetry_fails_closed() -> None:
    module, error = _module(LINUX), _module(BACKEND).WorkerIsolationUnsupportedError
    texts = ("VmSize: 4 kB\n", "VmRSS: 2 kB\n", "VmSize: 4 MB\nVmRSS: 2 kB\n")
    for text in texts:
        with pytest.raises(error):
            module.LinuxWorkerTelemetry(7, lambda _path, value=text: value).sample()


def test_darwin_telemetry_reads_exact_taskinfo_fields() -> None:
    module, observed = _module(DARWIN), {}

    def probe(pid: int, flavor: int, _arg: int, buffer: object, size: int) -> int:
        observed.update(pid=pid, flavor=flavor, size=size)
        info = ctypes.cast(t.cast("ctypes.c_void_p", buffer), ctypes.POINTER(module.ProcTaskInfo)).contents
        info.pti_resident_size, info.pti_virtual_size = 123, 456
        return ctypes.sizeof(module.ProcTaskInfo)

    sample = module.DarwinWorkerTelemetry(9, probe).sample()
    assert sample == _module(BACKEND).WorkerResourceSample(123, 456)
    assert observed["size"] == ctypes.sizeof(module.ProcTaskInfo) == 96


def test_darwin_first_successful_vms_sample_is_immutable_baseline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.gap_frame), _SuperviseOptions(system="Darwin", real_readiness=True))
    wait_event = next(event for event in run.events if event.startswith("readiness-waitid:"))
    assert int(wait_event.split(":")[1]) & _module(SUPERVISOR).os.WNOWAIT
    assert run.events.index(wait_event) < run.events.index("telemetry") < run.events.index(f"signal:{signal.SIGCONT}") < run.events.index("exchange")


def test_missing_darwin_baseline_is_isolation_unsupported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    missing = _module(BACKEND).WorkerResourceSample(1, None)
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(), _SuperviseOptions(system="Darwin", real_readiness=True, sample_value=missing))
    assert run.load.required_gaps == ("source_budget_worker_isolation_unsupported",)
    assert f"signal:{signal.SIGCONT}" not in run.events
    assert not any(event.startswith(("register:stdin", "write:")) for event in run.events)


def test_bootstrap_applies_resources_before_isolated_engine_import(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    run = _bootstrap(monkeypatch, worker_case, worker_frame.encode_request_frame(worker_case.request, worker_case.content))
    assert run.code == os.EX_OK
    assert run.events.index("limits") < run.events.index(f"stop:9:{signal.SIGSTOP}")
    assert run.events.index(f"stop:9:{signal.SIGSTOP}") < run.events.index("read") < run.events.index("import")


def test_bootstrap_reads_only_one_bounded_request_frame(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    frame = worker_frame.encode_request_frame(worker_case.request, worker_case.content)
    run = _bootstrap(monkeypatch, worker_case, frame, io_steps=((InterruptedError(), frame, InterruptedError(), b""), ()))
    assert run.code == os.EX_OK
    assert max(run.maximums) <= PROTOCOL.stdin_max_bytes + 1
    assert (run.events.count("read"), run.events.count("close:0")) == (4, 1)


def test_bootstrap_revalidates_request_signature_digest_and_ceiling(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    frame = bytearray(worker_frame.encode_request_frame(worker_case.request, worker_case.content))
    frame[-1] ^= 1
    run = _bootstrap(monkeypatch, worker_case, bytes(frame))
    assert run.code == os.EX_DATAERR
    assert "import" not in run.events


def test_bootstrap_emits_exactly_one_typed_result_frame(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    run = _bootstrap(monkeypatch, worker_case, worker_frame.encode_request_frame(worker_case.request, worker_case.content), io_steps=((), (InterruptedError(), 5, InterruptedError(), len(worker_case.success_frame))))
    assert run.code == os.EX_OK
    assert run.output == worker_case.success_frame
    assert run.write_attempts == [worker_case.success_frame, worker_case.success_frame, worker_case.success_frame[5:], worker_case.success_frame[5:]]
    assert worker_frame.decode_result_frame(run.output) == worker_case.success


def test_bootstrap_never_receives_source_path_environment_or_source_fd(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    assert set(worker_protocol.WorkerRequest.model_fields).isdisjoint({"path", "root", "source", "source_fd"})
    run = _bootstrap(monkeypatch, worker_case, worker_frame.encode_request_frame(worker_case.request, worker_case.content))
    assert run.code == os.EX_OK
    assert run.events[:3] == ["limits", f"stop:9:{signal.SIGSTOP}", "read"]


def test_bootstrap_maps_pre_request_capability_failure_to_private_exit_78(
    monkeypatch: pytest.MonkeyPatch, worker_case: types.SimpleNamespace
) -> None:
    error = _module(BACKEND).WorkerIsolationUnsupportedError("missing limit")
    run = _bootstrap(monkeypatch, worker_case, b"", error)
    assert run.code == os.EX_CONFIG
    assert run.events == ["limits"]


def _launch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> types.SimpleNamespace:
    return _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.gap_frame))


def test_supervisor_launches_exact_isolated_python_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    launch = _launch(monkeypatch, tmp_path, worker_case)
    assert list(launch.calls[0][0][0]) == [sys.executable, *PROFILE.isolated_python_flags, "-m", BOOTSTRAP]
    assert launch.events.index("clock") < launch.events.index("spawn")
    assert f"deadline:{100.0 + PROFILE.wall_seconds}" in launch.events


def test_supervisor_uses_mode_0700_private_home_tmp_and_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    launch = _launch(monkeypatch, tmp_path, worker_case)
    kwargs, private = launch.calls[0][1], launch.private
    assert kwargs["cwd"] == str(private)
    assert kwargs["env"] == {key: str(private) for key in ("HOME", "TMPDIR", "TMP", "TEMP")}
    assert not private.exists()


def test_supervisor_closes_fds_starts_new_session_and_suppresses_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    kwargs = _launch(monkeypatch, tmp_path, worker_case).calls[0][1]
    assert (kwargs["stdin"], kwargs["stdout"], kwargs["stderr"]) == (subprocess.PIPE, subprocess.PIPE, subprocess.DEVNULL)
    assert (kwargs["bufsize"], kwargs["close_fds"], kwargs["start_new_session"]) == (0, True, True)


def test_supervisor_passes_no_repository_path_environment_or_source_fd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    args, kwargs = _launch(monkeypatch, tmp_path, worker_case).calls[0]
    assert str(_root()) not in repr((args[0][1:], kwargs))
    assert "PYTHONPATH" not in kwargs["env"]
    assert set(kwargs).isdisjoint({"pass_fds", "preexec_fn", "shell", "text", "encoding"})


def test_supervisor_rejects_noncanonical_request_or_content_before_spawn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    module, calls = _module(SUPERVISOR), []
    monkeypatch.setattr(module.subprocess, "Popen", lambda *_args, **_kwargs: calls.append(True))
    request = worker_case.request.model_copy(update={"request_digest": "0" * 64})
    load = module.run_isolated_worker(request, worker_case.content)
    assert load.required_gaps == ("source_budget_worker_protocol_invalid",)
    assert calls == []
    monkeypatch.setattr(module, "encode_request_frame", lambda *_args: (_ for _ in ()).throw(MemoryError()))
    exhausted = module.run_isolated_worker(worker_case.request, worker_case.content)
    assert exhausted.required_gaps == ("source_budget_worker_failed",)
    prior = _exchange(monkeypatch, tmp_path, _ExchangeOptions(initial_cause="resource_exhausted", cleanup_error_stage="memory"))
    assert (prior.result.first_cause, prior.result.cleanup_failed) == ("resource_exhausted", True)


def test_worker_runtime_uses_no_poll_or_communicate() -> None:
    spec = importlib.util.find_spec("ethos")
    assert spec is not None
    assert spec.origin is not None
    root = Path(spec.origin).parent / "adapters/repo/source_budget/measurement/worker"
    sources = tuple(path.read_text() for path in root.rglob("*.py"))
    calls = [node for source in sources for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    assert not any(isinstance(node.func, ast.Attribute) and node.func.attr in {"poll", "communicate"} for node in calls)
    assert all(token not in "\n".join(sources) for token in ("ExitStack", "pop_all", "_emergency_cleanup"))
    process_waits = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and node.func.attr == "wait"
        and any(keyword.arg == "timeout" for keyword in node.keywords)
    ]
    assert len(process_waits) == 1


def test_exchange_handles_partial_nonblocking_request_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    frame = worker_frame.encode_request_frame(worker_case.request, worker_case.content)
    actions = (InterruptedError(), "stdin", InterruptedError(), "stdin", "stdin", "stdout", "stdout")
    writes = (InterruptedError(), BlockingIOError(), 1, InterruptedError(), len(frame))
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(frame=frame, actions=actions, writes=writes, reads=(worker_case.success_frame, b""), polls=(None,) * 8 + (0,)))
    assert bytes(run.raw.sent) == frame
    assert run.raw.write_attempts == [frame, frame, frame, frame[1:], frame[1:]]
    assert run.result.stdout == worker_case.success_frame
    assert run.raw.blocking == [(31, False), (32, False)]
    assert run.selector.timeouts[:2] == [0, 0]
    assert 0 < t.cast("float", run.selector.timeouts[2]) >= t.cast("float", run.selector.timeouts[3])


def test_exchange_closes_stdin_after_exact_frame(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    frame = worker_frame.encode_request_frame(worker_case.request, worker_case.content)
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(frame=frame, writes=(len(frame),), reads=(worker_case.success_frame, b"")))
    assert run.events.index(f"write:31:{len(frame)}") < run.events.index("close:31")


def test_exchange_accepts_exact_65536_byte_result_and_eof(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = b"x" * PROTOCOL.result_max_bytes
    reads = (InterruptedError(), BlockingIOError(), payload, InterruptedError(), b"")
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin", "stdout", "stdout", "stdout"), reads=reads, polls=(None,) * 8 + (0,)))
    assert (run.result.stdout, run.result.stdout_eof, run.result.first_cause) == (payload, True, None)


def test_exchange_rejects_65537th_stdout_byte_as_output_exceeded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"x" * PROTOCOL.result_max_bytes, b"x"), polls=(None,) * 8, group_alive=True))
    assert run.result.first_cause == "output_exceeded"
    assert len(run.result.stdout) == PROTOCOL.result_max_bytes + 1
    assert run.signals[0][1] == signal.SIGTERM


def test_exchange_rejects_truncated_result_second_response_and_trailing_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    for stdout in (worker_case.success_frame[:-1], worker_case.success_frame * 2, worker_case.success_frame + b"x"):
        run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=stdout))
        assert run.load.required_gaps == ("source_budget_worker_protocol_invalid",)


def test_exchange_does_not_buffer_or_read_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace
) -> None:
    frame = worker_frame.encode_request_frame(worker_case.request, worker_case.content)
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(frame=frame, writes=(len(frame),), reads=(worker_case.success_frame, b"")))
    assert all(event.startswith("read:32:") for event in run.events if event.startswith("read:"))
    assert not hasattr(run.process, "stderr")


def test_exchange_samples_resources_every_10ms_under_backpressure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    error = _module(BACKEND).WorkerIsolationUnsupportedError("gone")
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin", "idle", "stdout", "stdout"), reads=(b"ok", b""), polls=(None, None, 0), samples=(error,)))
    assert {"read:32:65536", "sample"} <= set(run.events)
    assert run.result.stdout == b"ok"
    assert run.result.stdout_eof
    assert run.result.first_cause is None
    assert all(int(event.split(":")[1]) & _module(EXCHANGE).os.WNOWAIT for event in run.events if event.startswith("waitid:"))
    crashed = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin", "idle", "stdout", "stdout"), reads=(b"bad", b""), polls=(None, None, 3), samples=(error,)))
    assert crashed.result.returncode == 3
    assert crashed.result.first_cause is None


def test_wall_deadline_maps_to_timeout_and_terminates_group(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(wall_deadline=0.0, polls=(None,) * 20, group_alive=True))
    assert run.result.first_cause == "timeout"
    assert not any(event.startswith("register:") for event in run.events)
    actions = (InterruptedError(), "idle") + (InterruptedError(),) * 64
    interrupted = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=actions, wall_deadline=0.05, polls=(None,) * 80, group_alive=True))
    assert interrupted.result.first_cause == "timeout"
    assert interrupted.selector.timeouts[:2] == [0, 0]
    remaining = [value for value in interrupted.selector.timeouts if value]
    assert remaining == sorted(remaining, reverse=True)


def test_rss_trip_maps_to_resource_exhausted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    high = _module(BACKEND).WorkerResourceSample(PROFILE.rss_bytes + 1, 1)
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin", "idle"), samples=(high,), polls=(None,) * 8, group_alive=True))
    assert run.result.first_cause == "resource_exhausted"


def test_exchange_api_has_one_write_once_cause(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    module = _module(EXCHANGE)
    config_fields = {item.name for item in dataclasses.fields(module.WorkerExchangeConfig)}
    result_fields = {item.name for item in dataclasses.fields(module.WorkerExchangeResult)}
    forbidden = {"timed_out", "resource_exhausted", "output_exceeded", "pipe_failed", "capability_failed"}
    assert config_fields & {f"{name}_before_exchange" for name in forbidden} == set()
    assert result_fields & forbidden == set()
    assert "initial_cause" in config_fields
    assert {"first_cause", "cleanup_failed"} <= result_fields
    initial = _exchange(monkeypatch, tmp_path, _ExchangeOptions(initial_cause="output_exceeded", wall_deadline=0.0, cleanup_error_stage="signal"))
    assert (initial.result.first_cause, initial.result.cleanup_failed) == ("output_exceeded", True)
    direct = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"x" * (PROTOCOL.result_max_bytes + 1),), group_alive=True))
    assert direct.result.first_cause == "output_exceeded"
    result_type = module.WorkerExchangeResult
    constructors = deque((MemoryError("freeze"), result_type))
    def construct(**values: object) -> object:
        return _step(constructors, result_type)(**values)
    monkeypatch.setattr(module, "WorkerExchangeResult", construct)
    freeze, state_type = vars(module)["_freeze_exchange"], _module(LIFECYCLE).WorkerExchangeState
    frozen = freeze(state_type(stdout=bytearray(b"discard"), first_cause="resource_exhausted"))
    assert frozen.stdout == b""
    assert frozen.first_cause == "resource_exhausted"
    monkeypatch.setattr(module, "WorkerExchangeResult", lambda **_values: (_ for _ in ()).throw(MemoryError("freeze")))
    supervisor = _module(SUPERVISOR)
    monkeypatch.setattr(supervisor, "_run_admitted_worker", lambda _admitted: freeze(state_type()))
    failed = supervisor.run_isolated_worker(worker_case.request, worker_case.content)
    assert failed.required_gaps == ("source_budget_worker_failed",)


def test_darwin_writes_no_request_before_vms_baseline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.gap_frame), _SuperviseOptions(system="Darwin"))
    assert run.events.index("telemetry") < run.events.index(f"signal:{signal.SIGCONT}") < run.events.index("exchange")
    for ticks in ((100.0, 109.0), (100.0, 101.0, 109.0), (100.0, 101.0, 102.0, 109.0)):
        expired = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.gap_frame), _SuperviseOptions(system="Darwin", ticks=ticks))
        assert expired.load.required_gaps == ("source_budget_worker_timeout",)
        assert f"signal:{signal.SIGCONT}" not in expired.events
        assert "exchange-config:False:timeout" in expired.events


def test_darwin_vms_growth_trip_maps_to_resource_exhausted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    baseline = 10
    high = _module(BACKEND).WorkerResourceSample(1, baseline + PROFILE.darwin_vms_growth_bytes + 1)
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin", "idle"), samples=(high,), baseline=baseline, polls=(None,) * 8, group_alive=True))
    assert run.result.first_cause == "resource_exhausted"


def test_term_is_followed_by_kill_after_exact_100ms_grace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"x" * (PROTOCOL.result_max_bytes + 1),), polls=(None,) * 20, group_alive=True))
    term = next(item for item in run.signals if item[1] == signal.SIGTERM)
    kill = next(item for item in run.signals if item[1] == signal.SIGKILL)
    assert kill[0] - term[0] >= PROFILE.term_grace_ms / 1000
    kill_index = run.events.index(f"signal:{signal.SIGKILL}")
    assert "group-probe" in run.events[kill_index + 1 :]


def test_ignored_term_and_descendant_held_pipe_are_killed_by_process_group(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(actions=("stdin",) + ("idle",) * 20, polls=(0,) * 20, group_alive=True))
    assert run.result.first_cause == "timeout"
    assert [item[1] for item in run.signals][-2:] == [signal.SIGTERM, signal.SIGKILL]
    assert run.process.stdout.closed
    normal = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"ok", b""), polls=(None, 0), group_alive=True))
    assert [item[1] for item in normal.signals] == [signal.SIGTERM, signal.SIGKILL]
    kill_index = normal.events.index(f"signal:{signal.SIGKILL}")
    assert "group-probe" in normal.events[kill_index + 1 :]


def test_failure_cleanup_retains_private_directory_until_no_live_is_proved(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"x" * (PROTOCOL.result_max_bytes + 1),), polls=(None,) * 20, group_alive=True))
    assert (run.process.stdin.closed, run.process.stdout.closed, any(event.startswith("reap:") for event in run.events), run.events[-1]) == (True, True, True, "remove")
    counts = tuple(run.events.count(event) for event in (f"signal:{signal.SIGTERM}", f"signal:{signal.SIGKILL}", "remove"))
    reap_count = sum(event.startswith("reap:") for event in run.events)
    run.session.finish()
    assert tuple(run.events.count(event) for event in (f"signal:{signal.SIGTERM}", f"signal:{signal.SIGKILL}", "remove")) == counts
    assert sum(event.startswith("reap:") for event in run.events) == reap_count
    stage_events = {"signal": f"signal:{signal.SIGTERM}", "probe": "group-probe", "close": "selector-close", "wait": "cleanup-wait", "remove": "remove"}
    for stage, event in stage_events.items():
        injected = _exchange(
            monkeypatch,
            tmp_path,
            _ExchangeOptions(
                reads=(b"x" * (PROTOCOL.result_max_bytes + 1),),
                polls=(None,) * 20,
                group_alive=True,
                cleanup_error_stage=stage,
            ),
        )
        assert (injected.result.first_cause, injected.result.cleanup_failed) == ("output_exceeded", True)
        assert injected.process.stdin.closed
        assert injected.process.stdout.closed
        assert any(item.startswith("reap:") for item in injected.events)
        assert event in injected.events
        if stage in {"signal", "probe"}:
            assert injected.private.exists()
            assert "remove" not in injected.events
            injected.private.rmdir()
        else:
            assert not injected.private.exists()
            assert "remove" in injected.events
        if stage == "wait":
            kill_index = injected.events.index(f"signal:{signal.SIGKILL}")
            assert "group-probe" in injected.events[kill_index + 1 :]
    prepared = _supervise(monkeypatch, tmp_path, worker_case, _outcome(), _SuperviseOptions(sample_value=MemoryError("telemetry")))
    assert (prepared.load.required_gaps, prepared.private.exists(), prepared.events.count(f"signal:{signal.SIGTERM}"), prepared.events.count("reap:0.1")) == (("source_budget_worker_failed",), False, 1, 1)
    stalled = _exchange(monkeypatch, tmp_path, _ExchangeOptions(reads=(b"x" * (PROTOCOL.result_max_bytes + 1),), group_alive=True, cleanup_error_stage="wait-live"))
    assert (stalled.result.first_cause, stalled.result.cleanup_failed) == ("output_exceeded", True)
    assert (stalled.events.count("cleanup-wait"), stalled.events.count(f"signal:{signal.SIGKILL}")) == (2, 1)
    assert stalled.events.index(f"signal:{signal.SIGKILL}") < stalled.events.index("group-probe") < stalled.events.index("selector-close")


def test_missing_group_kill_or_reap_capability_is_isolation_unsupported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    capability = _supervise(monkeypatch, tmp_path, worker_case, _outcome(first_cause="capability_failed"))
    cleanup = _supervise(
        monkeypatch,
        tmp_path,
        worker_case,
        _outcome(cleanup_cause="capability_failed", cleanup_failed=True),
    )
    generic = _supervise(monkeypatch, tmp_path, worker_case, _outcome(cleanup_failed=True))
    timed = _supervise(
        monkeypatch,
        tmp_path,
        worker_case,
        _outcome(
            first_cause="timeout",
            cleanup_cause="capability_failed",
            cleanup_failed=True,
        ),
    )
    assert capability.load.required_gaps == ("source_budget_worker_isolation_unsupported",)
    assert cleanup.load.required_gaps == ("source_budget_worker_isolation_unsupported",)
    assert generic.load.required_gaps == ("source_budget_worker_failed",)
    assert timed.load.required_gaps == ("source_budget_worker_timeout",)


def test_spawn_unavailable_maps_to_worker_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(), _SuperviseOptions(spawn_error=OSError("missing")))
    assert run.load.required_gaps == ("source_budget_worker_unavailable",)
    assert not run.private.exists()


def test_bootstrap_exit_78_maps_to_isolation_unsupported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(returncode=os.EX_CONFIG))
    assert run.load.required_gaps == ("source_budget_worker_isolation_unsupported",)


def test_bootstrap_exit_65_maps_to_protocol_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(returncode=os.EX_DATAERR))
    assert run.load.required_gaps == ("source_budget_worker_protocol_invalid",)


def test_sigxcpu_maps_to_resource_exhausted_and_other_raw_failures_map_to_worker_failed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    limited = _supervise(monkeypatch, tmp_path, worker_case, _outcome(returncode=-signal.SIGXCPU))
    assert limited.load.required_gaps == ("source_budget_worker_resource_exhausted",)
    for outcome in (_outcome(returncode=-signal.SIGSEGV), _outcome(returncode=3), _outcome(stdout=b"")):
        run = _supervise(monkeypatch, tmp_path, worker_case, outcome)
        assert run.load.required_gaps == ("source_budget_worker_failed",)


def test_valid_frame_with_nonzero_exit_or_missing_eof_is_not_exposed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    for outcome in (_outcome(stdout=worker_case.success_frame, returncode=3), _outcome(stdout=worker_case.success_frame, stdout_eof=False)):
        run = _supervise(monkeypatch, tmp_path, worker_case, outcome)
        assert run.load.measurement is None
        assert run.load.required_gaps == ("source_budget_worker_failed",)


def test_child_gap_is_returned_only_when_worker_result_is_exact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.gap_frame))
    assert run.load.required_gaps == ("source_budget_native_runtime_unsupported",)
    assert run.load.measurement is None


def test_unknown_child_gap_or_parent_gap_from_child_is_protocol_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    for gap in ("source_budget_native_unknown", "source_budget_worker_timeout"):
        run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=_raw_result(worker_case.success, gap)))
        assert run.load.required_gaps == ("source_budget_worker_protocol_invalid",)


def test_parent_replays_success_from_trusted_request_contracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_case.success_frame))
    assert run.load.required_gaps == ()
    assert run.load.measurement == worker_protocol.replay_worker_result(worker_case.request, worker_case.success)


def test_parent_rejects_forged_result_bindings_values_or_measurement_digest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    result = worker_case.success.model_copy(update={"request_digest": "0" * 64})
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(stdout=worker_frame.encode_result_frame(result)))
    assert run.load.required_gaps == ("source_budget_worker_protocol_invalid",)


def _real_supported() -> bool:
    return sys.platform in {"linux", "darwin"} and platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 14)


def _stopped_bootstrap(owner: contextlib.ExitStack, private: Path) -> subprocess.Popen[bytes]:
    process = owner.enter_context(subprocess.Popen([sys.executable, *PROFILE.isolated_python_flags, "-m", BOOTSTRAP], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=private, env={key: str(private) for key in ("HOME", "TMPDIR", "TMP", "TEMP")}, close_fds=True, start_new_session=True, bufsize=0))
    owner.callback(process.kill)
    deadline, info = time.monotonic() + PROFILE.wall_seconds, None
    waitid = getattr(os, "waitid", None)
    assert callable(waitid)
    while info is None and time.monotonic() < deadline:
        info = waitid(os.P_PID, process.pid, os.WEXITED | os.WSTOPPED | os.WNOHANG | os.WNOWAIT)
    assert info is not None
    assert (info.si_code, info.si_status) == (os.CLD_STOPPED, signal.SIGSTOP)
    return process


def _real_exchange(tmp_path: Path, script: str):
    backend, module = _module(BACKEND).worker_backend(platform.system()), _module(EXCHANGE)
    hooks = module.WorkerExchangeHooks(send_group_signal=backend.signal_process_group, probe_process_group=backend.probe_process_group)
    session = module.prepare_worker_exchange(tmp_path, PROFILE, hooks)
    with contextlib.ExitStack() as owner:
        process = owner.enter_context(subprocess.Popen([sys.executable, "-I", "-B", "-X", "utf8", "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True, bufsize=0))
        owner.callback(process.kill)
        session.bind_process(process)
        config = module.WorkerExchangeConfig(request_frame=b"x", telemetry=_Telemetry((_module(BACKEND).WorkerResourceSample(1, 1),), []), profile=PROFILE, protocol=PROTOCOL, wall_deadline=time.monotonic() + PROFILE.wall_seconds)
        try:
            result = module.exchange_worker_process(config, hooks, session)
        finally:
            session.finish()
        lifecycle_returncode = process.returncode
        return result, lifecycle_returncode


@pytest.mark.skipif(not _real_supported(), reason="real worker requires supported CPython 3.14")
def test_real_worker_happy_path_uses_one_process_one_request_one_result(worker_case: types.SimpleNamespace) -> None:
    load = _module(SUPERVISOR).run_isolated_worker(worker_case.request, worker_case.content)
    assert load.required_gaps == ()
    assert load.measurement is not None


def test_unexpected_exchange_exception_has_one_cleanup_owner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, worker_case: types.SimpleNamespace) -> None:
    run = _supervise(monkeypatch, tmp_path, worker_case, _outcome(), _SuperviseOptions(exchange_error=_UnexpectedCleanupError()))
    assert run.load.required_gaps == ("source_budget_worker_failed",)
    assert [run.events.count(event) for event in ("spawn", f"signal:{signal.SIGTERM}", "cleanup-wait", "group-probe", "reap:0.1", "remove")] == [1] * 6
    assert f"signal:{signal.SIGKILL}" not in run.events
    reap = run.events.index("reap:0.1")
    assert not any(event.startswith("signal:") or event == "group-probe" for event in run.events[reap + 1 :])
    module = _module(SUPERVISOR)
    worker_launch = vars(module)["_WorkerLaunch"]
    monkeypatch.setattr(module, "_WorkerLaunch", lambda *_args: (_ for _ in ()).throw(MemoryError("carrier")))
    carrier = _supervise(monkeypatch, tmp_path, worker_case, _outcome())
    assert (carrier.load.required_gaps, carrier.private.exists(), carrier.process.returncode is not None, carrier.events.count(f"signal:{signal.SIGTERM}"), carrier.events.count("reap:0.1")) == (("source_budget_worker_failed",), False, True, 1, 1)
    monkeypatch.setattr(module, "_WorkerLaunch", worker_launch)
    exchange = _module(EXCHANGE)
    for allocation in ("WorkerExchangeState", "WorkerLifecycleOwner", "WorkerLifecycleBoundary", "WorkerLifecycleContext", "WorkerExchangeSession"):
        original = getattr(exchange, allocation)
        monkeypatch.setattr(exchange, allocation, lambda *_args, name=allocation, **_kwargs: (_ for _ in ()).throw(MemoryError(name)))
        rejected = _supervise(monkeypatch, tmp_path, worker_case, _outcome())
        assert rejected.load.required_gaps == ("source_budget_worker_failed",)
        assert "spawn" not in rejected.events
        assert not rejected.private.exists()
        monkeypatch.setattr(exchange, allocation, original)
    entry = _supervise(monkeypatch, tmp_path, worker_case, _outcome(), _SuperviseOptions(exchange_error=MemoryError("entry")))
    assert (entry.load.required_gaps, entry.private.exists(), entry.process.returncode is not None, entry.events.count(f"signal:{signal.SIGTERM}"), entry.events.count("reap:0.1")) == (("source_budget_worker_failed",), False, True, 1, 1)


@pytest.mark.skipif(not _real_supported(), reason="real worker requires supported CPython 3.14")
def test_real_worker_child_gap_has_no_partial_measurement(worker_case: types.SimpleNamespace) -> None:
    content = b"{"
    request = worker_protocol.WorkerRequest.create(content=content, contracts=worker_case.resolved.contracts, provider_descriptor=worker_case.resolved.provider_descriptor, execution_descriptor=worker_case.resolved.execution_descriptor)
    load = _module(SUPERVISOR).run_isolated_worker(request, content)
    assert load.measurement is None
    assert len(load.required_gaps) == 1
    assert load.required_gaps[0].startswith("source_budget_native_parse_failed:")


@pytest.mark.skipif(os.name != "posix", reason="real process-group proof requires POSIX")
def test_real_worker_output_flood_is_bounded(tmp_path: Path) -> None:
    script = f"import os;os.write(1,b'x'*{PROTOCOL.result_max_bytes + 1})"
    result, _returncode = _real_exchange(tmp_path, script)
    assert result.first_cause == "output_exceeded"
    assert len(result.stdout) == PROTOCOL.result_max_bytes + 1


@pytest.mark.skipif(os.name != "posix", reason="real process-group proof requires POSIX")
def test_real_worker_crash_and_ignored_term_leave_no_process_or_pipe_residue(tmp_path: Path) -> None:
    script = f"import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);os.fork();os.write(1,b'x'*{PROTOCOL.result_max_bytes + 1});time.sleep(30)"
    result, returncode = _real_exchange(tmp_path, script)
    assert result.first_cause == "output_exceeded"
    assert returncode is not None


@pytest.mark.skipif(not _real_supported(), reason="isolated module proof requires supported CPython 3.14")
def test_real_worker_module_is_importable_under_dash_i_without_pythonpath(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    started = time.monotonic()
    with pytest.raises(_UnexpectedCleanupError), contextlib.ExitStack() as owner:
        raise _UnexpectedCleanupError(failed := _stopped_bootstrap(owner, private))
    assert time.monotonic() - started < PROFILE.wall_seconds
    assert failed.returncode == -signal.SIGKILL
    assert all(stream is not None and stream.closed for stream in (failed.stdin, failed.stdout, failed.stderr))
    with contextlib.ExitStack() as owner:
        process = _stopped_bootstrap(owner, private)
        os.killpg(process.pid, signal.SIGCONT)
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        process.stdin.close()
        stdout, stderr = os.read(process.stdout.fileno(), PROTOCOL.result_max_bytes + 1), os.read(process.stderr.fileno(), 1)
        assert process.wait(timeout=PROFILE.wall_seconds) == os.EX_DATAERR
        assert stdout == b""
        assert stderr == b""
# fmt: on

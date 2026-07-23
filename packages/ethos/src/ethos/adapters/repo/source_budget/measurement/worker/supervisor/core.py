"""One-shot parent supervisor for isolated source-budget measurement."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import platform
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal
from typing import Protocol
from typing import cast

from pydantic import BaseModel
from pydantic import ValidationError

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerBackend
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerResourceSample
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerTelemetry
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import worker_backend
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import WorkerExchangeConfig
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import WorkerExchangeHooks
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import WorkerExchangeResult
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import WorkerExchangeSession
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import (
    exchange_worker_process,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.io import (
    prepare_worker_exchange,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    bind_worker_process,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    create_private_directory,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    discard_unstarted_directory,
)
from ethos.adapters.repo.source_budget.measurement.worker.supervisor.lifecycle.core import (
    resolve_worker_process_acquisition,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    WorkerProtocolDescriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerRequest
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    admit_child_worker_gap,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import replay_worker_result
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    worker_protocol_descriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import decode_result_frame
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import (
    encode_request_frame,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    WorkerResourceProfileDescriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)
from ethos_core.contracts.source_budget.measurements import NativeMeasurementLoad

if TYPE_CHECKING:
    from pathlib import Path

_BOOTSTRAP_MODULE = "ethos.adapters.repo.source_budget.measurement.worker.bootstrap.core"
_SUPERVISOR_FAILURES = (Exception,)
_GroupSignal = Callable[[int, int], None]
_EXIT_PROTOCOL_INVALID = 65
_EXIT_ISOLATION_UNSUPPORTED = 78
_REQUEST_ERROR = "worker request is not canonical"
_REQUEST_DIGEST_ERROR = "worker request content digest mismatch"
_VIRTUAL_TELEMETRY_ERROR = "worker virtual telemetry unavailable"
_PLATFORM_ERROR = "worker platform isolation unsupported"
_RESOURCE_SIGNALS = frozenset(
    int(item)
    for item in (getattr(signal, "SIGXCPU", None), getattr(signal, "SIGXFSZ", None))
    if item is not None
)
_PreparationCause = Literal["timeout", "resource_exhausted", "capability_failed"]


class _WaitObservation(Protocol):
    si_pid: int
    si_code: int
    si_status: int


@dataclass(frozen=True, slots=True)
class _AdmittedRequest:
    request: WorkerRequest
    request_frame: bytes
    protocol: WorkerProtocolDescriptor
    profile: WorkerResourceProfileDescriptor


@dataclass(frozen=True, slots=True)
class _WorkerLaunch:
    process: subprocess.Popen[bytes]
    wall_deadline: float


@dataclass(frozen=True, slots=True)
class _ReadinessResult:
    ready: bool
    initial_cause: Literal["timeout", "capability_failed"] | None


@dataclass(frozen=True, slots=True)
class _PreparedWorker:
    telemetry: WorkerTelemetry | None
    baseline: int | None
    sampled_at: float | None
    request_permitted: bool
    initial_cause: _PreparationCause | None


_InitialTelemetry = tuple[WorkerTelemetry, WorkerResourceSample, int | None, float]


def run_isolated_worker(
    request: WorkerRequest,
    content: bytes,
) -> NativeMeasurementLoad:
    """Run one typed request in one supervised process and replay its result."""
    try:
        admitted = _admit_parent_request(request, content)
    except MemoryError:
        return _failure("source_budget_worker_failed")
    except (
        AttributeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return _failure("source_budget_worker_protocol_invalid")
    try:
        return _run_admitted_worker(admitted)
    except MemoryError:
        return _failure("source_budget_worker_failed")
    except _SUPERVISOR_FAILURES:
        return _failure("source_budget_worker_failed")


def _admit_parent_request(request: WorkerRequest, content: bytes) -> _AdmittedRequest:
    canonical = _canonical_request(request)
    if canonical is None or type(content) is not bytes:
        raise ValueError(_REQUEST_ERROR)
    if canonical.content_sha256 != hashlib.sha256(content).hexdigest():
        raise ValueError(_REQUEST_DIGEST_ERROR)
    protocol = worker_protocol_descriptor()
    profile = worker_resource_profile_descriptor()
    return _AdmittedRequest(
        request=canonical,
        request_frame=encode_request_frame(canonical, content),
        protocol=protocol,
        profile=profile,
    )


def _run_admitted_worker(admitted: _AdmittedRequest) -> NativeMeasurementLoad:
    if not _bootstrap_available():
        return _failure("source_budget_worker_unavailable")
    platform_name = platform.system()
    runtime = _worker_runtime(platform_name)
    if runtime is None:
        return _failure("source_budget_worker_isolation_unsupported")
    backend, hooks = runtime
    directory: Path | None = None
    exchange: WorkerExchangeSession | None = None
    active_error: BaseException | None = None
    try:
        try:
            directory = create_private_directory()
        except (OSError, RuntimeError):
            return _failure("source_budget_worker_unavailable")
        exchange = prepare_worker_exchange(directory, admitted.profile, hooks)
        wall_deadline = time.monotonic() + admitted.profile.wall_seconds
        launch = _launch_worker(admitted.profile, wall_deadline, exchange)
        if launch is None:
            return _failure("source_budget_worker_unavailable")
        prepared = _prepare_worker(
            launch,
            backend,
            admitted.profile,
            platform_name,
            hooks.send_group_signal,
        )
        config = WorkerExchangeConfig(
            request_frame=admitted.request_frame,
            telemetry=prepared.telemetry,
            profile=admitted.profile,
            protocol=admitted.protocol,
            wall_deadline=launch.wall_deadline,
            darwin_vms_baseline=prepared.baseline,
            resource_sampled_at=prepared.sampled_at,
            request_permitted=prepared.request_permitted,
            initial_cause=prepared.initial_cause,
        )
        outcome = exchange_worker_process(config, hooks, exchange)
    except BaseException as error:
        active_error = error
        raise
    finally:
        _finish_worker_carrier(exchange, directory, active_error)
    return _interpret_worker_outcome(admitted.request, outcome)


def _finish_worker_carrier(
    exchange: WorkerExchangeSession | None,
    directory: Path | None,
    active_error: BaseException | None,
) -> None:
    if exchange is not None:
        exchange.finish(active_error)
    elif directory is not None:
        discard_unstarted_directory(directory)


def _worker_runtime(
    platform_name: str,
) -> tuple[WorkerBackend, WorkerExchangeHooks] | None:
    try:
        backend = worker_backend(platform_name)
        send_group_signal = backend.signal_process_group
        probe_process_group = backend.probe_process_group
    except (AttributeError, WorkerIsolationUnsupportedError):
        return None
    if not callable(send_group_signal) or not callable(probe_process_group):
        return None
    return backend, WorkerExchangeHooks(
        send_group_signal=send_group_signal,
        probe_process_group=probe_process_group,
    )


def _bootstrap_available() -> bool:
    try:
        return importlib.util.find_spec(_BOOTSTRAP_MODULE) is not None
    except (AttributeError, ImportError, ValueError):
        return False


def _launch_worker(
    profile: WorkerResourceProfileDescriptor,
    wall_deadline: float,
    exchange: WorkerExchangeSession,
) -> _WorkerLaunch | None:
    private = str(exchange.lifecycle.owner.private_directory)
    command = [sys.executable, *profile.isolated_python_flags, "-m", _BOOTSTRAP_MODULE]
    spawn = subprocess.Popen
    process: subprocess.Popen[bytes] | None = None
    try:
        exchange.lifecycle.owner.begin_process_acquisition()
        process = spawn(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=private,
            env={"HOME": private, "TMPDIR": private, "TMP": private, "TEMP": private},
            bufsize=0,
            close_fds=profile.close_file_descriptors,
            start_new_session=profile.start_new_session,
        )
        bind_worker_process(exchange.lifecycle, process)
        return _WorkerLaunch(process, wall_deadline)
    except (OSError, subprocess.SubprocessError, ValueError):
        resolve_worker_process_acquisition(
            exchange.lifecycle,
            process,
            no_process_is_safe=True,
        )
        return None
    except BaseException as error:
        resolve_worker_process_acquisition(
            exchange.lifecycle,
            process,
            no_process_is_safe=False,
            active_error=error,
        )
        raise


def _prepare_worker(
    launch: _WorkerLaunch,
    backend: WorkerBackend,
    profile: WorkerResourceProfileDescriptor,
    platform_name: str,
    send_group_signal: _GroupSignal,
) -> _PreparedWorker:
    readiness = _await_resource_ready(launch.process, launch.wall_deadline)
    if not readiness.ready:
        return _unprepared_worker(cause=readiness.initial_cause)
    initial = _prepare_initial_telemetry(launch, backend, profile, platform_name)
    if isinstance(initial, _PreparedWorker):
        return initial
    telemetry, sample, baseline, sampled_at = initial
    if sample.rss_bytes > profile.rss_bytes:
        return _unprepared_worker(
            cause="resource_exhausted",
            telemetry=telemetry,
            baseline=baseline,
            sampled_at=sampled_at,
        )
    return _continue_worker(launch, send_group_signal, initial)


def _prepare_initial_telemetry(
    launch: _WorkerLaunch,
    backend: WorkerBackend,
    profile: WorkerResourceProfileDescriptor,
    platform_name: str,
) -> _InitialTelemetry | _PreparedWorker:
    if timed_out := _timeout_worker(launch.wall_deadline):
        return timed_out
    telemetry: WorkerTelemetry | None = None
    try:
        telemetry = backend.open_parent_telemetry(launch.process.pid, profile)
        if timed_out := _timeout_worker(launch.wall_deadline, telemetry=telemetry):
            return timed_out
        sample = telemetry.sample()
        sampled_at = time.monotonic()
        baseline = (
            _admit_initial_sample(platform_name, sample)
            if sampled_at < launch.wall_deadline
            else None
        )
    except MemoryError:
        if timed_out := _timeout_worker(launch.wall_deadline, telemetry=telemetry):
            return timed_out
        raise
    except WorkerIsolationUnsupportedError:
        return _timeout_worker(launch.wall_deadline, telemetry=telemetry) or _unprepared_worker(
            cause="capability_failed"
        )
    return _timeout_worker(
        launch.wall_deadline,
        telemetry=telemetry,
        baseline=baseline,
        sampled_at=sampled_at,
    ) or (telemetry, sample, baseline, sampled_at)


def _continue_worker(
    launch: _WorkerLaunch,
    send_group_signal: _GroupSignal,
    initial: _InitialTelemetry,
) -> _PreparedWorker:
    telemetry, _sample, baseline, sampled_at = initial
    if timed_out := _timeout_from_initial(launch.wall_deadline, initial):
        return timed_out
    try:
        send_group_signal(launch.process.pid, signal.SIGCONT)
    except MemoryError:
        if timed_out := _timeout_from_initial(launch.wall_deadline, initial):
            return timed_out
        raise
    except (AttributeError, OSError, ValueError):
        return _timeout_from_initial(launch.wall_deadline, initial) or _unprepared_worker(
            cause="capability_failed",
            telemetry=telemetry,
            baseline=baseline,
            sampled_at=sampled_at,
        )
    if timed_out := _timeout_from_initial(launch.wall_deadline, initial):
        return timed_out
    return _PreparedWorker(
        telemetry=telemetry,
        baseline=baseline,
        sampled_at=sampled_at,
        request_permitted=True,
        initial_cause=None,
    )


def _timeout_from_initial(
    wall_deadline: float,
    initial: _InitialTelemetry,
) -> _PreparedWorker | None:
    telemetry, _sample, baseline, sampled_at = initial
    return _timeout_worker(
        wall_deadline,
        telemetry=telemetry,
        baseline=baseline,
        sampled_at=sampled_at,
    )


def _timeout_worker(
    wall_deadline: float,
    *,
    telemetry: WorkerTelemetry | None = None,
    baseline: int | None = None,
    sampled_at: float | None = None,
) -> _PreparedWorker | None:
    if time.monotonic() < wall_deadline:
        return None
    return _unprepared_worker(
        cause="timeout",
        telemetry=telemetry,
        baseline=baseline,
        sampled_at=sampled_at,
    )


def _unprepared_worker(
    *,
    cause: _PreparationCause | None,
    telemetry: WorkerTelemetry | None = None,
    baseline: int | None = None,
    sampled_at: float | None = None,
) -> _PreparedWorker:
    return _PreparedWorker(
        telemetry=telemetry,
        baseline=baseline,
        sampled_at=sampled_at,
        request_permitted=False,
        initial_cause=cause,
    )


def _canonical_request(request: WorkerRequest) -> WorkerRequest | None:
    if type(request) is not WorkerRequest:
        return None
    fields = set(WorkerRequest.model_fields)
    if set(vars(request)) != fields or request.model_fields_set != fields:
        return None
    return WorkerRequest.model_validate(
        BaseModel.model_dump(request, mode="python", by_alias=True, warnings="error")
    )


def _await_resource_ready(
    process: subprocess.Popen[bytes],
    wall_deadline: float,
) -> _ReadinessResult:
    required = ("P_PID", "WEXITED", "WSTOPPED", "WNOHANG", "WNOWAIT", "CLD_STOPPED")
    if not hasattr(os, "waitid") or any(not hasattr(os, name) for name in required):
        return _ReadinessResult(ready=False, initial_cause="capability_failed")
    options = os.WEXITED | os.WSTOPPED | os.WNOHANG | os.WNOWAIT
    while time.monotonic() < wall_deadline:
        try:
            observed = os.waitid(os.P_PID, process.pid, options)
        except InterruptedError:
            continue
        except (ChildProcessError, OSError, ValueError):
            if time.monotonic() >= wall_deadline:
                return _ReadinessResult(ready=False, initial_cause="timeout")
            return _ReadinessResult(ready=False, initial_cause="capability_failed")
        if time.monotonic() >= wall_deadline:
            return _ReadinessResult(ready=False, initial_cause="timeout")
        if observed is None or observed.si_pid == 0:
            continue
        return _classify_readiness_observation(cast("_WaitObservation", observed))
    return _ReadinessResult(ready=False, initial_cause="timeout")


def _classify_readiness_observation(observed: _WaitObservation) -> _ReadinessResult:
    if observed.si_code == os.CLD_STOPPED:
        exact = observed.si_status == signal.SIGSTOP
        return _ReadinessResult(
            ready=exact,
            initial_cause=None if exact else "capability_failed",
        )
    terminal_codes = {
        getattr(os, "CLD_EXITED", -1),
        getattr(os, "CLD_KILLED", -1),
        getattr(os, "CLD_DUMPED", -1),
    }
    if observed.si_code in terminal_codes:
        return _ReadinessResult(ready=False, initial_cause=None)
    return _ReadinessResult(ready=False, initial_cause="capability_failed")


def _admit_initial_sample(
    platform_name: str,
    sample: WorkerResourceSample,
) -> int | None:
    if sample.virtual_bytes is None:
        raise WorkerIsolationUnsupportedError(_VIRTUAL_TELEMETRY_ERROR)
    if platform_name == "Darwin":
        return sample.virtual_bytes
    if platform_name == "Linux":
        return None
    raise WorkerIsolationUnsupportedError(_PLATFORM_ERROR)


def _interpret_worker_outcome(
    request: WorkerRequest,
    outcome: WorkerExchangeResult,
) -> NativeMeasurementLoad:
    if gap := _parent_gap(outcome):
        return _failure(gap)
    try:
        result = decode_result_frame(outcome.stdout)
        if result.gap is not None:
            return NativeMeasurementLoad(None, (admit_child_worker_gap(result.gap),))
        return NativeMeasurementLoad(replay_worker_result(request, result), ())
    except MemoryError:
        return _failure("source_budget_worker_failed")
    except (
        AttributeError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return _failure("source_budget_worker_protocol_invalid")


def _parent_gap(outcome: WorkerExchangeResult) -> str | None:
    cause = outcome.first_cause
    direct = {
        "timeout": "source_budget_worker_timeout",
        "resource_exhausted": "source_budget_worker_resource_exhausted",
        "output_exceeded": "source_budget_worker_output_exceeded",
        "capability_failed": "source_budget_worker_isolation_unsupported",
    }
    if cause in direct:
        return direct[cause]
    if cause == "pipe_failed":
        return "source_budget_worker_failed"
    if outcome.cleanup_cause == "capability_failed":
        return "source_budget_worker_isolation_unsupported"
    returncode = outcome.returncode
    raw_failed = outcome.cleanup_failed or not outcome.stdout_eof or not outcome.stdout
    if returncode == _EXIT_ISOLATION_UNSUPPORTED:
        gap = "source_budget_worker_isolation_unsupported"
    elif returncode == _EXIT_PROTOCOL_INVALID:
        gap = "source_budget_worker_protocol_invalid"
    elif returncode is not None and -returncode in _RESOURCE_SIGNALS:
        gap = "source_budget_worker_resource_exhausted"
    elif returncode not in {None, 0} or raw_failed:
        gap = "source_budget_worker_failed"
    else:
        gap = None
    return gap


def _failure(gap: str) -> NativeMeasurementLoad:
    return NativeMeasurementLoad(None, (gap,))

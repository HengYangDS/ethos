"""Resource-first bootstrap for one isolated source-budget request."""

from __future__ import annotations

import importlib
import os
import signal
from contextlib import suppress

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import worker_backend
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import WorkerResult
from ethos_core.contracts.source_budget.measurement.worker.protocol.core import (
    worker_protocol_descriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import (
    decode_request_frame,
)
from ethos_core.contracts.source_budget.measurement.worker.protocol.frame import encode_result_frame
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)

_EXIT_PROTOCOL_INVALID = 65
_EXIT_UNEXPECTED_FAILURE = 70
_EXIT_ISOLATION_UNSUPPORTED = 78
_ISOLATED_ENGINE_MODULE = "ethos.adapters.repo.source_budget.measurement.native.isolated.core"
_READ_CHUNK_BYTES = 64 * 1024
_RESULT_TYPE_ERROR = "isolated engine returned a noncanonical result"
_READINESS_ERROR = "worker readiness stop unavailable"
_STDIN_LIMIT_ERROR = "worker request stdin exceeds maximum"
_RESULT_LIMIT_ERROR = "worker result frame exceeds maximum"
_WRITE_PROGRESS_ERROR = "worker result write made no progress"


def main() -> int:
    """Apply limits, decode one request, run the isolated engine, and emit one result."""
    try:
        profile = worker_resource_profile_descriptor()
        backend = worker_backend()
        backend.apply_child_limits(profile)
        _stop_until_parent_is_ready()
    except WorkerIsolationUnsupportedError:
        return _EXIT_ISOLATION_UNSUPPORTED
    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _EXIT_UNEXPECTED_FAILURE
    return _run_request()


def _run_request() -> int:
    try:
        protocol = worker_protocol_descriptor()
        encoded_request = _read_bounded_stdin(protocol.stdin_max_bytes)
        request, content = decode_request_frame(encoded_request)
    except MemoryError:
        return _EXIT_UNEXPECTED_FAILURE
    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _EXIT_PROTOCOL_INVALID
    finally:
        stdin_closed = _close_descriptor(0)

    if not stdin_closed:
        return _EXIT_UNEXPECTED_FAILURE

    try:
        module = importlib.import_module(_ISOLATED_ENGINE_MODULE)
        measure_isolated = module.measure_isolated
        result = _require_worker_result(measure_isolated(request, content))
        encoded_result = encode_result_frame(result)
        _write_bounded_stdout(encoded_result, protocol.result_max_bytes)
        if not _close_descriptor(1):
            return _EXIT_UNEXPECTED_FAILURE
    except (MemoryError, AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        return _EXIT_UNEXPECTED_FAILURE
    return 0


def _require_worker_result(result: object) -> WorkerResult:
    if type(result) is not WorkerResult:
        raise TypeError(_RESULT_TYPE_ERROR)
    return result


def _stop_until_parent_is_ready() -> None:
    try:
        os.kill(os.getpid(), signal.SIGSTOP)
    except (AttributeError, OSError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_READINESS_ERROR) from exc


def _read_bounded_stdin(maximum: int) -> bytes:
    chunks: list[bytes] = []
    retained = 0
    while True:
        remaining = maximum + 1 - retained
        if remaining <= 0:
            raise ValueError(_STDIN_LIMIT_ERROR)
        try:
            chunk = os.read(0, min(_READ_CHUNK_BYTES, remaining))
        except InterruptedError:
            continue
        if not chunk:
            break
        chunks.append(chunk)
        retained += len(chunk)
    return b"".join(chunks)


def _write_bounded_stdout(encoded: bytes, maximum: int) -> None:
    if type(encoded) is not bytes or len(encoded) > maximum:
        raise ValueError(_RESULT_LIMIT_ERROR)
    view = memoryview(encoded)
    offset = 0
    while offset < len(view):
        try:
            written = os.write(1, view[offset:])
        except InterruptedError:
            continue
        if written <= 0:
            raise OSError(_WRITE_PROGRESS_ERROR)
        offset += written


def _close_descriptor(descriptor: int) -> bool:
    try:
        os.close(descriptor)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    with suppress(BrokenPipeError):
        raise SystemExit(main())

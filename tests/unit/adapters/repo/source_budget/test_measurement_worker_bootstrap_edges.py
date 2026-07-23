"""Exceptional bootstrap contracts for isolated source-budget workers."""

from __future__ import annotations

import runpy
import types
import typing as t

import pytest

import ethos.adapters.repo.source_budget.measurement.worker.backend.core as backend_core
import ethos.adapters.repo.source_budget.measurement.worker.bootstrap.core as bootstrap
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)


def _prepare_request_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap,
        "worker_protocol_descriptor",
        lambda: types.SimpleNamespace(stdin_max_bytes=8, result_max_bytes=8),
    )
    monkeypatch.setattr(bootstrap, "_read_bounded_stdin", lambda _maximum: b"request")
    monkeypatch.setattr(bootstrap, "decode_request_frame", lambda _encoded: (object(), b"content"))
    monkeypatch.setattr(bootstrap, "_close_descriptor", lambda _descriptor: True)


def test_bootstrap_main_maps_unexpected_pre_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap,
        "worker_resource_profile_descriptor",
        lambda: (_ for _ in ()).throw(RuntimeError),
    )

    assert bootstrap.main() == vars(bootstrap)["_EXIT_UNEXPECTED_FAILURE"]


def test_bootstrap_module_entry_exits_with_protocol_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Backend:
        def apply_child_limits(self, _profile: object) -> None:
            events.append("limits")

    def select_backend() -> Backend:
        events.append("backend")
        return Backend()

    def read(descriptor: int, maximum: int) -> bytes:
        assert descriptor == 0
        assert maximum > 0
        events.append("read")
        return b""

    monkeypatch.setattr(backend_core, "worker_backend", select_backend)
    monkeypatch.setattr(
        bootstrap.os,
        "kill",
        lambda _pid, _signal: events.append("stop"),
    )
    monkeypatch.setattr(bootstrap.os, "read", read)
    monkeypatch.setattr(
        bootstrap.os,
        "close",
        lambda descriptor: events.append(f"close:{descriptor}"),
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path(bootstrap.__file__, run_name="__main__")

    assert raised.value.code == vars(bootstrap)["_EXIT_PROTOCOL_INVALID"]
    assert events == ["backend", "limits", "stop", "read", "close:0"]


def test_bootstrap_request_maps_memory_failure_and_closes_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(
        bootstrap,
        "worker_protocol_descriptor",
        lambda: types.SimpleNamespace(stdin_max_bytes=8),
    )
    monkeypatch.setattr(
        bootstrap,
        "_read_bounded_stdin",
        lambda _maximum: (_ for _ in ()).throw(MemoryError),
    )

    def close(descriptor: int) -> bool:
        closed.append(descriptor)
        return True

    monkeypatch.setattr(bootstrap, "_close_descriptor", close)

    assert vars(bootstrap)["_run_request"]() == vars(bootstrap)["_EXIT_UNEXPECTED_FAILURE"]
    assert closed == [0]


def test_bootstrap_request_fails_before_engine_import_when_stdin_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_request_phase(monkeypatch)
    events: list[str] = []

    def importer(_name: str) -> object:
        events.append("import")
        return types.SimpleNamespace(measure_isolated=lambda *_args: object())

    def close(descriptor: int) -> bool:
        events.append(f"close:{descriptor}")
        return descriptor != 0

    monkeypatch.setattr(bootstrap.importlib, "import_module", importer)
    monkeypatch.setattr(bootstrap, "_require_worker_result", lambda _result: object())
    monkeypatch.setattr(bootstrap, "encode_result_frame", lambda _result: b"result")
    monkeypatch.setattr(
        bootstrap,
        "_write_bounded_stdout",
        lambda *_args: events.append("write"),
    )
    monkeypatch.setattr(bootstrap, "_close_descriptor", close)

    code = vars(bootstrap)["_run_request"]()

    assert events == ["close:0"]
    assert code == vars(bootstrap)["_EXIT_UNEXPECTED_FAILURE"]


def test_bootstrap_request_requires_stdout_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_request_phase(monkeypatch)
    closed: list[int] = []
    monkeypatch.setattr(
        bootstrap.importlib,
        "import_module",
        lambda _name: types.SimpleNamespace(measure_isolated=lambda *_args: object()),
    )
    monkeypatch.setattr(bootstrap, "_require_worker_result", lambda _result: object())
    monkeypatch.setattr(bootstrap, "encode_result_frame", lambda _result: b"result")
    monkeypatch.setattr(bootstrap, "_write_bounded_stdout", lambda *_args: None)

    def close(descriptor: int) -> bool:
        closed.append(descriptor)
        return descriptor != 1

    monkeypatch.setattr(bootstrap, "_close_descriptor", close)

    assert vars(bootstrap)["_run_request"]() == vars(bootstrap)["_EXIT_UNEXPECTED_FAILURE"]
    assert closed == [0, 1]


@pytest.mark.parametrize("error", [MemoryError(), AttributeError()])
def test_bootstrap_request_maps_isolated_engine_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    _prepare_request_phase(monkeypatch)
    monkeypatch.setattr(
        bootstrap.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(error),
    )

    assert vars(bootstrap)["_run_request"]() == vars(bootstrap)["_EXIT_UNEXPECTED_FAILURE"]


def test_bootstrap_requires_canonical_worker_result() -> None:
    with pytest.raises(TypeError):
        vars(bootstrap)["_require_worker_result"](object())


def test_bootstrap_readiness_stop_failure_is_isolation_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap.os, "getpid", lambda: 4312)
    monkeypatch.setattr(
        bootstrap.os,
        "kill",
        lambda *_args: (_ for _ in ()).throw(OSError),
    )

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(bootstrap)["_stop_until_parent_is_ready"]()


def test_bootstrap_stdin_limit_uses_bounded_os_read_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []

    def read(descriptor: int, maximum: int) -> bytes:
        calls.append((descriptor, maximum))
        return b"x" * maximum

    monkeypatch.setattr(bootstrap.os, "read", read)

    with pytest.raises(ValueError, match=vars(bootstrap)["_STDIN_LIMIT_ERROR"]):
        vars(bootstrap)["_read_bounded_stdin"](3)
    assert calls == [(0, 4)]


@pytest.mark.parametrize("encoded", [bytearray(b"x"), b"xx"])
def test_bootstrap_stdout_rejects_noncanonical_or_oversized_payload(
    encoded: object,
) -> None:
    with pytest.raises(ValueError, match=vars(bootstrap)["_RESULT_LIMIT_ERROR"]):
        vars(bootstrap)["_write_bounded_stdout"](t.cast("bytes", encoded), 1)


def test_bootstrap_stdout_requires_write_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap.os, "write", lambda _descriptor, _payload: 0)

    with pytest.raises(OSError, match=vars(bootstrap)["_WRITE_PROGRESS_ERROR"]):
        vars(bootstrap)["_write_bounded_stdout"](b"result", 6)


def test_bootstrap_descriptor_close_reports_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap.os,
        "close",
        lambda _descriptor: (_ for _ in ()).throw(OSError),
    )

    assert vars(bootstrap)["_close_descriptor"](1) is False

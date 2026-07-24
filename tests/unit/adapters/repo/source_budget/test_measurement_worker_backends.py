"""Deterministic public process-group contracts for Linux and Darwin workers."""

from __future__ import annotations

import ctypes
import errno
import resource
import typing as t
from pathlib import Path

import pytest

import ethos.adapters.repo.source_budget.measurement.worker.backend.darwin.core as darwin
import ethos.adapters.repo.source_budget.measurement.worker.backend.linux.core as linux
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerResourceSample
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    WorkerResourceProfileDescriptor,
)
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    worker_resource_profile_descriptor,
)

PROFILE = worker_resource_profile_descriptor()
_CAPABILITY_UNAVAILABLE = "unavailable"


class _ScandirEntry:
    def __init__(self, path: str) -> None:
        self.path = path


class _Scandir:
    def __init__(
        self,
        available: int,
        *,
        error: BaseException | None = None,
        error_after: int = 0,
    ) -> None:
        self.available = available
        self.error = error
        self.error_after = error_after
        self.consumed = 0
        self.closed = False

    def __enter__(self) -> _Scandir:
        return self

    def __exit__(
        self,
        _error_type: object,
        _error: object,
        _traceback: object,
    ) -> None:
        self.close()

    def __iter__(self) -> _Scandir:
        return self

    def __next__(self) -> _ScandirEntry:
        if self.error is not None and self.consumed >= self.error_after:
            raise self.error
        if self.consumed >= self.available:
            raise StopIteration
        self.consumed += 1
        return _ScandirEntry(f"/proc/{self.consumed}")

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("member_state", "direct_child_terminal", "expected"),
    [
        ("R", False, WorkerProcessGroupState.LIVE),
        ("Z", True, WorkerProcessGroupState.TERMINAL_ONLY),
    ],
)
def test_linux_group_probe_classifies_present_members(
    monkeypatch: pytest.MonkeyPatch,
    member_state: str,
    *,
    direct_child_terminal: bool,
    expected: WorkerProcessGroupState,
) -> None:
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: (Path("4312"),))
    monkeypatch.setattr(linux, "_read_process_stat", lambda _path: "stat")
    monkeypatch.setattr(
        linux,
        "_parse_process_stat",
        lambda _payload, _pid: (member_state, 4312),
    )

    observed = linux.LinuxWorkerBackend().probe_process_group(
        4312,
        direct_child_terminal=direct_child_terminal,
    )

    assert observed is expected


def test_linux_group_probe_classifies_an_absent_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: ())
    monkeypatch.setattr(
        linux.os,
        "killpg",
        lambda _group, _signal: (_ for _ in ()).throw(ProcessLookupError),
    )

    observed = linux.LinuxWorkerBackend().probe_process_group(
        4312,
        direct_child_terminal=False,
    )

    assert observed is WorkerProcessGroupState.ABSENT


def test_linux_terminal_group_without_terminal_child_proof_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: (Path("4312"),))
    monkeypatch.setattr(linux, "_read_process_stat", lambda _path: "stat")
    monkeypatch.setattr(linux, "_parse_process_stat", lambda _payload, _pid: ("Z", 4312))

    with pytest.raises(WorkerIsolationUnsupportedError):
        linux.LinuxWorkerBackend().probe_process_group(
            4312,
            direct_child_terminal=False,
        )


@pytest.mark.parametrize(
    "case",
    [
        ("live", (4312,), True, False, WorkerProcessGroupState.LIVE),
        ("absent", (), False, False, WorkerProcessGroupState.ABSENT),
        ("denied", (4312,), False, True, WorkerProcessGroupState.TERMINAL_ONLY),
    ],
)
def test_darwin_group_probe_classifies_all_states(
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, tuple[int, ...], bool, bool, WorkerProcessGroupState],
) -> None:
    kernel_result, pids, pid_live, direct_terminal, expected = case
    monkeypatch.setattr(darwin, "_darwin_group_pids", lambda _group: pids)
    monkeypatch.setattr(darwin, "_darwin_pid_is_live", lambda _pid: pid_live)
    monkeypatch.setattr(
        darwin.os,
        "getpgid",
        lambda _pid: (_ for _ in ()).throw(ProcessLookupError),
    )

    def probe(_group: int, _signal: int) -> None:
        if kernel_result == "absent":
            raise ProcessLookupError
        if kernel_result == "denied":
            raise PermissionError

    monkeypatch.setattr(darwin.os, "killpg", probe)

    observed = darwin.DarwinWorkerBackend().probe_process_group(
        4312,
        direct_child_terminal=direct_terminal,
    )

    assert observed is expected


@pytest.mark.parametrize("mode", ["retry", "exhaust"])
def test_linux_proc_enumeration_has_an_exact_interrupted_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls = 0
    scans: list[_Scandir] = []

    def scandir(path: str) -> _Scandir:
        nonlocal calls
        assert path == "/proc"
        calls += 1
        scan = (
            _Scandir(0) if mode == "retry" and calls == 3 else _Scandir(0, error=InterruptedError())
        )
        scans.append(scan)
        return scan

    monkeypatch.setattr(linux.os, "scandir", scandir)
    monkeypatch.setattr(
        linux.os,
        "killpg",
        lambda _group, _signal: (_ for _ in ()).throw(ProcessLookupError),
    )
    backend = linux.LinuxWorkerBackend()

    if mode == "exhaust":
        with pytest.raises(WorkerIsolationUnsupportedError):
            backend.probe_process_group(4312, direct_child_terminal=False)
    else:
        assert (
            backend.probe_process_group(4312, direct_child_terminal=False)
            is WorkerProcessGroupState.ABSENT
        )
    assert calls == 3
    assert all(scan.closed for scan in scans)


@pytest.mark.parametrize(
    ("available", "must_fail", "expected_consumed"),
    [(65_536, False, 65_536), (70_000, True, 65_537)],
)
def test_linux_proc_enumeration_has_a_hard_entry_capacity(
    monkeypatch: pytest.MonkeyPatch,
    available: int,
    *,
    must_fail: bool,
    expected_consumed: int,
) -> None:
    scan = _Scandir(available)

    def scandir(path: str) -> _Scandir:
        assert path == "/proc"
        return scan

    monkeypatch.setattr(
        linux.os,
        "scandir",
        scandir,
    )

    if must_fail:
        with pytest.raises(WorkerIsolationUnsupportedError):
            vars(linux)["_linux_process_entries"]()
    else:
        entries = vars(linux)["_linux_process_entries"]()
        assert len(entries) == 65_536
        assert entries[0] == Path("/proc/1")
        assert entries[-1] == Path("/proc/65536")
    assert scan.consumed == expected_consumed
    assert scan.closed is True


def test_linux_proc_enumeration_maps_error_during_bounded_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan = _Scandir(2, error=OSError(), error_after=1)
    monkeypatch.setattr(linux.os, "scandir", lambda _path: scan)

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_linux_process_entries"]()
    assert scan.consumed == 1
    assert scan.closed is True


@pytest.mark.parametrize("mode", ["retry", "exhaust"])
def test_linux_stat_read_has_an_exact_interrupted_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls = 0
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: (Path("4312"),))

    def read_text(_path: Path, *, encoding: str) -> str:
        nonlocal calls
        assert encoding == "ascii"
        calls += 1
        if mode == "retry" and calls == 3:
            return "4312 (worker) R 1 4312"
        raise InterruptedError

    monkeypatch.setattr(Path, "read_text", read_text)
    backend = linux.LinuxWorkerBackend()

    if mode == "exhaust":
        with pytest.raises(WorkerIsolationUnsupportedError):
            backend.probe_process_group(4312, direct_child_terminal=False)
    else:
        assert (
            backend.probe_process_group(4312, direct_child_terminal=False)
            is WorkerProcessGroupState.LIVE
        )
    assert calls == 3


@pytest.mark.parametrize("mode", ["retry", "exhaust"])
def test_linux_empty_group_probe_has_an_exact_interrupted_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls = 0
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: ())

    def killpg(_group: int, _signal: int) -> None:
        nonlocal calls
        calls += 1
        if mode == "retry" and calls == 3:
            raise ProcessLookupError
        raise InterruptedError

    monkeypatch.setattr(linux.os, "killpg", killpg)
    backend = linux.LinuxWorkerBackend()

    if mode == "exhaust":
        with pytest.raises(WorkerIsolationUnsupportedError):
            backend.probe_process_group(4312, direct_child_terminal=False)
    else:
        assert (
            backend.probe_process_group(4312, direct_child_terminal=False)
            is WorkerProcessGroupState.ABSENT
        )
    assert calls == 3


@pytest.mark.parametrize("mode", ["retry", "exhaust"])
def test_darwin_direct_child_lookup_has_an_exact_interrupted_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls = 0
    monkeypatch.setattr(darwin, "_darwin_group_pids", lambda _group: ())

    def getpgid(_pid: int) -> int:
        nonlocal calls
        calls += 1
        if mode == "retry" and calls == 3:
            raise ProcessLookupError
        raise InterruptedError

    monkeypatch.setattr(darwin.os, "getpgid", getpgid)
    monkeypatch.setattr(
        darwin.os,
        "killpg",
        lambda _group, _signal: (_ for _ in ()).throw(ProcessLookupError),
    )
    backend = darwin.DarwinWorkerBackend()

    if mode == "exhaust":
        with pytest.raises(WorkerIsolationUnsupportedError):
            backend.probe_process_group(4312, direct_child_terminal=False)
    else:
        assert (
            backend.probe_process_group(4312, direct_child_terminal=False)
            is WorkerProcessGroupState.ABSENT
        )
    assert calls == 3


@pytest.mark.parametrize("mode", ["retry", "exhaust"])
def test_darwin_kernel_group_probe_has_an_exact_interrupted_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    calls = 0
    monkeypatch.setattr(darwin, "_darwin_group_pids", lambda _group: ())
    monkeypatch.setattr(
        darwin.os,
        "getpgid",
        lambda _pid: (_ for _ in ()).throw(ProcessLookupError),
    )

    def killpg(_group: int, _signal: int) -> None:
        nonlocal calls
        calls += 1
        if mode == "retry" and calls == 3:
            raise ProcessLookupError
        raise InterruptedError

    monkeypatch.setattr(darwin.os, "killpg", killpg)
    backend = darwin.DarwinWorkerBackend()

    if mode == "exhaust":
        with pytest.raises(WorkerIsolationUnsupportedError):
            backend.probe_process_group(4312, direct_child_terminal=False)
    else:
        assert (
            backend.probe_process_group(4312, direct_child_terminal=False)
            is WorkerProcessGroupState.ABSENT
        )
    assert calls == 3


@pytest.mark.parametrize("platform_name", ["linux", "darwin"])
def test_non_interrupted_group_lookup_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
) -> None:
    if platform_name == "linux":
        monkeypatch.setattr(
            linux.os,
            "scandir",
            lambda _path: (_ for _ in ()).throw(OSError),
        )
        backend = linux.LinuxWorkerBackend()
    else:
        monkeypatch.setattr(darwin, "_darwin_group_pids", lambda _group: ())
        monkeypatch.setattr(
            darwin.os,
            "getpgid",
            lambda _pid: (_ for _ in ()).throw(OSError),
        )
        backend = darwin.DarwinWorkerBackend()

    with pytest.raises(WorkerIsolationUnsupportedError):
        backend.probe_process_group(4312, direct_child_terminal=False)


@pytest.mark.parametrize(
    ("rss_bytes", "virtual_bytes"),
    [(True, None), (0, -1)],
)
def test_resource_samples_reject_noncanonical_values(
    rss_bytes: object,
    virtual_bytes: object,
) -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        WorkerResourceSample(
            rss_bytes=t.cast("int", rss_bytes),
            virtual_bytes=t.cast("int | None", virtual_bytes),
        )


@pytest.mark.parametrize(
    "loader_name",
    ["_system_proc_pidinfo", "_system_proc_listpgrppids"],
)
def test_darwin_libproc_loader_binds_the_exact_symbol(
    monkeypatch: pytest.MonkeyPatch,
    loader_name: str,
) -> None:
    symbol_name = {
        "_system_proc_pidinfo": "proc_pidinfo",
        "_system_proc_listpgrppids": "proc_listpgrppids",
    }[loader_name]
    expected_arity = 5 if loader_name == "_system_proc_pidinfo" else 3

    class Function:
        argtypes: list[object] | None = None
        restype: object | None = None

    function = Function()
    library = type("LibProc", (), {symbol_name: function})()
    loader = getattr(darwin, loader_name)
    loader.cache_clear()
    monkeypatch.setattr(darwin.ctypes.util, "find_library", lambda _name: "/tmp/libproc")
    monkeypatch.setattr(darwin.ctypes, "CDLL", lambda *_args, **_kwargs: library)

    try:
        observed = loader()
        assert observed is function
        assert function.argtypes is not None
        assert len(function.argtypes) == expected_arity
        assert function.restype is ctypes.c_int
    finally:
        loader.cache_clear()


@pytest.mark.parametrize(
    "loader_name",
    ["_system_proc_pidinfo", "_system_proc_listpgrppids"],
)
def test_darwin_libproc_loader_fails_closed_when_symbol_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    loader_name: str,
) -> None:
    loader = getattr(darwin, loader_name)
    loader.cache_clear()
    monkeypatch.setattr(darwin.ctypes.util, "find_library", lambda _name: "/tmp/libproc")
    monkeypatch.setattr(darwin.ctypes, "CDLL", lambda *_args, **_kwargs: object())

    try:
        with pytest.raises(WorkerIsolationUnsupportedError):
            loader()
    finally:
        loader.cache_clear()


@pytest.mark.parametrize(
    "mode",
    ["initial-error", "invalid-upper", "fill-error", "negative-count", "invalid-pid"],
)
def test_darwin_group_pid_enumeration_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    def enumerate_group(_group: int, buffer: object | None, _size: int) -> int:
        if buffer is None:
            if mode == "initial-error":
                raise OSError
            return -1 if mode == "invalid-upper" else 1
        if mode == "fill-error":
            raise TypeError
        if mode == "negative-count":
            return -1
        typed = ctypes.cast(
            t.cast("ctypes.Array[ctypes.c_int]", buffer),
            ctypes.POINTER(ctypes.c_int),
        )
        typed[0] = 0
        return 1

    monkeypatch.setattr(darwin, "_system_proc_listpgrppids", lambda: enumerate_group)

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(darwin)["_darwin_group_pids"](4312)


def test_darwin_group_pid_enumeration_rejects_unstable_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(darwin, "_PROC_GROUP_PID_CAPACITY", 4)

    def enumerate_group(_group: int, buffer: object | None, size: int) -> int:
        if buffer is None:
            return 1
        return size // ctypes.sizeof(ctypes.c_int)

    monkeypatch.setattr(darwin, "_system_proc_listpgrppids", lambda: enumerate_group)

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(darwin)["_darwin_group_pids"](4312)


def test_darwin_group_pid_enumeration_returns_unique_positive_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def enumerate_group(_group: int, buffer: object | None, _size: int) -> int:
        if buffer is None:
            return 2
        typed = ctypes.cast(
            t.cast("ctypes.Array[ctypes.c_int]", buffer),
            ctypes.POINTER(ctypes.c_int),
        )
        typed[0] = 4312
        typed[1] = 4313
        return 2

    monkeypatch.setattr(darwin, "_system_proc_listpgrppids", lambda: enumerate_group)

    assert vars(darwin)["_darwin_group_pids"](4312) == (4312, 4313)


@pytest.mark.parametrize(
    "mode",
    ["live", "missing", "unexpected", "error"],
)
def test_darwin_pid_liveness_requires_exact_libproc_result(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    def probe(_pid: int, _flavor: int, _arg: int, _buffer: object, _size: int) -> int:
        if mode == "error":
            raise OSError
        if mode == "missing":
            ctypes.set_errno(errno.ESRCH)
            return 0
        return vars(darwin)["_PROC_TASKINFO_SIZE"] if mode == "live" else 0

    monkeypatch.setattr(darwin, "_system_proc_pidinfo", lambda: probe)

    if mode in {"unexpected", "error"}:
        with pytest.raises(WorkerIsolationUnsupportedError):
            vars(darwin)["_darwin_pid_is_live"](4312)
    else:
        assert vars(darwin)["_darwin_pid_is_live"](4312) is (mode == "live")


def test_darwin_direct_child_lookup_reports_present_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(darwin.os, "getpgid", lambda pid: pid)

    assert vars(darwin)["_darwin_direct_child_missing"](4312) is False


@pytest.mark.parametrize("mode", ["lookup-error", "permission-error", "kernel-error", "live"])
def test_darwin_empty_live_scan_cross_checks_kernel_state(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    monkeypatch.setattr(darwin, "_darwin_direct_child_missing", lambda _group: False)

    def probe(_group: int, _signal: int) -> None:
        if mode == "lookup-error":
            raise ProcessLookupError
        if mode == "permission-error":
            raise PermissionError
        if mode == "kernel-error":
            raise OSError

    monkeypatch.setattr(darwin.os, "killpg", probe)

    if mode == "live":
        assert (
            vars(darwin)["_darwin_no_live_state"](4312, (), direct_child_terminal=False)
            is WorkerProcessGroupState.LIVE
        )
    else:
        with pytest.raises(WorkerIsolationUnsupportedError):
            vars(darwin)["_darwin_no_live_state"](4312, (4312,), direct_child_terminal=False)


@pytest.mark.parametrize("mode", ["error", "mismatch"])
def test_darwin_limit_binding_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    if mode == "error":
        monkeypatch.setattr(
            darwin.resource,
            "setrlimit",
            lambda *_args: (_ for _ in ()).throw(ValueError),
        )
    else:
        monkeypatch.setattr(darwin.resource, "setrlimit", lambda *_args: None)
        monkeypatch.setattr(darwin.resource, "getrlimit", lambda _limit: (-1, -1))

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(darwin)["_apply_exact_limit"](resource.RLIMIT_CPU, (1, 1))


def test_darwin_telemetry_rejects_invalid_pid_and_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerTelemetry(0)

    monkeypatch.setattr(darwin.ctypes, "sizeof", lambda _value: 1)
    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerTelemetry(4312)


@pytest.mark.parametrize("mode", ["capability", "error", "short"])
def test_darwin_telemetry_sample_fails_closed(
    mode: str,
) -> None:
    def probe(_pid: int, _flavor: int, _arg: int, _buffer: object, _size: int) -> int:
        if mode == "capability":
            raise WorkerIsolationUnsupportedError(_CAPABILITY_UNAVAILABLE)
        if mode == "error":
            raise TypeError
        return 0

    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerTelemetry(4312, probe).sample()


def test_darwin_parent_telemetry_rejects_privileged_or_invalid_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerBackend().open_parent_telemetry(
            4312,
            t.cast("WorkerResourceProfileDescriptor", object()),
        )

    monkeypatch.setattr(darwin.os, "getuid", lambda: 0)
    monkeypatch.setattr(darwin.os, "geteuid", lambda: 501)
    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerBackend().open_parent_telemetry(4312, PROFILE)


def test_darwin_backend_binds_nonprivileged_telemetry_and_forwards_group_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(darwin.os, "getuid", lambda: 501)
    monkeypatch.setattr(darwin.os, "geteuid", lambda: 501)
    monkeypatch.setattr(darwin.os, "killpg", lambda group, number: signals.append((group, number)))
    backend = darwin.DarwinWorkerBackend()

    telemetry = backend.open_parent_telemetry(4312, PROFILE)
    backend.signal_process_group(4312, 15)

    assert isinstance(telemetry, darwin.DarwinWorkerTelemetry)
    assert telemetry.pid == 4312
    assert signals == [(4312, 15)]


def test_darwin_group_probe_rejects_invalid_identifier() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        darwin.DarwinWorkerBackend().probe_process_group(0, direct_child_terminal=False)


def test_linux_status_reader_uses_utf8(tmp_path: Path) -> None:
    status = tmp_path / "status"
    status.write_text("worker\n", encoding="utf-8")

    assert vars(linux)["_read_status"](status) == "worker\n"


@pytest.mark.parametrize("mode", ["invalid-pid", "read-error"])
def test_linux_nproc_context_requires_exact_proc_identity(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    if mode == "read-error":
        monkeypatch.setattr(
            linux,
            "_read_status",
            lambda _path: (_ for _ in ()).throw(UnicodeError),
        )

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_require_nproc_enforcement_context"](0 if mode == "invalid-pid" else 4312)


def test_linux_identity_parser_ignores_unrelated_status_fields() -> None:
    fields = vars(linux)["_required_identity_fields"](
        "Name: worker\nUid: 1000 1000 1000 1000\nCapEff: 0\nCapPrm: 0\n"
    )

    assert fields == {
        "Uid:": ("1000", "1000", "1000", "1000"),
        "CapEff:": ("0",),
        "CapPrm:": ("0",),
    }


def test_linux_identity_parsers_reject_out_of_domain_values() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_parse_real_uid"](("4294967296", "0", "0", "0"))
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_parse_capability"](())


def test_linux_limit_binding_maps_resource_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        linux.resource,
        "setrlimit",
        lambda *_args: (_ for _ in ()).throw(OSError),
    )

    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_apply_exact_limit"](resource.RLIMIT_CPU, (1, 1))


@pytest.mark.parametrize("mode", ["vanished", "os-error", "unicode"])
def test_linux_process_stat_read_maps_filesystem_outcomes(mode: str) -> None:
    class Entry:
        def read_text(self, *, encoding: str) -> str:
            assert encoding == "ascii"
            if mode == "unicode":
                raise UnicodeError
            error = OSError()
            error.errno = errno.ENOENT if mode == "vanished" else errno.EPERM
            raise error

    if mode == "vanished":
        assert vars(linux)["_read_process_stat"](t.cast("Path", Entry())) is None
    else:
        with pytest.raises(WorkerIsolationUnsupportedError):
            vars(linux)["_read_process_stat"](t.cast("Path", Entry()))


def test_linux_process_stat_parser_rejects_malformed_payload() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        vars(linux)["_parse_process_stat"]("not a proc stat", 4312)


@pytest.mark.parametrize("mode", ["error", "live"])
def test_linux_empty_scan_requires_kernel_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    def probe(_group: int, _signal: int) -> None:
        if mode == "error":
            raise OSError

    monkeypatch.setattr(linux.os, "killpg", probe)

    if mode == "live":
        assert vars(linux)["_linux_empty_scan_state"](4312) is WorkerProcessGroupState.LIVE
    else:
        with pytest.raises(WorkerIsolationUnsupportedError):
            vars(linux)["_linux_empty_scan_state"](4312)


def test_linux_telemetry_rejects_invalid_pid_and_read_error() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        linux.LinuxWorkerTelemetry(0)

    with pytest.raises(WorkerIsolationUnsupportedError):
        linux.LinuxWorkerTelemetry(
            4312,
            lambda _path: (_ for _ in ()).throw(UnicodeError),
        ).sample()


def test_linux_parent_telemetry_rejects_invalid_profile() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        linux.LinuxWorkerBackend().open_parent_telemetry(
            4312,
            t.cast("WorkerResourceProfileDescriptor", object()),
        )


def test_linux_backend_forwards_group_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(linux.os, "killpg", lambda group, number: calls.append((group, number)))

    linux.LinuxWorkerBackend().signal_process_group(4312, 15)

    assert calls == [(4312, 15)]


def test_linux_group_probe_rejects_invalid_identifier() -> None:
    with pytest.raises(WorkerIsolationUnsupportedError):
        linux.LinuxWorkerBackend().probe_process_group(0, direct_child_terminal=False)


def test_linux_group_probe_skips_nonmembers_and_vanished_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = (Path("worker"), Path("0"), Path("7"), Path("8"))
    monkeypatch.setattr(linux, "_linux_process_entries", lambda: entries)
    monkeypatch.setattr(
        linux,
        "_read_process_stat",
        lambda path: None if path.parent.name == "7" else "8 (worker) R 1 999",
    )
    monkeypatch.setattr(
        linux,
        "_linux_empty_scan_state",
        lambda _group: WorkerProcessGroupState.ABSENT,
    )

    assert (
        linux.LinuxWorkerBackend().probe_process_group(4312, direct_child_terminal=False)
        is WorkerProcessGroupState.ABSENT
    )

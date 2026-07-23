"""Darwin resource limits and strict libproc parent telemetry."""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import resource
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerIsolationUnsupportedError,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerResourceSample
from ethos.adapters.repo.source_budget.measurement.worker.backend.core import WorkerTelemetry
from ethos_core.contracts.source_budget.measurement.worker.resource import (
    WorkerResourceProfileDescriptor,
)

_PROC_PIDTASKINFO = 4
_PROC_TASKINFO_SIZE = 96
_PROC_GROUP_PID_CAPACITY = 65_536
_INTERRUPTED_ATTEMPTS = 3
_TELEMETRY_ERROR = "worker telemetry unavailable"
_GROUP_PROBE_ERROR = "worker group probe unavailable"
_LIMIT_ERROR = "required worker limit unavailable"
_LIMIT_MISMATCH_ERROR = "required worker limit did not bind exactly"
_TELEMETRY_LAYOUT_ERROR = "worker telemetry layout unavailable"
_PROCESS_ISOLATION_ERROR = "worker process isolation unavailable"


class ProcTaskInfo(ctypes.Structure):
    """Exact Darwin ``struct proc_taskinfo`` layout for PROC_PIDTASKINFO."""

    _fields_ = [
        ("pti_virtual_size", ctypes.c_uint64),
        ("pti_resident_size", ctypes.c_uint64),
        ("pti_total_user", ctypes.c_uint64),
        ("pti_total_system", ctypes.c_uint64),
        ("pti_threads_user", ctypes.c_uint64),
        ("pti_threads_system", ctypes.c_uint64),
        ("pti_policy", ctypes.c_int32),
        ("pti_faults", ctypes.c_int32),
        ("pti_pageins", ctypes.c_int32),
        ("pti_cow_faults", ctypes.c_int32),
        ("pti_messages_sent", ctypes.c_int32),
        ("pti_messages_received", ctypes.c_int32),
        ("pti_syscalls_mach", ctypes.c_int32),
        ("pti_syscalls_unix", ctypes.c_int32),
        ("pti_csw", ctypes.c_int32),
        ("pti_threadnum", ctypes.c_int32),
        ("pti_numrunning", ctypes.c_int32),
        ("pti_priority", ctypes.c_int32),
    ]


_ProcPidInfo = Callable[[int, int, int, object, int], int]
_ProcListGroupPids = Callable[[int, object, int], int]


@lru_cache(maxsize=1)
def _system_proc_pidinfo() -> _ProcPidInfo:
    try:
        path = ctypes.util.find_library("proc") or "/usr/lib/libproc.dylib"
        library = ctypes.CDLL(path, use_errno=True)
        function = library.proc_pidinfo
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        function.restype = ctypes.c_int
    except (AttributeError, OSError) as exc:
        raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR) from exc
    return function


@lru_cache(maxsize=1)
def _system_proc_listpgrppids() -> _ProcListGroupPids:
    try:
        path = ctypes.util.find_library("proc") or "/usr/lib/libproc.dylib"
        library = ctypes.CDLL(path, use_errno=True)
        function = library.proc_listpgrppids
        function.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        function.restype = ctypes.c_int
    except (AttributeError, OSError) as exc:
        raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
    return function


def _darwin_group_pids(process_group: int) -> tuple[int, ...]:
    function = _system_proc_listpgrppids()
    ctypes.set_errno(0)
    try:
        upper = function(process_group, None, 0)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
    if upper < 0 or upper >= _PROC_GROUP_PID_CAPACITY:
        raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
    capacity = max(1, upper + 1)
    while capacity <= _PROC_GROUP_PID_CAPACITY:
        buffer = (ctypes.c_int * capacity)()
        ctypes.set_errno(0)
        try:
            count = function(process_group, buffer, ctypes.sizeof(buffer))
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        if count < 0:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
        if count < capacity:
            pids = tuple(buffer[:count])
            if any(pid <= 0 for pid in pids) or len(set(pids)) != len(pids):
                raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
            return pids
        capacity *= 2
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)


def _darwin_pid_is_live(pid: int) -> bool:
    info = ProcTaskInfo()
    ctypes.set_errno(0)
    try:
        observed = _system_proc_pidinfo()(
            pid,
            _PROC_PIDTASKINFO,
            0,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
    if observed == _PROC_TASKINFO_SIZE:
        return True
    if observed == 0 and ctypes.get_errno() == errno.ESRCH:
        return False
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)


def _darwin_direct_child_missing(process_group: int) -> bool:
    interrupted: InterruptedError | None = None
    for _attempt in range(_INTERRUPTED_ATTEMPTS):
        try:
            os.getpgid(process_group)
        except InterruptedError as exc:
            interrupted = exc
        except ProcessLookupError:
            return True
        except (AttributeError, OSError) as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        else:
            return False
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from interrupted


def _darwin_no_live_state(
    process_group: int,
    pids: tuple[int, ...],
    *,
    direct_child_terminal: bool,
) -> WorkerProcessGroupState:
    child_missing = _darwin_direct_child_missing(process_group)
    interrupted: InterruptedError | None = None
    for _attempt in range(_INTERRUPTED_ATTEMPTS):
        try:
            os.killpg(process_group, 0)
        except InterruptedError as exc:
            interrupted = exc
        except ProcessLookupError as exc:
            if not pids and child_missing:
                return WorkerProcessGroupState.ABSENT
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        except PermissionError as exc:
            if pids and child_missing and direct_child_terminal:
                return WorkerProcessGroupState.TERMINAL_ONLY
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        except (AttributeError, OSError) as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        else:
            return WorkerProcessGroupState.LIVE
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from interrupted


def _apply_exact_limit(limit: int, value: tuple[int, int]) -> None:
    try:
        resource.setrlimit(limit, value)
        observed = resource.getrlimit(limit)
    except (AttributeError, OSError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_LIMIT_ERROR) from exc
    if observed != value:
        raise WorkerIsolationUnsupportedError(_LIMIT_MISMATCH_ERROR)


@dataclass(frozen=True, slots=True)
class DarwinWorkerTelemetry:
    """Strict PROC_PIDTASKINFO telemetry bound to one child PID."""

    pid: int
    proc_pidinfo: _ProcPidInfo | None = None

    def __post_init__(self) -> None:
        if type(self.pid) is not int or self.pid <= 0:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        if ctypes.sizeof(ProcTaskInfo) != _PROC_TASKINFO_SIZE:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_LAYOUT_ERROR)

    def sample(self) -> WorkerResourceSample:
        """Return exact resident and virtual byte fields from libproc."""
        info = ProcTaskInfo()
        size = ctypes.sizeof(info)
        try:
            function = self.proc_pidinfo or _system_proc_pidinfo()
            observed = function(self.pid, _PROC_PIDTASKINFO, 0, ctypes.byref(info), size)
        except WorkerIsolationUnsupportedError:
            raise
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR) from exc
        if observed != _PROC_TASKINFO_SIZE:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        return WorkerResourceSample(
            rss_bytes=int(info.pti_resident_size),
            virtual_bytes=int(info.pti_virtual_size),
        )


class DarwinWorkerBackend:
    """Apply truthful Darwin kernel limits and expose libproc telemetry."""

    def apply_child_limits(self, profile: WorkerResourceProfileDescriptor) -> None:
        """Install common limits without claiming independent AS or RSS limits."""
        calls = (
            (resource.RLIMIT_CPU, (profile.cpu_soft_seconds, profile.cpu_hard_seconds)),
            (resource.RLIMIT_NOFILE, (profile.nofile, profile.nofile)),
            (resource.RLIMIT_NPROC, (profile.nproc, profile.nproc)),
            (resource.RLIMIT_CORE, (profile.core_bytes, profile.core_bytes)),
            (
                resource.RLIMIT_FSIZE,
                (profile.regular_file_bytes, profile.regular_file_bytes),
            ),
        )
        for limit, value in calls:
            _apply_exact_limit(limit, value)

    def open_parent_telemetry(
        self,
        pid: int,
        profile: WorkerResourceProfileDescriptor,
    ) -> WorkerTelemetry:
        """Bind strict non-privileged libproc telemetry to one child PID."""
        if (
            type(profile) is not WorkerResourceProfileDescriptor
            or os.getuid() == 0
            or os.geteuid() == 0
        ):
            raise WorkerIsolationUnsupportedError(_PROCESS_ISOLATION_ERROR)
        return DarwinWorkerTelemetry(pid)

    def signal_process_group(self, process_group: int, signal_number: int) -> None:
        """Send one exact signal to the Darwin worker process group."""
        os.killpg(process_group, signal_number)

    def probe_process_group(
        self,
        process_group: int,
        *,
        direct_child_terminal: bool,
    ) -> WorkerProcessGroupState:
        """Classify Darwin group state through libproc and kernel cross-checks."""
        if type(process_group) is not int or process_group <= 0:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
        pids = _darwin_group_pids(process_group)
        if any(_darwin_pid_is_live(pid) for pid in pids):
            return WorkerProcessGroupState.LIVE
        return _darwin_no_live_state(
            process_group,
            pids,
            direct_child_terminal=direct_child_terminal,
        )

"""Linux resource limits and strict parent process telemetry."""

from __future__ import annotations

import errno
import os
import resource
from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

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

_StatusReader = Callable[[Path], str]
_PRIVILEGED_CAPABILITIES = (1 << 21) | (1 << 24)
_MAX_UID = (1 << 32) - 1
_UID_DECIMAL_DIGITS = 10
_CAPABILITY_HEX_DIGITS = 16
_VANISHED_ERRNOS = frozenset({errno.ENOENT, errno.ESRCH, errno.ENOTDIR})
_TERMINAL_STATES = frozenset({"Z", "X", "x"})
_CAPABILITY_PART_COUNT = 2
_UID_PART_COUNT = 5
_STATUS_PART_COUNT = 3
_STAT_REQUIRED_FIELDS = 3
_STAT_PGRP_INDEX = 2
_PROC_ENTRY_CAPACITY = 65_536
_INTERRUPTED_ATTEMPTS = 3
_PROCESS_ISOLATION_ERROR = "worker process isolation unavailable"
_CAPABILITY_TELEMETRY_ERROR = "worker capability telemetry unavailable"
_TELEMETRY_ERROR = "worker telemetry unavailable"
_LIMIT_ERROR = "required worker limit unavailable"
_LIMIT_MISMATCH_ERROR = "required worker limit did not bind exactly"
_GROUP_PROBE_ERROR = "worker group probe unavailable"


def _read_status(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _require_nproc_enforcement_context(pid: int) -> None:
    if type(pid) is not int or pid <= 0:
        raise WorkerIsolationUnsupportedError(_PROCESS_ISOLATION_ERROR)
    try:
        payload = _read_status(Path("/proc") / str(pid) / "status")
    except (OSError, UnicodeError) as exc:
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR) from exc
    fields = _required_identity_fields(payload)
    real_uid = _parse_real_uid(fields["Uid:"])
    capabilities = tuple(_parse_capability(fields[key]) for key in ("CapEff:", "CapPrm:"))
    if real_uid == 0 or any(value & _PRIVILEGED_CAPABILITIES for value in capabilities):
        raise WorkerIsolationUnsupportedError(_PROCESS_ISOLATION_ERROR)


def _required_identity_fields(payload: str) -> dict[str, tuple[str, ...]]:
    required = {"Uid:", "CapEff:", "CapPrm:"}
    fields: dict[str, tuple[str, ...]] = {}
    for line in payload.splitlines():
        parts = line.split()
        if not parts or parts[0] not in required:
            continue
        key = parts[0]
        if key in fields:
            raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
        fields[key] = tuple(parts[1:])
    if set(fields) != required:
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
    return fields


def _parse_real_uid(values: tuple[str, ...]) -> int:
    if len(values) != _UID_PART_COUNT - 1 or any(
        not value.isascii() or not value.isdecimal() or len(value) > _UID_DECIMAL_DIGITS
        for value in values
    ):
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
    parsed = tuple(int(value) for value in values)
    if any(value > _MAX_UID for value in parsed):
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
    return parsed[0]


def _parse_capability(values: tuple[str, ...]) -> int:
    if len(values) != _CAPABILITY_PART_COUNT - 1:
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
    encoded = values[0]
    if (
        not encoded
        or len(encoded) > _CAPABILITY_HEX_DIGITS
        or not encoded.isascii()
        or any(character not in "0123456789abcdefABCDEF" for character in encoded)
    ):
        raise WorkerIsolationUnsupportedError(_CAPABILITY_TELEMETRY_ERROR)
    return int(encoded, 16)


def _parse_status(payload: str) -> WorkerResourceSample:
    values: dict[str, int] = {}
    for line in payload.splitlines():
        parts = line.split()
        if not parts or parts[0] not in {"VmRSS:", "VmSize:"}:
            continue
        key = parts[0]
        if (
            key in values
            or len(parts) != _STATUS_PART_COUNT
            or parts[2] != "kB"
            or not parts[1].isdigit()
        ):
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        values[key] = int(parts[1]) * 1024
    if set(values) != {"VmRSS:", "VmSize:"}:
        raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
    return WorkerResourceSample(
        rss_bytes=values["VmRSS:"],
        virtual_bytes=values["VmSize:"],
    )


def _apply_exact_limit(limit: int, value: tuple[int, int]) -> None:
    try:
        resource.setrlimit(limit, value)
        observed = resource.getrlimit(limit)
    except (AttributeError, OSError, ValueError) as exc:
        raise WorkerIsolationUnsupportedError(_LIMIT_ERROR) from exc
    if observed != value:
        raise WorkerIsolationUnsupportedError(_LIMIT_MISMATCH_ERROR)


def _linux_process_entries() -> tuple[Path, ...]:
    interrupted: InterruptedError | None = None
    for _attempt in range(_INTERRUPTED_ATTEMPTS):
        try:
            with os.scandir("/proc") as scan:
                entries = tuple(
                    Path(entry.path) for entry in islice(scan, _PROC_ENTRY_CAPACITY + 1)
                )
        except InterruptedError as exc:
            interrupted = exc
        except OSError as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        else:
            if len(entries) > _PROC_ENTRY_CAPACITY:
                raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
            return entries
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from interrupted


def _read_process_stat(path: Path) -> str | None:
    interrupted: InterruptedError | None = None
    for _attempt in range(_INTERRUPTED_ATTEMPTS):
        try:
            return path.read_text(encoding="ascii")
        except InterruptedError as exc:
            interrupted = exc
        except OSError as exc:
            if exc.errno in _VANISHED_ERRNOS:
                return None
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        except UnicodeError as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from interrupted


def _parse_process_stat(payload: str, expected_pid: int) -> tuple[str, int]:
    head, separator, tail = payload.rpartition(") ")
    pid_text, marker, _command = head.partition(" (")
    fields = tail.split()
    if (
        not separator
        or not marker
        or not pid_text.isdigit()
        or int(pid_text) != expected_pid
        or len(fields) < _STAT_REQUIRED_FIELDS
        or len(fields[0]) != 1
        or not fields[_STAT_PGRP_INDEX].isdigit()
        or int(fields[_STAT_PGRP_INDEX]) <= 0
    ):
        raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
    return fields[0], int(fields[_STAT_PGRP_INDEX])


def _linux_empty_scan_state(process_group: int) -> WorkerProcessGroupState:
    interrupted: InterruptedError | None = None
    for _attempt in range(_INTERRUPTED_ATTEMPTS):
        try:
            os.killpg(process_group, 0)
        except InterruptedError as exc:
            interrupted = exc
        except ProcessLookupError:
            return WorkerProcessGroupState.ABSENT
        except (AttributeError, OSError) as exc:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from exc
        else:
            return WorkerProcessGroupState.LIVE
    raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR) from interrupted


@dataclass(frozen=True, slots=True)
class LinuxWorkerTelemetry:
    """Strict ``/proc/<pid>/status`` telemetry bound to one child PID."""

    pid: int
    read_status: _StatusReader = _read_status

    def __post_init__(self) -> None:
        if type(self.pid) is not int or self.pid <= 0:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)

    def sample(self) -> WorkerResourceSample:
        """Return exact VmRSS and VmSize bytes without defaulting."""
        try:
            payload = self.read_status(Path("/proc") / str(self.pid) / "status")
        except (OSError, UnicodeError) as exc:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR) from exc
        return _parse_status(payload)


class LinuxWorkerBackend:
    """Apply exact Linux child limits and expose strict parent telemetry."""

    def apply_child_limits(self, profile: WorkerResourceProfileDescriptor) -> None:
        """Install common limits and the Linux address-space limit."""
        calls = (
            (resource.RLIMIT_CPU, (profile.cpu_soft_seconds, profile.cpu_hard_seconds)),
            (resource.RLIMIT_NOFILE, (profile.nofile, profile.nofile)),
            (resource.RLIMIT_NPROC, (profile.nproc, profile.nproc)),
            (resource.RLIMIT_CORE, (profile.core_bytes, profile.core_bytes)),
            (
                resource.RLIMIT_FSIZE,
                (profile.regular_file_bytes, profile.regular_file_bytes),
            ),
            (
                resource.RLIMIT_AS,
                (profile.linux_address_space_bytes, profile.linux_address_space_bytes),
            ),
        )
        for limit, value in calls:
            _apply_exact_limit(limit, value)

    def open_parent_telemetry(
        self,
        pid: int,
        profile: WorkerResourceProfileDescriptor,
    ) -> WorkerTelemetry:
        """Bind strict non-privileged ``/proc`` telemetry to one child PID."""
        if type(profile) is not WorkerResourceProfileDescriptor:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        _require_nproc_enforcement_context(pid)
        return LinuxWorkerTelemetry(pid)

    def signal_process_group(self, process_group: int, signal_number: int) -> None:
        """Send one exact signal to the Linux worker process group."""
        os.killpg(process_group, signal_number)

    def probe_process_group(
        self,
        process_group: int,
        *,
        direct_child_terminal: bool,
    ) -> WorkerProcessGroupState:
        """Classify Linux group members through strict ``/proc`` state."""
        if type(process_group) is not int or process_group <= 0:
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
        terminal_seen = False
        for entry in _linux_process_entries():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid <= 0 or (payload := _read_process_stat(entry / "stat")) is None:
                continue
            state, member_group = _parse_process_stat(payload, pid)
            if member_group != process_group:
                continue
            if state not in _TERMINAL_STATES:
                return WorkerProcessGroupState.LIVE
            terminal_seen = True
        if terminal_seen:
            if direct_child_terminal:
                return WorkerProcessGroupState.TERMINAL_ONLY
            raise WorkerIsolationUnsupportedError(_GROUP_PROBE_ERROR)
        return _linux_empty_scan_state(process_group)

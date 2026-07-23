"""Platform capability contract for one-shot source-budget workers."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.measurement.worker.resource import (
        WorkerResourceProfileDescriptor,
    )

_TELEMETRY_ERROR = "worker telemetry unavailable"
_PLATFORM_ERROR = "worker platform isolation unsupported"
_LINUX_BACKEND_MODULE = "ethos.adapters.repo.source_budget.measurement.worker.backend.linux.core"
_DARWIN_BACKEND_MODULE = "ethos.adapters.repo.source_budget.measurement.worker.backend.darwin.core"


class WorkerIsolationUnsupportedError(RuntimeError):
    """Required platform isolation capability is unavailable."""


class WorkerProcessGroupState(Enum):
    """Observed liveness state of one isolated worker process group."""

    LIVE = "live"
    TERMINAL_ONLY = "terminal_only"
    ABSENT = "absent"


@dataclass(frozen=True, slots=True)
class WorkerResourceSample:
    """One parent-observed process resource sample."""

    rss_bytes: int
    virtual_bytes: int | None

    def __post_init__(self) -> None:
        if type(self.rss_bytes) is not int or self.rss_bytes < 0:
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)
        if self.virtual_bytes is not None and (
            type(self.virtual_bytes) is not int or self.virtual_bytes < 0
        ):
            raise WorkerIsolationUnsupportedError(_TELEMETRY_ERROR)


class WorkerTelemetry(Protocol):
    """Platform process telemetry used by the parent supervisor."""

    def sample(self) -> WorkerResourceSample:
        """Return one exact non-negative resource sample or fail closed."""
        ...


class WorkerBackend(Protocol):
    """Child-limit and parent-telemetry capability for one platform."""

    def apply_child_limits(self, profile: WorkerResourceProfileDescriptor) -> None:
        """Install every required child limit exactly or raise unsupported."""
        ...

    def open_parent_telemetry(
        self,
        pid: int,
        profile: WorkerResourceProfileDescriptor,
    ) -> WorkerTelemetry:
        """Bind telemetry to one child PID or raise unsupported."""
        ...

    def signal_process_group(self, process_group: int, signal_number: int) -> None:
        """Send one exact signal to the worker process group."""
        ...

    def probe_process_group(
        self,
        process_group: int,
        *,
        direct_child_terminal: bool,
    ) -> WorkerProcessGroupState:
        """Classify live, terminal-only, or absent worker-group state."""
        ...


def worker_backend(platform_name: str | None = None) -> WorkerBackend:
    """Return only the exact Linux or Darwin backend; fail closed otherwise."""
    selected = platform.system() if platform_name is None else platform_name
    if selected == "Linux":
        return import_module(_LINUX_BACKEND_MODULE).LinuxWorkerBackend()
    if selected == "Darwin":
        return import_module(_DARWIN_BACKEND_MODULE).DarwinWorkerBackend()
    raise WorkerIsolationUnsupportedError(_PLATFORM_ERROR)

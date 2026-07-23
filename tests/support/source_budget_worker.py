"""Reusable deterministic doubles for source-budget worker supervision tests."""

from __future__ import annotations

import selectors
import types
import typing as t
from collections import deque

from ethos.adapters.repo.source_budget.measurement.worker.backend.core import (
    WorkerProcessGroupState,
)


class UnexpectedCleanupError(Exception):
    """Test-only exception outside the runtime's ordinary error taxonomy."""


class EmergencyExchangeConfig(t.Protocol):
    """Minimal emergency-exchange contract asserted by the supervisor double."""

    telemetry: object | None
    request_permitted: bool
    initial_cause: str | None


class WorkerPipe:
    """Minimal binary pipe double with observable close state."""

    def __init__(self, fd: int, events: list[str]) -> None:
        self.fd, self.events, self.closed = fd, events, False

    def fileno(self) -> int:
        return self.fd

    def close(self) -> None:
        if not self.closed:
            self.events.append(f"close:{self.fd}")
            self.closed = True


class WorkerProcess:
    """One-child process double with deterministic reap observations."""

    def __init__(self, events: list[str], returncodes: tuple[int | None, ...] = (None, 0)) -> None:
        self.pid, self.events = 4312, events
        self.stdin, self.stdout = WorkerPipe(31, events), WorkerPipe(32, events)
        self.returncode: int | None = None
        self.returncodes = deque(returncodes)

    def wait(self, timeout: float | None = None) -> int:
        self.events.append(f"reap:{timeout}")
        self.returncode = 0 if self.returncode is None else self.returncode
        return self.returncode


class WorkerTelemetry:
    """Deterministic resource-sample stream."""

    def __init__(self, samples: tuple[object, ...], events: list[str]) -> None:
        self.samples, self.events = deque(samples), events

    def sample(self) -> object:
        self.events.append("sample")
        value = self.samples[0] if len(self.samples) == 1 else self.samples.popleft()
        if isinstance(value, BaseException):
            raise value
        return value


class WorkerGroupProbe:
    """Deterministic process-group state probe."""

    def __init__(self, alive: dict[str, bool], events: list[str], *, fail: bool = False) -> None:
        self.alive, self.events, self.fail = alive, events, fail

    def __call__(self, _pid: int, *, direct_child_terminal: bool) -> WorkerProcessGroupState:
        self.events.append("group-probe")
        if self.fail:
            raise UnexpectedCleanupError
        if self.alive["value"]:
            return WorkerProcessGroupState.LIVE
        return (
            WorkerProcessGroupState.TERMINAL_ONLY
            if direct_child_terminal
            else WorkerProcessGroupState.ABSENT
        )


class WorkerClock:
    """Monotonic clock double advanced only by declared operations."""

    def __init__(self, tick: float = 0.0) -> None:
        self.now, self.tick = 0.0, tick

    def monotonic(self) -> float:
        self.now += self.tick
        return self.now


class WorkerSelector:
    """Selector double driven by a finite action stream."""

    def __init__(
        self,
        clock: WorkerClock,
        actions: tuple[str | BaseException, ...],
        events: list[str],
        *,
        fail_close: bool = False,
    ) -> None:
        self.clock, self.actions, self.events = clock, deque(actions), events
        self.fail_close = fail_close
        self.registered: dict[int, t.Any] = {}
        self.timeouts: list[float | None] = []

    def register(self, fileobj: WorkerPipe | t.BinaryIO, mask: int, data: object = None) -> None:
        key = types.SimpleNamespace(fileobj=fileobj, fd=fileobj.fileno(), data=data, events=mask)
        self.registered[key.fd] = key
        self.events.append(f"register:{data}")

    def unregister(self, fileobj: WorkerPipe | t.BinaryIO) -> None:
        self.registered.pop(fileobj.fileno(), None)

    def select(self, timeout: float | None = None) -> list[tuple[t.Any, int]]:
        self.timeouts.append(timeout)
        action = self.actions.popleft() if self.actions else "idle"
        if isinstance(action, BaseException):
            self.clock.now += min(0.001, max(0.0, timeout or 0.0))
            raise action
        self.clock.now += 0.0 if timeout is None else timeout
        for key in self.registered.values():
            wanted = selectors.EVENT_WRITE if action == "stdin" else selectors.EVENT_READ
            if key.data == action and key.events & wanted:
                return [(key, wanted)]
        return []

    def close(self) -> None:
        self.events.append("selector-close")
        if self.fail_close:
            raise UnexpectedCleanupError


class WorkerRawIO:
    """Partial raw read/write stream with observable attempts."""

    def __init__(
        self,
        writes: tuple[int | BaseException, ...],
        reads: tuple[bytes | BaseException, ...],
        events: list[str],
    ) -> None:
        self.writes, self.reads, self.events = deque(writes), deque(reads), events
        self.sent, self.blocking, self.write_attempts = bytearray(), [], []

    def set_blocking(self, fd: int, value: object) -> None:
        self.blocking.append((fd, value))

    def write(self, fd: int, payload: bytes | memoryview) -> int:
        self.write_attempts.append(bytes(payload))
        count = min(len(payload), step(self.writes, len(payload)))
        self.sent.extend(bytes(payload[:count]))
        self.events.append(f"write:{fd}:{count}")
        return count

    def read(self, fd: int, maximum: int) -> bytes:
        self.events.append(f"read:{fd}:{maximum}")
        return step(self.reads, b"")


def assert_emergency_exchange(
    config: EmergencyExchangeConfig,
    process: WorkerProcess,
    events: list[str],
    grace_seconds: float,
) -> None:
    """Assert raw emergency shape and record deterministic child reaping."""
    events.append("emergency-exchange")
    assert config.telemetry is None
    assert config.request_permitted is False
    assert config.initial_cause == "pipe_failed"
    process.wait(grace_seconds)


def step[T](steps: deque[T | BaseException], default: T) -> T:
    """Return the next declared value or raise the next declared error."""
    value = steps.popleft() if steps else default
    if isinstance(value, BaseException):
        raise value
    return value

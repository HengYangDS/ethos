"""A fake clock for bounded waits: each sleep advances it by its own duration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import override

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeClock:
    """A fake clock whose sleeps advance it by their own duration."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class ReleasingClock(FakeClock):
    """A fake clock that runs one release, such as a holder's leaving, once its time is reached."""

    def __init__(self, at: float, release: Callable[[], object]) -> None:
        super().__init__()
        self.at = at
        self.release: Callable[[], object] | None = release

    @override
    def sleep(self, seconds: float) -> None:
        super().sleep(seconds)
        if self.release is not None and self.now >= self.at:
            release, self.release = self.release, None
            release()

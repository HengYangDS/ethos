"""A fake clock for bounded waits: each sleep advances it by its own duration."""

from __future__ import annotations


class FakeClock:
    """A fake clock whose sleeps advance it by their own duration."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

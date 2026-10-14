"""Start the longest recorded tests first so parallel workers finish together.

pytest-xdist hands tests to idle workers in collection order, so a long test
collected near the end keeps one worker busy after the others have finished.
The test gate loads this plugin to record each test's measured duration in the
pytest cache and to order the next collection by descending recorded duration.
Tests without a record keep their collection order ahead of recorded tests, so a
new test never starts last. The order changes scheduling only: every collected
test still runs, and failed-first ordering still applies after it. The xdist
controller reads the record once and hands the same snapshot to every worker,
because workers must collect the same sequence.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from xdist.workermanage import WorkerController

_RECORD = "ethos/test-durations"
_SNAPSHOT = "ethos_test_durations"


def _seconds(record: object) -> dict[str, float]:
    if not isinstance(record, dict):
        return {}
    return {
        str(name): float(seconds)
        for name, seconds in record.items()
        if isinstance(seconds, int | float) and not isinstance(seconds, bool)
    }


class DurationOrder:
    """Order one session's collection by recorded duration and record what it measures."""

    def __init__(self, config: pytest.Config) -> None:
        self._config = config
        self._worker_input = getattr(config, "workerinput", None)
        if self._worker_input is not None:
            self._recorded = _seconds(self._worker_input.get(_SNAPSHOT))
        else:
            cache = config.cache
            self._recorded = _seconds(cache.get(_RECORD, {}) if cache is not None else {})
        self._measured: dict[str, float] = {}

    @pytest.hookimpl(optionalhook=True)
    def pytest_configure_node(self, node: WorkerController) -> None:
        """Give every xdist worker the controller's snapshot of the record."""
        node.workerinput[_SNAPSHOT] = self._recorded

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        """Keep unrecorded tests first, then start recorded tests longest first."""
        items.sort(key=lambda item: -self._recorded.get(item.nodeid, math.inf))

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Sum the setup, call and teardown time of each test."""
        self._measured[report.nodeid] = self._measured.get(report.nodeid, 0.0) + report.duration

    def pytest_sessionfinish(self) -> None:
        """Merge this run's measurements into the record from the controlling process."""
        cache = self._config.cache
        if self._worker_input is None and cache is not None and self._measured:
            measured = {name: round(seconds, 3) for name, seconds in self._measured.items()}
            cache.set(_RECORD, self._recorded | measured)


def pytest_configure(config: pytest.Config) -> None:
    """Register the duration order for this session."""
    config.pluginmanager.register(DurationOrder(config), "ethos-duration-order")

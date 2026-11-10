"""The `gate` marker: a marked test proves one gate's role and can never pass by skipping."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.registries import proof_registry

if TYPE_CHECKING:
    from collections.abc import Generator

ROLES = frozenset({"refusing", "conforming", "fail_closed"})
_INVALID = pytest.StashKey[str]()
DESELECTED = pytest.StashKey[int]()


def pytest_configure(config: pytest.Config) -> None:
    """Register the marker beside the semantics that give it meaning."""
    config.addinivalue_line(
        "markers", "gate(id, role): the gate and the role this test proves; it cannot skip."
    )


def gate_marks(item: pytest.Item) -> tuple[tuple[str, str], ...]:
    """Return each (gate, role) pair an item's `gate` marks declare."""
    return tuple(
        (str(mark.args[0]), str(mark.args[1]))
        for mark in item.iter_markers("gate")
        if len(mark.args) == 2
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Record every malformed or unknown mark on its item; failing here would stop xdist."""
    gates = proof_registry()
    for item in items:
        for mark in item.iter_markers("gate"):
            gate, role = (*mark.args, "", "")[:2]
            if len(mark.args) != 2 or mark.kwargs:
                item.stash[_INVALID] = f"gate mark needs exactly (id, role): {mark.args}"
            elif gate not in gates:
                item.stash[_INVALID] = f"gate mark names an unregistered gate: {gate}"
            elif role not in ROLES:
                item.stash[_INVALID] = f"gate mark names an unknown role: {role}"
        item.user_properties.extend(("ethos.gate", f"{g}:{r}") for g, r in gate_marks(item))


def pytest_deselected(items: list[pytest.Item]) -> None:
    """Count deselected items; a run that deselects any is not the whole suite."""
    if items:
        stash = items[0].config.stash
        stash[DESELECTED] = stash.get(DESELECTED, 0) + len(items)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Fail an item whose mark collection refused."""
    if message := item.stash.get(_INVALID, ""):
        pytest.fail(message, pytrace=False)


@pytest.hookimpl(tryfirst=True, wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """A marked test that skips, xfails or unexpectedly passes an xfail has proven nothing."""
    report = yield
    if not gate_marks(item):
        return report
    xfailed = hasattr(report, "wasxfail")
    if report.skipped or xfailed:
        report.outcome = "failed"
        report.longrepr = f"a test marked with gate cannot skip or xfail ({call.when})"
        if xfailed:
            del report.wasxfail
    return report

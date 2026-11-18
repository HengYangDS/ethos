"""A calm load sample from before the readiness gates is the first of the two that admit a proof."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.proof_slot as proof_slot
from tests.support.clock import FakeClock
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = "a" * 40


def _sleeps(repo: Path, loads: list[float], earlier: tuple[float, float | None] | None) -> list:
    """Admit a proof one minute into a fake clock and return the sleeps its admission took."""
    clock = FakeClock()
    clock.now = 60.0
    with proof_slot.admitted_full_proof(
        repo,
        head=_HEAD,
        current=lambda: True,
        limit=lambda: (8.0, "test"),
        load=lambda: loads.pop(0) if len(loads) > 1 else loads[0],
        clock=lambda: clock.now,
        sleep=clock.sleep,
        seconds=600.0,
        report=lambda _event: None,
        earlier=earlier,
    ):
        pass
    return clock.sleeps


@pytest.mark.parametrize(
    ("earlier", "loads", "sleeps"),
    [
        # Calm before the readiness gates and calm after them: two calm samples, no wait.
        ((0.0, 4.0), [5.0], []),
        # No earlier sample, a busy one, or one that the host could not give: one interval.
        (None, [5.0], [15.0]),
        ((0.0, 30.0), [5.0], [15.0]),
        ((0.0, None), [5.0], [15.0]),
        # An earlier sample younger than one interval is no second look.
        ((50.0, 4.0), [5.0], [15.0]),
        # A busy sample at admission ends the run of calm ones; two fresh ones are needed.
        ((0.0, 4.0), [20.0, 5.0, 6.0], [15.0, 15.0]),
    ],
)
def test_a_calm_sample_before_the_readiness_gates_counts_once(
    tmp_path: Path,
    earlier: tuple[float, float | None] | None,
    loads: list[float],
    sleeps: list[float],
) -> None:
    """Two calm samples one interval apart admit; the readiness gates' own time is that interval."""
    assert _sleeps(init_git_repo(tmp_path / "repo"), loads, earlier) == sleeps

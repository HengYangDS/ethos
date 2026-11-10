"""Cognitive complexity has one owner: no function grows past the threshold or its pinned score."""

from __future__ import annotations

import json
from pathlib import Path

from complexipy import code_complexity
from complexipy import file_complexity

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ("src", "tools")
THRESHOLD = 15
# The functions above the threshold when complexipy became the owner, each with its score. The file
# only shrinks: a function that improves or disappears must leave it, and none may exceed its score.
BASELINE = ROOT / "tests/fixtures/decision-density-baseline.json"


def scores(root: Path, bases: tuple[str, ...]) -> dict[str, int]:
    """Each function's cognitive complexity by path and qualified name; overloads keep the max."""
    measured: dict[str, int] = {}
    for base in bases:
        for path in sorted((root / base).rglob("*.py")):
            for function in file_complexity(str(path)).functions:
                key = f"{path.relative_to(root).as_posix()}::{function.name}"
                measured[key] = max(measured.get(key, 0), function.complexity)
    return measured


def departures(measured: dict[str, int], pinned: dict[str, int]) -> dict[str, str]:
    """Name every function above its allowance and every pinned entry that no longer applies."""
    grown = {
        key: f"{score} > {max(THRESHOLD, pinned.get(key, 0))}"
        for key, score in measured.items()
        if score > max(THRESHOLD, pinned.get(key, 0))
    }
    stale = {
        key: f"pinned {score}, measured {measured.get(key, 0)}"
        for key, score in pinned.items()
        if measured.get(key, 0) != score
    }
    return grown | stale


def test_no_function_grows_past_its_allowance() -> None:
    """New code stays within the threshold; pinned code never grows and leaves when it shrinks."""
    pinned = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert departures(scores(ROOT, PRODUCT), pinned) == {}


def test_a_dense_function_is_refused_and_a_stale_pin_is_named() -> None:
    """Nested decisions add up; an improved pinned function must leave the baseline."""
    nested = "def judge(a, b, c):\n" + "".join(
        f"{'    ' * (depth + 1)}if a > {depth} and b or c:\n" for depth in range(6)
    )
    score = code_complexity(nested + "        " * 4 + "return a\n").complexity

    assert score > THRESHOLD
    assert departures({"m.py::judge": score}, {}) == {"m.py::judge": f"{score} > {THRESHOLD}"}
    assert departures({"m.py::judge": 3}, {"m.py::judge": 20}) == {
        "m.py::judge": "pinned 20, measured 3"
    }

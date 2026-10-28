"""One declared hang bound owns every test's upper time limit."""

from __future__ import annotations

import ast
import math
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.toml"


def test_test_level_timeouts_only_tighten_the_declared_hang_bound() -> None:
    """A test may time one fast operation more tightly but never extend the shared bound."""
    bound = float(tomllib.loads(PYTEST_CONFIG.read_text(encoding="utf-8"))["pytest"]["timeout"])
    marks = {
        f"{path.relative_to(ROOT)}:{node.lineno}": seconds
        for path in sorted((ROOT / "tests").rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and (seconds := _timeout_mark(node)) is not None
    }
    assert marks, "the scan must see the deliberately short marks"
    assert {site: seconds for site, seconds in marks.items() if seconds >= bound} == {}


def _timeout_mark(call: ast.Call) -> float | None:
    """Return the seconds of a ``pytest.mark.timeout`` call; a non-literal value is unbounded."""
    match call.func:
        case ast.Attribute(
            attr="timeout", value=ast.Attribute(attr="mark", value=ast.Name(id="pytest"))
        ):
            values = [
                *call.args[:1],
                *(word.value for word in call.keywords if word.arg == "timeout"),
            ]
            match values:
                case [ast.Constant(value=int() | float() as seconds)]:
                    return float(seconds)
            return math.inf
    return None

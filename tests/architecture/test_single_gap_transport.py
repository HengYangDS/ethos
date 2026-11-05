"""Product code carries every gap of a refusal; no error or failure helper gets only the first."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Local failure helpers raise the refusal they are given.
_HELPERS = re.compile(r"^(_fail|_require|require_\w+)$")


def test_product_code_never_transports_only_the_first_gap() -> None:
    """Every refusal in `src/` raises all of its gaps, as `refusal(*gaps)` does."""
    assert _single_gap_transports(ROOT / "src") == []


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("raise ValueError(gaps[0])", 1),
        ("raise ValueError(gaps[0] if gaps else 'gate_missing')", 1),
        ("_fail(str(report['required_gaps'][0]))", 1),
        ("require_release(ready, gaps[0])", 1),
        ("raise ProcessExecutionError(gaps[0], reason='r')", 1),
        ("return subprocess.CompletedProcess(args, 1, out, gaps[0])", 1),
        ("raise ProcessExecutionError(gaps[0], reason='r', observation={'required_gaps': g})", 0),
        ("raise OutcomeError(outcome, message=gaps[0])", 0),
        ("raise refusal(*gaps)", 0),
        ("reason = gaps[0] if gaps else ''", 0),
    ],
)
def test_a_single_gap_transport_is_found_and_a_leading_gap_is_not(
    tmp_path: Path, source: str, found: int
) -> None:
    """A planted first-gap refusal fails the check; choosing a leading gap to name stays allowed."""
    (tmp_path / "planted.py").write_text(source, encoding="utf-8")
    assert len(_single_gap_transports(tmp_path)) == found


def _single_gap_transports(root: Path) -> list[str]:
    """List each call that hands an error or failure helper only element zero of a gap list."""
    return [
        f"{path.relative_to(root)}:{node.lineno}"
        for path in sorted(root.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and _transports(node)
    ]


def _transports(call: ast.Call) -> bool:
    """A refusal or native result whose positional argument is a first gap, without the rest."""
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    if not (name.endswith("Error") or name == "CompletedProcess" or _HELPERS.match(name)):
        return False
    carried = any(keyword.arg == "observation" for keyword in call.keywords)
    return not carried and any(_first_gap(argument) for argument in call.args)


def _first_gap(node: ast.expr) -> bool:
    """Return whether an expression is, or falls back from, element zero of a gap sequence."""
    if isinstance(node, ast.IfExp):
        return _first_gap(node.body)
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "str" and node.args:
        return _first_gap(node.args[0])
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == 0
        and "gaps" in ast.unparse(node.value)
    )

"""Product code takes every wait from a declared parameter, never from a literal."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
# Delivery acceptance runs outside a governed repository's proof; its owners migrate these values,
# so the count only falls.
TOOLS_WAITS = 31


def test_product_code_holds_no_literal_wait_and_tools_only_shed_theirs() -> None:
    """`src/` reads every wait from its parameter; `tools/` keeps at most its recorded count."""
    assert _literal_waits(ROOT / "src") == []
    assert len(_literal_waits(ROOT / "tools")) <= TOOLS_WAITS


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("run(timeout=30)", 1),
        ("def wait(*, lock_timeout=5.0): ...", 1),
        ("def wait(timeout_seconds=-1): ...", 1),
        ("_PUSH_SECONDS = 120\n_REQUEST_TIMEOUT: int = 9", 2),
        ("_ABORT_GRACE_SECONDS = 5\n_POLL_SECONDS = 15.0\nrun(timeout=seconds('git'))", 0),
    ],
)
def test_a_literal_wait_is_found_and_protocol_timing_is_not(
    tmp_path: Path, source: str, found: int
) -> None:
    """A planted literal fails the check; a named grace or polling interval stays allowed."""
    (tmp_path / "planted.py").write_text(source, encoding="utf-8")
    assert len(_literal_waits(tmp_path)) == found


def _literal_waits(root: Path) -> list[str]:
    """List each numeric literal bound to a timeout name or a duration constant under a root."""
    return [
        f"{path.relative_to(root)}:{value.lineno}:{name}"
        for path in sorted(root.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        for name, value, constant in _bindings(node)
        if _numeric(value) and _wait(name, constant=constant)
    ]


def _bindings(node: ast.AST) -> Iterator[tuple[str, ast.expr, bool]]:
    """Yield a node's keyword arguments, parameter defaults and constant assignments."""
    match node:
        case ast.keyword(arg=str() as name, value=value):
            yield name, value, False
        case ast.FunctionDef(args=arguments) | ast.AsyncFunctionDef(args=arguments):
            positional = [*arguments.posonlyargs, *arguments.args]
            pairs = [
                # Defaults belong to the last positional parameters.
                *zip(positional[::-1], arguments.defaults[::-1], strict=False),
                *zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True),
            ]
            for argument, default in pairs:
                if default is not None:
                    yield argument.arg, default, False
        case (
            ast.Assign(targets=[ast.Name(id=name)], value=value)
            | ast.AnnAssign(target=ast.Name(id=name), value=ast.expr() as value)
        ):
            yield name, value, name.isupper()


def _numeric(value: ast.expr) -> bool:
    """Return whether an expression is a plain, possibly negated, number."""
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
        value = value.operand
    return isinstance(value, ast.Constant) and type(value.value) in {int, float}


def _wait(name: str, *, constant: bool) -> bool:
    """A timeout name binds a wait; so does a duration constant other than ETHOS's own timing."""
    lowered = name.lower()
    if lowered == "timeout" or lowered.endswith(("_timeout", "timeout_seconds")):
        return True
    named = "timeout" in lowered or lowered.endswith("_seconds")
    return constant and named and not lowered.endswith(("grace_seconds", "poll_seconds"))

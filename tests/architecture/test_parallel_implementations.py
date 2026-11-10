"""One behavior has one implementation: no two function bodies in product code are the same."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import override

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ("src", "tools")
# Below this many syntax nodes a body is an idiom, such as one delegated call, not an
# implementation; at or above it, a second copy is a parallel implementation.
MINIMUM_NODES = 6


class _BoundNames(ast.NodeTransformer):
    """Rename what a function binds, in order of first use, and keep the names it reads."""

    def __init__(self, bound: frozenset[str]) -> None:
        self.bound = bound
        self.renamed: dict[str, str] = {}

    def _rename(self, name: str) -> str:
        return self.renamed.setdefault(name, f"_{len(self.renamed)}")

    @override
    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self.bound:
            node.id = self._rename(node.id)
        return node

    @override
    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._rename(node.arg)
        node.annotation = None
        return node


def _statements(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    """Return the body without its docstring."""
    head, *rest = function.body
    docstring = (
        isinstance(head, ast.Expr)
        and isinstance(head.value, ast.Constant)
        and isinstance(head.value.value, str)
    )
    return rest if docstring else function.body


def _shape(function: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Return a body's structure with bound names renamed, or None for an idiom or a stub."""
    copy = ast.parse(ast.unparse(function)).body[0]
    if not isinstance(copy, ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    bound = frozenset(
        {node.arg for node in ast.walk(copy) if isinstance(node, ast.arg)}
        | {
            node.id
            for node in ast.walk(copy)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
        }
    )
    body = ast.Module(body=_statements(copy), type_ignores=[])
    if sum(1 for _node in ast.walk(body)) < MINIMUM_NODES:
        return None
    # One renaming for the signature and then the body, so `a - b` never equals `b - a`.
    renaming = _BoundNames(bound)
    return ast.dump(renaming.visit(copy.args)) + ast.dump(renaming.visit(body))


def _overload(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        (isinstance(item, ast.Name) and item.id == "overload")
        or (isinstance(item, ast.Attribute) and item.attr == "overload")
        for item in function.decorator_list
    )


def implementations(root: Path, bases: tuple[str, ...]) -> list[list[str]]:
    """Group every function whose body another function repeats, by place."""
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for base in bases:
        for path in sorted((root / base).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                    and not _overload(node)
                    and (shape := _shape(node)) is not None
                ):
                    place = f"{path.relative_to(root).as_posix()}:{node.lineno}:{node.name}"
                    groups[shape].append(place)
    return [places for places in groups.values() if len(places) > 1]


def test_no_behavior_is_implemented_twice() -> None:
    """Each repeated body names one owner that every caller imports instead."""
    assert implementations(ROOT, PRODUCT) == []


def test_a_renamed_copy_is_the_same_implementation(tmp_path: Path) -> None:
    """Renamed parameters and locals do not hide a copy; another callee does not make one."""
    (tmp_path / "src").mkdir()
    for name, source in (
        (
            "a.py",
            "def fail(reason):\n    message = reason.strip()\n    raise ValueError(message)\n",
        ),
        ("b.py", "def _invalid(code):\n    text = code.strip()\n    raise ValueError(text)\n"),
        ("c.py", "def other(code):\n    text = code.strip()\n    raise TypeError(text)\n"),
        ("d.py", "def minus(a, b):\n    total = a - b\n    return total\n"),
        ("e.py", "def swapped(a, b):\n    total = b - a\n    return total\n"),
    ):
        (tmp_path / "src" / name).write_text(source, encoding="utf-8")

    assert implementations(tmp_path, ("src",)) == [["src/a.py:1:fail", "src/b.py:1:_invalid"]]

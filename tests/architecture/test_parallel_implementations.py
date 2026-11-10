"""One behavior has one implementation: no two source, tool or test function bodies are the same."""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from itertools import starmap
from pathlib import Path
from typing import override

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ("src", "tools", "tests")
# Statement and expression nodes, without the module wrapper and the Load/Store markers: a bare
# `return name` is an idiom; a delegated call such as `raise ValueError(reason)` is the smallest
# implementation a second module may not repeat.
MINIMUM_NODES = 4
# A script the CI runs without the project environment cannot import an owner, so it is its own
# deployment unit: its source is derived from the CI projection, never listed by hand.
_STANDALONE = re.compile(r"uv run --no-project python(?: -\w+)* (tools/\S+\.py)")
_CAPTURES = (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)


class _BoundNames(ast.NodeTransformer):
    """Rename what a function binds, in order of first use, and keep the names it reads."""

    def __init__(self, bound: frozenset[str]) -> None:
        self.bound = bound
        self.renamed: dict[str, str] = {}

    def _rename(self, name: str | None) -> str | None:
        return (
            self.renamed.setdefault(name, f"_{len(self.renamed)}") if name in self.bound else name
        )

    @override
    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = self._rename(node.id) or node.id
        return node

    @override
    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._rename(node.arg) or node.arg
        node.annotation = None
        return node

    @override
    def generic_visit(self, node: ast.AST) -> ast.AST:
        if isinstance(node, _CAPTURES):
            node.name = self._rename(node.name)
        elif isinstance(node, ast.MatchMapping):
            node.rest = self._rename(node.rest)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            node.name = self._rename(node.name) or node.name
        elif isinstance(node, ast.alias):
            node.asname = self._rename(node.asname or node.name.split(".")[0])
        return super().generic_visit(node)


def _bound(function: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """Every name the function binds: parameters, targets, captures, nested definitions, imports."""
    names: set[str | None] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, _CAPTURES):
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping):
            names.add(node.rest)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(None if node is function else node.name)
    return frozenset(name for name in names if name)


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
    """Return a body's structure with bound names renamed, or None for an idiom or a stub.

    A test's decorators are part of its shape: parametrize data is a test's input, so two tests
    that share a body such as `assert helper(x)` but not their parameters are no copies.
    """
    copy = ast.parse(ast.unparse(function)).body[0]
    if not isinstance(copy, ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    body = ast.Module(body=_statements(copy), type_ignores=[])
    size = sum(1 for node in ast.walk(body) if not isinstance(node, ast.Module | ast.expr_context))
    if size < MINIMUM_NODES:
        return None
    # Decorators are read in the enclosing scope, so they keep every name they use.
    inputs = "".join(map(ast.dump, copy.decorator_list)) if copy.name.startswith("test_") else ""
    # One renaming for the signature and then the body, so `a - b` never equals `b - a`.
    renaming = _BoundNames(_bound(copy))
    return inputs + ast.dump(renaming.visit(copy.args)) + ast.dump(renaming.visit(body))


def _overload(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        (isinstance(item, ast.Name) and item.id == "overload")
        or (isinstance(item, ast.Attribute) and item.attr == "overload")
        for item in function.decorator_list
    )


def standalone_scripts(root: Path) -> frozenset[str]:
    """The scripts the hosted CI runs outside the project environment."""
    workflows = (root / ".github/workflows").glob("*.yml")
    return frozenset(m for path in workflows for m in _STANDALONE.findall(path.read_text("utf-8")))


def implementations(root: Path, bases: tuple[str, ...]) -> list[list[str]]:
    """Group every function whose body another function of the same deployment unit repeats.

    The package, its tools and its tests form one unit; each standalone script is a unit of its
    own, so a copy inside one script is found while a script never has to import the package.
    """
    groups: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    standalone = standalone_scripts(root)
    for base in bases:
        for path in sorted((root / base).rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            unit = relative if relative in standalone else "package"
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                    and not _overload(node)
                    and (shape := _shape(node)) is not None
                ):
                    groups[unit, shape].append(f"{relative}:{node.lineno}:{node.name}")
    return [places for places in groups.values() if len(places) > 1]


def test_no_behavior_is_implemented_twice() -> None:
    """Each repeated body names one owner that every caller imports instead."""
    assert implementations(ROOT, PRODUCT) == []


def _imported(path: Path) -> set[str]:
    """Top-level names of the modules one file imports absolutely."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def test_a_standalone_script_imports_only_the_standard_library() -> None:
    """A script run without the project environment cannot reach an owner, so it must not try."""
    scripts = standalone_scripts(ROOT)

    assert scripts
    assert {
        (script, name)
        for script in scripts
        for name in _imported(ROOT / script)
        if name not in sys.stdlib_module_names
    } == set()


def test_a_renamed_copy_is_the_same_implementation(tmp_path: Path) -> None:
    """Renamed parameters, locals and captures do not hide a copy; another callee is no copy."""
    (tmp_path / "src").mkdir()
    for name, source in (
        ("a.py", "def fail(reason):\n    raise ValueError(reason)\n"),
        ("b.py", "def _invalid(code):\n    raise ValueError(code)\n"),
        ("c.py", "def other(code):\n    raise TypeError(code)\n"),
        ("d.py", "def minus(a, b):\n    return a - b\n"),
        ("e.py", "def swapped(a, b):\n    return b - a\n"),
        (
            "f.py",
            (
                "def read(p):\n    try:\n        return p.open()\n"
                "    except OSError as error:\n        raise ValueError(p) from error\n"
            ),
        ),
        (
            "g.py",
            (
                "def load(q):\n    try:\n        return q.open()\n"
                "    except OSError as exc:\n        raise ValueError(q) from exc\n"
            ),
        ),
        ("h.py", "def name(self):\n    return self\n"),
        ("i.py", "def same(other):\n    return other\n"),
    ):
        (tmp_path / "src" / name).write_text(source, encoding="utf-8")
    # A standalone script is compared with itself only: its copy of `fail` is no package copy.
    (tmp_path / "tools").mkdir()
    script = "def a(p):\n    raise ValueError(p)\n\n\ndef b(q):\n    raise ValueError(q)\n"
    (tmp_path / "tools/s.py").write_text(script, encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    run = "run: uv run --no-project python -B -I tools/s.py\n"
    (tmp_path / ".github/workflows/w.yml").write_text(run, encoding="utf-8")

    assert implementations(tmp_path, ("src", "tools")) == [
        ["src/a.py:1:fail", "src/b.py:1:_invalid"],
        ["src/f.py:1:read", "src/g.py:1:load"],
        ["tools/s.py:1:a", "tools/s.py:5:b"],
    ]


def test_a_test_with_other_parameters_is_no_copy(tmp_path: Path) -> None:
    """Equal decorators repeat a test; other parametrize data gives the same body other input."""
    case = '@pytest.mark.parametrize("x", [{}])\ndef test_{}(x):\n    assert helper(x)\n'
    (tmp_path / "tests").mkdir()
    source = "".join(starmap(case.format, ((1, "a"), (2, "b"), (1, "c"))))
    (tmp_path / "tests/t.py").write_text(source, encoding="utf-8")

    assert implementations(tmp_path, ("tests",)) == [["tests/t.py:2:test_a", "tests/t.py:8:test_c"]]

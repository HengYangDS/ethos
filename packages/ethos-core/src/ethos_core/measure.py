"""Effective-LOC measurement — the single source of truth for the code-size hard rule.

Lives at the BOTTOM of the dependency graph (pure kernel, zero IO beyond reading a
path) so every consumer — the code-size gate, the pre-tool write-admission hook, and
CI — imports downward into ONE metric and agrees byte-for-byte.

Effective LOC = physical lines, minus:
  - blank lines
  - full-line and inline ``#`` comments
  - docstring spans (the leading string Expr of every Module/Class/Function)
  - bare string-literal expression statements (multi-line-string padding)
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _string_expr_line_spans(tree: ast.AST) -> set[int]:
    """Line numbers occupied by docstrings and bare string-literal statements."""
    spans: set[int] = set()
    # Bare string-literal expression statements anywhere. A docstring is the leading
    # bare string Expr of a module/class/function body, so this single walk already
    # covers docstrings and multi-line-string padding alike.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            end = node.value.end_lineno or node.value.lineno
            spans.update(range(node.value.lineno, end + 1))
    return spans


def effective_code_lines(path: Path) -> int:
    """Count effective code lines in a Python file (see module docstring)."""
    source = path.read_text(encoding="utf-8")
    try:
        tree: ast.AST | None = ast.parse(source)
    except SyntaxError:
        tree = None
    excluded = _string_expr_line_spans(tree) if tree is not None else set()
    count = 0
    for index, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if index in excluded:
            continue
        count += 1
    return count

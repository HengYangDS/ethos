"""Measure Python source consistently for per-file and aggregate budgets.

Count physical lines occupied by meaningful tokens, including literal data.
Exclude comments, whitespace and standalone string expressions (including
docstrings), without removing other code on those lines. Invalid Python has no
measurement. Formatting remains a separate native-tool obligation.
"""

from __future__ import annotations

import ast
import io
import tokenize
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _without_string_expressions(source: str, tree: ast.AST) -> str:
    """Mask exact AST byte spans, preserving line structure and neighboring code."""
    lines = [bytearray(line.encode("utf-8")) for line in io.StringIO(source)]
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            end = node.end_lineno or node.lineno
            for row in range(node.lineno, end + 1):
                line = lines[row - 1]
                first = node.col_offset if row == node.lineno else 0
                last = node.end_col_offset if row == end else len(line.rstrip(b"\r\n"))
                line[first:last] = b" " * (len(line[first:last]))
    return b"".join(lines).decode("utf-8")


@lru_cache(maxsize=4_096)
def effective_code_lines_for_source(source: str) -> int:
    """Count token-bearing physical lines; propagate invalid syntax to the caller."""
    source = io.StringIO(source, newline=None).read()
    masked = _without_string_expressions(source, ast.parse(source))
    excluded = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
    occupied: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(masked).readline):
        if token.type in excluded or (token.type == tokenize.OP and token.string == ";"):
            continue
        occupied.update(range(token.start[0], token.end[0] + bool(token.end[1])))
    return len(occupied)


def effective_code_lines(path: Path) -> int:
    """Count effective code lines in a Python file (see module docstring)."""
    return effective_code_lines_for_source(path.read_text(encoding="utf-8"))

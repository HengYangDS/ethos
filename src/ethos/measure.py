"""Measure source consistently for per-file and aggregate budgets.

Count physical lines occupied by meaningful tokens, including literal data.
Exclude comments, whitespace and documentation: in Python, standalone string
expressions (including docstrings), without removing other code on those lines;
in every other language, what its Pygments lexer types as a comment or
documentation, except directives, attributes and shebangs. Invalid Python has no
measurement. Formatting remains a separate native-tool obligation.

Python also has a layout-invariant count: the code tokens that remain once comments, line
structure, standalone string expressions, statement semicolons and a comma directly before a
closing bracket are removed. A reformat that keeps the syntax tree cannot move it.
"""

from __future__ import annotations

import ast
import io
import tokenize
from functools import lru_cache

from pygments.lexers import get_lexer_by_name
from pygments.token import Comment
from pygments.token import String
from pygments.token import Whitespace

_CODE_COMMENTS = (Comment.Preproc, Comment.PreprocFile, Comment.Hashbang)
_LAYOUT = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }
)
_CLOSERS = frozenset({")", "]", "}"})


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


def _code_tokens(source: str) -> list[tokenize.TokenInfo]:
    """Tokens that are code: no comment, layout, standalone string or statement semicolon."""
    source = io.StringIO(source, newline=None).read()
    masked = _without_string_expressions(source, ast.parse(source))
    return [
        token
        for token in tokenize.generate_tokens(io.StringIO(masked).readline)
        if token.type not in _LAYOUT and not (token.type == tokenize.OP and token.string == ";")
    ]


@lru_cache(maxsize=4_096)
def effective_code_lines_for_source(source: str) -> int:
    """Count token-bearing physical lines; propagate invalid syntax to the caller."""
    occupied: set[int] = set()
    for token in _code_tokens(source):
        occupied.update(range(token.start[0], token.end[0] + bool(token.end[1])))
    return len(occupied)


@lru_cache(maxsize=4_096)
def layout_invariant_code_tokens(source: str) -> int:
    """Count code tokens, without a trailing comma; propagate invalid syntax to the caller."""
    tokens = _code_tokens(source)
    return sum(
        not (
            token.type == tokenize.OP
            and token.string == ","
            and index + 1 < len(tokens)
            and tokens[index + 1].string in _CLOSERS
        )
        for index, token in enumerate(tokens)
    )


@lru_cache(maxsize=4_096)
def lexed_effective_lines(source: str, lexer: str) -> int:
    """Count physical lines that hold a token which is not whitespace, comment or documentation."""
    occupied: set[int] = set()
    line = 1
    for token, value in get_lexer_by_name(lexer, stripnl=False, ensurenl=False).get_tokens(source):
        excluded = token in Whitespace or token in String.Doc
        excluded |= token in Comment and not any(token in kind for kind in _CODE_COMMENTS)
        for index, part in enumerate(value.split("\n")):
            line += bool(index)
            if part.strip() and not excluded:
                occupied.add(line)
    return len(occupied)

"""One effective-line definition: a token that is not whitespace, a comment or documentation."""

from __future__ import annotations

import pytest

from ethos.measure import effective_code_lines_for_source
from ethos.measure import layout_invariant_code_tokens
from ethos.measure import lexed_effective_lines


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"padding"; value = 1\n', 1),
        ('"文档"; 值 = 1\n', 1),
        ('"a\u2028b"; value = 1\n', 1),
        ('"a\u2029b"; value = 1\n', 1),
        ('"documentation"\r\nvalue = 1\r\n', 1),
        ('"documentation"\rvalue = 1\r', 1),
        ('def value(): "documentation"; return 1\n', 1),
        ('(\n "documentation"\n)\nvalue = 1\n', 1),
        ('payload = """first\n# literal data\nlast"""\n', 3),
        ('payload = """first\n\nlast"""\n', 3),
        ('payload = f"""first\n# {1 + 2}\nlast"""\n', 3),
        ('payload = f"""\n;\n{value}\n"""\n', 4),
        ('# comment\n"""documentation\nmore documentation"""\nvalue = 1 # inline\n', 1),
        ('"only a string";\n', 0),
    ],
)
def test_effective_lines_preserve_code_and_literal_data(source: str, expected: int) -> None:
    """Only syntax-classified non-code is excluded, never neighboring code or string data."""
    assert effective_code_lines_for_source(source) == expected


def test_invalid_python_is_not_a_valid_size_measurement() -> None:
    """Unparseable input cannot be certified by a fallback line counter."""
    with pytest.raises(SyntaxError):
        effective_code_lines_for_source("def invalid(\n")


@pytest.mark.parametrize(
    ("lexer", "source", "expected"),
    [
        (
            "rust",
            "/// Docs.\n//! Crate.\n#[derive(Debug)]\nstruct Point;\n// note\n/** a\nb */\n",
            2,
        ),
        ("javascript", "#!/usr/bin/env node\n/* a\n b */\nconst a = 1; // x\n\n", 2),
        ("javascript", "const t = `\n${a}\n`;\n", 3),
        ("go", "package main\n// Doc.\nfunc main() {\n\t@\n}\n", 4),
        ("bash", "#!/bin/sh\r\n# comment\r\necho hi\r\n", 2),
    ],
    ids=[
        "rust-docs-and-attributes",
        "hashbang-and-comments",
        "template-lines",
        "error-token",
        "crlf",
    ],
)
def test_lexed_effective_lines_keep_one_definition(lexer: str, source: str, expected: int) -> None:
    """Comments and documentation never count; attributes, shebangs and lexer errors do."""
    assert lexed_effective_lines(source, lexer) == expected


@pytest.mark.parametrize(
    ("wrapped", "joined"),
    [
        ("value = call(\n    first,\n    second,\n)\n", "value = call(first, second)\n"),
        ("items = [\n    1,\n    2,\n]\n", "items = [1, 2]\n"),
        ("def f(\n    a,\n    b,\n):\n    return a\n", "def f(a, b):\n    return a\n"),
    ],
)
def test_layout_invariant_tokens_ignore_wrapping_and_trailing_commas(
    wrapped: str, joined: str
) -> None:
    """A formatter collapse keeps the count that the Python source budget enforces (DR-0019)."""
    assert effective_code_lines_for_source(wrapped) > effective_code_lines_for_source(joined)
    assert layout_invariant_code_tokens(wrapped) == layout_invariant_code_tokens(joined)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"""documentation"""\n# comment\n', 0),
        ("value = 1;\n", 3),
        ('def f():\n    "doc"\n    return (1,)\n', 9),
    ],
)
def test_layout_invariant_tokens_count_code_only(source: str, expected: int) -> None:
    """Comments, docstrings, statement semicolons and a comma before a closer count nothing."""
    assert layout_invariant_code_tokens(source) == expected


def test_invalid_python_has_no_token_count() -> None:
    """The token count fails like the line count rather than measure broken source."""
    with pytest.raises(SyntaxError):
        layout_invariant_code_tokens("def invalid(\n")

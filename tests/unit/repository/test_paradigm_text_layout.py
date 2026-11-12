"""One canonical layout for authored text that no native formatter owns."""

from __future__ import annotations

import pytest

from ethos.repository.paradigm.text_layout import canonical_text
from ethos.repository.paradigm.text_layout import text_layout_violation

_REPAIRED = {
    "doubled-blank": ("build/\n\n\n*.log\n", "build/\n\n*.log\n", 2),
    "leading-blank": ("\n\nbuild/\n", "build/\n", 0),
    "trailing-blank": ("build/\n\n\n", "build/\n", 1),
    "no-final-newline": ("0.2.0", "0.2.0\n", 0),
    "whitespace-only-line": ("a = 1\n  \nb = 2\n", "a = 1\n\nb = 2\n", 1),
}


@pytest.mark.parametrize(
    ("authored", "canonical", "line"), _REPAIRED.values(), ids=_REPAIRED.keys()
)
def test_canonical_text_repairs_each_blank_line_shape(
    authored: str, canonical: str, line: int
) -> None:
    """Each shape is found at its first differing line and repaired to a fixed point."""
    assert text_layout_violation(authored) == line
    assert canonical_text(authored) == canonical
    assert canonical_text(canonical) == canonical
    assert text_layout_violation(canonical) is None


@pytest.mark.parametrize("text", ["", "build/\n", "a\n\nb\n", "pattern\\ \n"])
def test_canonical_text_keeps_conforming_text_and_content_lines(text: str) -> None:
    """An empty file stays empty, and a content line's own bytes are never changed."""
    assert canonical_text(text) == text
    assert text_layout_violation(text) is None

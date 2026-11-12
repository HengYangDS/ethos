"""One canonical layout for authored text that no native formatter owns.

A whitespace-only line is emptied, blank lines at the start and the end are dropped, one blank line
is kept from each run, and a non-empty text ends with one newline. Content lines keep their bytes:
a `.gitignore` pattern can end in an escaped space.
"""

from __future__ import annotations


def canonical_text(text: str) -> str:
    """Return the text in its canonical layout; an empty text stays empty."""
    kept: list[str] = []
    for line in text.split("\n"):
        blank = not line.strip()
        if blank and (not kept or not kept[-1]):
            continue
        kept.append("" if blank else line)
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept) + "\n" if kept else ""


def text_layout_violation(text: str) -> int | None:
    """Return the zero-based line where the text first leaves its canonical layout, or None."""
    canonical = canonical_text(text)
    if canonical == text:
        return None
    lines, wanted = text.split("\n"), canonical.split("\n")
    return next(
        (
            index
            for index, (line, kept) in enumerate(zip(lines, wanted, strict=False))
            if line != kept
        ),
        min(len(lines), len(wanted)) - 1,
    )

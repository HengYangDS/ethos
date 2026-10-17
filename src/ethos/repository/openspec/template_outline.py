"""Compare official OpenSpec artifacts with the literal outline of their resolved templates."""

from __future__ import annotations

from typing import Literal
from typing import NamedTuple

from markdown_it import MarkdownIt

OutlineGapKind = Literal["missing", "misplaced", "misordered"]

_LEVELS = {"h1": 1, "h2": 2, "h3": 3}


class OutlineHeading(NamedTuple):
    """One second- or third-level heading and the second-level heading containing it."""

    level: int
    text: str
    parent: str

    @property
    def path(self) -> str:
        """Name the heading by its template position."""
        return f"{self.parent} > {self.text}" if self.parent else self.text


def markdown_outline(markdown: str) -> tuple[OutlineHeading, ...]:
    """Return actual CommonMark headings, never fenced pseudo-structure."""
    headings: list[OutlineHeading] = []
    parent, level = "", 0
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type == "heading_open":
            level = _LEVELS.get(token.tag, 0)
        elif token.type == "heading_close":
            level = 0
        elif token.type == "inline" and level:
            text = " ".join(token.content.split())
            if level < 3:
                parent = text if level == 2 else ""
            if level > 1:
                headings.append(OutlineHeading(level, text, parent if level == 3 else ""))
    return tuple(headings)


def template_outline(markdown: str) -> tuple[OutlineHeading, ...]:
    """Return the literal headings of a template; an HTML comment marks a placeholder."""
    return tuple(
        heading
        for heading in markdown_outline(markdown)
        if "<!--" not in heading.text and "<!--" not in heading.parent
    )


def outline_gaps(
    template: tuple[OutlineHeading, ...], artifact: tuple[OutlineHeading, ...]
) -> tuple[tuple[OutlineGapKind, str], ...]:
    """Return each template heading that is absent, under another parent, or out of order."""
    positions: dict[int, int] = {}
    gaps: dict[int, OutlineGapKind] = {}
    for index, required in enumerate(template):
        named = [
            position for position, heading in enumerate(artifact) if heading.text == required.text
        ]
        placed = [
            position
            for position in named
            if (artifact[position].level, artifact[position].parent)
            == (required.level, required.parent)
        ]
        if placed:
            positions[index] = placed[0]
        else:
            gaps[index] = "misplaced" if named else "missing"
    ordered = _longest_increasing(positions)
    gaps.update(dict.fromkeys(set(positions) - ordered, "misordered"))
    return tuple((gaps[index], template[index].path) for index in sorted(gaps))


def _longest_increasing(positions: dict[int, int]) -> set[int]:
    """Keep the largest set of placed headings that already follow template order."""
    indexes = sorted(positions)
    chains: dict[int, tuple[int, ...]] = {}
    for index in indexes:
        earlier = [
            chains[previous]
            for previous in indexes
            if previous < index and positions[previous] < positions[index]
        ]
        chains[index] = (*max(earlier, key=len, default=()), index)
    return set(max(chains.values(), key=len, default=()))

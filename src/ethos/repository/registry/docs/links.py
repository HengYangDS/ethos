"""Native Markdown links used by documentation registry navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from pathlib import Path

_MARKDOWN = MarkdownIt("commonmark")


def markdown_links(path: Path) -> list[tuple[int, str]]:
    """Return rendered link destinations with their native block source line."""
    links: list[tuple[int, str]] = []
    for token in _MARKDOWN.parse(path.read_text(encoding="utf-8")):
        if token.type != "inline" or token.map is None:
            continue
        links.extend(
            (token.map[0] + 1, target)
            for child in token.children or ()
            if child.type == "link_open"
            and isinstance(target := child.attrGet("href"), str)
            and target
        )
    return links

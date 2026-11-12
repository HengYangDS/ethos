"""One blank-line rule for Markdown list items, decided from the CommonMark structure.

Inside a list item, a paragraph that follows another block, and any block that follows a block
that is not a paragraph, is separated from it by one blank line; a block that follows the
paragraph that introduces it follows directly. An item that holds such a separator is spread, and
one blank line follows it before the next item; every other item is followed directly by the next
one. Prettier writes the separator after a spread item but keeps a stray one after any other item,
which makes the whole list loose in CommonMark; this rule removes it.
"""

from __future__ import annotations

import re
from itertools import pairwise
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from markdown_it.token import Token

_PARSER = MarkdownIt("commonmark")
_LISTS = frozenset({"bullet_list_open", "ordered_list_open"})
_QUOTE = re.compile(r"^(?:[ \t]*>)+")


def _blank(line: str) -> bool:
    """Name a separator line: empty once its blockquote markers and whitespace are removed."""
    return not line.replace(">", "").strip()


def _children(tokens: list[Token], start: int) -> list[tuple[int, int, str]]:
    """Return each direct child block of the container at `start`: index, first line, type."""
    level = tokens[start].level + 1
    children: list[tuple[int, int, str]] = []
    for index in range(start + 1, len(tokens)):
        token = tokens[index]
        if token.level < level:
            break
        if token.level == level and token.map is not None and token.nesting >= 0:
            children.append((index, token.map[0], token.type))
    return children


def _item_separators(tokens: list[Token], item: int, wanted: dict[int, int]) -> bool:
    """Record the blank lines each block of one item needs; return whether the item is spread."""
    blocks = _children(tokens, item)
    spread = False
    for (_index, _line, before), (_next, line, kind) in pairwise(blocks):
        separated = kind == "paragraph_open" or before != "paragraph_open"
        wanted[line] = int(separated)
        spread = spread or separated
    return spread


def _wanted(tokens: list[Token]) -> dict[int, int]:
    """Map each block start inside or between list items to the blank lines it needs."""
    wanted: dict[int, int] = {}
    for start, token in enumerate(tokens):
        if token.type not in _LISTS:
            continue
        previous_spread: bool | None = None
        for index, line, kind in _children(tokens, start):
            if kind != "list_item_open":
                continue
            if previous_spread is not None:
                wanted[line] = int(previous_spread)
            previous_spread = _item_separators(tokens, index, wanted)
    return wanted


def spacing_violations(text: str) -> dict[int, int]:
    """Map each zero-based line whose preceding blank lines break the rule to the wanted count."""
    lines = text.split("\n")
    violations: dict[int, int] = {}
    for line, count in _wanted(_PARSER.parse(text)).items():
        blanks = 0
        while line - blanks > 0 and _blank(lines[line - blanks - 1]):
            blanks += 1
        if blanks != count:
            violations[line] = count
    return violations


def canonical_spacing(text: str) -> str:
    """Apply the rule; every blank line outside list items stays as the formatter wrote it."""
    lines = text.split("\n")
    for line, count in sorted(spacing_violations(text).items(), reverse=True):
        first = line
        while first > 0 and _blank(lines[first - 1]):
            first -= 1
        quote = _QUOTE.match(lines[line])
        marker = ">" * quote.group(0).count(">") if quote else ""
        lines[first:line] = [marker] * count
    return "\n".join(lines)

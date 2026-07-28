"""Minimal Markdown parsing used by docs registry plan discovery."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def markdown_links(path: Path) -> list[tuple[int, str]]:
    """Extract Markdown links from a document."""
    links: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in MARKDOWN_LINK.finditer(line):
            target = match.group(1).strip()
            if not target or target.startswith("<"):
                continue
            target = target.split(None, 1)[0]
            links.append((lineno, target))
    return links

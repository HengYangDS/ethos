"""Minimal Markdown parsing used by docs registry plan discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.references.markdown import markdown_tokens

if TYPE_CHECKING:
    from pathlib import Path


def markdown_links(path: Path) -> list[tuple[int, str]]:
    """Read actual link nodes, including references, without counting literals."""
    tokens = markdown_tokens(path.read_text(encoding="utf-8"))
    if tokens is None:
        return []
    return [
        (token.map[0] + 1 if token.map else 1, target)
        for token in tokens
        if token.type == "inline"
        for child in token.children or ()
        if child.type == "link_open" and isinstance(target := child.attrGet("href"), str) and target
    ]

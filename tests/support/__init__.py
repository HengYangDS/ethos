"""Shared test helpers for ETHOS product tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def write_text(path: Path, text: str = "") -> None:
    """Create parent directories and write UTF-8 fixture text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

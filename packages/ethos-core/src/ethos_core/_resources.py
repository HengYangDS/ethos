"""Canonical-system declaration loading with packaged-wheel fallback."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_SOURCE_FILE = Path(__file__).resolve()


def declaration_text(path: Path, *, resource: str, canonical: Path) -> str:
    """Read a requested declaration, then wheel resource, then checkout source."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    try:
        return resources.files("ethos_core").joinpath(resource).read_text(encoding="utf-8")
    except FileNotFoundError:
        for parent in _SOURCE_FILE.parents:
            source = parent / canonical
            if source.is_file():
                return source.read_text(encoding="utf-8")
    msg = f"declaration resource unavailable: {resource}"
    raise FileNotFoundError(msg)

"""Canonical-system declaration loading with packaged-wheel fallback."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_SOURCE_FILE = Path(__file__).resolve()


def resolve_declaration_path(path: Path | str | None, *, canonical: Path, module_file: str) -> Path:
    """Prefer an explicit declaration or discover its checkout default."""
    if path is not None:
        return Path(path)
    cwd_candidate = Path.cwd() / canonical
    if cwd_candidate.exists():
        return cwd_candidate
    for parent in Path(module_file).resolve().parents:
        candidate = parent / canonical
        if candidate.exists():
            return candidate
    return canonical


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

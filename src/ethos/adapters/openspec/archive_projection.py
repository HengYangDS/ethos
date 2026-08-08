"""Canonicalize repository-owned text projected by an OpenSpec archive."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath


def normalize_projected_specs(root: Path, *, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Give changed canonical Markdown specs exactly one terminal newline."""
    normalized: list[str] = []
    for relative in dict.fromkeys(paths):
        path = PurePosixPath(relative)
        if not _canonical_markdown_spec(path):
            continue
        target = root.joinpath(*path.parts)
        try:
            content = target.read_bytes()
        except OSError:
            continue
        canonical = content.rstrip(b"\n") + b"\n"
        if canonical == content:
            continue
        target.write_bytes(canonical)
        normalized.append(relative)
    return tuple(normalized)


def _canonical_markdown_spec(path: PurePosixPath) -> bool:
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and len(path.parts) >= 4
        and path.parts[:2] == ("openspec", "specs")
        and path.name == "spec.md"
    )

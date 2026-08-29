"""Recognize official OpenSpec archive roots and exact Git relocations."""

from __future__ import annotations

import hashlib

from ethos.repository.openspec.identifiers import OPEN_SPEC_ARCHIVE_ROOT
from ethos.repository.openspec.identifiers import parse_archived_change_root


def archived_change_from_path(path: str) -> tuple[str, str] | None:
    """Return the official archive root and logical Change containing ``path``."""
    prefix = f"{OPEN_SPEC_ARCHIVE_ROOT}/"
    if not path.startswith(prefix):
        return None
    parts = path.split("/", 4)
    candidate = "/".join(parts[:4]) if len(parts) >= 4 else path
    parsed = parse_archived_change_root(candidate)
    if parsed is None:
        return None
    return candidate, parsed[0]


def archive_root_from_path(path: str, change: str) -> str:
    """Return the official archive root containing ``path`` or ``""``."""
    parsed = archived_change_from_path(path)
    return parsed[0] if parsed is not None and parsed[1] == change else ""


def collision_preservation_path(path: str, tree: str, head: str) -> str:
    """Return the deterministic immutable preservation path for a collision."""
    suffix = hashlib.sha256(f"{tree}\0{head}".encode()).hexdigest()[:12]
    return f"{path}-{suffix}"

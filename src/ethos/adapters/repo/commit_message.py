"""Deterministic subjects for OpenSpec lifecycle commits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

if TYPE_CHECKING:
    from pathlib import Path

LifecycleAction = Literal["archive", "materialize", "start"]


def lifecycle_commit_subject(_root: Path, action: LifecycleAction, change: str) -> str:
    """Return the repository-independent lifecycle commit subject."""
    return f"chore(openspec): {action} {change}"

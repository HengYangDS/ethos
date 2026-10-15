"""The gap record and tracked-carrier reader that every paradigm obligation shares."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import NamedTuple

if TYPE_CHECKING:
    from pathlib import Path


class ParadigmGap(NamedTuple):
    """One paradigm gap with its carrier, violated obligation and canonical repair."""

    obligation: str
    carrier: str
    repair: str

    @property
    def required_gap(self) -> str:
        """Return the stable gap identity that proof, land and publish report."""
        return f"repository_paradigm_{self.obligation.replace('-', '_')}:{self.carrier}"


def tracked_text(root: Path, path: str, tracked: frozenset[str]) -> str | None:
    """Read one tracked carrier as UTF-8 text, or return None when it is absent or unreadable."""
    if path not in tracked:
        return None
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

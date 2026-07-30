"""OpenSpec-carrier admission gaps for a mutation transition role."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.repository.openspec.audit import active_change_violations_for_role

if TYPE_CHECKING:
    from pathlib import Path


def openspec_carrier_gaps(root: Path, role: str) -> list[str]:
    """Blocking gaps when OpenSpec carriers are illegal for a transition role.

    Work Lanes may carry active OpenSpec changes. Candidate and
    accepted-root checkouts may not retain any active carrier: after promotion
    the current truth belongs in source, canonical specs, and Attestations.
    """
    if not openspec_profile_enabled(root):
        return []
    openspec_root = root / "openspec"
    return active_change_violations_for_role(openspec_root, role)

"""OpenSpec-carrier admission gaps for a mutation transition role.

Split out of mutation.core to keep it under the logic-role size budget: this is the
self-contained "may this role still carry active OpenSpec changes?" rule, consumed by
evaluate_mutation / evaluate_closeout_mutation / the candidate closeout check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.openspec.audit import active_change_violations_for_role
from ethos.repository.openspec.audit import completed_unarchived_changes

if TYPE_CHECKING:
    from pathlib import Path


def openspec_carrier_gaps(root: Path, role: str) -> list[str]:
    """Blocking gaps when OpenSpec carriers are illegal for a transition role.

    Work Lanes may carry active in-progress OpenSpec changes. Candidate and
    accepted-root checkouts may not retain any active carrier: after promotion
    the current truth belongs in source, canonical specs, claims, evidence, and
    chronicle.
    """
    openspec_root = root / "openspec"
    completed_gaps = completed_unarchived_changes(openspec_root)
    completed_names = {gap.rsplit(":", 1)[-1] for gap in completed_gaps}
    active_gaps = [
        gap
        for gap in active_change_violations_for_role(openspec_root, role)
        if gap.split(":", 2)[1] not in completed_names
    ]
    return [*active_gaps, *completed_gaps]

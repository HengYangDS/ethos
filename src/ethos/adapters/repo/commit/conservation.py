"""Observe accepted contribution identity through native history and rewrite evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.rewrite import refreshed_object_provenance
from ethos.adapters.repo.commit.signature import repaired_object_provenance
from ethos.adapters.repo.git import is_ancestor
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def accepted_contribution(root: Path, old: str, accepted: str) -> dict[str, object]:
    """Require ancestry or conserved native rewrite provenance, never patch-id."""
    if is_ancestor(root, old, accepted):
        return {"verdict": "pass", "state": "ancestor", "old": old, "replacement": old}
    repair = repaired_object_provenance(root, old=old, new=accepted)
    if repair is not None:
        mapping = cast("Mapping[str, str]", repair["mapping"])
        return {
            "verdict": "pass",
            "state": "repaired",
            "old": old,
            "replacement": mapping[old],
            "attestation_id": repair["attestation_id"],
        }
    report = refreshed_object_provenance(root, old=old, new=accepted) or {
        "state": "not_absorbed",
        "old": old,
    }
    conservation = report.get("conservation")
    verdict = (
        "pass"
        if report["state"] == "refreshed"
        else "unknown"
        if isinstance(conservation, dict) and report_verdict(conservation) == "unknown"
        else "block"
    )
    return report | {"verdict": verdict}

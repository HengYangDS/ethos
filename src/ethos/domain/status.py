"""Status-stage domain reducers and audit orchestration.

Pure reducers plus the
repository/adopter audit composition (audit_for_root and friends), which orchestrate
lower-layer reports. Imports flow downward only (ethos.repository/ethos.adapters/
ethos.contracts), keeping the surface→domain→... layering acyclic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.repository.audit as repository_audit_module
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.context import context_for_root
from ethos.repository.context import is_product_root

if TYPE_CHECKING:
    from pathlib import Path


def audit_for_root(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
    """Dispatch to the product-repository or adopter audit for the given root."""
    if is_product_root(root):
        return product_repository_audit(root, openspec_mode=openspec_mode)
    return adopter_audit(root)


def product_repository_audit(root: Path, *, openspec_mode: str) -> dict[str, object]:
    """Run the product repository audit (deep openspec validation when requested)."""
    reporter = openspec_governance_report if openspec_mode == "deep" else None
    return repository_audit_module.repository_audit(
        root,
        openspec_mode=openspec_mode,
        openspec_reporter=reporter,
    )


def adopter_audit(root: Path) -> dict[str, object]:
    """Validate only the one adopter binding; capabilities remain explicit opt-ins."""
    adopter = inspect_adopter(root)
    gaps = list(cast("list[str]", adopter["required_gaps"]))
    capabilities = cast("dict[str, dict[str, bool]]", adopter["adopter"])["capabilities"]
    return {
        "ok": not gaps,
        "mode": "repository",
        "governance_context": context_for_root(root),
        "required_gaps": gaps,
        "adopter": adopter,
        "openspec": {
            "ok": True,
            "mode": "adopter-shape",
            "configured": bool(capabilities["openspec"]),
            "required_gaps": [],
        },
    }


def status_worktree_gaps(status: dict[str, object]) -> list[str]:
    """Collect blocking gaps from a workspace-status payload (drop lease-only noise)."""
    gaps = [
        str(gap)
        for gap in cast("list[object]", status.get("required_gaps", []))
        if str(gap) and not str(gap).startswith("work_lane_missing_lease:")
    ]
    closeout = status.get("closeout_support")
    if isinstance(closeout, dict):
        gaps.extend(
            str(gap)
            for gap in cast("list[object]", closeout.get("required_gaps", []))
            if str(gap) and not str(gap).startswith("work_lane_missing_lease:")
        )
    return list(dict.fromkeys(gaps))

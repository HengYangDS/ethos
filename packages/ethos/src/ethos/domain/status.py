"""Status-stage domain reducers and audit orchestration.

Pure reducers (string_list, adoption_mutation_gaps, status_worktree_gaps) plus the
repository/adopter audit composition (audit_for_root and friends), which orchestrate
lower-layer reports. Imports flow downward only (ethos.repository/ethos.adapters/
ethos_core.contracts), keeping the surface→domain→... layering acyclic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.repository.audit as repository_audit_module
from ethos.adapters.openspec.core import openspec_governance_report
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.adoption.planner import detect_repo_profile
from ethos.repository.context import governance_context
from ethos.repository.evidence.claims import claims_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.docs import docs_health_report

if TYPE_CHECKING:
    from pathlib import Path


def string_list(value: object) -> list[str]:
    """Coerce an arbitrary value to list[str] (empty if not a list)."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def adoption_mutation_gaps(
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    current_head: str,
) -> tuple[str, ...]:
    """Derive adoption-mutation precondition gaps (empty when not applying)."""
    if not apply:
        return ()
    gaps: list[str] = []
    if not authorize:
        gaps.append("authorization_required")
    if current_head == "untracked":
        gaps.append("git_repository_missing")
    if not expect_head:
        gaps.append("expect_head_required")
    elif expect_head != current_head:
        gaps.append("expected_head_mismatch")
    return tuple(gaps)


def is_product_root(root: Path) -> bool:
    """True when root is the ETHOS product repository (has packages/ethos + kernel schemas)."""
    return (root / "packages" / "ethos" / "README.md").exists() and (
        root / "system" / "schemas" / "kernel"
    ).exists()


def audit_for_root(
    root: Path, *, openspec_mode: str = "shape", current_head: str = ""
) -> dict[str, object]:
    """Dispatch to the product-repository or adopter audit for the given root."""
    if is_product_root(root):
        return product_repository_audit(
            root, openspec_mode=openspec_mode, current_head=current_head
        )
    return adopter_audit(root)


def product_repository_audit(
    root: Path, *, openspec_mode: str, current_head: str = ""
) -> dict[str, object]:
    """Run the product repository audit (deep openspec validation when requested)."""
    reporter = openspec_governance_report if openspec_mode == "deep" else None
    return repository_audit_module.repository_audit(
        root,
        openspec_mode=openspec_mode,
        openspec_reporter=reporter,
        current_head=current_head,
    )


def adopter_audit(root: Path) -> dict[str, object]:
    """Compose the adopter-repository audit (adopter + schema + claims + docs)."""
    adopter = inspect_adopter(root)
    schemas = schema_validation_report(root)
    claims = claims_report(root)
    docs = docs_health_report(root)
    gaps = list(cast("list[str]", adopter["required_gaps"])) + [
        f"schema:{gap}" for gap in cast("list[str]", schemas["required_gaps"])
    ]
    adopter_governance = cast("dict[str, dict[str, bool]]", adopter["adopter"])["governance"]
    adopter_openspec = bool(adopter_governance["openspec"])
    return {
        "ok": not gaps,
        "mode": "repository",
        "governance_context": governance_context(
            root,
            profile=detect_repo_profile(root),
        ),
        "required_gaps": gaps,
        "adopter": adopter,
        "schemas": {
            "ok": bool(schemas["ok"]),
            "validation": schemas,
            "missing": [],
        },
        "claims": claims,
        "docs": docs,
        "openspec": {
            "ok": adopter_openspec,
            "mode": "adopter-shape",
            "required_gaps": [] if adopter_openspec else ["adopter_missing:openspec"],
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

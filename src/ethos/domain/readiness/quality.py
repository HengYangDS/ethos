"""Singular hard-quality owner shared by lifecycle commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.gates.tool import module_layout_gate_report
from ethos.adapters.gates.ty import ty_gate_report
from ethos.domain.prove import code_size_report
from ethos.domain.source_budget.core import source_budget_report
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.coverage import coverage_quality_report
from ethos.repository.policy.docstrings.core import docstring_coverage_report

if TYPE_CHECKING:
    from pathlib import Path


def hard_quality_floor_report(repo: Path) -> dict[str, object]:
    """Return every hard product quality verdict without score mediation."""
    gates = {
        "python-size": code_size_report(repo),
        "source-budget": source_budget_report(repo),
        "coverage": coverage_quality_report(repo),
        "types": ty_gate_report(repo),
        "docstrings": docstring_coverage_report(repo),
        "module-layout": module_layout_gate_report(repo),
        "generated-artifacts": generated_artifact_topology_report(repo),
        "product-boundary": product_boundary_report(repo),
        "contributor-policy": contributor_policy_report(repo),
    }
    required_gaps = [
        gap for report in gates.values() for gap in cast("list[str]", report["required_gaps"])
    ]
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "required_gaps": required_gaps,
        "gates": gates,
    }


def adopter_quality_floor_report() -> dict[str, object]:
    """Keep adopter gates profile-owned rather than imposing ETHOS internals."""
    return {"ok": True, "state": "profile_deferred", "required_gaps": [], "gates": {}}

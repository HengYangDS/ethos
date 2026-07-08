from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.topology import evidence_topology_report

if TYPE_CHECKING:
    from pathlib import Path


def evidence_freshness_report(root: Path) -> dict[str, Any]:
    """Compose claim, evolution, and evidence-topology freshness checks.

    Args:
        root: Repository root to inspect.

    Returns:
        A read-only report for the public evidence freshness quality gate.
    """
    claim_report = claims_report(root)
    evolution = evolution_report(root)
    topology = evidence_topology_report(root)
    required_gaps = (
        tuple(cast("list[str]", claim_report["required_gaps"]))
        + tuple(cast("list[str]", evolution["required_gaps"]))
        + tuple(cast("list[str]", topology["required_gaps"]))
    )
    return {
        "ok": bool(claim_report["ok"]) and bool(evolution["ok"]) and bool(topology["ok"]),
        "summary": {
            "evidence_roots": ["evidence"],
            "evolution_active_count": evolution["active_count"],
            "topology_issue_count": len(topology["required_gaps"]),
        },
        "required_gaps": list(required_gaps),
        "data": {
            "stale": [],
            "claims": claim_report,
            "evolution": evolution,
            "topology": topology,
        },
    }

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.repo.git as git_adapter
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity.core import parity_gaps_report
from ethos.repository.evidence.shadow.routing import parity_evidence_path
from ethos.repository.evidence.topology import evidence_topology_report
from ethos.repository.profile import profile_relative_root

if TYPE_CHECKING:
    from pathlib import Path


def evidence_freshness_report(root: Path, *, current_head: str = "") -> dict[str, Any]:
    """Compose claim, evolution, and evidence-topology freshness checks.

    Args:
        root: Repository root to inspect.
        current_head: Git HEAD used to classify active claim freshness.

    Returns:
        A read-only report for the public evidence freshness quality gate.
    """
    head = current_head or git_adapter.current_tracked_head(root)
    claim_report = claims_report(root, current_head=head)
    evolution = evolution_report(root)
    topology = evidence_topology_report(root)
    evidence_root = profile_relative_root(root, "durable_evidence")
    parity = _generic_parity_freshness(root=root, current_head=head)
    parity_gaps = tuple(cast("list[str]", parity["required_gaps"]))
    required_gaps = (
        tuple(cast("list[str]", claim_report["required_gaps"]))
        + tuple(cast("list[str]", evolution["required_gaps"]))
        + tuple(cast("list[str]", topology["required_gaps"]))
        + parity_gaps
    )
    return {
        "ok": (
            bool(claim_report["ok"])
            and bool(evolution["ok"])
            and bool(topology["ok"])
            and bool(parity["ok"])
        ),
        "summary": {
            "evidence_roots": [evidence_root],
            "current_head": head,
            "evolution_active_count": evolution["active_count"],
            "topology_issue_count": len(topology["required_gaps"]),
            "parity_issue_count": len(parity_gaps),
        },
        "required_gaps": list(required_gaps),
        "data": {
            "stale": list(parity_gaps),
            "claims": claim_report,
            "evolution": evolution,
            "topology": topology,
            "parity": parity,
        },
    }


def _generic_parity_freshness(*, root: Path, current_head: str) -> dict[str, object]:
    """Return generic parity freshness when this repository tracks that evidence.

    Generic parity is a product proof input only after the repository has opted
    into its tracked evidence carrier. A missing carrier remains the parity
    command's concern, which keeps profile fixtures and repositories without the
    product parity capability out of an unrelated quality gate.
    """
    evidence_path = parity_evidence_path(root=root, adopter="generic")
    if not evidence_path.exists():
        return {
            "ok": True,
            "state": "not_configured",
            "required_gaps": [],
            "evidence_path": evidence_path.relative_to(root).as_posix(),
        }
    return parity_gaps_report(
        adopter="generic",
        root=root,
        target=root,
        current_product_head=current_head,
        current_target_head=current_head,
    )

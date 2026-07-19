from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity.core import parity_gaps_report
from ethos.repository.evidence.shadow.routing import parity_evidence_path
from ethos.repository.evidence.topology import evidence_topology_report
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps
from ethos_core.contracts.evidence.layout import load_evidence_layout_declaration

if TYPE_CHECKING:
    from pathlib import Path


def evidence_freshness_report(root: Path, *, current_head: str) -> dict[str, Any]:
    """Compose claim, evolution, and evidence-topology freshness checks.

    Args:
        root: Repository root to inspect.
        current_head: Caller-supplied Git HEAD used to classify active claim freshness.

    Returns:
        A read-only report for the public evidence freshness quality gate.
    """
    head = current_head
    declaration = load_evidence_layout_declaration()
    reports = {
        "claims": claims_report(root, current_head=head),
        "evolution": evolution_report(root),
        "topology": evidence_topology_report(root),
        "parity": _generic_parity_freshness(root=root, current_head=head),
    }
    profile = load_repository_profile(root)
    evidence_root = (
        profile.declaration.roots.durable_evidence if profile.declaration else "evidence"
    )
    components = tuple(
        cast("dict[str, object]", {"ok": bool(report["ok"])}) for report in reports.values()
    )
    required_gaps = (
        *profile_required_gaps(profile),
        *tuple(
            gap for report in reports.values() for gap in cast("list[str]", report["required_gaps"])
        ),
    )
    parity_gaps = cast("list[str]", reports["parity"]["required_gaps"])
    return {
        "ok": declaration.freshness_ok(components) and not required_gaps,
        "summary": {
            "evidence_roots": [evidence_root],
            "current_head": head,
            "evolution_active_count": reports["evolution"]["active_count"],
            "topology_issue_count": len(cast("list[str]", reports["topology"]["required_gaps"])),
            "parity_issue_count": len(parity_gaps),
        },
        "required_gaps": list(required_gaps),
        "data": {
            "stale": parity_gaps,
            **reports,
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

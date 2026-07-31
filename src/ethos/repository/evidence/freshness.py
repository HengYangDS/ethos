from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.contracts.evidence.layout import load_evidence_layout_declaration
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.repository.evidence.topology import evidence_topology_report
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

if TYPE_CHECKING:
    from pathlib import Path


def evidence_freshness_report(root: Path, *, current_head: str) -> dict[str, Any]:
    """Compose evidence-topology freshness checks.

    Args:
        root: Repository root to inspect.
        current_head: Caller-supplied Git HEAD reported with the current observation.

    Returns:
        A read-only report for the public evidence freshness quality gate.
    """
    head = current_head
    declaration = load_evidence_layout_declaration()
    topology = evidence_topology_report(root)
    profile = load_repository_profile(root)
    evidence_root = (
        profile.declaration.roots.durable_evidence if profile.declaration else "evidence"
    )
    topology_verdict = report_verdict(topology)
    components = (cast("dict[str, object]", {"verdict": topology_verdict}),)
    topology_warnings = tuple(str(item) for item in topology.get("warnings", ()) if str(item))
    profile_gaps = profile_required_gaps(profile)
    required_gaps = (
        *profile_gaps,
        *cast("list[str]", topology["required_gaps"]),
    )
    freshness_ok = declaration.freshness_ok(components)
    if topology_verdict == "pass" and not freshness_ok and not required_gaps:
        required_gaps = (*required_gaps, "evidence_freshness_policy_failed")
    freshness_verdict = (
        "pass" if freshness_ok else "unknown" if topology_verdict == "unknown" else "block"
    )
    return {
        "verdict": reduce_verdicts(
            "block" if profile_gaps else "pass",
            topology_verdict,
            freshness_verdict,
            required_gaps=tuple(required_gaps),
            warnings=topology_warnings,
        ),
        "warnings": list(topology_warnings),
        "summary": {
            "evidence_roots": [evidence_root],
            "current_head": head,
            "topology_issue_count": len(cast("list[str]", topology["required_gaps"])),
        },
        "required_gaps": list(required_gaps),
        "data": {"topology": topology},
    }

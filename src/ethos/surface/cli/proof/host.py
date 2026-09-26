"""Host-only gate observation without repository proof authority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import observe_gate_execution
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


def host_probe_boundary(*, host: bool, probe: bool) -> dict[str, object]:
    """Describe optional host-readiness flags without minting proof truth."""
    return {
        "requested": host or probe,
        "host": host,
        "probe": probe,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "not_requested" if not (host or probe) else "boundary_recorded",
    }


def host_gate_observation(
    *, repo: Path, gate_ids: tuple[str, ...], expect_head: str | None, full: bool = False
) -> EthosResult:
    """Execute focused gates without repository lifecycle or Attestation authority."""
    observed = observe_gate_execution(repo, gate_ids=gate_ids, full=full, expect_head=expect_head)
    checks, required_gaps = observed["checks"], tuple(observed["required_gaps"])
    current_head, verdict = observed["head"], observed["verdict"]
    return EthosResult(
        command="prove",
        verdict=verdict,
        state="observed" if verdict == "pass" else "gapped",
        summary={
            "boundary": "host",
            "gate_count": len(checks),
            "proof_attestation_issued": False,
        },
        required_gaps=required_gaps,
        next_action="repair the selected host gate" if required_gaps else "",
        data={
            "executed": bool(checks),
            "execution_source": observed["execution_source"],
            "policy_digest": observed["policy_digest"],
            "boundary": "host",
            "host_probe": host_probe_boundary(host=True, probe=False),
            "checks": checks,
            "attestation": {},
            "expected_head": {
                "expected": expect_head or "",
                "current": current_head,
                "matches": expect_head is None or expect_head == current_head,
            },
        },
    )

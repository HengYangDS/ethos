"""Mutation request and decision-envelope contracts."""

from __future__ import annotations

from typing import Literal

from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.admission import DecisionBasis
from ethos_core.contracts.admission import MutationSubject
from ethos_core.contracts.lifecycle.core import MutationEvaluation
from ethos_core.contracts.lifecycle.core import MutationRequest

MutationVerdict = Literal["allow", "block", "defer"]

__all__ = ["MutationEvaluation", "MutationRequest", "mutation_envelope"]


def mutation_envelope(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    request: MutationRequest,
    *,
    action: str,
    resource: str,
    expected_state: dict[str, object],
    verdict: MutationVerdict,
    required_gaps: tuple[str, ...] = (),
    why: tuple[str, ...] = (),
    next_actions: tuple[str, ...] = (),
    state: str = "",
    identity_basis: str = "not_evaluated",
    evidence_boundary: str = "current_local_observation",
    enforcement_boundary: str = "local_process_guard",
    verifier_provenance: str = "current_runner",
) -> dict[str, object]:
    """Build the canonical exact-request mutation envelope."""
    decision = AdmissionDecision(
        verdict=verdict,
        subject=MutationSubject(
            action=action,
            resource=resource,
            expected_state=expected_state,
        ),
        policy_refs=(f"commitment:{request.command}-admission",),
        evidence_refs=(f"evidence:{evidence_boundary}",),
        basis=DecisionBasis(
            enforcement_boundary=enforcement_boundary,
            identity_basis=identity_basis,
            state_bindings=tuple(expected_state),
            evidence_boundary=evidence_boundary,
            verifier_provenance=verifier_provenance,
            time_basis="evaluation_time",
        ),
        why=why or ((state or "request_admitted",) if verdict == "allow" else required_gaps),
        next=next_actions,
        required_gaps=required_gaps,
    )
    return {"request": request.to_payload(), "decision": decision.to_payload()}

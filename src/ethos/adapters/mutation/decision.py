"""Mutation request and decision-envelope contracts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.lifecycle.reducer import TransitionFacts
from ethos.contracts.lifecycle.reducer import reduce_transition

if TYPE_CHECKING:
    from ethos.contracts.coordination import MutationAdmissionRequest
    from ethos.contracts.lifecycle.reducer import TransitionRequest


def _transition_policy(root: Path, identifier: str):
    return load_lifecycle_declaration(root).policy(identifier)


def _closeout_candidate_gaps(
    root: Path,
    candidate: dict[str, object],
    current_head: str,
    *,
    require_proof: bool = True,
) -> list[str]:
    """Candidate-side closeout blockers, ordered by lifecycle before evidence."""
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    candidate_path = Path(str(candidate["worktree_path"]))
    if workspace_status(candidate_path)["dirty"]:
        return ["candidate_worktree_dirty"]
    candidate_head = str(candidate.get("head") or "")
    if not is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    gaps = openspec_carrier_gaps(candidate_path, ROLE_CANDIDATE)
    return gaps + proof_gaps(candidate_path, candidate_head) if require_proof else gaps


def evaluate_mutation(
    request: TransitionRequest,
    *,
    root: Path,
    current_head: str,
    status: dict[str, object] | None = None,
):
    if not request.apply and request.command != "land":
        return reduce_transition(
            _transition_policy(root, "work_lane"),
            request,
            TransitionFacts(current_head=current_head),
        )
    status = status if status is not None else workspace_status(root)
    closeout = cast("dict[str, object]", status.get("closeout_support", {}))
    return reduce_transition(
        _transition_policy(root, "work_lane"),
        request,
        TransitionFacts(
            current_head=current_head,
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            initial_gaps=tuple(
                str(gap)
                for gap in (
                    *openspec_carrier_gaps(root, ROLE_WORK_LANE),
                    *cast("list[object]", closeout.get("required_gaps", [])),
                )
            ),
            evidence_gaps=tuple(proof_gaps(root, current_head)),
        ),
    )


def evaluate_closeout_mutation(
    request: TransitionRequest,
    *,
    root: Path,
    current_head: str,
):
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    return reduce_transition(
        _transition_policy(root, "closeout"),
        request,
        TransitionFacts(
            current_head=current_head,
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            initial_gaps=(
                *openspec_carrier_gaps(root, ROLE_ACCEPTED_ROOT),
                *_closeout_candidate_gaps(
                    root,
                    candidate,
                    current_head,
                    require_proof=request.apply
                    and str(candidate.get("head") or "") != current_head,
                ),
            ),
            current=str(candidate.get("head") or "") == current_head,
        ),
    )


def mutation_envelope(
    transition: TransitionRequest,
    admission: MutationAdmissionRequest,
) -> dict[str, object]:
    """Build the canonical exact-request mutation envelope."""
    decision = AdmissionDecision(
        verdict=admission.verdict,
        subject=MutationSubject(
            action=admission.action,
            resource=admission.resource,
            expected_state=admission.expected_state,
        ),
        policy_refs=(f"commitment:{transition.command}-admission",),
        evidence_refs=(f"evidence:{admission.evidence_boundary}",),
        basis=DecisionBasis(
            enforcement_boundary=admission.enforcement_boundary,
            identity_basis=admission.identity_basis,
            state_bindings=tuple(admission.expected_state),
            evidence_boundary=admission.evidence_boundary,
            verifier_provenance=admission.verifier_provenance,
            time_basis="evaluation_time",
        ),
        why=admission.why
        or (
            (admission.state or "request_admitted",)
            if admission.verdict == "pass"
            else admission.required_gaps
        ),
        next=admission.next_actions,
        required_gaps=admission.required_gaps,
    )
    return {"request": transition.to_payload(), "decision": decision.to_payload()}

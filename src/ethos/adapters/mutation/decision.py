"""Current-fact mutation admission and public decision projection."""

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

if TYPE_CHECKING:
    from ethos.contracts.verdict import Verdict


def admission_decision(
    *,
    subject: MutationSubject,
    verdict: Verdict,
    basis: DecisionBasis,
    policy_ref: str,
    required_gaps: tuple[str, ...] = (),
    why: tuple[str, ...] = (),
    next_action: str = "",
) -> AdmissionDecision:
    """Return the sole exact-request mutation decision contract."""
    return AdmissionDecision(
        verdict=verdict,
        subject=subject,
        policy_refs=(policy_ref,),
        evidence_refs=(f"evidence:{basis.evidence_boundary}",),
        basis=basis,
        why=why or required_gaps or ("request_admitted",),
        next_action=next_action,
        required_gaps=required_gaps,
    )


def _closeout_candidate_gaps(
    root: Path,
    candidate: dict[str, object],
    current_head: str,
    *,
    require_proof: bool,
) -> list[str]:
    """Return candidate facts that block accepted-root promotion."""
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
    return [*gaps, *proof_gaps(candidate_path, candidate_head)] if require_proof else gaps


def _request_gaps(
    *, apply: bool, authorized: bool, expect_head: str | None, current_head: str
) -> list[str]:
    gaps = []
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and expect_head is None:
        gaps.append("expect_head_required")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return gaps


def evaluate_mutation(
    *,
    command: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    root: Path,
    current_head: str,
    status: dict[str, object] | None = None,
) -> AdmissionDecision:
    """Admit land or publish from current facts."""
    action = "candidate.integrate" if command == "land" else "remote.publish"
    base_state: dict[str, object] = {
        "root": root.resolve().as_posix(),
        "head": current_head,
        "apply": apply,
        "confirmation_present": authorized,
        "expect_head": expect_head or "",
    }
    if not apply and command != "land":
        return admission_decision(
            subject=MutationSubject(
                action=action, resource=root.resolve().as_posix(), expected_state=base_state
            ),
            verdict="pass",
            basis=DecisionBasis(
                enforcement_boundary="local_process_guard",
                identity_basis="not_evaluated",
                state_bindings=tuple(base_state),
                evidence_boundary="current_local_observation",
                verifier_provenance="current_runner",
                time_basis="evaluation_time",
            ),
            policy_ref=f"commitment:{command}-admission",
            why=("readiness_only",),
        )
    status = status if status is not None else workspace_status(root)
    closeout = cast("dict[str, object]", status.get("closeout_support", {}))
    gaps = _request_gaps(
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        current_head=current_head,
    )
    role = str(status["role"])
    gaps.extend(
        ["protected_root_mutation"]
        if role != ROLE_WORK_LANE
        else ["work_lane_dirty"]
        if status["dirty"]
        else []
    )
    gaps.extend(
        str(gap)
        for gap in (
            *openspec_carrier_gaps(root, ROLE_WORK_LANE),
            *cast("list[object]", closeout.get("required_gaps", [])),
        )
    )
    if apply:
        gaps.extend(proof_gaps(root, current_head))
    required_gaps = tuple(dict.fromkeys(gaps))
    expected_state = {**base_state, "role": role, "dirty": bool(status["dirty"])}
    return admission_decision(
        subject=MutationSubject(
            action=action, resource=root.resolve().as_posix(), expected_state=expected_state
        ),
        verdict="block" if required_gaps else "pass",
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="not_evaluated",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        required_gaps=required_gaps,
        policy_ref=f"commitment:{command}-admission",
    )


def evaluate_closeout_mutation(
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    root: Path,
    current_head: str,
) -> AdmissionDecision:
    """Admit accepted-root closeout from current candidate facts."""
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    gaps = _request_gaps(
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        current_head=current_head,
    )
    role = str(status["role"])
    gaps.extend(
        ["accepted_root_required"]
        if role != ROLE_ACCEPTED_ROOT
        else ["accepted_root_dirty"]
        if status["dirty"]
        else []
    )
    gaps.extend(
        (
            *openspec_carrier_gaps(root, ROLE_ACCEPTED_ROOT),
            *_closeout_candidate_gaps(
                root,
                candidate,
                current_head,
                require_proof=apply and candidate_head != current_head,
            ),
        )
    )
    required_gaps = tuple(dict.fromkeys(gaps))
    expected_state = {
        "root": root.resolve().as_posix(),
        "head": current_head,
        "candidate_head": candidate_head,
        "role": role,
        "dirty": bool(status["dirty"]),
        "apply": apply,
        "confirmation_present": authorized,
        "expect_head": expect_head or "",
    }
    return admission_decision(
        subject=MutationSubject(
            action="accepted.advance",
            resource=root.resolve().as_posix(),
            expected_state=expected_state,
        ),
        verdict="block" if required_gaps else "pass",
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="not_evaluated",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        required_gaps=required_gaps,
        policy_ref="commitment:land-admission",
    )


def mutation_envelope(
    *,
    command: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    decision: AdmissionDecision,
) -> dict[str, object]:
    """Project one exact AdmissionDecision with its invocation intent."""
    return {
        "request": {
            "command": command,
            "apply": apply,
            "expect_head": expect_head,
            "confirmation_present": authorized,
        },
        "decision": decision.to_payload(),
    }

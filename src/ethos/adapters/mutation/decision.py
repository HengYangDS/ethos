"""Current-fact mutation admission and public decision envelopes."""

from __future__ import annotations

from dataclasses import dataclass
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
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

if TYPE_CHECKING:
    from ethos.contracts.coordination import MutationAdmissionRequest


@dataclass(frozen=True, slots=True)
class MutationDecision:
    """Transient verdict over one current mutation observation."""

    verdict: Verdict
    state: str
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_closed_verdict(self.verdict, self.gaps)


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
    if not require_proof:
        return gaps
    return [*gaps, *proof_gaps(candidate_path, candidate_head)]


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
) -> MutationDecision:
    """Admit land or publish from current facts without a lifecycle reducer."""
    if not apply and command != "land":
        return MutationDecision(verdict="pass", state="dry_run")
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
    return MutationDecision(
        "block" if required_gaps else "pass",
        "blocked" if required_gaps else "work_lane_ready" if apply else "dry_run",
        required_gaps,
    )


def evaluate_closeout_mutation(
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    root: Path,
    current_head: str,
) -> MutationDecision:
    """Admit accepted-root closeout from current candidate facts."""
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
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
                require_proof=apply and str(candidate.get("head") or "") != current_head,
            ),
        )
    )
    required_gaps = tuple(dict.fromkeys(gaps))
    current = str(candidate.get("head") or "") == current_head
    return MutationDecision(
        "block" if required_gaps else "pass",
        "blocked"
        if required_gaps
        else "current"
        if current
        else "closeout_ready"
        if apply
        else "dry_run",
        required_gaps,
    )


def mutation_envelope(
    *,
    command: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    admission: MutationAdmissionRequest,
) -> dict[str, object]:
    """Build one exact current-fact mutation envelope."""
    decision = AdmissionDecision(
        verdict=admission.verdict,
        subject=MutationSubject(
            action=admission.action,
            resource=admission.resource,
            expected_state=admission.expected_state,
        ),
        policy_refs=(f"commitment:{command}-admission",),
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
        next_action=admission.next_action,
        required_gaps=admission.required_gaps,
    )
    return {
        "request": {
            "command": command,
            "apply": apply,
            "expect_head": expect_head,
            "confirmation_present": authorized,
        },
        "decision": decision.to_payload(),
    }

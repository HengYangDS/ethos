"""Exact renew, resume, and transfer of an existing local Lease."""

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING

from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.coordination import LeaseOperationRequest


_OPERATIONS = {
    "renew": ("renewed", False),
    "resume": ("resumed", True),
    "transfer": ("transferred", False),
}


def execute_lease_operation(*, root: Path, request: LeaseOperationRequest) -> dict[str, object]:
    """Evaluate and optionally apply one exact four-coordinate Lease CAS."""
    repo = repository_root(root)
    status = workspace_status(repo)
    observed = leases_by_branch(repo).get(request.branch, {})
    operation = _OPERATIONS.get(request.operation)
    gaps = _lease_operation_gaps(status, request, observed, operation)
    verdict = (
        "unknown"
        if any(gap.startswith("work_lane_lease_unknown:") for gap in gaps)
        else "block"
        if gaps
        else "pass"
    )
    lease: dict[str, object] = {}
    if request.apply and verdict == "pass":
        try:
            lease = apply_lease_operation(state_database(repo), request=request)
        except (sqlite3.Error, ValueError) as error:
            verdict, gaps = "block", (str(error),)
    state = (
        operation[0]
        if operation is not None and request.apply and verdict == "pass"
        else "planned"
        if verdict == "pass"
        else "blocked"
    )
    expected_state = {
        "root": repo.resolve().as_posix(),
        "branch": request.branch,
        "holder_ref": request.holder_ref,
        "generation": request.generation,
        "expires_at": request.expires_at,
        "target_holder_ref": request.target_holder_ref,
        "actor_ref": os.environ.get("ETHOS_ACTOR", "").strip(),
        "lease_state": str(observed.get("lease_state") or "missing"),
        "head": current_head(repo),
        "tree": current_tree(repo),
    }
    decision = admission_decision(
        subject=MutationSubject(
            action=f"lane.lease.{request.operation}",
            resource=f"refs/heads/{request.branch}",
            expected_state=expected_state,
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="local_sqlite_compare_and_swap",
            identity_basis="declared_actor_ref_equality",
            state_bindings=tuple(expected_state),
            evidence_boundary="fresh_git_and_local_lease_observation",
            verifier_provenance="current_worktree_runner",
            time_basis="evaluation_time",
        ),
        policy_ref=f"lease:{request.operation}",
        required_gaps=gaps,
        why=(state,) if verdict == "pass" else (),
    )
    return {
        "verdict": verdict,
        "state": state,
        "branch": request.branch,
        "lease": lease,
        "required_gaps": list(gaps),
        "mutation": mutation_envelope(
            command=f"lane-lease-{request.operation}",
            apply=request.apply,
            authorized=False,
            expect_head=current_head(repo),
            decision=decision,
        ),
    }


def _lease_operation_gaps(
    status: dict[str, object],
    request: LeaseOperationRequest,
    observed: dict[str, object],
    operation: tuple[str, bool] | None,
) -> tuple[str, ...]:
    if operation is None:
        return (f"lease_operation_unknown:{request.operation}",)
    lease_state = str(observed.get("lease_state") or "missing")
    gaps = []
    if status.get("role") != "work_lane":
        gaps.append("work_lane_required")
    if status.get("branch") != request.branch:
        gaps.append("lane_branch_mismatch")
    if gap := _lease_state_gap(lease_state, request.branch, require_expired=operation[1]):
        gaps.append(gap)
    expected = (
        request.branch,
        request.holder_ref,
        request.generation,
        request.expires_at,
    )
    actual = (
        str(observed.get("lane_ref") or observed.get("subject") or ""),
        str(observed.get("holder_ref") or ""),
        integer_value(observed.get("generation")),
        str(observed.get("expires_at") or ""),
    )
    if lease_state not in {"missing", "unknown"} and expected != actual:
        gaps.append(f"lease_generation_stale:{request.branch}")
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if request.apply and actor != request.holder_ref:
        gaps.append("lease_actor_mismatch")
    if request.operation == "transfer" and not request.target_holder_ref:
        gaps.append("target_holder_ref_required")
    if request.operation == "resume" and request.contrary_decision:
        gaps.append("lease_resume_blocked_by_decision")
    return tuple(dict.fromkeys(gaps))


def _lease_state_gap(lease_state: str, branch: str, *, require_expired: bool) -> str:
    if lease_state == "unknown":
        return f"work_lane_lease_unknown:{branch}"
    if lease_state == "missing":
        return f"work_lane_missing_lease:{branch}"
    expected = "expired" if require_expired else "valid"
    if lease_state == expected:
        return ""
    return f"lease_not_expired:{branch}" if require_expired else f"work_lane_lease_expired:{branch}"

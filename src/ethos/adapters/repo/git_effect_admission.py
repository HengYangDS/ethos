"""Read-only authority and live-state admission for exact Git effects."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import GitEffect
    from ethos.contracts.plan import TransitionPlan


def require_effect_permission(effect: GitEffect, plan: TransitionPlan) -> None:
    """Admit one CAS through its Commitment or narrow command authority."""
    admitted = set(plan.permissions)
    if "git.ref.compare-and-swap" in admitted or set(effect.permissions) <= admitted:
        return
    if _is_commitment_rebind_authority(effect, plan) or _is_candidate_integration_authority(
        effect, plan
    ):
        return
    message = "git_effect_permission_denied"
    raise ValueError(message)


def _is_commitment_rebind_authority(effect: GitEffect, plan: TransitionPlan) -> bool:
    if plan.policy.get("operation") not in {"commitment.rebind", "change.identity-repair"}:
        return False
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    successor = facts.get("lease_successor")
    if not isinstance(generation, Mapping) or not isinstance(successor, Mapping):
        return False
    updates = tuple(effect.updates.items())
    if len(updates) != 1:
        return False
    ref, update = updates[0]
    new_digest = str(facts.get("new_commitment_digest") or "")
    return (
        ref == f"refs/heads/{generation.get('branch') or ''}"
        and update.expected == generation.get("expected_head")
        and update.desired == successor.get("expected_head")
        and successor.get("epoch") == int(generation.get("epoch") or 0) + 1
        and successor.get("holder_ref") == generation.get("holder_ref")
        and successor.get("lease_id") == generation.get("lease_id")
        and successor.get("lane_incarnation_id") == generation.get("lane_incarnation_id")
        and facts.get("new_commitment_path") == successor.get("base_commitment_path")
        and facts.get("new_commitment_bytes_sha256")
        == successor.get("base_commitment_bytes_sha256")
        and new_digest == successor.get("base_commitment_digest")
        and plan.policy.get("old_commitment_digest") == generation.get("base_commitment_digest")
        and plan.policy.get("new_commitment_digest") == new_digest
    )


def _is_candidate_integration_authority(effect: GitEffect, plan: TransitionPlan) -> bool:
    if plan.policy.get("operation") != "candidate.integrate":
        return False
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    proof = plan.prior_attestations.get("proof")
    if not isinstance(generation, Mapping) or not isinstance(proof, Mapping):
        return False
    updates, assertions = tuple(effect.updates.items()), tuple(effect.assertions.items())
    if len(updates) != 1 or len(assertions) != 1:
        return False
    ref, update = updates[0]
    source_ref, source_head = assertions[0]
    candidate = str(plan.policy.get("candidate_branch") or "")
    proof_statement = proof.get("statement")
    statement = proof_statement if isinstance(proof_statement, Mapping) else {}
    return (
        bool(candidate)
        and ref == f"refs/heads/{candidate}"
        and source_ref == f"refs/heads/{generation.get('branch') or ''}"
        and source_head == update.desired == plan.facts.get("head")
        and update.expected != update.desired
        and generation.get("expected_head") == update.desired
        and proof.get("predicate") == "proof:execution"
        and proof.get("verdict") == "pass"
        and proof.get("subject") == f"git:commit:{update.desired}"
        and statement.get("head", update.desired) == update.desired
        and proof.get("commitment_digest") == generation.get("base_commitment_digest")
        and proof.get("commitment_digest") == plan.inputs.commitment
    )


def require_plan_prestate(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None = None,
    detached_branch: str = "",
) -> None:
    """Reject a carried plan whose exact mutation facts have gone stale."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    expected_refs = {ref: update.expected for ref, update in effect.updates.items()}
    if facts.get("refs") != expected_refs or facts.get("assertions") != effect.assertions:
        message = "git_effect_plan_prestate_mismatch"
        raise ValueError(message)
    require_live_lease(
        root,
        plan,
        environment=environment,
        detached_branch=detached_branch,
    )
    head = str(plan.facts.get("head") or "")
    current = current_tracked_head(root)
    if plan.policy.get("operation") == "lane.start.compensate":
        if head not in {update.expected for update in effect.updates.values()}:
            message = "git_effect_plan_prestate_stale"
            raise ValueError(message)
    elif current != head:
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)
    if current_tree(root, head) != str(plan.facts.get("tree") or ""):
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)


def require_live_lease(
    root: Path,
    plan: TransitionPlan,
    *,
    environment: Mapping[str, str] | None = None,
    detached_branch: str = "",
    recovering: bool = False,
) -> None:
    """Admit an exact live Lease generation and its execution identity."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    if not isinstance(generation, Mapping):
        return
    branch = str(generation.get("branch") or "")
    current = leases_by_branch(root, object_environment=dict(environment or {})).get(branch, {})
    live = lease_generation(current)
    stable = ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
    recovery_match = recovering and all(generation.get(key) == live.get(key) for key in stable)
    successor = facts.get("lease_successor")
    if isinstance(successor, Mapping):
        recovery_match = (
            recovery_match
            and set(successor) == set(live) - {"payload_sha256"}
            and all(
                mutable_json(live.get(key)) == mutable_json(value)
                for key, value in successor.items()
            )
        )
    else:
        recovery_match = recovery_match and (
            generation.get("epoch") == live.get("epoch")
            and live.get("expected_head")
            in {generation.get("expected_head"), plan.facts.get("head")}
        )
    if (
        current.get("lease_state") != "valid"
        or current.get("commitment_binding") != "bound"
        or not (mutable_json(generation) == mutable_json(live) or recovery_match)
    ):
        message = "git_effect_lease_generation_stale"
        raise ValueError(message)
    operation = str(plan.policy.get("operation") or "")
    actor = (
        str(plan.policy.get("holder_ref") or "")
        if operation.startswith("lane.start")
        else os.environ.get("ETHOS_ACTOR", "").strip()
    )
    if actor != str(generation.get("holder_ref") or ""):
        message = "lease_actor_mismatch"
        raise ValueError(message)
    if operation == "lane.start":
        if run_git(root, "branch", "--show-current").stdout.strip():
            message = "git_effect_lease_branch_mismatch"
            raise ValueError(message)
    elif operation != "lane.start.compensate":
        execution_branch = str(plan.policy.get("execution_branch") or branch)
        attached_branch = run_git(root, "branch", "--show-current").stdout.strip()
        if attached_branch != execution_branch and not (
            detached_branch == execution_branch
            and not attached_branch
            and current_tracked_head(root) == str(plan.facts.get("head") or "")
        ):
            message = "git_effect_lease_branch_mismatch"
            raise ValueError(message)

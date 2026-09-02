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
    """Admit one CAS only through exact operation-bound authority."""
    if _is_exact_effect_authority(effect, plan):
        return
    message = "git_effect_permission_denied"
    raise ValueError(message)


def _is_exact_effect_authority(effect: GitEffect, plan: TransitionPlan) -> bool:
    """Admit the primitive only when policy binds this exact effect digest."""
    return (
        plan.policy.get("operation") == "git.ref.compare-and-swap"
        and plan.policy.get("effect_digest") == effect.digest()
    )


def require_plan_prestate(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    detached_branch: str = "",
) -> None:
    """Reject a carried plan whose exact mutation facts have gone stale."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    expected_refs = {ref: update.expected for ref, update in effect.updates.items()}
    if facts.get("refs") != expected_refs or facts.get("assertions") != effect.assertions:
        message = "git_effect_plan_prestate_mismatch"
        raise ValueError(message)
    require_lease_generation(
        root,
        plan,
        detached_branch=detached_branch,
    )
    head = str(plan.facts.get("head") or "")
    current = current_tracked_head(root)
    operation = str(plan.policy.get("transition") or plan.policy.get("operation") or "")
    if operation == "lane.start.compensate":
        if head not in {update.expected for update in effect.updates.values()}:
            message = "git_effect_plan_prestate_stale"
            raise ValueError(message)
    elif current != head:
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)
    if current_tree(root, head) != str(plan.facts.get("tree") or ""):
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)


def require_lease_generation(
    root: Path,
    plan: TransitionPlan,
    *,
    detached_branch: str = "",
) -> None:
    """Admit the exact Lease generation and execution identity bound by a plan."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    if not isinstance(generation, Mapping):
        return
    branch = str(generation.get("lane_ref") or "")
    current = leases_by_branch(root).get(branch, {})
    live = lease_generation(current)
    operation = str(plan.policy.get("transition") or plan.policy.get("operation") or "")
    expected_state = str(facts.get("lease_generation_state") or "valid")
    if expected_state not in {"valid", "expired"}:
        message = "git_effect_lease_state_invalid"
        raise ValueError(message)
    if current.get("lease_state") != expected_state or mutable_json(generation) != mutable_json(
        live
    ):
        message = "git_effect_lease_generation_stale"
        raise ValueError(message)
    _require_lease_actor(plan, generation, operation=operation, state=expected_state)
    _require_lease_execution_branch(
        root,
        plan,
        branch=branch,
        operation=operation,
        detached_branch=detached_branch,
    )


def _require_lease_actor(
    plan: TransitionPlan,
    generation: Mapping[str, object],
    *,
    operation: str,
    state: str,
) -> None:
    """Admit the holder, or the sole deletion-only expired-Lease transition."""
    if state == "expired":
        if not (
            operation == "lane.retire"
            and plan.policy.get("retirement_kind") == "linked-lane"
            and plan.policy.get("retirement_mode") == "landed"
            and str(plan.authority.get("actor") or "")
        ):
            message = "git_effect_expired_lease_not_admitted"
            raise ValueError(message)
    else:
        actor = (
            str(plan.policy.get("holder_ref") or "")
            if operation.startswith("lane.start")
            else os.environ.get("ETHOS_ACTOR", "").strip()
        )
        if actor != str(generation.get("holder_ref") or ""):
            message = "lease_actor_mismatch"
            raise ValueError(message)


def _require_lease_execution_branch(
    root: Path,
    plan: TransitionPlan,
    *,
    branch: str,
    operation: str,
    detached_branch: str,
) -> None:
    """Require the checkout identity independently bound by the effect plan."""
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

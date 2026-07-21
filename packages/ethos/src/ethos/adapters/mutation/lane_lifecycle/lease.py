"""Generation-bound local Lane Lease operations."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import accept_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import offer_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.lifecycle.core import resume_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.lifecycle.core import LeaseFacts
from ethos_core.contracts.lifecycle.core import LeaseOperationRequest
from ethos_core.contracts.lifecycle.core import MutationEvaluation
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.contracts.lifecycle.core import reduce_lease_request
from ethos_core.contracts.workflow import load_workflow_contract_declaration

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos_core.contracts.lifecycle.core import LeaseTransition

_LEASE_EFFECTS: dict[str, Callable[..., dict[str, Any]]] = {
    "renew": renew_lease,
    "resume": resume_lease,
    "handoff_offer": offer_lease_handoff,
    "handoff_accept": accept_lease_handoff,
}


def execute_lease_operation(*, root: Path, request: LeaseOperationRequest) -> dict[str, object]:
    """Evaluate and optionally execute one declaration-owned lease transition."""
    repo = repo_root(root)
    status = workspace_status(repo)
    database = accepted_worktree_root(status.get("worktrees"), repo) / ".ethos/state/state.sqlite"
    expected_state, holder_gaps = _lease_expected_state(repo, request)
    transition, effect, contract_gaps = _lease_effect_binding(repo, request.operation)

    if transition is None or contract_gaps:
        evaluation = MutationEvaluation(
            ok=False,
            state="blocked",
            gaps=tuple(dict.fromkeys((*contract_gaps, *holder_gaps))),
        )
    else:
        evaluation = reduce_lease_request(
            transition,
            LeaseFacts(
                role=str(status.get("role") or ""),
                current_branch=str(status.get("branch") or ""),
                current_head=run_git(repo, "rev-parse", "HEAD").stdout.strip(),
                branch=request.branch,
                holder_ref=request.holder_ref,
                target_holder_ref=request.target_holder_ref,
                actor_ref=str(expected_state["actor_ref"]),
                expect_head=request.expect_head,
                lease_id=request.lease_id,
                expected_epoch=request.expected_epoch,
                expected_expires_at=request.expected_expires_at,
                expected_payload_sha256=request.expected_payload_sha256,
                ttl_seconds=request.ttl_seconds,
                offer_id=request.offer_id,
                holder_quiesced=request.holder_quiesced,
                contrary_decision=request.contrary_decision,
                apply=request.apply,
                initial_gaps=holder_gaps,
            ),
        )

    ok, state, gaps = evaluation.ok, evaluation.state, evaluation.gaps
    lease: dict[str, object] = {}
    handoff_offer: dict[str, object] = {}
    receipt: dict[str, object] = {}
    if request.apply and ok and effect is not None and transition is not None:
        arguments = request.model_dump()
        arguments.update(
            holder_ref=str(expected_state["holder_ref"]),
            target_holder_ref=str(expected_state["target_holder_ref"]),
        )
        effect_arguments = {field: arguments[field] for field in transition.effect_fields}
        try:
            payload = effect(
                database,
                subject=request.branch,
                expected_lease_id=request.lease_id,
                expected_head=request.expect_head,
                **effect_arguments,
            )
        except ValueError as exc:
            ok, state, gaps = False, "blocked", (str(exc),)
        else:
            if "offer_id" in payload:
                handoff_offer = payload
            else:
                lease = payload
            state = transition.applied_state
            receipt = _lease_operation_receipt(
                operation=request.operation,
                effect=payload,
            )

    result: dict[str, object] = {
        "ok": ok,
        "state": state,
        "branch": request.branch,
        "lease": lease,
        "handoff_offer": handoff_offer,
        "receipt": receipt,
        "required_gaps": list(gaps),
    }
    result["mutation"] = mutation_envelope(
        MutationRequest(
            command=f"lane-{request.operation.replace('_', '-')}",
            apply=request.apply,
            authorized=request.holder_quiesced,
            expect_head=request.expect_head or None,
        ),
        action=f"lane.lease.{request.operation.replace('_', '.')}",
        resource=f"refs/heads/{request.branch}",
        expected_state=expected_state,
        verdict="allow" if ok else "block",
        required_gaps=gaps,
        why=(state,) if ok else (),
        state=state,
        identity_basis="declared_actor_ref_equality",
        evidence_boundary="current_git_and_local_lease_observation",
        enforcement_boundary="local_sqlite_compare_and_swap",
        verifier_provenance="current_worktree_runner",
    )
    return result


def _lease_effect_binding(
    repo: Path, operation: str
) -> tuple[
    LeaseTransition | None,
    Callable[..., dict[str, Any]] | None,
    tuple[str, ...],
]:
    """Bind one declared operation to its exact local effect capability."""
    try:
        transitions = load_workflow_contract_declaration(repo).lease_transition
    except (OSError, ValueError):
        return None, None, ("lease_transition_contract_invalid",)
    transition = next((item for item in transitions if item.id == operation), None)
    if transition is None:
        return None, None, (f"lease_transition_unknown:{operation}",)
    effect = _LEASE_EFFECTS.get(operation)
    if effect is None:
        return transition, None, (f"lease_effect_unknown:{transition.id}",)
    return transition, effect, ()


def _lease_expected_state(
    repo: Path, request: LeaseOperationRequest
) -> tuple[dict[str, object], tuple[str, ...]]:
    expected: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "branch": request.branch,
        "head": request.expect_head,
        "holder_ref": request.holder_ref,
        "lease_id": request.lease_id,
        "epoch": request.expected_epoch or 0,
        "expires_at": request.expected_expires_at,
        "payload_sha256": request.expected_payload_sha256,
        "target_holder_ref": request.target_holder_ref,
        "offer_id": request.offer_id,
        "actor_ref": os.environ.get("ETHOS_ACTOR", "").strip(),
    }
    gaps: list[str] = []
    for field in ("holder_ref", "target_holder_ref"):
        value = str(expected[field])
        if not value and field == "target_holder_ref":
            continue
        try:
            expected[field] = HolderRef.parse(value).serialize()
        except ValueError:
            gaps.append(f"{field}_invalid")
    return expected, tuple(gaps)


def _lease_operation_receipt(*, operation: str, effect: dict[str, object]) -> dict[str, object]:
    return {
        "receipt_id": f"receipt:{operation}:{effect.get('lease_id') or effect.get('offer_id')}",
        "operation": operation.replace("handoff_", "handoff-"),
        "applied": True,
        "lease_id": str(effect.get("lease_id") or ""),
        "holder_ref": str(effect.get("holder_ref") or ""),
        "epoch": integer_value(effect.get("epoch")),
        "lane_ref": str(effect.get("lane_ref") or ""),
        "expected_head": str(effect.get("expected_head") or ""),
        "expires_at": str(effect.get("expires_at") or ""),
        "payload_sha256": str(effect.get("payload_sha256") or ""),
        "mints_authority": False,
        "transferable": False,
    }

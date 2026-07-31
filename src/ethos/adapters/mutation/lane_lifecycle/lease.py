"""Generation-bound local Lane Lease operations."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.decision import MutationDecision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import MutationAdmissionRequest
from ethos.contracts.coordination import lease_operation

if TYPE_CHECKING:
    from pathlib import Path


def execute_lease_operation(*, root: Path, request: LeaseOperationRequest) -> dict[str, object]:
    """Evaluate and optionally execute one declaration-owned lease transition."""
    repo = repository_root(root)
    status = workspace_status(repo)
    database = state_database(repo)
    expected_state, holder_gaps = _lease_expected_state(repo, request)
    try:
        operation = lease_operation(request.operation)
    except ValueError as exc:
        operation = None
        contract_gaps = (str(exc),)
    else:
        contract_gaps = ()

    if operation is None:
        evaluation = MutationDecision(
            verdict="block",
            state="blocked",
            gaps=tuple(dict.fromkeys((*contract_gaps, *holder_gaps))),
        )
    else:
        effect_values = {
            "holder_ref": request.holder_ref,
            "target_holder_ref": request.target_holder_ref,
            "offer_id": request.offer_id,
            "holder_quiesced": request.holder_quiesced,
            "expected_expires_at": request.expected_expires_at,
            "expected_payload_sha256": request.expected_payload_sha256,
        }
        effect_value_gaps = {
            "holder_ref": "holder_ref_invalid",
            "target_holder_ref": "target_holder_ref_invalid",
            "offer_id": "handoff_offer_id_required",
            "holder_quiesced": "holder_quiescence_confirmation_required",
            "expected_expires_at": "lease_expires_at_required",
            "expected_payload_sha256": "lease_payload_sha256_required",
        }
        checks = (
            (status.get("role") == "work_lane", "work_lane_required"),
            (status.get("branch") == request.branch, "lane_branch_mismatch"),
            (bool(request.expect_head), "expect_head_required"),
            (
                not request.expect_head
                or run_git(repo, "rev-parse", "HEAD").stdout.strip() == request.expect_head,
                "expect_head_mismatch",
            ),
            (bool(request.lease_id), "lease_id_required"),
            (
                "expected_epoch" not in operation.effect_fields
                or (request.expected_epoch is not None and request.expected_epoch >= 1),
                "lease_epoch_required",
            ),
            (
                "ttl_seconds" not in operation.effect_fields or request.ttl_seconds >= 1,
                "lease_ttl_invalid",
            ),
            (
                not operation.require_expired or not request.contrary_decision,
                "lease_resume_blocked_by_decision",
            ),
            (
                not request.apply
                or expected_state["actor_ref"] == effect_values[operation.actor_field],
                "lease_actor_mismatch",
            ),
            *(
                (effect_values[field] not in ("", None, False), effect_value_gaps[field])
                for field in operation.effect_fields
                if field in effect_values
            ),
        )
        gaps = tuple(dict.fromkeys((*holder_gaps, *(gap for valid, gap in checks if not valid))))
        evaluation = MutationDecision(
            verdict=(
                "unknown"
                if any(gap.startswith("work_lane_lease_unknown:") for gap in gaps)
                else "block"
                if gaps
                else "pass"
            ),
            state="blocked" if gaps else operation.applied_state if request.apply else "planned",
            gaps=gaps,
        )

    verdict, state, gaps = evaluation.verdict, evaluation.state, evaluation.gaps
    lease: dict[str, object] = {}
    handoff_offer: dict[str, object] = {}
    if request.apply and verdict == "pass" and operation is not None:
        try:
            payload = apply_lease_operation(
                database,
                request=_lease_effect_request(request, operation.effect_fields, expected_state),
            )
        except Exception as exc:
            verdict, state, gaps = "block", "blocked", (str(exc),)
        else:
            if "offer_id" in payload:
                handoff_offer = payload
            else:
                lease = payload
            state = operation.applied_state

    result: dict[str, object] = {
        "verdict": verdict,
        "state": state,
        "branch": request.branch,
        "lease": lease,
        "handoff_offer": handoff_offer,
        "required_gaps": list(gaps),
    }
    result["mutation"] = mutation_envelope(
        command=f"lane-{request.operation.replace('_', '-')}",
        apply=request.apply,
        authorized=request.holder_quiesced,
        expect_head=request.expect_head or None,
        admission=MutationAdmissionRequest(
            action=f"lane.lease.{request.operation.replace('_', '.')}",
            resource=f"refs/heads/{request.branch}",
            expected_state=expected_state,
            verdict=verdict,
            required_gaps=gaps,
            why=(state,) if verdict == "pass" else (),
            state=state,
            identity_basis="declared_actor_ref_equality",
            evidence_boundary="current_git_and_local_lease_observation",
            enforcement_boundary="local_sqlite_compare_and_swap",
            verifier_provenance="current_worktree_runner",
        ),
    )
    return result


def _lease_effect_request(
    request: LeaseOperationRequest,
    effect_fields: tuple[str, ...],
    expected_state: dict[str, object],
) -> LeaseOperationRequest:
    """Compile the exact effect envelope with bound current state."""
    effect_values: dict[str, Any] = request.model_dump(include=set(effect_fields))
    effect_values["holder_ref"] = str(expected_state["holder_ref"])
    if "target_holder_ref" in effect_values:
        effect_values["target_holder_ref"] = str(expected_state["target_holder_ref"])
    return LeaseOperationRequest.model_validate(
        {
            "operation": request.operation,
            "branch": request.branch,
            "lease_id": request.lease_id,
            "expect_head": request.expect_head,
            "apply": True,
            **effect_values,
        }
    )


def _lease_expected_state(
    repo: Path, request: LeaseOperationRequest
) -> tuple[dict[str, object], tuple[str, ...]]:
    observed = leases_by_branch(repo).get(request.branch, {})
    lease_state = str(observed.get("lease_state") or "missing")
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
        "lease_state": lease_state,
        "base_commitment_digest": str(observed.get("base_commitment_digest") or ""),
    }
    gaps = _lease_observation_gaps(request, observed, lease_state)
    for field in ("holder_ref", "target_holder_ref"):
        value = str(expected[field])
        if not value and field == "target_holder_ref":
            continue
        try:
            expected[field] = HolderRef.parse(value).serialize()
        except ValueError:
            gaps.append(f"{field}_invalid")
    return expected, tuple(gaps)


def _lease_observation_gaps(
    request: LeaseOperationRequest,
    observed: dict[str, object],
    lease_state: str,
) -> list[str]:
    branch = request.branch
    if lease_state == "unknown":
        return [f"work_lane_lease_unknown:{branch}"]
    if lease_state == "missing":
        return [f"work_lane_missing_lease:{branch}"]
    if request.operation == "resume":
        if lease_state != "expired":
            return [f"lease_not_expired:{branch}"]
    elif lease_state != "valid":
        return [f"work_lane_lease_expired:{branch}"]
    checks = (
        (str(observed.get("lease_id") or "") == request.lease_id, "lease_id_stale"),
        (
            str(observed.get("holder_ref") or "") == request.holder_ref,
            "lease_holder_mismatch",
        ),
        (
            integer_value(observed.get("epoch")) == (request.expected_epoch or 0),
            "lease_epoch_stale",
        ),
        (str(observed.get("expected_head") or "") == request.expect_head, "lease_head_stale"),
        (
            str(observed.get("expires_at") or "") == request.expected_expires_at,
            "lease_expires_at_stale",
        ),
        (
            str(observed.get("payload_sha256") or "") == request.expected_payload_sha256,
            "lease_payload_sha256_stale",
        ),
        (
            bool(str(observed.get("base_commitment_digest") or "")),
            "lease_base_commitment_digest_missing",
        ),
    )
    return [f"{gap}:{branch}" for valid, gap in checks if not valid]

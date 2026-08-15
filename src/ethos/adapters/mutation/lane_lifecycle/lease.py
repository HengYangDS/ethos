"""Generation-bound local Lane Lease operations."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import takeover_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.coordination import lease_operation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def execute_lease_operation(*, root: Path, request: LeaseOperationRequest) -> dict[str, object]:
    """Evaluate and optionally execute one declaration-owned lease transition."""
    repo = repository_root(root)
    guard = local_state_mutation_guard(repo) if request.apply else {"required_gaps": []}
    if guard["required_gaps"]:
        return _blocked_state_migration(request.branch, guard)
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
        verdict = "block"
        state = "blocked"
        gaps = tuple(dict.fromkeys((*contract_gaps, *holder_gaps)))
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
        verdict = (
            "unknown"
            if any(gap.startswith("work_lane_lease_unknown:") for gap in gaps)
            else "block"
            if gaps
            else "pass"
        )
        state = "blocked" if gaps else operation.applied_state if request.apply else "planned"
    lease: dict[str, object] = {}
    handoff_offer: dict[str, object] = {}
    if request.apply and verdict == "pass" and operation is not None:
        try:
            payload = apply_lease_operation(
                database,
                request=_lease_effect_request(request, operation.effect_fields, expected_state),
            )
        except (sqlite3.Error, ValueError) as exc:
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
    decision = admission_decision(
        subject=MutationSubject(
            action=f"lane.lease.{request.operation.replace('_', '.')}",
            resource=f"refs/heads/{request.branch}",
            expected_state=expected_state,
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="local_sqlite_compare_and_swap",
            identity_basis="declared_actor_ref_equality",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_git_and_local_lease_observation",
            verifier_provenance="current_worktree_runner",
            time_basis="evaluation_time",
        ),
        policy_ref=f"commitment:lane-{request.operation.replace('_', '-')}-admission",
        required_gaps=gaps,
        why=(state,) if verdict == "pass" else (),
    )
    result["mutation"] = mutation_envelope(
        command=f"lane-{request.operation.replace('_', '-')}",
        apply=request.apply,
        authorized=request.holder_quiesced,
        expect_head=request.expect_head or None,
        decision=decision,
    )
    return result


def execute_lease_takeover(*, root: Path, request: LeaseTakeoverRequest) -> dict[str, object]:
    """Execute one accepted, exact, transcript-free Lease takeover."""
    repo = repository_root(root)
    guard = local_state_mutation_guard(repo) if request.apply else {"required_gaps": []}
    if guard["required_gaps"]:
        return _blocked_state_migration(request.branch, guard)
    observed = leases_by_branch(repo).get(request.branch, {})
    expected = _takeover_expected_state(repo, request, observed)
    gaps = _takeover_gaps(repo, request, expected)
    recovered = _takeover_already_applied(request, expected)
    if recovered:
        gaps = _takeover_authorization_gaps(repo, request, expected)
    verdict = (
        "unknown" if any(gap.endswith("_unknown") for gap in gaps) else "block" if gaps else "pass"
    )
    lease: dict[str, object] = {}
    attestation: Attestation | None = None
    if request.apply and verdict == "pass":
        before = _takeover_authorized_state(request)
        try:
            lease = (
                observed
                if recovered
                else takeover_lease(
                    state_database(repo),
                    request=request,
                    observe_repository=lambda: (
                        current_head(repo),
                        current_tree(repo),
                        dirty_content_sha256(repo),
                    ),
                )
            )
        except (OSError, sqlite3.Error, ValueError) as exc:
            verdict, gaps = "block", (str(exc),)
        else:
            repository = load_repository_commitment(repo)
            effect = NativeEffect(
                predicate="lane-resolution:takeover",
                operation="takeover",
                command=("ethos", "lane", "lease", "takeover"),
                subject={"branch": request.branch, "head": request.expect_head},
                before=before,
                after={
                    "branch": request.branch,
                    "head": request.expect_head,
                    "tree": request.expected_tree,
                    "dirty_content_sha256": request.expected_dirty_content_sha256,
                    "holder_ref": request.target_holder_ref,
                    "epoch": lease["epoch"],
                    "source_state": request.source_state,
                },
            )
            candidate = issue_native_effect(
                repo,
                effect=effect,
                state="applied",
                commitment_digest=str(observed.get("base_commitment_digest") or ""),
                repository_id=repository.id,
                issued_at=datetime.fromisoformat(str(lease["renewed_at"])),
            )
            record_attestations(repo, (candidate,))
            attestation = candidate
    state = (
        "taken_over"
        if verdict == "pass" and request.apply
        else "planned"
        if verdict == "pass"
        else "blocked"
    )
    return {
        "verdict": verdict,
        "state": state,
        "branch": request.branch,
        "source_state": request.source_state,
        "lease": lease,
        "attestation": attestation.model_dump(mode="json") if attestation else {},
        "required_gaps": list(gaps),
    }


def _blocked_state_migration(branch: str, guard: dict[str, object]) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "lease": {},
        "handoff_offer": {},
        "attestation": {},
        "required_gaps": guard["required_gaps"],
        "next_action": guard["next_action"],
    }


def _takeover_expected_state(
    repo: Path, request: LeaseTakeoverRequest, observed: dict[str, object]
) -> dict[str, object]:
    return {
        "branch": request.branch,
        "head": current_head(repo),
        "tree": current_tree(repo),
        "dirty_content_sha256": dirty_content_sha256(repo),
        "lane_incarnation_id": str(observed.get("lane_incarnation_id") or ""),
        "lease_id": str(observed.get("lease_id") or ""),
        "lease_epoch": integer_value(observed.get("epoch")),
        "lease_payload_sha256": str(observed.get("payload_sha256") or ""),
        "base_commitment_digest": str(observed.get("base_commitment_digest") or ""),
        "source_holder_ref": str(observed.get("holder_ref") or ""),
        "target_holder_ref": request.target_holder_ref,
        "source_state": request.source_state,
        "actor_ref": os.environ.get("ETHOS_ACTOR", "").strip(),
        "lease_state": str(observed.get("lease_state") or "missing"),
    }


def _takeover_gaps(
    repo: Path, request: LeaseTakeoverRequest, observed: dict[str, object]
) -> tuple[str, ...]:
    expected = _takeover_authorized_state(request)
    coordinate_gaps = {
        "head": "head_drift",
        "tree": "tree_drift",
        "dirty_content_sha256": "dirty_content_drift",
        "lane_incarnation_id": "incarnation_drift",
        "lease_id": "lease_id_drift",
        "lease_epoch": "epoch_drift",
        "lease_payload_sha256": "payload_drift",
        "source_holder_ref": "source_holder_drift",
    }
    checks = [
        (observed["lease_state"] in {"valid", "expired"}, "lease_unknown"),
        (observed["actor_ref"] == request.target_holder_ref, "actor_mismatch"),
        *((observed[key] == expected[key], gap) for key, gap in coordinate_gaps.items()),
    ]
    return (
        *(f"lease_takeover_{gap}" for valid, gap in checks if not valid),
        *_takeover_authorization_gaps(repo, request, observed),
    )


def _takeover_authorized_state(request: LeaseTakeoverRequest) -> dict[str, object]:
    return {
        "branch": request.branch,
        "head": request.expect_head,
        "tree": request.expected_tree,
        "dirty_content_sha256": request.expected_dirty_content_sha256,
        "lane_incarnation_id": request.expected_lane_incarnation_id,
        "lease_id": request.lease_id,
        "lease_epoch": request.expected_epoch,
        "lease_payload_sha256": request.expected_payload_sha256,
        "source_holder_ref": request.source_holder_ref,
        "target_holder_ref": request.target_holder_ref,
        "source_state": request.source_state,
    }


def _takeover_authorization_gaps(
    repo: Path, request: LeaseTakeoverRequest, observed: dict[str, object]
) -> tuple[str, ...]:
    authorization = request.authorization
    try:
        _root, attestations = read_attestation_set(repo)
        accepted = next((item for item in attestations if item.id == authorization.id), None)
    except ValueError:
        accepted = None
    now = datetime.now(UTC)
    checks = (
        (accepted == authorization, "lease_takeover_authorization_unaccepted"),
        (
            authorization.predicate == "lane-resolution:takeover",
            "lease_takeover_authorization_kind",
        ),
        (authorization.verdict == "pass", "lease_takeover_authorization_blocked"),
        (
            authorization.subject == f"git:branch:{request.branch}",
            "lease_takeover_authorization_subject_drift",
        ),
        (
            authorization.commitment_digest == str(observed.get("base_commitment_digest") or ""),
            "lease_takeover_authorization_commitment_drift",
        ),
        (
            (authorization.valid_from or authorization.issued_at) <= now
            and (authorization.valid_until is None or now <= authorization.valid_until),
            "lease_takeover_authorization_stale",
        ),
        (
            authorization.payload.body.get("authorization") == _takeover_authorized_state(request),
            "lease_takeover_authorization_drift",
        ),
    )
    return tuple(gap for valid, gap in checks if not valid)


def _takeover_already_applied(request: LeaseTakeoverRequest, observed: dict[str, object]) -> bool:
    return all(
        (
            observed["head"] == request.expect_head,
            observed["tree"] == request.expected_tree,
            observed["dirty_content_sha256"] == request.expected_dirty_content_sha256,
            observed["lane_incarnation_id"] == request.expected_lane_incarnation_id,
            observed["lease_id"] == request.lease_id,
            observed["lease_epoch"] == request.expected_epoch + 1,
            observed["source_holder_ref"] == request.target_holder_ref,
            observed["actor_ref"] == request.target_holder_ref,
        )
    )


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

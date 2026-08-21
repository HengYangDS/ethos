"""Attestation persistence for one complete Commitment rebind."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import commitment_generation_origin
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import validated_plan_attestation
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.coordination import LaneLease
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import integer

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.coordination import CommitmentRebindRequest
    from ethos.contracts.plan import TransitionPlan


def old_generation(request: CommitmentRebindRequest) -> dict[str, object]:
    """Reconstruct the exact old Lease generation carried by the request."""
    payload = {
        "lane_ref": request.branch,
        "lane_incarnation_id": request.expected_lane_incarnation_id,
        "lease_id": request.lease_id,
        "epoch": request.expected_epoch,
        "holder_ref": request.holder_ref,
        "expected_head": request.expect_head,
        "expected_tree": request.expected_tree,
        "base_commitment_path": request.expected_commitment_path,
        "base_commitment_bytes_sha256": request.expected_commitment_bytes_sha256,
        "base_commitment_digest": request.expected_commitment_digest,
        "issued_at": request.expected_issued_at,
        "renewed_at": request.expected_renewed_at,
        "path_scope": list(request.expected_path_scope),
        "handoff": None,
        "expires_at": request.expected_expires_at,
    }
    return {
        **LaneLease.from_payload(payload).to_payload(),
        "payload_sha256": request.expected_payload_sha256,
    }


def issue_rebind_attestation(
    *,
    repo: Path,
    request: CommitmentRebindRequest,
    new_lease: dict[str, object],
    plan: TransitionPlan,
    effect: GitEffect,
    git_state: str,
    issued_at: datetime,
) -> Attestation:
    """Issue one immutable attestation over the complete old/new transition."""
    _require_fresh_terminal_state(repo, request, new_lease)
    values = plan.facts.get("values")
    old_lease = values.get("lease_generation") if isinstance(values, Mapping) else None
    if not isinstance(old_lease, Mapping):
        message = "commitment_rebind_plan_lease_generation_invalid"
        raise TypeError(message)
    statement = {
        "claim": {"operation": "commitment-rebind", "branch": request.branch},
        "old_lease_generation": dict(old_lease),
        "new_lease_generation": lease_generation(new_lease),
        "result": {"git": git_state, "lease": "epoch_advanced"},
    }
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "effect:commitment-rebind",
            "verifier": request.holder_ref,
            "subject": f"commitment-rebind:{effect.digest()}",
            "issued_at": issued_at,
            "valid_from": issued_at,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": "effect:commitment-rebind", "body": statement},
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": str(plan.policy.get("old_commitment_digest") or ""),
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect.digest(),
            "mints_authority": False,
        }
    )


def _require_fresh_terminal_state(
    repo: Path,
    request: CommitmentRebindRequest,
    expected_lease: dict[str, object],
) -> None:
    current_lease = leases_by_branch(repo).get(request.branch, {})
    checks = (
        (ref_head(repo, request.branch) == request.target_commit, "commitment_rebind_ref_stale"),
        (current_tracked_head(repo) == request.target_commit, "commitment_rebind_head_stale"),
        (
            current_tree(repo, request.target_commit) == request.expect_index_tree,
            "commitment_rebind_tree_stale",
        ),
        (
            run_git(repo, "write-tree").stdout.strip() == request.expect_index_tree,
            "commitment_rebind_index_tree_mismatch",
        ),
        (
            current_lease.get("lease_state") == "valid"
            and current_lease.get("commitment_binding") == "bound"
            and lease_generation(current_lease) == lease_generation(expected_lease),
            "commitment_rebind_lease_generation_stale",
        ),
        (
            working_overlay_sha256(repo) == request.expected_working_overlay_sha256,
            "commitment_rebind_overlay_changed",
        ),
    )
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)


def persist_rebind_attestation(repo: Path, effect: GitEffect, attestation: Attestation) -> None:
    """Select one exact rebind Attestation in the sole repository set."""
    if attestation.effect_digest != effect.digest():
        message = "commitment_rebind_attestation_invalid"
        raise ValueError(message)
    record_attestations(repo, (attestation,))


def recognized_rebind_attestation(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
    plan: TransitionPlan,
) -> Attestation | None:
    """Return an exact fresh terminal attestation, or reject mismatched evidence."""
    try:
        _root, attestations = read_attestation_set(repo)
    except ValueError as error:
        message = "commitment_rebind_attestation_invalid"
        raise ValueError(message) from error
    matches = tuple(
        attestation
        for attestation in attestations
        if attestation.predicate == "effect:commitment-rebind"
        and attestation.effect_digest == effect.digest()
    )
    if not matches:
        return None
    if len(matches) != 1:
        message = "commitment_rebind_attestation_collision"
        raise ValueError(message)
    attestation = matches[0]
    statement = mutable_json(attestation.payload.body)
    result = statement.get("result") if isinstance(statement, dict) else None
    if not isinstance(result, dict) or result not in (
        {"git": "applied", "lease": "epoch_advanced"},
        {"git": "recovered", "lease": "epoch_advanced"},
    ):
        message = "commitment_rebind_terminal_mismatch"
        raise ValueError(message)
    git_state = result.get("git")
    if not isinstance(git_state, str):
        message = "commitment_rebind_terminal_mismatch"
        raise TypeError(message)
    try:
        expected = issue_rebind_attestation(
            repo=repo,
            request=request,
            new_lease=lease,
            plan=plan,
            effect=effect,
            git_state=git_state,
            issued_at=attestation.issued_at,
        )
    except ValueError as error:
        message = "commitment_rebind_terminal_mismatch"
        raise ValueError(message) from error
    if ref_head(repo, request.branch) != request.target_commit or attestation != expected:
        message = "commitment_rebind_terminal_mismatch"
        raise ValueError(message)
    return attestation


def rebind_generation_authority(
    repo: Path,
    attestation: Attestation,
    *,
    repository_id: str,
    commitment_digest: str,
    lease: dict[str, object],
    attestations: tuple[Attestation, ...] | None = None,
) -> dict[str, object]:
    """Project one exact completed rebind as current Change continuity."""
    statement = mutable_json(attestation.payload.body)
    if not isinstance(statement, dict):
        statement = {}
    old = statement.get("old_lease_generation")
    new = statement.get("new_lease_generation")
    result = statement.get("result")
    if not isinstance(old, dict) or not isinstance(new, dict) or not isinstance(result, dict):
        return {}

    current = lease_generation(lease)
    generation_identity = (
        "branch",
        "lane_incarnation_id",
        "lease_id",
        "holder_ref",
        "base_commitment_path",
        "base_commitment_digest",
    )
    if any(new.get(name) != current.get(name) for name in generation_identity):
        return {}

    try:
        validated = (
            validated_plan_attestation(
                repo,
                attestation.plan_digest,
                issuer=attestation.verifier,
                attestations=attestations,
            )
            if attestation.plan_digest
            else None
        )
    except ValueError:
        validated = None
    if validated is None:
        return {}
    plan, _git_attestation = validated
    values = mutable_json(plan.facts.get("values"))
    if not isinstance(values, dict):
        return {}
    branch = str(current.get("branch") or "")
    previous_head = str(old.get("expected_head") or "")
    generation_head = str(new.get("expected_head") or "")
    head = str(current.get("expected_head") or "")
    effect = GitEffect(
        updates={
            f"refs/heads/{branch}": GitRefUpdate(expected=previous_head, desired=generation_head)
        }
    )
    claim = statement.get("claim")
    transition = (
        "change.identity-repair"
        if plan.policy.get("transition") == "change.identity-repair"
        else "commitment.rebind"
    )
    try:
        load_commitment(
            repo,
            carrier=str(new.get("base_commitment_path") or ""),
            tree_ref=generation_head,
            expected_digest=str(new.get("base_commitment_digest") or ""),
        )
        generation_base = commitment_generation_origin(
            repo,
            head=previous_head,
            carrier=str(old.get("base_commitment_path") or ""),
            change_id=str(plan.commitment.get("id") or "").removeprefix("change:"),
        )
    except ValueError:
        return {}
    successor = {name: value for name, value in new.items() if name != "payload_sha256"}
    stable = (
        "branch",
        "lane_incarnation_id",
        "lease_id",
        "holder_ref",
        "epoch",
        "issued_at",
        "renewed_at",
        "expires_at",
        "path_scope",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
        "base_commitment_digest",
    )
    now = datetime.now(UTC)
    valid = all(
        (
            attestation.predicate == attestation.payload.kind == "effect:commitment-rebind",
            attestation.verdict == "pass",
            attestation.verifier == current.get("holder_ref"),
            attestation.subject == f"commitment-rebind:{effect.digest()}",
            attestation.effect_digest == effect.digest() == plan.inputs.effect,
            claim == {"operation": "commitment-rebind", "branch": branch},
            plan.policy.get("operation") == "git.ref.compare-and-swap",
            plan.policy.get("transition") == transition,
            transition in {"commitment.rebind", "change.identity-repair"},
            git_effect_from_plan(plan) == effect,
            attestation.commitment_digest
            == plan.policy.get("old_commitment_digest")
            == old.get("base_commitment_digest"),
            attestation.facts_digest == plan.inputs.facts,
            attestation.plan_digest == plan.digest,
            attestation.policy_digest == plan.inputs.policy,
            plan.commitment.get("subjects") == (repository_id,),
            values.get("lease_generation") == old,
            mutable_json(values.get("lease_successor")) == successor,
            values.get("index_tree") == new.get("expected_tree"),
            values.get("new_commitment_path") == new.get("base_commitment_path"),
            values.get("new_commitment_bytes_sha256") == new.get("base_commitment_bytes_sha256"),
            values.get("new_commitment_digest") == new.get("base_commitment_digest"),
            result
            in (
                {"git": "applied", "lease": "epoch_advanced"},
                {"git": "recovered", "lease": "epoch_advanced"},
            ),
            attestation.valid_from == attestation.issued_at,
            attestation.valid_from is not None
            and attestation.valid_from <= now
            and (attestation.valid_until is None or now <= attestation.valid_until),
            bool(generation_base),
            all(new.get(name) == current.get(name) for name in stable),
            all(
                old.get(name) == new.get(name)
                for name in ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
            ),
            integer(old.get("epoch"), default=-1) + 1 == integer(new.get("epoch"), default=-1),
            commitment_digest == current.get("base_commitment_digest"),
            ref_head(repo, branch) == head,
            current_tree(repo, head) == current.get("expected_tree"),
            current_tree(repo, generation_head) == new.get("expected_tree"),
            git_stdout(repo, "rev-parse", f"{generation_head}^") == previous_head,
            is_ancestor(repo, generation_head, head),
        )
    )
    return (
        {
            "predicate": attestation.predicate,
            "attestation_id": attestation.id,
            "claim": claim,
            "previous_head": generation_base,
            "source": "rebind_generation",
        }
        if valid
        else {}
    )

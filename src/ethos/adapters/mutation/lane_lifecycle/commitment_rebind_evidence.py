"""Attestation persistence for one complete Commitment rebind."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.coordination import LaneLease
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from datetime import datetime

    from ethos.contracts.coordination import CommitmentRebindRequest
    from ethos.contracts.plan import GitEffect
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
    fact_values = values if isinstance(values, Mapping) else {}
    old_lease = fact_values.get("lease_generation")
    if not isinstance(old_lease, Mapping):
        message = "commitment_rebind_plan_lease_generation_invalid"
        raise TypeError(message)
    old_digest = str(plan.policy.get("old_commitment_digest") or "")
    new_generation = lease_generation(new_lease)
    target = {
        name: new_generation[name]
        for name in (
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }
    repository = load_repository_commitment(repo, tree_ref=request.target_commit).id
    overlay = str(fact_values.get("working_overlay_sha256") or "")
    statement = {
        "claim": {"operation": "commitment.rebind", "branch": request.branch},
        "repository": repository,
        "old_lease_generation": dict(old_lease),
        "new_lease_generation": new_generation,
        "old_commitment": {"head": request.expect_head, "digest": old_digest},
        "new_commitment": target,
        "index_tree": request.expect_index_tree,
        "target_commit": request.target_commit,
        "working_overlay_sha256": overlay,
        "result": {"git": git_state, "lease": "epoch_advanced"},
        "input_digest": canonical_json_digest(
            {
                "lease": dict(old_lease),
                "head": request.expect_head,
                "index_tree": request.expect_index_tree,
                "old_commitment_digest": old_digest,
            }
        ),
        "output_digest": canonical_json_digest(
            {
                "lease": new_generation,
                "head": request.target_commit,
                "new_commitment": target,
            }
        ),
        "observed_at": issued_at.isoformat(),
        "freshness": {
            "mode": "semantic_scope",
            "repository": repository,
            "head": request.target_commit,
            "lease_generation": new_generation,
            "working_overlay_sha256": overlay,
        },
    }
    return Attestation.issue(
        {
            "predicate": "effect:commitment-rebind",
            "verifier": request.holder_ref,
            "subject": f"commitment-rebind:{effect.digest()}",
            "issued_at": issued_at,
            "valid_from": issued_at,
            "verdict": "pass",
            "commitment_digest": old_digest,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect.digest(),
            "statement": statement,
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
    """Persist one content-addressed rebind attestation."""
    write_content_addressed(
        _attestation_path(repo, effect),
        attestation.canonical_json().encode(),
        collision="commitment_rebind_attestation_collision",
    )


def replayed_rebind_attestation(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
    plan: TransitionPlan,
) -> Attestation | None:
    """Return an exact fresh terminal attestation, or reject mismatched evidence."""
    path = _attestation_path(repo, effect)
    if not path.exists():
        return None
    try:
        attestation = Attestation.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        message = "commitment_rebind_attestation_invalid"
        raise ValueError(message) from error
    statement = mutable_json(attestation.statement)
    result = statement.get("result") if isinstance(statement, dict) else None
    if not isinstance(result, dict) or result not in (
        {"git": "applied", "lease": "epoch_advanced"},
        {"git": "recovered", "lease": "epoch_advanced"},
    ):
        message = "commitment_rebind_replay_mismatch"
        raise ValueError(message)
    git_state = result.get("git")
    if not isinstance(git_state, str):
        message = "commitment_rebind_replay_mismatch"
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
        message = "commitment_rebind_replay_mismatch"
        raise ValueError(message) from error
    if ref_head(repo, request.branch) != request.target_commit or attestation != expected:
        message = "commitment_rebind_replay_mismatch"
        raise ValueError(message)
    return attestation


def _attestation_path(repo: Path, effect: GitEffect) -> Path:
    return (
        Path(git_common_dir(repo))
        / "ethos"
        / "attestations"
        / "commitment-rebind"
        / f"{effect.digest()}.json"
    )

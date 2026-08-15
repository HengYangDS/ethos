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
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import terminal_v1_binding
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
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.semantic import canonical_utc_time
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
        "claim": {"operation": request.operation, "branch": request.branch},
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
        "observed_at": canonical_utc_time(issued_at),
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
            "commitment_digest": old_digest,
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
) -> dict[str, object]:
    """Project one exact completed rebind as current Change continuity."""
    statement = mutable_json(attestation.payload.body)
    if not isinstance(statement, dict):
        return {}
    current = lease_generation(lease)
    old = statement.get("old_lease_generation")
    new = statement.get("new_lease_generation")
    new_commitment = statement.get("new_commitment")
    result = statement.get("result")
    claim = statement.get("claim")
    if not all(isinstance(value, dict) for value in (old, new, new_commitment, result)):
        return {}
    validated = None
    try:
        if attestation.plan_digest:
            validated = validated_plan_attestation(
                repo,
                attestation.plan_digest,
                issuer=attestation.verifier,
            )
    except ValueError:
        pass
    if validated is None:
        return {}
    plan, _git_attestation = validated
    plan_values = mutable_json(plan.facts.get("values"))
    if not isinstance(plan_values, dict):
        return {}
    branch = str(current.get("branch") or "")
    previous_head = str(old.get("expected_head") or "")
    generation_head = str(new.get("expected_head") or "")
    head = str(current.get("expected_head") or "")
    binding = {
        name: new.get(name)
        for name in (
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }
    effect = GitEffect(
        updates={
            f"refs/heads/{branch}": GitRefUpdate(expected=previous_head, desired=generation_head)
        }
    )
    operation = str(plan.policy.get("operation") or "")
    expected_transition = (
        "v1-to-v2-bootstrap"
        if claim == {"operation": "v1-to-v2-bootstrap", "branch": branch}
        else "change.identity-repair"
        if plan.policy.get("transition") == "change.identity-repair"
        else "commitment.rebind"
    )
    freshness = mutable_json(statement.get("freshness"))
    plan_successor = mutable_json(plan_values.get("lease_successor"))
    planned_new = {name: value for name, value in new.items() if name != "payload_sha256"}
    now = datetime.now(UTC)
    try:
        bootstrap = expected_transition == "v1-to-v2-bootstrap"
        origin_head = generation_head if bootstrap else previous_head
        origin_carrier = str(
            (
                new_commitment.get("base_commitment_path")
                if bootstrap
                else old.get("base_commitment_path")
            )
            or ""
        )
        origin_id = (
            terminal_v1_binding(
                repo,
                tree_ref=previous_head,
                carrier=str(old.get("base_commitment_path") or ""),
                repository=False,
            )["id"]
            if bootstrap
            else plan.commitment.get("id")
        )
        load_commitment(
            repo,
            carrier=str(new_commitment.get("base_commitment_path") or ""),
            tree_ref=generation_head,
            expected_digest=str(new_commitment.get("base_commitment_digest") or ""),
        )
        generation_base = commitment_generation_origin(
            repo,
            head=origin_head,
            carrier=origin_carrier,
            change_id=str(origin_id or "").removeprefix("change:"),
        )
    except ValueError:
        generation_base = ""
    valid = (
        attestation.predicate == "effect:commitment-rebind"
        and attestation.payload.kind == "effect:commitment-rebind"
        and attestation.verdict == "pass"
        and attestation.verifier == current.get("holder_ref")
        and attestation.subject == f"commitment-rebind:{effect.digest()}"
        and attestation.effect_digest == effect.digest()
        and claim
        in (
            {"operation": "commitment-rebind", "branch": branch},
            {"operation": "v1-to-v2-bootstrap", "branch": branch},
        )
        and operation == "git.ref.compare-and-swap"
        and plan.policy.get("transition") == expected_transition
        and expected_transition
        in {"v1-to-v2-bootstrap", "commitment.rebind", "change.identity-repair"}
        and git_effect_from_plan(plan) == effect
        and attestation.commitment_digest == plan.policy.get("old_commitment_digest")
        and attestation.facts_digest == plan.inputs.facts
        and attestation.plan_digest == plan.digest
        and attestation.policy_digest == plan.inputs.policy
        and attestation.effect_digest == plan.inputs.effect
        and plan_values.get("lease_generation") == old
        and plan_successor == planned_new
        and plan_values.get("index_tree") == statement.get("index_tree")
        and plan_values.get("working_overlay_sha256") == statement.get("working_overlay_sha256")
        and plan_values.get("new_commitment_path") == new_commitment.get("base_commitment_path")
        and plan_values.get("new_commitment_bytes_sha256")
        == new_commitment.get("base_commitment_bytes_sha256")
        and plan_values.get("new_commitment_digest") == new_commitment.get("base_commitment_digest")
        and statement.get("repository") == repository_id
        and statement.get("target_commit") == generation_head
        and statement.get("index_tree") == new.get("expected_tree")
        and result
        in (
            {"git": "applied", "lease": "epoch_advanced"},
            {"git": "recovered", "lease": "epoch_advanced"},
        )
        and statement.get("old_commitment")
        == {"head": previous_head, "digest": old.get("base_commitment_digest")}
        and statement.get("input_digest")
        == canonical_json_digest(
            {
                "lease": old,
                "head": previous_head,
                "index_tree": statement.get("index_tree"),
                "old_commitment_digest": old.get("base_commitment_digest"),
            }
        )
        and statement.get("output_digest")
        == canonical_json_digest(
            {
                "lease": new,
                "head": generation_head,
                "new_commitment": new_commitment,
            }
        )
        and freshness
        == {
            "mode": "semantic_scope",
            "repository": repository_id,
            "head": generation_head,
            "lease_generation": new,
            "working_overlay_sha256": statement.get("working_overlay_sha256"),
        }
        and attestation.valid_from == attestation.issued_at
        and attestation.valid_from <= now
        and (attestation.valid_until is None or now <= attestation.valid_until)
        and bool(generation_base)
        and mutable_json(new_commitment) == binding
        and all(
            new.get(name) == current.get(name)
            for name in (
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
        )
        and all(
            old.get(name) == new.get(name)
            for name in ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
        )
        and integer(old.get("epoch"), default=-1) + 1 == integer(new.get("epoch"), default=-1)
        and attestation.commitment_digest == old.get("base_commitment_digest")
        and commitment_digest == current.get("base_commitment_digest")
        and ref_head(repo, branch) == head
        and current_tree(repo, head) == current.get("expected_tree")
        and current_tree(repo, generation_head) == new.get("expected_tree")
        and git_stdout(repo, "rev-parse", f"{generation_head}^") == previous_head
        and is_ancestor(repo, generation_head, head)
    )
    return (
        {
            "predicate": attestation.predicate,
            "attestation_id": attestation.id,
            "claim": statement["claim"],
            "previous_head": generation_base,
            "source": "rebind_generation",
        }
        if valid
        else {}
    )

"""Generic proof Attestation issuance, persistence, and admission."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.mutation.proof_admission
from ethos.adapters.admission.lease_binding import resolve_current_authority
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import normalize_checks
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.mutation.proof_artifacts import write_proof_artifact
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.start_effect import CurrentGenerationScope
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path


def _proof_issue_values(
    payload: Mapping[str, object],
) -> tuple[
    TransitionPlan,
    tuple[dict[str, object], ...],
    str,
    str,
    str,
    str,
    datetime | None,
    str,
    tuple[str, ...],
]:
    """Validate the entity-free proof issuance payload."""
    plan = payload.get("plan")
    checks = payload.get("checks")
    verdict = payload.get("verdict")
    issuer = payload.get("issuer")
    scope = payload.get("scope")
    boundary = payload.get("boundary")
    issued_at = payload.get("issued_at")
    objective = payload.get("objective", "ethos proof")
    required_gaps = payload.get("required_gaps", ())
    if not isinstance(plan, TransitionPlan):
        msg = "proof_attestation_plan_invalid"
        raise TypeError(msg)
    if not isinstance(checks, tuple):
        msg = "proof_attestation_checks_invalid"
        raise TypeError(msg)
    if (
        not isinstance(verdict, str)
        or not isinstance(issuer, str)
        or not isinstance(scope, str)
        or not isinstance(boundary, str)
        or not isinstance(objective, str)
    ):
        msg = "proof_attestation_payload_invalid"
        raise TypeError(msg)
    if not issuer or not scope or not boundary or not objective:
        msg = "proof_attestation_payload_invalid"
        raise TypeError(msg)
    if verdict not in {"pass", "block", "unknown"}:
        msg = "proof_attestation_verdict_invalid"
        raise ValueError(msg)
    if issued_at is not None and not isinstance(issued_at, datetime):
        msg = "proof_attestation_issued_at_invalid"
        raise TypeError(msg)
    if not isinstance(required_gaps, tuple):
        msg = "proof_attestation_required_gaps_invalid"
        raise TypeError(msg)
    normalized_required_gaps: tuple[str, ...] = tuple(
        gap for gap in required_gaps if isinstance(gap, str)
    )
    if len(normalized_required_gaps) != len(required_gaps):
        msg = "proof_attestation_required_gaps_invalid"
        raise TypeError(msg)
    normalized_checks = normalize_checks(checks, allow_empty=verdict != "pass")
    return (
        plan,
        normalized_checks,
        verdict,
        issuer,
        scope,
        boundary,
        issued_at,
        objective,
        normalized_required_gaps,
    )


def issue_proof_attestation(root: Path, payload: Mapping[str, object]) -> Attestation:
    """Issue a proof with a self-contained plan and executed-check closure."""
    plan, checks, verdict, issuer, scope, boundary, issued_at, objective, required_gaps = (
        _proof_issue_values(payload)
    )
    head = str(plan.facts.get("head") or "")
    if plan.verdict != "pass":
        msg = "proof_plan_not_admitted"
        raise ValueError(msg)
    if (
        current_tracked_head(root) != head
        or current_tree(root, head) != plan.facts.get("tree")
        or repository_identity(root, tree_ref=head) != plan.facts.get("repository")
    ):
        msg = "proof_attestation_live_facts_stale"
        raise ValueError(msg)
    values = plan.facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
    change_id = str(fact_values.get("change_id") or "")
    branch = current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    work_lane = load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE
    if work_lane:
        if mutable_json(fact_values.get("lease_generation")) != mutable_json(
            lease_generation(lease)
        ):
            msg = "proof_lease_generation_stale"
            raise ValueError(msg)
        authority = resolve_current_authority(
            root=root,
            branch=branch,
            lease=lease,
            actor=os.environ.get("ETHOS_ACTOR", "").strip(),
            current_head=head,
        )
        if authority.verdict != "pass":
            raise ValueError(authority.reason)
        commitment = load_profile_commitment(root, change_id=change_id or None, tree_ref=head)
    else:
        commitment = load_profile_commitment(root, change_id=change_id or None, tree_ref=head)
    policy = resolve_gate_policy(
        root,
        tree_ref=head,
        gate_ids=tuple(node.id for node in plan.nodes),
    )
    if (
        not head
        or commitment.digest() != plan.inputs.commitment
        or policy.digest != plan.inputs.policy
        or plan.inputs.prior_attestations != canonical_json_digest(plan.prior_attestations)
        or plan.inputs.effect
        != proof_effect_digest(
            commitment=plan.inputs.commitment,
            facts=plan.inputs.facts,
            policy=plan.inputs.policy,
            nodes=plan.nodes,
        )
    ):
        msg = "proof_plan_binding_mismatch"
        raise ValueError(msg)
    execution_order = tuple(node.id for node in plan.nodes)
    checks_by_id = {str(check["action_id"]): check for check in checks}
    if set(checks_by_id) != set(execution_order):
        msg = "proof_attestation_check_plan_mismatch"
        raise ValueError(msg)
    normalized = tuple(checks_by_id[gate_id] for gate_id in execution_order)
    checks_pass = all(check["verdict"] == "pass" for check in normalized)
    if verdict == "pass" and (required_gaps or not checks_pass):
        msg = "proof_attestation_verdict_mismatch"
        raise ValueError(msg)
    artifact = write_proof_artifact(proof_artifact_root(root), head, normalized)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    issued = issued_at or datetime.now(UTC)
    attestation = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "proof:execution",
            "verifier": issuer,
            "subject": f"git:commit:{head}",
            "issued_at": issued,
            "valid_from": issued,
            "valid_until": None,
            "verdict": verdict,
            "payload": {
                "kind": "proof:execution",
                "body": {
                    "claim": {"objective": objective, "verdict": verdict},
                    "scope": [scope],
                    "plane": "local",
                    "context": {"boundary": boundary},
                    "boundary": boundary,
                    "required_gaps": list(required_gaps),
                    "plan": plan.model_dump(mode="json"),
                    "artifact": artifact,
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"sha256:{digest}",),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": plan.inputs.effect,
            "mints_authority": False,
        }
    )
    gaps = proof_statement_gaps(attestation, normalized)
    structural_gaps = tuple(
        gap
        for gap in gaps
        if gap
        not in {
            "proof_attestation_verdict_block",
            "proof_attestation_verdict_unknown",
            "proof_attestation_check_not_passed",
            "trust_bearing_proof_missing",
        }
    )
    if structural_gaps:
        raise ValueError(structural_gaps[0])
    return attestation


def persist_proof_attestation(root: Path, attestation: Attestation) -> dict[str, object]:
    """Validate and select one proof Attestation in the sole Git set."""
    if attestation.predicate != "proof:execution" or not attestation.subject.startswith(
        "git:commit:"
    ):
        msg = "proof_attestation_binding_missing"
        raise ValueError(msg)
    checks, artifact_gaps = artifact_checks(proof_artifact_root(root), attestation)
    gaps = artifact_gaps if checks is None else proof_statement_gaps(attestation, checks)
    structural_gaps = [
        gap
        for gap in gaps
        if gap
        not in {
            "proof_attestation_verdict_block",
            "proof_attestation_verdict_unknown",
            "proof_attestation_check_not_passed",
            "trust_bearing_proof_missing",
        }
    ]
    if structural_gaps:
        raise ValueError(structural_gaps[0])
    return record_attestations(root, (attestation,))


def proof_plan(
    root: Path,
    *,
    head: str,
    binding_branch: str | None = None,
    change_id: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    changed_paths: tuple[str, ...] = (),
    generation_scope: CurrentGenerationScope | None = None,
) -> TransitionPlan:
    """Compile the exact commitment-, fact-, and policy-bound proof plan."""
    branch = binding_branch if binding_branch is not None else current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    work_lane = load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE
    if work_lane:
        authority = resolve_current_authority(
            root=root,
            branch=branch,
            lease=lease,
            actor=os.environ.get("ETHOS_ACTOR", "").strip(),
            current_head=head,
        )
        if authority.verdict != "pass":
            raise ValueError(authority.reason)
        commitment = load_profile_commitment(root, change_id=change_id, tree_ref=head)
    else:
        commitment = load_profile_commitment(root, change_id=change_id, tree_ref=head)
    repository = repository_identity(root, tree_ref=head)
    selected_change_id = commitment.id.removeprefix("change:")
    archived = attested_archive_transition(root, head=head, change=selected_change_id)
    policy = resolve_gate_policy(root, tree_ref=head, gate_ids=gate_ids, full=full)
    nodes = policy.nodes
    observed_scope = generation_scope or (
        current_generation_scope(
            root,
            head=head,
            repository_id=repository,
            commitment=commitment,
            lease=lease,
            fallback_paths=changed_paths,
        )
        if work_lane and changed_paths
        else None
    )
    effective_paths = (
        observed_scope.paths
        if generation_scope is not None and observed_scope is not None
        else changed_paths
    )
    facts = Facts(
        repository=repository,
        head=head,
        tree=current_tree(root, head),
        observed_at=datetime.now().astimezone(),
        values={
            "changed_paths": effective_paths,
            "change_id": selected_change_id,
            "gate_ids": tuple(node.id for node in nodes),
            **(
                {
                    "selected_carrier": observed_scope.selected_carrier,
                    "path_attributions": observed_scope.attribution_projection(),
                }
                if observed_scope is not None
                else {}
            ),
            **({"lease_generation": lease_generation(lease)} if work_lane else {}),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            *(("lease:current-generation",) if work_lane else ()),
        ),
    )
    archive_authority = (
        archived[1]
        if archived is not None
        else observed_scope.archive_authority
        if work_lane and effective_paths and observed_scope is not None
        else {}
    )
    prior_attestations = {"openspec_archive": archive_authority} if archive_authority else {}
    if observed_scope is not None and observed_scope.start_authority:
        prior_attestations["openspec_change_start"] = observed_scope.start_authority
    return compile_plan(
        commitment,
        facts,
        nodes,
        policy=policy.projection,
        prior_attestations=prior_attestations,
        required_gaps=tuple(
            dict.fromkeys(
                (*policy.gaps, *(observed_scope.gaps if observed_scope is not None else ()))
            )
        ),
    )


def proof_attestation(root: Path, head: str) -> Attestation | None:
    """Return one resolved generic proof Attestation for one exact HEAD."""
    attestation, gaps = ethos.adapters.mutation.proof_admission.proof_attestation(
        root, head, store=proof_artifact_root(root)
    )
    return attestation if not gaps else None


def proof_for_repository_transition(
    root: Path,
    head: str,
) -> tuple[Attestation | None, list[str]]:
    """Resolve the proof authority applicable to one repository transition."""
    return ethos.adapters.mutation.proof_admission.proof_attestation(
        root,
        head,
        require_archive=True,
        store=proof_artifact_root(root),
    )


def proof_gaps(root: Path, head: str) -> list[str]:
    """Return fail-closed proof Attestation gaps for one exact HEAD."""
    try:
        store = proof_artifact_root(root)
    except ValueError as error:
        if str(error) == "git_common_directory_unavailable":
            return ["attestation_set_repository_invalid"]
        raise
    _attestation, gaps = ethos.adapters.mutation.proof_admission.proof_attestation(
        root, head, store=store
    )
    return gaps


def proof_admission_report(
    root: Path,
    head: str,
    *,
    repository_transition: bool = False,
) -> dict[str, object]:
    """Project the one exact proof authority consumed by guarded transitions."""
    attestation, gaps = (
        proof_for_repository_transition(root, head)
        if repository_transition
        else ethos.adapters.mutation.proof_admission.proof_attestation(
            root,
            head,
            store=proof_artifact_root(root),
        )
    )
    next_action = ""
    if gaps:
        try:
            next_action = runtime_command(
                root,
                "prove",
                "--root",
                root.resolve().as_posix(),
                "--execute",
                "--expect-head",
                head,
                "--json",
            )
        except ValueError as error:
            runtime_gap = str(error) or error.__class__.__name__
            if runtime_gap not in gaps:
                gaps.append(runtime_gap)
            next_action = hook_runtime_binding(root)["next_action"]
    if attestation is None:
        return {
            "verdict": "block",
            "state": "missing",
            "selection": "repository_transition" if repository_transition else "current_commitment",
            "attestation": {},
            "required_gaps": gaps or ["proof_not_proven"],
            "next_action": next_action,
        }
    plan = plan_from_statement(attestation)
    return {
        "verdict": "pass",
        "state": "admitted",
        "selection": "repository_transition" if repository_transition else "current_commitment",
        "attestation": {
            "id": attestation.id,
            "predicate": attestation.predicate,
            "verdict": attestation.verdict,
            "commit": head,
            "tree": str(plan.facts.get("tree") or ""),
            "commitment_digest": attestation.commitment_digest,
            "facts_digest": attestation.facts_digest,
            "plan_digest": attestation.plan_digest,
            "policy_digest": attestation.policy_digest,
            "effect_digest": attestation.effect_digest,
            "gate_ids": tuple(node.id for node in plan.nodes),
        },
        "required_gaps": [],
        "next_action": "",
    }

"""Generic proof Attestation issuance, persistence, and admission."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path

import ethos.adapters.mutation.proof_admission
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import normalize_checks
from ethos.adapters.mutation.proof_artifacts import write_proof_artifact
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import current_branch
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from ethos.repository.policy.gates import resolve_gate_policy

_DEFAULT_ATTESTATION_DIR = Path(".ethos") / "state" / "attestations"
_TEST_ATTESTATION_STATE_DIR_ENV = "ETHOS_TEST_ATTESTATION_STATE_DIR"


def _pytest_state_active() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_XDIST_WORKER"))


def attestation_store_dir(root: Path) -> Path:
    """Return the one ignored content-addressed local Attestation store."""
    override = os.environ.get(_TEST_ATTESTATION_STATE_DIR_ENV, "").strip()
    if override and _pytest_state_active():
        path = Path(override).expanduser()
        if path.is_absolute():
            return path
        common = git_common_dir(root)
        return (Path(common).parent if common else root) / path
    common = git_common_dir(root)
    base = Path(common).parent if common else root
    return base / _DEFAULT_ATTESTATION_DIR


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
        or load_repository_commitment(root, tree_ref=head).id != plan.facts.get("repository")
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
        if fact_values.get("lease_generation") != lease_generation(lease):
            msg = "proof_lease_generation_stale"
            raise ValueError(msg)
        if os.environ.get("ETHOS_ACTOR", "").strip() != str(lease.get("holder_ref") or ""):
            msg = "lease_actor_mismatch"
            raise ValueError(msg)
    commitment = (
        load_profile_lease_bound_commitment(
            root,
            change_id=change_id or None,
            expected_head=head,
            base_commitment_digest=str(lease.get("base_commitment_digest") or ""),
        )
        if work_lane
        else load_profile_commitment(root, change_id=change_id or None, tree_ref=head)
    )
    policy = resolve_gate_policy(
        root,
        tree_ref=head,
        gate_ids=tuple(node.id for node in plan.nodes),
    )
    if (
        not head
        or commitment.digest() != plan.inputs.commitment
        or policy.digest != plan.inputs.policy
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
    artifact = write_proof_artifact(attestation_store_dir(root), head, normalized)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    issued = issued_at or datetime.now(UTC)
    attestation = Attestation.issue(
        {
            "predicate": "proof:execution",
            "verifier": issuer,
            "subject": f"git:commit:{head}",
            "issued_at": issued,
            "valid_from": issued,
            "verdict": verdict,
            "statement": {
                "claim": {"objective": objective, "verdict": verdict},
                "objective": objective,
                "repository": str(plan.facts.get("repository") or ""),
                "head": head,
                "tree": str(plan.facts.get("tree") or ""),
                "change_id": str(fact_values.get("change_id") or ""),
                "changed_paths": [str(item) for item in fact_values.get("changed_paths", ())],
                "gate_ids": list(execution_order),
                "scope": [scope],
                "plane": "local",
                "context": {"boundary": boundary},
                "boundary": boundary,
                "required_gaps": list(required_gaps),
                "inputs": {
                    "commitment": plan.inputs.commitment,
                    "facts": plan.inputs.facts,
                    "plan": plan.digest,
                    "policy": plan.inputs.policy,
                    "effect": plan.inputs.effect,
                },
                "output": {"artifact": digest, "verdict": verdict},
                "freshness": {
                    "mode": "semantic_scope",
                    "repository": str(plan.facts.get("repository") or ""),
                    "head": head,
                    "tree": str(plan.facts.get("tree") or ""),
                    "policy": plan.inputs.policy,
                },
                "plan": plan.model_dump(mode="json"),
                "commitment": commitment.identity_projection(),
                "policy": policy.projection,
                "artifact": artifact,
            },
            "evidence_refs": (f"sha256:{digest}",),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": plan.inputs.effect,
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


def persist_proof_attestation(root: Path, attestation: Attestation) -> Path:
    """Persist one proof Attestation directly by its content-addressed identity."""
    if attestation.predicate != "proof:execution" or not attestation.subject.startswith(
        "git:commit:"
    ):
        msg = "proof_attestation_binding_missing"
        raise ValueError(msg)
    checks, artifact_gaps = artifact_checks(attestation_store_dir(root), attestation)
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
    payload = attestation.canonical_json().encode("utf-8")
    Attestation.model_validate_json(payload)
    return write_content_addressed(
        attestation_store_dir(root) / f"{attestation.id}.json",
        payload,
        collision="attestation_identity_collision",
    )


def proof_plan(
    root: Path,
    *,
    head: str,
    binding_branch: str | None = None,
    change_id: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    changed_paths: tuple[str, ...] = (),
) -> TransitionPlan:
    """Compile the exact commitment-, fact-, and policy-bound proof plan."""
    branch = binding_branch if binding_branch is not None else current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    work_lane = load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE
    if work_lane:
        if lease.get("lease_state") != "valid":
            message = f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}"
            raise ValueError(message)
        if str(lease.get("expected_head") or "") != head:
            message = f"lease_head_stale:{branch}"
            raise ValueError(message)
        if os.environ.get("ETHOS_ACTOR", "").strip() != str(lease.get("holder_ref") or ""):
            message = "lease_actor_mismatch"
            raise ValueError(message)
    if work_lane:
        commitment = load_profile_lease_bound_commitment(
            root,
            change_id=change_id,
            expected_head=head,
            base_commitment_digest=str(lease.get("base_commitment_digest") or ""),
        )
    else:
        commitment = load_profile_commitment(root, change_id=change_id, tree_ref=head)
    repository = load_repository_commitment(root, tree_ref=head)
    selected_change_id = (
        commitment.id.removeprefix("change:") if commitment.id != repository.id else ""
    )
    policy = resolve_gate_policy(root, tree_ref=head, gate_ids=gate_ids, full=full)
    nodes = policy.nodes
    facts = Facts(
        repository=repository.id,
        head=head,
        tree=current_tree(root, head),
        observed_at=datetime.now().astimezone(),
        values={
            "changed_paths": changed_paths,
            "change_id": selected_change_id,
            "gate_ids": tuple(node.id for node in nodes),
            **({"lease_generation": lease_generation(lease)} if work_lane else {}),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            *(("lease:current-generation",) if work_lane else ()),
        ),
    )
    return compile_plan(
        commitment,
        facts,
        nodes,
        policy=policy.projection,
        required_gaps=policy.gaps,
    )


def proof_attestation(root: Path, head: str) -> Attestation | None:
    """Return one resolved generic proof Attestation for one exact HEAD."""
    attestation, gaps = ethos.adapters.mutation.proof_admission.proof_attestation(
        root, head, store=attestation_store_dir(root)
    )
    return attestation if not gaps else None


def proof_plan_for_attestation(root: Path, attestation: Attestation) -> TransitionPlan:
    """Return the exact plan closure after immutable proof admission."""
    return ethos.adapters.mutation.proof_admission.plan_for_attestation(
        root, attestation, store=attestation_store_dir(root)
    )


def proof_gaps(root: Path, head: str) -> list[str]:
    """Return fail-closed proof Attestation gaps for one exact HEAD."""
    _attestation, gaps = ethos.adapters.mutation.proof_admission.proof_attestation(
        root, head, store=attestation_store_dir(root)
    )
    return gaps


def proof_evidence_digest(root: Path, head: str) -> str:
    """Return the admitted proof set's stable semantic evidence identity."""
    return ethos.adapters.mutation.proof_admission.evidence_digest(
        root, head, store=attestation_store_dir(root)
    )


def proof_readiness_report(root: Path, head: str) -> dict[str, object]:
    """Describe whether the exact HEAD has a valid generic proof Attestation."""
    gaps = proof_gaps(root, head)
    independent = independent_verification_admission_report(
        root=root,
        action="publish",
        request=independent_verification_request(root=root, action="publish"),
    )
    return {
        "kind": "proof_attestation_readiness",
        "head": head,
        "state": "proven" if not gaps else "missing",
        "blocking": bool(gaps),
        "local_readiness": not gaps,
        "evidence_class": str(independent.get("evidence_class") or "local_readiness"),
        "independent_verification": independent,
        "required_gaps": gaps,
        "next_action": "" if not gaps else f"ethos prove --execute --expect-head {head} --json",
    }

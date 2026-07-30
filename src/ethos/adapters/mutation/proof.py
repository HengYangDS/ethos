"""Generic proof Attestation issuance, persistence, and admission."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import normalize_checks
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.mutation.proof_artifacts import write_content_addressed
from ethos.adapters.mutation.proof_artifacts import write_proof_artifact
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import current_branch
from ethos.contracts.authority import AuthorityQuery
from ethos.contracts.authority import descriptor_from_attestation
from ethos.contracts.authority import resolve_authority
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
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


def _plan_closure(plan: TransitionPlan) -> dict[str, object]:
    """Embed the exact transient plan inside the immutable proof statement."""
    return {
        "commitment_digest": plan.commitment_digest,
        "facts_digest": plan.facts_digest,
        "policy_digest": plan.policy_digest,
        "permissions": list(plan.permissions),
        "facts": plan.facts,
        "nodes": [node.model_dump(mode="json") for node in plan.nodes],
        "initial_verdict": plan.initial_verdict,
        "validation_issues": list(plan.validation_issues),
        "digest": plan.digest(),
    }


def issue_proof_attestation(root: Path, payload: Mapping[str, object]) -> Attestation:
    """Issue a proof with a self-contained plan and executed-check closure."""
    plan, checks, verdict, issuer, scope, boundary, issued_at, objective, required_gaps = (
        _proof_issue_values(payload)
    )
    head = str(plan.facts.get("head") or "")
    if plan.verdict != "pass":
        msg = "proof_plan_not_admitted"
        raise ValueError(msg)
    if not head or not _proof_plan_matches(root, head, plan):
        msg = "proof_plan_binding_mismatch"
        raise ValueError(msg)
    execution_order = tuple(node.id for node in plan.ordered_nodes())
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
    values = plan.facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
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
                "objective": objective,
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
                "plan": _plan_closure(plan),
                "artifact": artifact,
            },
            "evidence_refs": (f"sha256:{digest}",),
            "commitment_digest": plan.commitment_digest,
            "facts_digest": plan.facts_digest,
            "plan_digest": plan.digest(),
            "policy_digest": plan.policy_digest,
            "effect_digest": digest,
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
    if (
        attestation.predicate != "proof:execution"
        or not attestation.subject.startswith("git:commit:")
        or not all(
            (
                attestation.commitment_digest,
                attestation.facts_digest,
                attestation.plan_digest,
                attestation.policy_digest,
                attestation.effect_digest,
            )
        )
    ):
        msg = "proof_attestation_binding_missing"
        raise ValueError(msg)
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
    change_id: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    changed_paths: tuple[str, ...] = (),
) -> TransitionPlan:
    """Compile the exact commitment-, fact-, and policy-bound proof plan."""
    branch = current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    work_lane = load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE
    if work_lane:
        if lease.get("lease_state") != "valid":
            message = f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}"
            raise ValueError(message)
        if str(lease.get("expected_head") or "") != head:
            message = f"lease_head_stale:{branch}"
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
        },
        source_refs=("git:HEAD", "git:HEAD^{tree}"),
    )
    return compile_plan(
        commitment,
        facts,
        nodes,
        policy_digest=policy.digest,
        validation_issues=policy.gaps,
    )


def _proof_candidate_gaps(root: Path, head: str, attestation: Attestation) -> list[str]:
    """Validate a proof from immutable Attestation closure only."""
    if attestation.subject != f"git:commit:{head}" or attestation.statement.get("head") != head:
        return ["proof_attestation_head_mismatch"]
    checks, artifact_gaps = artifact_checks(attestation_store_dir(root), attestation)
    if artifact_gaps or checks is None:
        return artifact_gaps
    return [
        *proof_statement_gaps(attestation, checks),
        *_proof_policy_gaps(root, head, checks),
    ]


def _proof_policy_gaps(
    root: Path,
    head: str,
    checks: tuple[dict[str, object], ...],
) -> list[str]:
    gaps: list[str] = []
    policy = resolve_gate_policy(root, tree_ref=head)
    required = policy.gate_ids
    present = {str(check["action_id"]) for check in checks}
    if missing := sorted(gate_id for gate_id in required if gate_id not in present):
        gaps.append(f"proof_incomplete:{','.join(missing)}")
    selected = resolve_gate_policy(
        root,
        tree_ref=head,
        gate_ids=tuple(str(check["action_id"]) for check in checks),
    )
    gaps.extend(selected.conformance_gaps(list(checks)))
    return gaps


def _proof_query(head: str, validity: datetime) -> AuthorityQuery:
    return AuthorityQuery(
        subject=f"git:commit:{head}",
        predicate="proof:execution",
        scope=("repository",),
        plane="local",
        validity=validity,
        context=(("boundary", "repository"),),
    )


def _proof_validation(root: Path, head: str) -> tuple[Attestation | None, list[str]]:
    attestations, store_gaps = scan_attestations(attestation_store_dir(root))
    candidates = tuple(
        attestation
        for attestation in attestations
        if (
            attestation.predicate == "proof:execution"
            and attestation.subject == f"git:commit:{head}"
        )
    )
    if store_gaps or not candidates:
        return None, store_gaps or ["proof_not_proven"]
    evaluated = [
        (attestation, _proof_candidate_gaps(root, head, attestation)) for attestation in candidates
    ]
    integrity_gaps = [
        gap
        for _attestation, gaps in evaluated
        for gap in gaps
        if gap.startswith(
            (
                "proof_attestation_artifact_",
                "proof_attestation_binding_mismatch:",
                "proof_attestation_head_",
                "proof_attestation_plan_",
                "proof_attestation_tree_",
            )
        )
    ]
    if integrity_gaps:
        return None, list(dict.fromkeys(integrity_gaps))
    valid = tuple(attestation for attestation, gaps in evaluated if not gaps)
    if valid:
        validity = datetime.now(UTC)
        extracted = tuple(
            descriptor_from_attestation(attestation, validity=validity) for attestation in valid
        )
        if any(result.required_gaps for result in extracted):
            return None, ["model_gap"]
        descriptors = tuple(
            result.descriptor for result in extracted if result.descriptor is not None
        )
        resolution = resolve_authority(_proof_query(head, validity), descriptors)
        if resolution.verdict != "pass":
            return None, list(resolution.required_gaps)
        return max(valid, key=lambda attestation: (attestation.issued_at, attestation.id)), []
    latest = max(evaluated, key=lambda item: (item[0].issued_at, item[0].id))
    return None, latest[1]


def proof_attestation(root: Path, head: str) -> Attestation | None:
    """Return the newest fully valid generic proof Attestation for one exact HEAD."""
    attestation, gaps = _proof_validation(root, head)
    return attestation if not gaps else None


def proof_plan_for_attestation(root: Path, attestation: Attestation) -> TransitionPlan:
    """Return the exact plan closure after immutable proof admission."""
    head = attestation.subject.removeprefix("git:commit:")
    selected, gaps = _proof_validation(root, head)
    if gaps or selected is None or selected.id != attestation.id:
        raise ValueError(gaps[0] if gaps else "proof_attestation_not_current")
    return plan_from_statement(attestation)


def proof_gaps(root: Path, head: str) -> list[str]:
    """Return fail-closed proof Attestation gaps for one exact HEAD."""
    _attestation, gaps = _proof_validation(root, head)
    return gaps


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


def _proof_plan_matches(root: Path, head: str, plan: TransitionPlan) -> bool:
    values = plan.facts.get("values")
    changed = values.get("changed_paths", ()) if isinstance(values, Mapping) else ()
    changed_paths = (
        tuple(str(path) for path in changed) if isinstance(changed, list | tuple) else ()
    )
    change_id = str(values.get("change_id") or "") if isinstance(values, Mapping) else ""
    try:
        expected = proof_plan(
            root,
            head=head,
            change_id=change_id or None,
            gate_ids=tuple(node.id for node in plan.nodes),
            changed_paths=changed_paths,
        )
    except ValueError:
        return False
    return expected.digest() == plan.digest()

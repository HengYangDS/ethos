"""Generic proof Attestation issuance, persistence, and admission."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.repo.change_contract import load_change_contract
from ethos.adapters.repo.change_contract import load_lease_bound_change_contract
from ethos.adapters.repo.change_contract import load_repository_contract
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import current_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import RepositoryFacts
from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import adopter_gate_descriptor_gaps
from ethos.repository.policy.gates import committed_product_default_gate_ids
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_nodes
from ethos.repository.policy.gates import gate_policy_conformance_gaps
from ethos.repository.policy.gates import gate_policy_digest

_DEFAULT_ATTESTATION_DIR = Path(".ethos") / "state" / "attestations"
_TEST_ATTESTATION_STATE_DIR_ENV = "ETHOS_TEST_ATTESTATION_STATE_DIR"
_ARTIFACT_SUBDIR = Path("artifacts")
_HEX = frozenset("0123456789abcdef")
_SHA256_HEX_LENGTH = hashlib.sha256().digest_size * 2


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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
        base = Path(common).parent if common else root
        return base / path
    common = git_common_dir(root)
    return (
        Path(common).parent / _DEFAULT_ATTESTATION_DIR
        if common
        else root / _DEFAULT_ATTESTATION_DIR
    )


def _content_addressed_write(path: Path, payload: bytes, *, collision: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        try:
            existing = path.read_bytes()
        except OSError as error:
            raise ValueError(collision) from error
        if existing != payload:
            raise ValueError(collision) from None
    return path


def _normalized_diagnostics(diagnostics: object, *, action_id: str) -> list[dict[str, object]]:
    if not isinstance(diagnostics, list | tuple):
        message = f"proof_attestation_check_invalid:{action_id}"
        raise TypeError(message)
    normalized: list[dict[str, object]] = []
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, Mapping):
            message = f"proof_attestation_check_invalid:{action_id}"
            raise TypeError(message)
        item: dict[str, object] = {}
        for name, value in diagnostic.items():
            if not isinstance(name, str):
                message = f"proof_attestation_check_invalid:{action_id}"
                raise TypeError(message)
            item[name] = value
        normalized.append(item)
    return normalized


def _normalize_checks(
    checks: object, *, allow_empty: bool = False
) -> tuple[dict[str, object], ...]:
    if not isinstance(checks, list | tuple):
        msg = "proof_attestation_checks_required"
        raise TypeError(msg)
    if not checks:
        if allow_empty:
            return ()
        msg = "proof_attestation_checks_required"
        raise ValueError(msg)
    normalized: list[dict[str, object]] = []
    for raw in checks:
        if not isinstance(raw, Mapping):
            msg = "proof_attestation_check_invalid"
            raise TypeError(msg)
        action_id = raw.get("action_id")
        command = raw.get("command")
        verdict = raw.get("verdict")
        exit_code = raw.get("exit_code")
        if (
            not isinstance(action_id, str)
            or not action_id
            or not isinstance(command, list | tuple)
            or not command
            or any(not isinstance(token, str) or not token for token in command)
            or not isinstance(verdict, str)
            or verdict not in {"pass", "block", "unknown"}
            or isinstance(exit_code, bool)
            or (exit_code is not None and not isinstance(exit_code, int))
        ):
            message = f"proof_attestation_check_invalid:{action_id}"
            raise ValueError(message)
        normalized.append(
            {
                "action_id": action_id,
                "command": [str(token) for token in command],
                "exit_code": exit_code,
                "stdout": str(raw.get("stdout") or ""),
                "stderr": str(raw.get("stderr") or ""),
                "verdict": verdict,
                "evidence_class": str(raw.get("evidence_class") or ""),
                "trust_bearing": raw.get("trust_bearing") is True,
                "diagnostics": _normalized_diagnostics(
                    raw.get("diagnostics", ()), action_id=action_id
                ),
            }
        )
    if len({check["action_id"] for check in normalized}) != len(normalized):
        msg = "proof_attestation_check_duplicate"
        raise ValueError(msg)
    return tuple(normalized)


def _artifact_payload(head: str, checks: tuple[dict[str, Any], ...]) -> bytes:
    return _stable_json(
        {
            "schema_version": 1,
            "head": head,
            "checks": list(checks),
        }
    ).encode("utf-8")


def _write_proof_artifact(
    root: Path, head: str, checks: tuple[dict[str, Any], ...]
) -> dict[str, object]:
    payload = _artifact_payload(head, checks)
    digest = hashlib.sha256(payload).hexdigest()
    relative = _ARTIFACT_SUBDIR / f"{digest}.json"
    path = attestation_store_dir(root) / relative
    _content_addressed_write(
        path,
        payload,
        collision="proof_attestation_artifact_identity_collision",
    )
    return {
        "path": relative.as_posix(),
        "sha256": f"sha256:{digest}",
        "size_bytes": len(payload),
        "media_type": "application/json",
    }


def _proof_issue_values(
    payload: Mapping[str, object],
) -> tuple[
    PlanIR, tuple[dict[str, object], ...], str, str, str, str, datetime | None, str, tuple[str, ...]
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
    if not isinstance(plan, PlanIR):
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
    normalized_checks = _normalize_checks(checks, allow_empty=verdict != "pass")
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
    """Issue one generic proof Attestation and its digest-referenced detail artifact."""
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
    supplied_checks = checks
    execution_order = tuple(node.id for node in plan.ordered_nodes())
    checks_by_id = {str(check["action_id"]): check for check in supplied_checks}
    if set(checks_by_id) != set(execution_order):
        msg = "proof_attestation_check_plan_mismatch"
        raise ValueError(msg)
    normalized = tuple(checks_by_id[gate_id] for gate_id in execution_order)
    if verdict == "pass" and (
        required_gaps or any(check["verdict"] != "pass" for check in normalized)
    ):
        msg = "proof_attestation_verdict_mismatch"
        raise ValueError(msg)
    artifact = _write_proof_artifact(root, head, normalized)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    values = plan.facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
    selected_gate_ids = tuple(str(gate_id) for gate_id in fact_values.get("gate_ids", ()))
    return Attestation.issue(
        {
            "kind": "proof",
            "issuer": issuer,
            "subject": f"git:commit:{head}",
            "issued_at": issued_at or datetime.now(UTC),
            "verdict": verdict,
            "content": {
                "objective": objective,
                "head": head,
                "tree": str(plan.facts.get("tree") or ""),
                "change_id": str(fact_values.get("change_id") or ""),
                "changed_paths": [str(path) for path in fact_values.get("changed_paths", ())],
                "gate_ids": list(selected_gate_ids),
                "scope": scope,
                "boundary": boundary,
                "required_gaps": list(required_gaps),
                "artifact": artifact,
            },
            "evidence_refs": (f"sha256:{digest}",),
            "change_contract_digest": plan.contract_digest,
            "repository_facts_digest": plan.facts_digest,
            "plan_digest": plan.digest(),
            "policy_digest": plan.policy_digest,
            "effect_digest": digest,
        }
    )


def persist_proof_attestation(root: Path, attestation: Attestation) -> Path:
    """Persist one proof Attestation directly by its content-addressed identity."""
    if (
        attestation.kind != "proof"
        or not attestation.subject.startswith("git:commit:")
        or not all(
            (
                attestation.change_contract_digest,
                attestation.repository_facts_digest,
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
    return _content_addressed_write(
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
    changed_paths: tuple[str, ...] = (),
) -> PlanIR:
    """Compile the exact contract-, fact-, and policy-bound proof plan."""
    branch = current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    if load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE:
        if lease.get("lease_state") != "valid":
            message = f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}"
            raise ValueError(message)
        if str(lease.get("expected_head") or "") != head:
            message = f"lease_head_stale:{branch}"
            raise ValueError(message)
        contract = load_lease_bound_change_contract(
            root,
            change_id=change_id,
            expected_head=head,
            base_change_contract_digest=str(lease.get("base_change_contract_digest") or ""),
        )
    else:
        try:
            contract = load_change_contract(root, change_id=change_id, tree_ref=head)
        except ValueError as error:
            if change_id is not None or str(error) != "change_contract_missing":
                raise
            contract = load_repository_contract(root, tree_ref=head)
    repository = load_repository_contract(root, tree_ref=head)
    selected_change_id = contract.id.removeprefix("change:") if contract.id != repository.id else ""
    nodes, validation_issues = gate_nodes(gate_ids, root=root, tree_ref=head)
    facts = RepositoryFacts(
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
        contract,
        facts,
        nodes,
        policy_digest=gate_policy_digest(root, tree_ref=head),
        validation_issues=validation_issues,
    )


def _historical_proof_plan(
    root: Path,
    attestation: Attestation,
) -> PlanIR:
    """Recompile an immutable attestation without requiring a live lease."""
    content = attestation.content
    gate_ids = content.get("gate_ids")
    changed_paths = content.get("changed_paths")
    if not isinstance(gate_ids, tuple | list) or not isinstance(changed_paths, tuple | list):
        msg = "proof_attestation_content_invalid"
        raise TypeError(msg)
    head = str(content.get("head") or "")
    change_id = str(content.get("change_id") or "") or None
    repository = load_repository_contract(root, tree_ref=head)
    contract = (
        repository
        if change_id is None and repository.digest() == attestation.change_contract_digest
        else load_change_contract(
            root,
            change_id=change_id,
            tree_ref=head,
            expected_digest=attestation.change_contract_digest,
            require_active=False,
        )
    )
    selected_change_id = contract.id.removeprefix("change:") if contract.id != repository.id else ""
    nodes, validation_issues = gate_nodes(gate_ids, root=root, tree_ref=head)
    facts = RepositoryFacts(
        repository=repository.id,
        head=head,
        tree=current_tree(root, head),
        observed_at=datetime.now().astimezone(),
        values={
            "changed_paths": tuple(str(path) for path in changed_paths),
            "change_id": selected_change_id,
            "gate_ids": tuple(node.id for node in nodes),
        },
        source_refs=("git:HEAD", "git:HEAD^{tree}"),
    )
    return compile_plan(
        contract,
        facts,
        nodes,
        policy_digest=gate_policy_digest(root, tree_ref=head),
        validation_issues=validation_issues,
    )


def promotion_required_gate_ids(root: Path, *, tree_ref: str | None = None) -> tuple[str, ...]:
    """Return the exact default proof floor required for promotion."""
    if tree_ref is not None:
        committed = committed_product_default_gate_ids(root, tree_ref)
        if committed is not None:
            return committed
    return default_gate_ids(full=False, root=root, tree_ref=tree_ref)


def _valid_identity_name(path: Path) -> bool:
    return (
        path.suffix == ".json"
        and len(path.stem) == _SHA256_HEX_LENGTH
        and not (set(path.stem) - _HEX)
    )


def _scan_attestations(root: Path) -> tuple[tuple[Attestation, ...], list[str]]:
    store = attestation_store_dir(root)
    if not store.is_dir():
        return (), []
    attestations: list[Attestation] = []
    gaps: list[str] = []
    for path in sorted(item for item in store.iterdir() if item.is_file()):
        if not _valid_identity_name(path):
            gaps.append(f"attestation_store_filename_invalid:{path.name}")
            continue
        try:
            attestation = Attestation.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            gaps.append(f"attestation_store_invalid:{path.name}")
            continue
        if attestation.id != path.stem:
            gaps.append(f"attestation_store_identity_mismatch:{path.name}")
            continue
        attestations.append(attestation)
    return tuple(attestations), gaps


def _artifact_checks(
    root: Path, attestation: Attestation
) -> tuple[tuple[dict[str, Any], ...] | None, list[str]]:
    artifact = attestation.content.get("artifact")
    expected_relative = (_ARTIFACT_SUBDIR / f"{attestation.effect_digest}.json").as_posix()
    if not isinstance(artifact, Mapping):
        return None, ["proof_attestation_artifact_missing"]
    if (
        artifact.get("path") != expected_relative
        or artifact.get("sha256") != f"sha256:{attestation.effect_digest}"
        or attestation.evidence_refs != (f"sha256:{attestation.effect_digest}",)
    ):
        return None, ["proof_attestation_artifact_binding_mismatch"]
    path = attestation_store_dir(root) / expected_relative
    try:
        payload = path.read_bytes()
    except OSError:
        gap = (
            "proof_attestation_artifact_missing"
            if not path.is_file()
            else "proof_attestation_artifact_unavailable"
        )
        return None, [gap]
    if hashlib.sha256(payload).hexdigest() != attestation.effect_digest:
        return None, ["proof_attestation_artifact_digest_mismatch"]
    if artifact.get("size_bytes") != len(payload):
        return None, ["proof_attestation_artifact_size_mismatch"]
    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        return None, ["proof_attestation_artifact_invalid"]
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("head") != attestation.content.get("head")
    ):
        return None, ["proof_attestation_artifact_content_mismatch"]
    try:
        return _normalize_checks(document.get("checks"), allow_empty=True), []
    except (TypeError, ValueError) as error:
        return None, [str(error)]


def _attestation_binding_gaps(attestation: Attestation, plan: PlanIR) -> list[str]:
    gaps: list[str] = []
    expected_bindings = {
        "change_contract_digest": plan.contract_digest,
        "repository_facts_digest": plan.facts_digest,
        "plan_digest": plan.digest(),
        "policy_digest": plan.policy_digest,
    }
    for name, expected in expected_bindings.items():
        if getattr(attestation, name) != expected:
            gap = (
                "proof_policy_digest_stale"
                if name == "policy_digest"
                else f"proof_attestation_binding_mismatch:{name}"
            )
            gaps.append(gap)
    if attestation.content.get("tree") != plan.facts.get("tree"):
        gaps.append("proof_attestation_tree_mismatch")
    return gaps


def _attestation_check_gaps(
    attestation: Attestation,
    checks: tuple[dict[str, Any], ...],
    plan: PlanIR,
) -> list[str]:
    gaps: list[str] = []
    execution_order = tuple(node.id for node in plan.ordered_nodes())
    if tuple(str(check["action_id"]) for check in checks) != execution_order:
        gaps.append("proof_attestation_check_plan_mismatch")
    required_gaps = attestation.content.get("required_gaps")
    if not isinstance(required_gaps, tuple | list):
        gaps.append("proof_attestation_required_gaps_invalid")
    elif attestation.verdict == "pass" and required_gaps:
        gaps.append("proof_attestation_verdict_mismatch")
    if attestation.verdict != "pass":
        gaps.append(f"proof_attestation_verdict_{attestation.verdict}")
    if any(check["verdict"] != "pass" for check in checks):
        gaps.append("proof_attestation_check_not_passed")
    if not any(check["trust_bearing"] is True for check in checks):
        gaps.append("trust_bearing_proof_missing")
    return gaps


def _proof_policy_gaps(root: Path, head: str, checks: tuple[dict[str, Any], ...]) -> list[str]:
    gaps = [
        *adopter_code_correctness_gaps(root, tree_ref=head),
        *adopter_gate_descriptor_gaps(root, tree_ref=head),
    ]
    required = promotion_required_gate_ids(root, tree_ref=head)
    present = {str(check["action_id"]) for check in checks}
    if missing := sorted(gate_id for gate_id in required if gate_id not in present):
        gaps.append(f"proof_incomplete:{','.join(missing)}")
    gaps.extend(gate_policy_conformance_gaps(list(checks), root, tree_ref=head))
    return gaps


def _proof_candidate_gaps(
    root: Path, head: str, attestation: Attestation
) -> tuple[PlanIR | None, list[str]]:
    if attestation.subject != f"git:commit:{head}" or attestation.content.get("head") != head:
        return None, ["proof_attestation_head_mismatch"]
    checks, artifact_gaps = _artifact_checks(root, attestation)
    if artifact_gaps or checks is None:
        return None, artifact_gaps
    try:
        plan = _historical_proof_plan(root, attestation)
    except (TypeError, ValueError) as error:
        return None, [f"proof_attestation_plan_invalid:{error}"]
    gaps = [
        *_attestation_binding_gaps(attestation, plan),
        *_attestation_check_gaps(attestation, checks, plan),
        *_proof_policy_gaps(root, head, checks),
    ]
    return plan, list(dict.fromkeys(gaps))


def _proof_validation(root: Path, head: str) -> tuple[Attestation | None, PlanIR | None, list[str]]:
    attestations, store_gaps = _scan_attestations(root)
    if store_gaps:
        return None, None, store_gaps
    candidates = tuple(
        attestation
        for attestation in attestations
        if attestation.kind == "proof" and attestation.subject == f"git:commit:{head}"
    )
    if not candidates:
        return None, None, ["proof_not_proven"]
    evaluated = [
        (attestation, *_proof_candidate_gaps(root, head, attestation)) for attestation in candidates
    ]
    integrity_gaps = [
        gap
        for _attestation, _plan, gaps in evaluated
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
        return None, None, list(dict.fromkeys(integrity_gaps))
    valid = [
        (attestation, plan)
        for attestation, plan, gaps in evaluated
        if not gaps and plan is not None
    ]
    if valid:
        selected, plan = max(
            valid,
            key=lambda item: (item[0].issued_at, item[0].sequence, item[0].id),
        )
        return selected, plan, []
    latest = max(
        evaluated,
        key=lambda item: (item[0].issued_at, item[0].sequence, item[0].id),
    )
    return None, None, latest[2]


def proof_attestation(root: Path, head: str) -> Attestation | None:
    """Return the newest fully valid generic proof Attestation for one exact HEAD."""
    attestation, _plan, gaps = _proof_validation(root, head)
    return attestation if not gaps else None


def proof_plan_for_attestation(root: Path, attestation: Attestation) -> PlanIR:
    """Recompile and verify the transient PlanIR bound by one proof Attestation."""
    head = attestation.subject.removeprefix("git:commit:")
    selected, plan, gaps = _proof_validation(root, head)
    if gaps or selected is None or plan is None or selected.id != attestation.id:
        raise ValueError(gaps[0] if gaps else "proof_attestation_not_current")
    return plan


def proof_gaps(root: Path, head: str) -> list[str]:
    """Return fail-closed proof Attestation gaps for one exact HEAD."""
    _attestation, _plan, gaps = _proof_validation(root, head)
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


def _proof_plan_matches(root: Path, head: str, plan: PlanIR) -> bool:
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

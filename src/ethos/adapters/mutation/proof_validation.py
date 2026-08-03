"""Validate self-contained proof Attestation closure from current bindings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_STATEMENT_FIELDS = {
    "artifact",
    "boundary",
    "change_id",
    "changed_paths",
    "claim",
    "commitment",
    "context",
    "freshness",
    "gate_ids",
    "head",
    "inputs",
    "objective",
    "output",
    "plan",
    "plane",
    "policy",
    "repository",
    "required_gaps",
    "scope",
    "tree",
}
_FACT_VALUE_FIELDS = {"change_id", "changed_paths", "gate_ids", "lease_generation"}
_PLAN_INVALID = "proof_attestation_plan_invalid"
_POLICY_INVALID = "proof_attestation_policy_invalid"


def plan_from_statement(attestation: Attestation) -> TransitionPlan:
    """Rehydrate the exact transient plan carried by an admitted proof statement."""
    statement = string_mapping(attestation.model_dump(mode="json").get("statement"))
    closure = statement.get("plan")
    if not isinstance(closure, Mapping):
        message = "proof_attestation_plan_missing"
        raise TypeError(message)
    try:
        plan = TransitionPlan.model_validate(closure)
    except (TypeError, ValueError) as error:
        message = (
            "proof_attestation_plan_digest_mismatch"
            if "transition_plan_digest_mismatch" in str(error)
            else "proof_attestation_plan_invalid"
        )
        raise ValueError(message) from error
    try:
        facts = _facts(plan)
    except (TypeError, ValueError) as error:
        message = "proof_attestation_plan_invalid"
        raise ValueError(message) from error
    if facts.digest() != plan.inputs.facts:
        message = "proof_attestation_facts_digest_mismatch"
        raise ValueError(message)
    return plan


def _commitment(value: object) -> Commitment | None:
    try:
        return Commitment.model_validate_json(json.dumps(mutable_json(value)))
    except (TypeError, ValueError):
        return None


def _facts(plan: TransitionPlan) -> Facts:
    payload = mutable_json(plan.facts)
    if not isinstance(payload, dict):
        raise TypeError(_PLAN_INVALID)
    return Facts.model_validate_json(
        json.dumps(
            {
                **payload,
                "observed_at": datetime.now(UTC).isoformat(),
                "source_refs": tuple(string_sequence(payload.get("source_refs"))),
            }
        )
    )


def _policy_parts(policy: Mapping[str, object]) -> tuple[tuple[PlanNode, ...], tuple[str, ...]]:
    raw_gates = policy.get("gates")
    raw_gaps = policy.get("gaps")
    if not isinstance(raw_gates, tuple | list) or not isinstance(raw_gaps, tuple | list):
        raise TypeError(_POLICY_INVALID)
    nodes: list[PlanNode] = []
    for raw_gate in raw_gates:
        if not isinstance(raw_gate, Mapping):
            raise TypeError(_POLICY_INVALID)
        gate_id = raw_gate.get("id")
        command = raw_gate.get("execution_identity")
        dependencies = raw_gate.get("depends_on")
        if (
            not isinstance(gate_id, str)
            or not gate_id
            or not isinstance(command, tuple | list)
            or not command
            or not all(isinstance(token, str) and token for token in command)
            or not isinstance(dependencies, tuple | list)
            or not all(isinstance(item, str) and item for item in dependencies)
        ):
            raise TypeError(_POLICY_INVALID)
        nodes.append(
            PlanNode(
                id=gate_id,
                kind="check",
                command=tuple(string_sequence(command)),
                depends_on=tuple(string_sequence(dependencies)),
            )
        )
    if not all(isinstance(gap, str) and gap for gap in raw_gaps):
        raise ValueError(_POLICY_INVALID)
    return tuple(nodes), tuple(string_sequence(raw_gaps))


def _semantic_gaps(
    plan: TransitionPlan,
    commitment: Commitment,
    policy: Mapping[str, object],
) -> list[str]:
    try:
        facts = _facts(plan)
        nodes, policy_gaps = _policy_parts(policy)
    except (TypeError, ValueError) as error:
        return [str(error)]
    gate_ids = tuple(node.id for node in nodes)
    fact_values = facts.values
    fact_gate_ids = tuple(string_sequence(fact_values.get("gate_ids")))
    if (
        len(gate_ids) != len(set(gate_ids))
        or gate_ids != tuple(node.id for node in plan.nodes)
        or fact_gate_ids != gate_ids
    ):
        return ["proof_attestation_policy_gate_set_mismatch"]
    canonical = compile_plan(
        commitment,
        facts,
        nodes,
        policy=dict(policy),
        required_gaps=policy_gaps,
    )
    if canonical.inputs.effect != plan.inputs.effect:
        return ["proof_attestation_effect_digest_mismatch"]
    if canonical != plan:
        details = tuple(gap for gap in canonical.required_gaps if gap not in plan.required_gaps)
        suffix = f":{details[0]}" if details else ""
        return [f"proof_attestation_plan_semantics_mismatch{suffix}"]
    return []


def _projection_gaps(
    plan: TransitionPlan,
    commitment: object,
    policy: object,
) -> list[str]:
    parsed_commitment = _commitment(commitment)
    commitment_digest = parsed_commitment.digest() if parsed_commitment is not None else ""
    policy_mapping = (
        {str(key): value for key, value in policy.items()} if isinstance(policy, Mapping) else None
    )
    policy_digest = canonical_json_digest(policy_mapping) if policy_mapping is not None else ""
    gaps = []
    if commitment_digest != plan.inputs.commitment:
        gaps.append("proof_attestation_commitment_digest_mismatch")
    if policy_digest != plan.inputs.policy:
        gaps.append("proof_policy_digest_stale")
    if not gaps and parsed_commitment is not None and policy_mapping is not None:
        gaps.extend(_semantic_gaps(plan, parsed_commitment, policy_mapping))
    return gaps


def _binding_gaps(attestation: Attestation, plan: TransitionPlan) -> list[str]:
    bindings = {
        "commitment_digest": plan.inputs.commitment,
        "facts_digest": plan.inputs.facts,
        "plan_digest": plan.digest,
        "policy_digest": plan.inputs.policy,
        "effect_digest": plan.inputs.effect,
    }
    return [
        "proof_policy_digest_stale"
        if name == "policy_digest"
        else f"proof_attestation_binding_mismatch:{name}"
        for name, expected in bindings.items()
        if getattr(attestation, name) != expected
    ]


def _result_gaps(
    attestation: Attestation,
    checks: tuple[dict[str, Any], ...],
    required_gaps: tuple | list,
) -> list[str]:
    gaps: list[str] = []
    if attestation.verdict == "pass" and required_gaps:
        gaps.append("proof_attestation_verdict_mismatch")
    if attestation.verdict != "pass":
        gaps.append(f"proof_attestation_verdict_{attestation.verdict}")
    if any(check["verdict"] != "pass" for check in checks):
        gaps.append("proof_attestation_check_not_passed")
    if not any(check["trust_bearing"] is True for check in checks):
        gaps.append("trust_bearing_proof_missing")
    return gaps


def _context_gaps(statement: Mapping[str, object]) -> list[str]:
    scope, plane, context, boundary = (
        statement.get("scope"),
        statement.get("plane"),
        statement.get("context"),
        statement.get("boundary"),
    )
    gaps: list[str] = []
    if (
        not isinstance(scope, tuple | list)
        or len(scope) != 1
        or not isinstance(scope[0], str)
        or not scope[0]
    ):
        gaps.append("proof_attestation_scope_mismatch")
    if plane != "local":
        gaps.append("proof_attestation_plane_mismatch")
    if not isinstance(boundary, str) or boundary not in {"focused", "repository"}:
        gaps.append("proof_attestation_boundary_mismatch")
    elif context != {"boundary": boundary}:
        gaps.append("proof_attestation_context_mismatch")
    return gaps


def _statement_gaps(
    attestation: Attestation,
    statement: Mapping[str, object],
    plan: TransitionPlan,
) -> list[str]:
    values = plan.facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
    artifact = string_mapping(statement.get("artifact"))
    artifact_digest = str(artifact.get("sha256") or "").removeprefix("sha256:")
    expected = {
        "change_id": str(fact_values.get("change_id") or ""),
        "changed_paths": string_sequence(fact_values.get("changed_paths")),
        "claim": {"objective": statement.get("objective"), "verdict": attestation.verdict},
        "repository": plan.facts.get("repository"),
        "inputs": {
            "commitment": plan.inputs.commitment,
            "facts": plan.inputs.facts,
            "plan": plan.digest,
            "policy": plan.inputs.policy,
            "effect": plan.inputs.effect,
        },
        "output": {"artifact": artifact_digest, "verdict": attestation.verdict},
        "freshness": {
            "mode": "semantic_scope",
            "repository": plan.facts.get("repository"),
            "head": plan.facts.get("head"),
            "tree": plan.facts.get("tree"),
            "policy": plan.inputs.policy,
        },
    }
    gaps = [
        f"proof_attestation_{name}_mismatch"
        for name, value in expected.items()
        if statement.get(name) != value
    ]
    if statement.keys() - _STATEMENT_FIELDS or fact_values.keys() - _FACT_VALUE_FIELDS:
        gaps.append("model_gap")
    gaps.extend(_context_gaps(statement))
    if plan.facts.get("head") != statement.get("head"):
        gaps.append("proof_attestation_plan_head_mismatch")
    if statement.get("tree") != plan.facts.get("tree"):
        gaps.append("proof_attestation_tree_mismatch")
    return gaps


def _gate_gaps(
    plan: TransitionPlan,
    checks: tuple[dict[str, Any], ...],
    gate_ids: tuple | list,
    policy: object,
) -> list[str]:
    execution_order = tuple(node.id for node in plan.nodes)
    gaps = []
    if tuple(str(item) for item in gate_ids) != execution_order:
        gaps.append("proof_attestation_gate_plan_mismatch")
    if tuple(str(check["action_id"]) for check in checks) != execution_order:
        gaps.append("proof_attestation_check_plan_mismatch")
    gates = policy.get("gates") if isinstance(policy, Mapping) else None
    by_gate = (
        {str(gate.get("id") or ""): gate for gate in gates if isinstance(gate, Mapping)}
        if isinstance(gates, tuple | list)
        else {}
    )
    for node, check in zip(plan.nodes, checks, strict=False):
        gate = by_gate.get(node.id)
        if (
            gate is None
            or tuple(string_sequence(gate.get("execution_identity"))) != node.command
            or tuple(string_sequence(check.get("command"))) != node.command
            or check.get("trust_bearing") is not gate.get("trust_bearing")
            or check.get("evidence_class") != gate.get("evidence_class")
        ):
            gaps.append(f"proof_gate_not_policy_conformant:{node.id}")
    return gaps


def proof_statement_gaps(
    attestation: Attestation,
    checks: tuple[dict[str, Any], ...],
) -> list[str]:
    """Validate generic proof closure from immutable statement and artifact only."""
    statement = string_mapping(attestation.model_dump(mode="json").get("statement"))
    gate_ids = statement.get("gate_ids")
    required_gaps = statement.get("required_gaps")
    if not isinstance(gate_ids, tuple | list):
        return ["proof_attestation_gate_ids_invalid"]
    if not isinstance(required_gaps, tuple | list):
        return ["proof_attestation_required_gaps_invalid"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return [str(error)]
    gaps = _binding_gaps(attestation, plan)
    commitment = statement.get("commitment")
    policy = statement.get("policy")
    gaps.extend(_projection_gaps(plan, commitment, policy))
    gaps.extend(_statement_gaps(attestation, statement, plan))
    gaps.extend(_gate_gaps(plan, checks, gate_ids, policy))
    return [*gaps, *_result_gaps(attestation, checks, required_gaps)]

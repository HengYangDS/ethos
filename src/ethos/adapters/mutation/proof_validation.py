"""Validate proof execution results against one carried TransitionPlan closure."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_STATEMENT_FIELDS = {
    "artifact",
    "boundary",
    "claim",
    "context",
    "plan",
    "plane",
    "required_gaps",
    "scope",
}
_FORMER_STATEMENT_FIELDS = (
    "change_id",
    "changed_paths",
    "commitment",
    "freshness",
    "gate_ids",
    "head",
    "inputs",
    "objective",
    "output",
    "policy",
    "repository",
    "tree",
)


def plan_from_statement(attestation: Attestation) -> TransitionPlan:
    """Return the exact immutable plan carried by a proof statement."""
    closure = string_mapping(attestation.model_dump(mode="json").get("statement")).get("plan")
    if not isinstance(closure, Mapping):
        message = "proof_attestation_plan_missing"
        raise TypeError(message)
    try:
        return TransitionPlan.model_validate(closure)
    except (TypeError, ValueError) as error:
        detail = str(error)
        message = (
            "model_gap"
            if "transition_plan_model_gap" in detail
            else "proof_attestation_plan_digest_mismatch"
            if "transition_plan_digest_mismatch" in detail
            else "proof_attestation_plan_invalid"
        )
        raise ValueError(message) from error


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
    scope = statement.get("scope")
    plane = statement.get("plane")
    context = statement.get("context")
    boundary = statement.get("boundary")
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


def former_official_statement_projection(
    attestation: Attestation, plan: TransitionPlan
) -> dict[str, object]:
    """Derive the exact redundant projection emitted by the former official runtime."""
    statement = string_mapping(attestation.model_dump(mode="json").get("statement"))
    claim = string_mapping(statement.get("claim"))
    artifact = string_mapping(statement.get("artifact"))
    facts_value = mutable_json(plan.facts)
    facts = facts_value if isinstance(facts_value, dict) else {}
    values = facts.get("values")
    values = values if isinstance(values, dict) else {}
    artifact_digest = str(artifact.get("sha256") or "").removeprefix("sha256:")
    return {
        "change_id": str(values.get("change_id") or ""),
        "changed_paths": list(string_sequence(values.get("changed_paths"))),
        "commitment": mutable_json(plan.commitment),
        "freshness": {
            "mode": "semantic_scope",
            "repository": facts.get("repository"),
            "head": facts.get("head"),
            "tree": facts.get("tree"),
            "policy": plan.inputs.policy,
        },
        "gate_ids": [node.id for node in plan.nodes],
        "head": facts.get("head"),
        "inputs": {
            "commitment": plan.inputs.commitment,
            "facts": plan.inputs.facts,
            "plan": plan.digest,
            "policy": plan.inputs.policy,
            "effect": plan.inputs.effect,
        },
        "objective": claim.get("objective"),
        "output": {"artifact": artifact_digest, "verdict": attestation.verdict},
        "policy": mutable_json(plan.policy),
        "repository": facts.get("repository"),
        "tree": facts.get("tree"),
    }


def _statement_schema_gaps(
    attestation: Attestation, plan: TransitionPlan, statement: Mapping[str, object]
) -> list[str]:
    fields = set(statement)
    if fields == _STATEMENT_FIELDS:
        return []
    if fields != _STATEMENT_FIELDS | set(_FORMER_STATEMENT_FIELDS):
        return ["model_gap"]
    expected = former_official_statement_projection(attestation, plan)
    return [
        f"proof_attestation_former_projection_mismatch:{field}"
        for field in _FORMER_STATEMENT_FIELDS
        if mutable_json(statement.get(field)) != mutable_json(expected[field])
    ]


def _statement_gaps(
    attestation: Attestation, plan: TransitionPlan, statement: Mapping[str, object]
) -> list[str]:
    claim = statement.get("claim")
    gaps = _statement_schema_gaps(attestation, plan, statement)
    if (
        not isinstance(claim, Mapping)
        or not isinstance(claim.get("objective"), str)
        or not claim.get("objective")
        or claim.get("verdict") != attestation.verdict
        or set(claim) != {"objective", "verdict"}
    ):
        gaps.append("proof_attestation_claim_mismatch")
    gaps.extend(_context_gaps(statement))
    return gaps


def _gate_gaps(
    plan: TransitionPlan,
    checks: tuple[dict[str, Any], ...],
) -> list[str]:
    execution_order = tuple(node.id for node in plan.nodes)
    gaps = []
    if tuple(str(check["action_id"]) for check in checks) != execution_order:
        gaps.append("proof_attestation_check_plan_mismatch")
    gates = plan.policy.get("gates")
    by_gate = (
        {str(gate.get("id") or ""): gate for gate in gates if isinstance(gate, Mapping)}
        if isinstance(gates, tuple | list)
        else {}
    )
    for node, check in zip(plan.nodes, checks, strict=False):
        gate = by_gate.get(node.id)
        if (
            gate is None
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
    """Validate a proof envelope without recompiling its semantic closure."""
    statement = string_mapping(attestation.model_dump(mode="json").get("statement"))
    required_gaps = statement.get("required_gaps")
    if not isinstance(required_gaps, tuple | list):
        return ["proof_attestation_required_gaps_invalid"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return [str(error)]
    return [
        *_binding_gaps(attestation, plan),
        *_statement_gaps(attestation, plan, statement),
        *_gate_gaps(plan, checks),
        *_result_gaps(attestation, checks, required_gaps),
    ]

"""Validate self-contained proof Attestation closure without historical replay."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.plan import TransitionPlan
from ethos.contracts.semantic import Facts
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


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
        facts = Facts.model_validate(
            {
                **plan.facts,
                "observed_at": datetime.now(UTC),
                "source_refs": tuple(string_sequence(plan.facts.get("source_refs"))),
            }
        )
    except (TypeError, ValueError) as error:
        message = "proof_attestation_plan_invalid"
        raise ValueError(message) from error
    if facts.digest() != plan.inputs.facts:
        message = "proof_attestation_facts_digest_mismatch"
        raise ValueError(message)
    return plan


def _binding_gaps(attestation: Attestation, plan: TransitionPlan) -> list[str]:
    bindings = {
        "commitment_digest": plan.inputs.commitment,
        "facts_digest": plan.inputs.facts,
        "plan_digest": plan.digest,
        "policy_digest": plan.inputs.policy,
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


def proof_statement_gaps(
    attestation: Attestation,
    checks: tuple[dict[str, Any], ...],
) -> list[str]:
    """Validate generic proof closure from immutable statement and artifact only."""
    statement = attestation.statement
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
    expected = {
        "claim": {"objective": statement.get("objective"), "verdict": attestation.verdict},
        "repository": plan.facts.get("repository"),
        "inputs": {
            "commitment": plan.inputs.commitment,
            "facts": plan.inputs.facts,
            "plan": plan.digest,
            "policy": plan.inputs.policy,
        },
        "output": {"artifact": attestation.effect_digest, "verdict": attestation.verdict},
        "freshness": {
            "mode": "semantic_scope",
            "repository": plan.facts.get("repository"),
            "head": plan.facts.get("head"),
            "tree": plan.facts.get("tree"),
            "policy": plan.inputs.policy,
        },
    }
    gaps.extend(
        f"proof_attestation_{name}_mismatch"
        for name, value in expected.items()
        if statement.get(name) != value
    )
    gaps.extend(_context_gaps(statement))
    if plan.facts.get("head") != statement.get("head"):
        gaps.append("proof_attestation_plan_head_mismatch")
    if statement.get("tree") != plan.facts.get("tree"):
        gaps.append("proof_attestation_tree_mismatch")
    execution_order = tuple(node.id for node in plan.nodes)
    if tuple(str(item) for item in gate_ids) != execution_order:
        gaps.append("proof_attestation_gate_plan_mismatch")
    if tuple(str(check["action_id"]) for check in checks) != execution_order:
        gaps.append("proof_attestation_check_plan_mismatch")
    return [*gaps, *_result_gaps(attestation, checks, required_gaps)]

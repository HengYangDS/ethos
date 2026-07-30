"""Validate self-contained proof Attestation closure without historical replay."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


def _closure_plan(closure: Mapping[str, object]) -> TransitionPlan:
    raw_nodes = closure.get("nodes")
    facts = closure.get("facts")
    if not isinstance(raw_nodes, tuple | list) or not isinstance(facts, Mapping):
        message = "proof_attestation_plan_invalid"
        raise TypeError(message)
    nodes = tuple(
        PlanNode.model_validate(
            {
                "id": str(node.get("id") or ""),
                "kind": node.get("kind"),
                "command": tuple(string_sequence(node.get("command"))),
                "depends_on": tuple(string_sequence(node.get("depends_on"))),
            }
        )
        for node in map(string_mapping, raw_nodes)
    )
    return TransitionPlan.model_validate(
        {
            "commitment_digest": str(closure["commitment_digest"]),
            "facts_digest": str(closure["facts_digest"]),
            "policy_digest": str(closure["policy_digest"]),
            "permissions": tuple(string_sequence(closure.get("permissions"))),
            "facts": string_mapping(facts),
            "nodes": nodes,
            "initial_verdict": closure.get("initial_verdict", "pass"),
            "validation_issues": tuple(string_sequence(closure.get("validation_issues"))),
        }
    )


def plan_from_statement(attestation: Attestation) -> TransitionPlan:
    """Rehydrate the exact transient plan carried by an admitted proof statement."""
    statement = string_mapping(attestation.model_dump(mode="json").get("statement"))
    closure = statement.get("plan")
    if not isinstance(closure, Mapping):
        message = "proof_attestation_plan_missing"
        raise TypeError(message)
    try:
        plan = _closure_plan(string_mapping(closure))
    except (KeyError, TypeError, ValueError) as error:
        message = "proof_attestation_plan_invalid"
        raise ValueError(message) from error
    digest = closure.get("digest")
    if not isinstance(digest, str) or digest != plan.digest():
        message = "proof_attestation_plan_digest_mismatch"
        raise ValueError(message)
    return plan


def _binding_gaps(attestation: Attestation, plan: TransitionPlan) -> list[str]:
    bindings = {
        "commitment_digest": plan.commitment_digest,
        "facts_digest": plan.facts_digest,
        "plan_digest": plan.digest(),
        "policy_digest": plan.policy_digest,
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
    if statement.get("tree") != plan.facts.get("tree"):
        gaps.append("proof_attestation_tree_mismatch")
    execution_order = tuple(node.id for node in plan.ordered_nodes())
    if tuple(str(item) for item in gate_ids) != execution_order:
        gaps.append("proof_attestation_gate_plan_mismatch")
    if tuple(str(check["action_id"]) for check in checks) != execution_order:
        gaps.append("proof_attestation_check_plan_mismatch")
    return [*gaps, *_result_gaps(attestation, checks, required_gaps)]

"""Validate proof execution results against one carried TransitionPlan closure."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import execution_source_gaps
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import execution_succeeded
from ethos.contracts.verdict import observation_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import quality_obligation_gaps

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.verdict import Verdict

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


def assess_proof_execution(
    *,
    audit: dict[str, object],
    lifecycle: dict[str, object],
    plan: TransitionPlan,
    checks: list[dict[str, object]],
    runs_ok: bool,
    execute: bool,
    full: bool,
    expected_head: str | None,
    current_head: str,
    scope_gaps: tuple[str, ...],
) -> tuple[Verdict, tuple[str, ...]]:
    """Reduce current execution observations; issuance still independently validates proof."""
    verdicts_ok = bool(checks) and all(execution_succeeded(check) for check in checks)
    trust_bearing_ok = any(
        check["trust_bearing"] is True and check["verdict"] == "pass" for check in checks
    )
    failed_gate_gaps = (
        tuple(
            f"gate_failed:{check['action_id']}"
            if check["verdict"] == "block"
            else f"gate_unknown:{check['action_id']}"
            for check in checks
            if check["verdict"] != "pass"
        )
        if execute
        else ()
    )
    trust_gaps = (
        ("trust_bearing_proof_missing",) if execute and verdicts_ok and not trust_bearing_ok else ()
    )
    required_gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + tuple(string_sequence(lifecycle.get("required_gaps")))
            + plan.required_gaps
            + failed_gate_gaps
            + (("full_proof_requires_execute",) if full and not execute else ())
            + trust_gaps
            + (
                ("expected_head_mismatch",)
                if expected_head is not None and expected_head != current_head
                else ()
            )
            + scope_gaps
        )
    )
    check_verdict: Verdict = (
        reduce_verdicts(*(cast("Verdict", check["verdict"]) for check in checks))
        if execute and checks
        else observation_verdict(ok=runs_ok)
        if checks
        else "unknown"
    )
    return (
        reduce_verdicts(
            report_verdict(audit),
            report_verdict(lifecycle),
            plan.verdict,
            check_verdict,
            required_gaps=required_gaps,
        ),
        required_gaps,
    )


def plan_from_statement(attestation: Attestation) -> TransitionPlan:
    """Return the exact immutable plan carried by a proof statement."""
    closure = string_mapping(attestation.payload.body).get("plan")
    if not isinstance(closure, Mapping):
        message = "proof_attestation_plan_missing"
        raise TypeError(message)
    try:
        return TransitionPlan.model_validate(mutable_json(closure))
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
) -> list[str]:
    gaps: list[str] = []
    if attestation.verdict != "pass":
        gaps.append(f"proof_attestation_verdict_{attestation.verdict}")
    if any(not execution_succeeded(check) for check in checks):
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


def _statement_schema_gaps(
    statement: Mapping[str, object],
) -> list[str]:
    return [] if set(statement) == _STATEMENT_FIELDS else ["model_gap"]


def _statement_gaps(attestation: Attestation, statement: Mapping[str, object]) -> list[str]:
    claim = statement.get("claim")
    gaps = _statement_schema_gaps(statement)
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
    gaps.extend(
        quality_obligation_gaps(plan.policy, checks, source_tree=str(plan.facts.get("tree") or ""))
    )
    return gaps


def proof_statement_gaps(
    attestation: Attestation,
    checks: tuple[dict[str, Any], ...],
) -> list[str]:
    """Validate a proof envelope without recompiling its semantic closure."""
    if attestation.payload.kind != "proof:execution":
        return ["proof_attestation_payload_kind_invalid"]
    statement = string_mapping(attestation.payload.body)
    required_gaps = statement.get("required_gaps")
    if not isinstance(required_gaps, tuple | list):
        return ["proof_attestation_required_gaps_invalid"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return [str(error)]
    return [
        *_binding_gaps(attestation, plan),
        *execution_source_gaps(plan.facts),
        *_statement_gaps(attestation, statement),
        *_gate_gaps(plan, checks),
        *_result_gaps(attestation, checks),
    ]

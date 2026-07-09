"""Workflow contract helpers for ETHOS derived runtime projections.

These helpers validate `system/workflows.toml` as a contract. They do not run a
workflow engine and do not store lifecycle truth.
"""

from __future__ import annotations

from typing import Any

from ethos_core.invalid_states import NODE_ORDER

_ALLOWED_NODE_KINDS = {"control", "producer", "action", "handoff", "guardrail"}
_ALLOWED_ENFORCEMENT = {"guarded", "handoff-guarded", "evidence-only", "advisory"}
_ALLOWED_METRICS = {"pass_at_k", "pass_power_k", "weighted_score", "instability_gap"}
_EXPECTED_TRANSITION_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
)


def workflow_contract_report(contract: dict[str, Any]) -> dict[str, Any]:
    """Validate and summarize the declared workflow runtime contract."""
    states = set(_strings(contract.get("lifecycle", {}).get("states")))
    guards = set(contract.get("guards", {})) if isinstance(contract.get("guards"), dict) else set()
    transitions = [item for item in contract.get("transition", []) if isinstance(item, dict)]
    nodes = [item for item in contract.get("node", []) if isinstance(item, dict)]
    events = [item for item in contract.get("event", []) if isinstance(item, dict)]
    runtime = contract.get("runtime", {}) if isinstance(contract.get("runtime"), dict) else {}
    eval_contract = contract.get("eval", {}) if isinstance(contract.get("eval"), dict) else {}
    evolution = contract.get("evolution", {}) if isinstance(contract.get("evolution"), dict) else {}

    gaps: list[str] = []
    gaps.extend(_transition_gaps(states, guards, transitions))
    gaps.extend(_node_gaps(nodes))
    gaps.extend(_runtime_gaps(runtime))
    gaps.extend(_event_gaps(events))
    gaps.extend(_eval_gaps(eval_contract))
    gaps.extend(_evolution_gaps(evolution))
    return {
        "ok": not gaps,
        "states": sorted(states),
        "transition_count": len(transitions),
        "node_count": len(nodes),
        "event_count": len(events),
        "guard_count": len(guards),
        "nodes": [_node_summary(item) for item in nodes],
        "runtime": runtime,
        "eval": eval_contract,
        "evolution": evolution,
        "required_gaps": list(dict.fromkeys(gaps)),
    }


def planned_transition_projection(
    contract: dict[str, Any],
    *,
    changed_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return deterministic transition projection data for `ethos plan`."""
    transitions = [item for item in contract.get("transition", []) if isinstance(item, dict)]
    return {
        "kind": "workflow_runtime_plan",
        "truth_boundary": "derived_repository_projection",
        "changed_path_count": len(changed_paths),
        "changed_paths": list(changed_paths),
        "transitions": [
            {
                "from": str(item.get("from", "")),
                "to": str(item.get("to", "")),
                "guard": str(item.get("guard", "")),
                "required_facts": _strings(item.get("required_facts")),
                "invalid_states": _strings(item.get("invalid_states")),
            }
            for item in transitions
        ],
        "nodes": workflow_contract_report(contract)["nodes"],
    }


def _transition_gaps(
    states: set[str],
    guards: set[str],
    transitions: list[dict[str, Any]],
) -> list[str]:
    taxonomy = set(NODE_ORDER)
    gaps: list[str] = []
    if not transitions:
        gaps.append("workflow_transition_missing")
    for index, item in enumerate(transitions):
        source = str(item.get("from", ""))
        target = str(item.get("to", ""))
        guard = str(item.get("guard", ""))
        invalid_state = str(item.get("invalid_state", ""))
        invalid_states = set(_strings(item.get("invalid_states")))
        if source not in states:
            gaps.append(f"workflow_transition_state_unknown:{index}:from:{source}")
        if target not in states:
            gaps.append(f"workflow_transition_state_unknown:{index}:to:{target}")
        if guard not in guards:
            gaps.append(f"workflow_transition_guard_unknown:{index}:{guard}")
        if invalid_state not in taxonomy:
            gaps.append(f"workflow_transition_invalid_state_unknown:{index}:{invalid_state}")
        if invalid_state and invalid_state not in invalid_states:
            gaps.append(f"workflow_transition_invalid_state_not_listed:{index}:{invalid_state}")
        unknown_invalid = invalid_states - taxonomy
        gaps.extend(
            f"workflow_transition_invalid_state_unknown:{index}:{unknown}"
            for unknown in sorted(unknown_invalid)
        )
    return gaps


def _node_gaps(nodes: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    ids: set[str] = set()
    for index, item in enumerate(nodes):
        node_id = str(item.get("id", ""))
        if not node_id:
            gaps.append(f"workflow_node_id_missing:{index}")
        elif node_id in ids:
            gaps.append(f"workflow_node_id_duplicate:{node_id}")
        ids.add(node_id)
        kind = str(item.get("kind", ""))
        enforcement = str(item.get("enforcement", ""))
        if kind not in _ALLOWED_NODE_KINDS:
            gaps.append(f"workflow_node_kind_unknown:{node_id or index}:{kind}")
        if enforcement not in _ALLOWED_ENFORCEMENT:
            gaps.append(f"workflow_node_enforcement_unknown:{node_id or index}:{enforcement}")
        if enforcement == "handoff-guarded" and kind != "handoff":
            gaps.append(f"workflow_node_handoff_enforcement_kind_mismatch:{node_id}")
        if kind == "guardrail" and enforcement == "advisory":
            gaps.append(f"workflow_guardrail_advisory:{node_id}")
    return gaps


def _runtime_gaps(runtime: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if runtime.get("truth_boundary") != "derived_repository_projection":
        gaps.append("workflow_runtime_truth_boundary_invalid")
    commands = tuple(_strings(runtime.get("public_lifecycle_commands")))
    if commands != _EXPECTED_TRANSITION_COMMANDS:
        gaps.append("workflow_runtime_public_commands_invalid")
    gaps.extend(
        f"workflow_runtime_{key}_missing"
        for key in ("run_state_schema", "handoff_package_schema")
        if not str(runtime.get(key, ""))
    )
    return gaps


def _event_gaps(events: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    for index, item in enumerate(events):
        event_id = str(item.get("id", "")) or str(index)
        if str(item.get("locality", "")) != "generated_until_chronicle_promotion":
            gaps.append(f"workflow_event_locality_invalid:{event_id}")
        if not str(item.get("chronicle_promotion", "")):
            gaps.append(f"workflow_event_chronicle_promotion_missing:{event_id}")
    return gaps


def _eval_gaps(eval_contract: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    metrics = set(_strings(eval_contract.get("metric_names")))
    if not metrics:
        gaps.append("workflow_eval_metrics_missing")
    gaps.extend(
        f"workflow_eval_metric_unknown:{metric}" for metric in sorted(metrics - _ALLOWED_METRICS)
    )
    if eval_contract.get("truth_boundary") != "skill_metadata_only":
        gaps.append("workflow_eval_truth_boundary_invalid")
    return gaps


def _evolution_gaps(evolution: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not evolution:
        gaps.append("workflow_evolution_bridge_missing")
        return gaps
    if evolution.get("selection_policy") != "evidence_weighted_candidate_comparison":
        gaps.append("workflow_evolution_selection_policy_invalid")
    commitment_effect_policy = (
        "practice_claim_declares_create_compose_refine_replace_remove_or_reject_commitment_effect"
    )
    if evolution.get("commitment_effect_policy") != commitment_effect_policy:
        gaps.append("workflow_evolution_commitment_effect_policy_invalid")
    if (
        evolution.get("practice_claim_policy")
        != "practice_claim_is_evolution_carrier_for_governed_commitment_effect"
    ):
        gaps.append("workflow_evolution_practice_claim_policy_invalid")
    practice_change_policy = (
        "relation_to_incumbent_determines_introduce_compose_refine_supersede_retire_or_reject"
    )
    if evolution.get("practice_change_policy") != practice_change_policy:
        gaps.append("workflow_evolution_practice_change_policy_invalid")
    if evolution.get("truth_boundary") != "evolution_ledger_claim_evidence_chronicle":
        gaps.append("workflow_evolution_truth_boundary_invalid")
    learning_path = _strings(evolution.get("learning_path"))
    required = [
        "research",
        "hypothesis",
        "experiment",
        "evaluation",
        "canonization",
        "retirement",
    ]
    missing = [item for item in required if item not in learning_path]
    gaps.extend(f"workflow_evolution_learning_stage_missing:{item}" for item in missing)
    return gaps


def _node_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "kind": str(item.get("kind", "")),
        "enforcement": str(item.get("enforcement", "")),
        "requires": _strings(item.get("requires")),
        "produces": _strings(item.get("produces")),
    }


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]

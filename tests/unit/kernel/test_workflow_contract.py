from __future__ import annotations

from ethos.repository.workflow import runtime as workflow_runtime_model
from ethos_core.contracts.system.contracts import load_system_contract
from ethos_core.contracts.workflow import planned_transition_projection
from ethos_core.contracts.workflow import workflow_contract_report


def test_workflow_contract_declares_runtime_nodes_and_evolution_bridge() -> None:
    contract = load_system_contract(__import__("pathlib").Path(), "workflows")

    report = workflow_contract_report(contract)

    assert report["ok"] is True
    assert report["node_count"] >= 6
    assert {node["kind"] for node in report["nodes"]} >= {
        "control",
        "producer",
        "action",
        "handoff",
        "guardrail",
    }
    assert report["runtime"]["truth_boundary"] == "derived_repository_projection"
    assert report["evolution"]["selection_policy"] == "evidence_weighted_candidate_comparison"
    assert (
        report["evolution"]["commitment_effect_policy"]
        == "practice_claim_declares_create_compose_refine_replace_remove_or_reject_commitment_effect"
    )
    assert (
        report["evolution"]["practice_claim_policy"]
        == "practice_claim_is_evolution_carrier_for_governed_commitment_effect"
    )
    assert (
        report["evolution"]["practice_change_policy"]
        == "relation_to_incumbent_determines_introduce_compose_refine_supersede_retire_or_reject"
    )
    assert report["evolution"]["truth_boundary"] == "evolution_ledger_claim_evidence_chronicle"


def test_planned_transition_projection_includes_changed_paths() -> None:
    contract = load_system_contract(__import__("pathlib").Path(), "workflows")

    projection = planned_transition_projection(contract, changed_paths=("docs/a.md",))

    assert projection["truth_boundary"] == "derived_repository_projection"
    assert projection["changed_paths"] == ["docs/a.md"]
    assert projection["transitions"]
    assert any(node["id"] == "handoff" for node in projection["nodes"])


def test_workflow_contract_rejects_invalid_public_command_boundary() -> None:
    contract = load_system_contract(__import__("pathlib").Path(), "workflows")
    contract = dict(contract)
    runtime = dict(contract["runtime"])
    runtime["public_lifecycle_commands"] = ["comet run"]
    contract["runtime"] = runtime

    report = workflow_contract_report(contract)

    assert report["ok"] is False
    assert "workflow_runtime_public_commands_invalid" in report["required_gaps"]


def test_workflow_contract_reports_missing_runtime_eval_and_evolution_contracts() -> None:
    report = workflow_contract_report(
        {
            "lifecycle": {"states": []},
            "guards": {},
            "transition": [],
            "node": [],
            "runtime": {},
            "event": [],
            "eval": {},
            "evolution": {},
        }
    )

    assert report["ok"] is False
    assert {
        "workflow_transition_missing",
        "workflow_runtime_truth_boundary_invalid",
        "workflow_runtime_public_commands_invalid",
        "workflow_runtime_run_state_schema_missing",
        "workflow_runtime_handoff_package_schema_missing",
        "workflow_eval_metrics_missing",
        "workflow_eval_truth_boundary_invalid",
        "workflow_evolution_bridge_missing",
    } <= set(report["required_gaps"])


def test_workflow_contract_reports_invalid_transition_node_event_eval_and_evolution_edges() -> None:
    report = workflow_contract_report(
        {
            "lifecycle": {"states": ["known"]},
            "guards": {"known-guard": {}},
            "transition": [
                {
                    "from": "missing-source",
                    "to": "missing-target",
                    "guard": "missing-guard",
                    "invalid_state": "missing-invalid-state",
                    "invalid_states": ["other-unknown-state"],
                }
            ],
            "node": [
                {"kind": "unknown", "enforcement": "unknown"},
                {"id": "duplicate", "kind": "control", "enforcement": "guarded"},
                {"id": "duplicate", "kind": "producer", "enforcement": "guarded"},
                {
                    "id": "handoff-mismatch",
                    "kind": "control",
                    "enforcement": "handoff-guarded",
                },
                {"id": "advisory-guardrail", "kind": "guardrail", "enforcement": "advisory"},
            ],
            "runtime": {
                "truth_boundary": "derived_repository_projection",
                "public_lifecycle_commands": [
                    "ethos status",
                    "ethos plan",
                    "ethos prove",
                    "ethos land",
                    "ethos publish",
                ],
                "run_state_schema": "system/schemas/kernel/workflow-run.schema.json",
                "handoff_package_schema": "system/schemas/kernel/handoff-package.schema.json",
            },
            "event": [{"id": "bad-event", "locality": "durable"}],
            "eval": {
                "metric_names": ["unknown_metric"],
                "truth_boundary": "runtime_truth",
            },
            "evolution": {
                "selection_policy": "manual_vote",
                "commitment_effect_policy": "implicit",
                "practice_claim_policy": "narrative_only",
                "practice_change_policy": "best_effort",
                "truth_boundary": "workflow_runtime",
                "learning_path": ["research"],
            },
        }
    )

    assert report["ok"] is False
    assert {
        "workflow_transition_state_unknown:0:from:missing-source",
        "workflow_transition_state_unknown:0:to:missing-target",
        "workflow_transition_guard_unknown:0:missing-guard",
        "workflow_transition_invalid_state_unknown:0:missing-invalid-state",
        "workflow_transition_invalid_state_not_listed:0:missing-invalid-state",
        "workflow_transition_invalid_state_unknown:0:other-unknown-state",
        "workflow_node_id_missing:0",
        "workflow_node_id_duplicate:duplicate",
        "workflow_node_kind_unknown:0:unknown",
        "workflow_node_enforcement_unknown:0:unknown",
        "workflow_node_handoff_enforcement_kind_mismatch:handoff-mismatch",
        "workflow_guardrail_advisory:advisory-guardrail",
        "workflow_event_locality_invalid:bad-event",
        "workflow_event_chronicle_promotion_missing:bad-event",
        "workflow_eval_metric_unknown:unknown_metric",
        "workflow_eval_truth_boundary_invalid",
        "workflow_evolution_selection_policy_invalid",
        "workflow_evolution_commitment_effect_policy_invalid",
        "workflow_evolution_practice_claim_policy_invalid",
        "workflow_evolution_practice_change_policy_invalid",
        "workflow_evolution_truth_boundary_invalid",
        "workflow_evolution_learning_stage_missing:hypothesis",
        "workflow_evolution_learning_stage_missing:retirement",
    } <= set(report["required_gaps"])


def test_workflow_runtime_container_helpers_reject_non_container_values() -> None:
    assert workflow_runtime_model._dict("not-a-dict") == {}
    assert workflow_runtime_model._dict_items("not-a-list") == []
    assert workflow_runtime_model._strings("not-a-list") == []

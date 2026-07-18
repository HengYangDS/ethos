from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.workflow import runtime as workflow_runtime_model
from ethos_core.contracts.system.contracts import load_system_contract
from ethos_core.contracts.workflow import WorkflowContract
from ethos_core.contracts.workflow import action_graph_from_workflow_contract
from ethos_core.contracts.workflow import load_workflow_contract_declaration
from ethos_core.contracts.workflow import planned_transition_projection
from ethos_core.contracts.workflow import workflow_contract_report
from ethos_core.normalization.core import string_list


def test_workflow_contract_is_strict_frozen_typed_declaration() -> None:
    contract = WorkflowContract.model_validate(load_system_contract(Path(), "workflows"))

    assert contract.runtime.truth_boundary == "derived_repository_projection"
    assert contract.node[0].id == "status"
    assert contract.transition[0].source == "planned"
    assert contract.transition[0].target == "admitted"
    assert contract.to_report()["node_count"] >= 6
    assert contract.to_projection(changed_paths=("docs/a.md",))["graph"]["ok"] is True

    with pytest.raises(ValidationError) as frozen_error:
        contract.runtime.truth_boundary = "mutable"
    assert frozen_error.value.errors()[0]["type"] == "frozen_instance"

    with pytest.raises(ValidationError) as extra_error:
        WorkflowContract.model_validate({"unexpected": True})
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


def test_workflow_contract_normalizes_list_fields_to_immutable_tuples() -> None:
    declaration = WorkflowContract.model_validate(load_system_contract(Path(), "workflows"))

    assert isinstance(declaration.node, tuple)
    assert isinstance(declaration.node[0].produces, tuple)
    assert isinstance(declaration.transition[0].invalid_states, tuple)
    assert isinstance(declaration.runtime.public_lifecycle_commands, tuple)
    assert isinstance(declaration.guards, tuple)
    assert "lane_prewrite_ok" in declaration.guards


def test_workflow_contract_defaults_invalid_guard_table_to_empty_tuple() -> None:
    declaration = WorkflowContract.model_validate({"guards": "not-a-table"})

    assert declaration.guards == ()


def test_workflow_contract_loader_returns_typed_declaration() -> None:
    declaration = load_workflow_contract_declaration()

    assert isinstance(declaration, WorkflowContract)
    assert workflow_contract_report(declaration)["ok"] is True
    assert planned_transition_projection(declaration)["truth_boundary"] == (
        "derived_repository_projection"
    )
    assert action_graph_from_workflow_contract(declaration).validate().ok is True


def test_workflow_contract_declares_runtime_nodes_and_evolution_bridge() -> None:
    contract = load_system_contract(Path(), "workflows")

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


def test_planned_transition_projection_includes_changed_paths_and_graph_plan() -> None:
    contract = load_system_contract(Path(), "workflows")

    projection = planned_transition_projection(contract, changed_paths=("docs/a.md",))

    assert projection["truth_boundary"] == "derived_repository_projection"
    assert projection["changed_paths"] == ["docs/a.md"]
    assert projection["transitions"]
    assert any(node["id"] == "handoff" for node in projection["nodes"])
    assert projection["graph"]["ok"] is True
    assert projection["graph"]["edges"] == [
        {"source": "status", "target": "plan", "relation": "depends_on"},
        {"source": "plan", "target": "prove", "relation": "depends_on"},
        {"source": "prove", "target": "land", "relation": "depends_on"},
        {"source": "land", "target": "publish", "relation": "depends_on"},
    ]
    assert projection["external_requirements"] == [
        {"node": "plan", "requires": ["openspec_carrier"]},
        {"node": "prove", "requires": ["gate_results"]},
        {"node": "land", "requires": ["claim_binding"]},
        {"node": "publish", "requires": ["release_readiness"]},
        {"node": "handoff", "requires": ["source_refs", "source_digests"]},
    ]


def test_action_graph_from_workflow_contract_compiles_requested_declared_nodes() -> None:
    contract = load_system_contract(Path(), "workflows")

    graph = action_graph_from_workflow_contract(
        contract,
        changed_paths=("b.py", "a.py"),
        node_ids=("status", "plan", "prove"),
    )

    assert graph.validate().ok is True
    assert [node.id for node in graph.nodes] == ["status", "plan", "prove"]
    assert graph.nodes[0].inputs == ("a.py", "b.py")
    assert graph.nodes[1].command == ("ethos", "plan", "--json")
    assert graph.nodes[1].outputs == ("action_graph", "workflow_runtime_read_model")
    assert graph.nodes[2].depends_on == ("plan",)
    assert graph.nodes[2].metadata["requires"] == ["action_graph", "gate_results"]


def test_action_graph_from_workflow_contract_reports_missing_requested_nodes() -> None:
    graph = action_graph_from_workflow_contract(
        {"node": [{"id": "status", "kind": "control", "command": "ethos status --json"}]},
        node_ids=("status", "missing"),
    )

    assert graph.validate().ok is False
    assert graph.validate().gaps == ("workflow_plan_node_missing:missing",)


def test_action_graph_from_workflow_contract_ignores_anonymous_selected_nodes() -> None:
    graph = action_graph_from_workflow_contract(
        {
            "node": [
                {"kind": "control", "command": "ethos anonymous --json"},
                {
                    "id": "status",
                    "kind": "control",
                    "command": "ethos status --json",
                    "produces": ["workspace_status"],
                },
            ]
        },
        node_ids=("", "status"),
    )

    assert graph.validate().ok is True
    assert [node.id for node in graph.nodes] == ["status"]


def test_workflow_contract_rejects_invalid_public_command_boundary() -> None:
    contract = WorkflowContract.model_validate(
        load_system_contract(Path(), "workflows")
    ).model_dump(by_alias=True)
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
                {
                    "id": "advisory-guardrail",
                    "kind": "guardrail",
                    "enforcement": "advisory",
                },
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
    assert string_list(["a", 2, ""]) == ["a", "2", ""]
    assert string_list("not-a-list") == []


def test_workflow_runtime_report_returns_gap_when_contract_is_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    def raise_missing(_root: Path) -> object:
        raise FileNotFoundError

    monkeypatch.setattr(workflow_runtime_model, "load_workflow_contract_declaration", raise_missing)

    report = workflow_runtime_model.workflow_runtime_report(
        tmp_path,
        changed_paths=("docs/a.md",),
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["workflow_contract_unavailable:FileNotFoundError"]
    assert report["contract"]["required_gaps"] == [
        "workflow_contract_unavailable:FileNotFoundError"
    ]
    assert report["plan"]["changed_paths"] == ["docs/a.md"]
    assert report["evolution_bridge"]["runtime_owns_evolution"] is False


def test_planned_transition_projection_skips_anonymous_nodes_and_self_requirements() -> None:
    projection = planned_transition_projection(
        {
            "node": [
                {"produces": ["anonymous_fact"]},
                {
                    "id": "self-contained",
                    "requires": ["self_fact"],
                    "produces": ["self_fact"],
                },
                {"id": "consumer", "requires": ["self_fact", "external_fact"]},
            ]
        }
    )

    assert projection["graph"] == {
        "ok": True,
        "ordered_ids": ["self-contained", "consumer"],
        "edges": [
            {
                "source": "self-contained",
                "target": "consumer",
                "relation": "depends_on",
            },
        ],
        "gaps": [],
    }
    assert projection["external_requirements"] == [
        {"node": "consumer", "requires": ["external_fact"]},
    ]

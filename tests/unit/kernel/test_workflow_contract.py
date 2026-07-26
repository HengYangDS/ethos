from __future__ import annotations

from copy import deepcopy
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import RepositoryFacts
from ethos.contracts.system.contracts import load_system_contract
from ethos.contracts.workflow import WorkflowContract
from ethos.contracts.workflow import load_workflow_contract_declaration
from ethos.contracts.workflow import planned_transition_projection
from ethos.contracts.workflow import workflow_contract_report

_CONTRACT = ChangeContract(id="change:test", intent="test", subjects=("repository:test",))
_FACTS = RepositoryFacts(
    repository="repository:test",
    head="a" * 40,
    tree="b" * 40,
    observed_at=datetime(2026, 7, 25, tzinfo=UTC),
    values={"changed_paths": ()},
)


def _facts(*paths: str) -> RepositoryFacts:
    return _FACTS.model_copy(update={"values": {"changed_paths": paths}})


def test_workflow_contract_is_frozen_typed_declaration() -> None:
    contract = WorkflowContract.model_validate(load_system_contract(Path(), "workflows"))

    assert "event" not in WorkflowContract.model_fields
    assert "event_count" not in contract.to_report()
    assert "event_stream_locality" not in type(contract.runtime).model_fields
    assert contract.runtime.truth_boundary == "derived_repository_projection"
    assert contract.node[0].id == "status"
    assert contract.transition[0].source == "planned"
    assert contract.transition[0].target == "admitted"
    assert tuple(item.id for item in contract.lease_transition) == tuple(
        item["id"] for item in load_system_contract(Path(), "workflows")["lease_transition"]
    )
    assert contract.to_report()["node_count"] >= 6
    assert (
        contract.to_projection(contract=_CONTRACT, facts=_facts("docs/a.md"))["plan_ir"]["verdict"]
        == "block"
    )

    with pytest.raises(ValidationError) as frozen_error:
        contract.runtime.truth_boundary = "mutable"
    assert frozen_error.value.errors()[0]["type"] == "frozen_instance"

    with pytest.raises(ValidationError) as extra_error:
        WorkflowContract.model_validate({"unexpected": True})
    assert extra_error.value.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda payload: payload["lease_transition"].append(
                deepcopy(payload["lease_transition"][0])
            ),
            id="duplicate-operation",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(effect_fields=[1]),
            id="non-string-effect-field",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(
                effect_fields=["holder_ref", "holder_ref"]
            ),
            id="duplicate-effect-field",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(
                effect_fields=["holder_ref", "unexpected"]
            ),
            id="unknown-effect-field",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].pop("actor_field"),
            id="missing-actor-field",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(actor_field="actor_ref"),
            id="invalid-actor-field",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(actor_field="target_holder_ref"),
            id="actor-field-not-effect-field",
        ),
    ],
)
def test_workflow_contract_rejects_invalid_lease_transition_matrix(mutate) -> None:
    payload = load_system_contract(Path(), "workflows")

    mutate(payload)

    with pytest.raises(ValidationError):
        WorkflowContract.model_validate(payload)


def test_workflow_contract_declares_exact_lease_effect_bindings() -> None:
    declaration = WorkflowContract.model_validate(load_system_contract(Path(), "workflows"))

    assert {
        item.id: (item.effect_fields, item.actor_field, item.blocks_contrary_decision)
        for item in declaration.lease_transition
    } == {
        "renew": (
            (
                "holder_ref",
                "expected_epoch",
                "expected_expires_at",
                "expected_payload_sha256",
                "ttl_seconds",
            ),
            "holder_ref",
            False,
        ),
        "resume": (
            (
                "holder_ref",
                "expected_epoch",
                "expected_expires_at",
                "expected_payload_sha256",
                "ttl_seconds",
            ),
            "holder_ref",
            True,
        ),
        "handoff_offer": (
            (
                "holder_ref",
                "expected_epoch",
                "expected_expires_at",
                "expected_payload_sha256",
                "target_holder_ref",
            ),
            "holder_ref",
            False,
        ),
        "handoff_accept": (
            (
                "holder_ref",
                "target_holder_ref",
                "offer_id",
                "expected_epoch",
                "expected_expires_at",
                "expected_payload_sha256",
                "holder_quiesced",
                "ttl_seconds",
            ),
            "target_holder_ref",
            False,
        ),
    }


def test_workflow_contract_declares_exact_transition_policies() -> None:
    declaration = WorkflowContract.model_validate(load_system_contract(Path(), "workflows"))

    assert tuple(item.id for item in declaration.transition_policy) == (
        "guarded",
        "work_lane",
        "closeout",
        "adopt",
    )
    assert declaration.policy("work_lane").dry_run_commands == ("land",)
    assert declaration.policy("closeout").required_role == "accepted_root"


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
    assert planned_transition_projection(
        declaration,
        change_contract=_CONTRACT,
        repository_facts=_FACTS,
    )["truth_boundary"] == ("derived_repository_projection")
    assert declaration.plan(contract=_CONTRACT, facts=_FACTS).gaps() == (
        "workflow_external_requirement_missing:plan:openspec_carrier",
        "workflow_external_requirement_missing:land:change_contract",
        "workflow_external_requirement_missing:publish:release_readiness",
        "workflow_external_requirement_missing:handoff:source_refs",
        "workflow_external_requirement_missing:handoff:source_digests",
    )


def test_workflow_contract_rejects_invalid_campaign_cel_projection() -> None:
    payload = load_system_contract(Path(), "workflows")
    campaign = dict(payload["campaign"])
    campaign["publication_projection"] = "{"
    payload["campaign"] = campaign

    with pytest.raises(ValidationError):
        WorkflowContract.model_validate(payload)


def test_workflow_contract_declares_runtime_nodes_and_evolution_bridge() -> None:
    contract = load_system_contract(Path(), "workflows")

    report = workflow_contract_report(contract)

    assert report["ok"] is True
    assert report["node_count"] >= 6
    assert {node["kind"] for node in report["nodes"]} == {"check", "decision", "effect"}
    assert report["runtime"]["truth_boundary"] == "derived_repository_projection"
    assert report["evolution"]["selection_policy"] == "evidence_weighted_candidate_comparison"
    assert (
        report["evolution"]["commitment_effect_policy"]
        == "practice_claim_declares_create_compose_refine_"
        "replace_remove_or_reject_commitment_effect"
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


def test_planned_transition_projection_includes_changed_paths_and_plan_ir() -> None:
    contract = load_system_contract(Path(), "workflows")

    projection = planned_transition_projection(
        contract,
        change_contract=_CONTRACT,
        repository_facts=_facts("docs/a.md"),
    )

    assert projection["truth_boundary"] == "derived_repository_projection"
    assert projection["changed_paths"] == ["docs/a.md"]
    assert projection["transitions"]
    assert any(node["id"] == "handoff" for node in projection["nodes"])
    assert projection["plan_ir"]["verdict"] == "block"
    assert [node["id"] for node in projection["plan_ir"]["nodes"]] == [
        "handoff",
        "status",
        "plan",
        "prove",
        "land",
        "publish",
    ]
    assert projection["external_requirements"] == [
        {"node": "plan", "requires": ["openspec_carrier"]},
        {"node": "land", "requires": ["change_contract"]},
        {"node": "publish", "requires": ["release_readiness"]},
        {"node": "handoff", "requires": ["source_refs", "source_digests"]},
    ]


def test_plan_ir_from_workflow_contract_compiles_requested_declared_nodes() -> None:
    contract = load_system_contract(Path(), "workflows")

    plan = WorkflowContract.model_validate(contract).plan(
        contract=_CONTRACT,
        facts=_FACTS.model_copy(update={"values": {"openspec_carrier": True}}),
        node_ids=("status", "plan", "prove"),
    )

    assert plan.ok is True
    assert [node.id for node in plan.nodes] == ["status", "plan", "prove"]
    assert plan.nodes[1].command == ("ethos", "plan", "--json")
    assert plan.nodes[2].depends_on == ("plan",)


def test_workflow_nodes_use_plan_ir_kinds_without_heuristic_mapping() -> None:
    source = Path("src/ethos/contracts/workflow.py").read_text(encoding="utf-8")
    declaration = load_system_contract(Path(), "workflows")

    assert "if self.kind ==" not in source
    assert {node["kind"] for node in declaration["node"]} == {"check", "decision", "effect"}


def test_plan_ir_from_workflow_contract_reports_missing_requested_nodes() -> None:
    plan = WorkflowContract.model_validate(
        {"node": [{"id": "status", "kind": "check", "command": "ethos status --json"}]}
    ).plan(contract=_CONTRACT, facts=_FACTS, node_ids=("status", "missing"))

    assert plan.ok is False
    assert plan.gaps() == ("workflow_plan_node_missing:missing",)


def test_plan_ir_from_workflow_contract_ignores_anonymous_selected_nodes() -> None:
    plan = WorkflowContract.model_validate(
        {
            "node": [
                {"kind": "check", "command": "ethos anonymous --json"},
                {
                    "id": "status",
                    "kind": "check",
                    "command": "ethos status --json",
                    "produces": ["workspace_status"],
                },
            ]
        }
    ).plan(contract=_CONTRACT, facts=_FACTS, node_ids=("", "status"))

    assert plan.ok is True
    assert [node.id for node in plan.nodes] == ["status"]


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


def test_workflow_contract_registers_handoff_acknowledgement_schema() -> None:
    payload = load_system_contract(Path(), "workflows")
    declaration = WorkflowContract.model_validate(payload)

    assert declaration.runtime.handoff_acknowledgement_schema == (
        "system/schemas/kernel/handoff-acknowledgement.schema.json"
    )

    runtime = dict(payload["runtime"])
    runtime.pop("handoff_acknowledgement_schema", None)
    payload["runtime"] = runtime

    report = workflow_contract_report(payload)

    assert report["ok"] is False
    assert "workflow_runtime_handoff_acknowledgement_schema_missing" in report["required_gaps"]


def test_workflow_contract_reports_missing_runtime_eval_and_evolution_contracts() -> None:
    report = workflow_contract_report(
        {
            "lifecycle": {"states": []},
            "guards": {},
            "transition": [],
            "node": [],
            "runtime": {},
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


def test_workflow_contract_reports_invalid_transition_node_eval_and_evolution_edges() -> None:
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
                {"enforcement": "unknown"},
                {"id": "duplicate", "kind": "check", "enforcement": "guarded"},
                {"id": "duplicate", "kind": "decision", "enforcement": "guarded"},
                {
                    "id": "effect-advisory",
                    "kind": "effect",
                    "enforcement": "handoff-guarded",
                },
                {
                    "id": "decision-advisory",
                    "kind": "decision",
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
        "workflow_transition_invalid_state_not_listed:0:missing-invalid-state",
        "workflow_node_id_missing:0",
        "workflow_node_id_duplicate:duplicate",
        "workflow_node_enforcement_unknown:0:unknown",
        "workflow_effect_enforcement_invalid:effect-advisory",
        "workflow_decision_advisory:decision-advisory",
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


def test_planned_transition_projection_skips_anonymous_nodes_and_self_requirements() -> None:
    projection = planned_transition_projection(
        {
            "node": [
                {"kind": "check", "produces": ["anonymous_fact"]},
                {
                    "id": "self-contained",
                    "kind": "decision",
                    "requires": ["self_fact"],
                    "produces": ["self_fact"],
                },
                {
                    "id": "consumer",
                    "kind": "effect",
                    "requires": ["self_fact", "external_fact"],
                },
            ]
        },
        change_contract=_CONTRACT,
        repository_facts=_FACTS,
    )

    assert projection["plan_ir"]["verdict"] == "block"
    assert projection["plan_ir"]["required_gaps"] == [
        "workflow_external_requirement_missing:consumer:external_fact"
    ]
    assert [node["id"] for node in projection["plan_ir"]["nodes"]] == [
        "self-contained",
        "consumer",
    ]
    assert projection["plan_ir"]["nodes"][1]["depends_on"] == ["self-contained"]
    assert projection["external_requirements"] == [
        {"node": "consumer", "requires": ["external_fact"]},
    ]


def test_workflow_external_requirement_is_satisfied_only_by_repository_fact() -> None:
    contract = WorkflowContract.model_validate(
        {
            "node": [
                {
                    "id": "consumer",
                    "kind": "decision",
                    "requires": ["external_fact"],
                }
            ]
        }
    )

    missing = contract.plan(contract=_CONTRACT, facts=_FACTS)
    present = contract.plan(
        contract=_CONTRACT,
        facts=_FACTS.model_copy(update={"values": {"external_fact": True}}),
    )
    false = contract.plan(
        contract=_CONTRACT,
        facts=_FACTS.model_copy(update={"values": {"external_fact": False}}),
    )
    null = contract.plan(
        contract=_CONTRACT,
        facts=_FACTS.model_copy(update={"values": {"external_fact": None}}),
    )

    assert missing.gaps() == ("workflow_external_requirement_missing:consumer:external_fact",)
    assert present.verdict == "pass"
    assert false.gaps() == missing.gaps()
    assert null.gaps() == missing.gaps()

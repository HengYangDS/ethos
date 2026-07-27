from __future__ import annotations

from copy import deepcopy
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.contracts.lifecycle.declaration import LifecycleContract
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import RepositoryFacts
from ethos.contracts.system.contracts import load_system_contract

_CONTRACT = ChangeContract(id="change:test", intent="test", subjects=("repository:test",))
_FACTS = RepositoryFacts(
    repository="repository:test",
    head="a" * 40,
    tree="b" * 40,
    observed_at=datetime(2026, 7, 25, tzinfo=UTC),
    values={"changed_paths": ()},
)


def test_lifecycle_contract_rejects_parallel_runtime_state_surface() -> None:
    payload = load_system_contract(Path(), "lifecycle")
    payload["runtime"] = {}

    with pytest.raises(ValidationError) as error:
        LifecycleContract.model_validate(payload)

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_lifecycle_declaration_is_frozen_and_source_bound() -> None:
    declaration = load_lifecycle_declaration()

    assert tuple(item.id for item in declaration.transition_policy) == (
        "guarded",
        "work_lane",
        "closeout",
        "adopt",
    )
    assert [item.id for item in declaration.node] == [
        "status",
        "plan",
        "prove",
        "land",
        "publish",
    ]
    assert declaration.policy("work_lane").dry_run_commands == ("land",)
    assert tuple(item.id for item in declaration.lease_transition) == (
        "renew",
        "resume",
        "handoff_offer",
        "handoff_accept",
    )
    assert tuple(item.kind for item in declaration.lease_transition) == (
        "refresh",
        "refresh",
        "offer",
        "accept",
    )
    with pytest.raises(ValidationError) as frozen:
        declaration.node[0].id = "plan"
    assert frozen.value.errors()[0]["type"] == "frozen_instance"


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
            lambda payload: payload["lease_transition"][0].update(
                effect_fields=deepcopy(payload["lease_transition"][2]["effect_fields"])
            ),
            id="operation-effect-fields-mismatch",
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
            lambda payload: payload["lease_transition"][3].update(actor_field="holder_ref"),
            id="operation-actor-field-mismatch",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(blocks_contrary_decision=True),
            id="operation-blocks-contrary-decision-mismatch",
        ),
        pytest.param(
            lambda payload: payload["lease_transition"][0].update(kind="offer"),
            id="derived-kind-cannot-be-overridden",
        ),
    ],
)
def test_lifecycle_contract_rejects_invalid_lease_transition_matrix(mutate) -> None:
    payload = load_system_contract(Path(), "lifecycle")
    mutate(payload)

    with pytest.raises(ValidationError):
        LifecycleContract.model_validate(payload)


def test_lifecycle_contract_rejects_invalid_or_duplicate_plan_actions() -> None:
    payload = load_system_contract(Path(), "lifecycle")
    payload["node"][1]["enforcement"] = "evidence-only"

    with pytest.raises(ValidationError):
        LifecycleContract.model_validate(payload)

    payload = load_system_contract(Path(), "lifecycle")
    payload["node"].append(deepcopy(payload["node"][0]))
    with pytest.raises(ValidationError):
        LifecycleContract.model_validate(payload)


def test_lifecycle_contract_compiles_declared_actions_to_plan_ir() -> None:
    declaration = load_lifecycle_declaration()
    facts = _FACTS.model_copy(update={"values": {"openspec_carrier": True}})

    plan = declaration.plan(
        contract=_CONTRACT,
        facts=facts,
        node_ids=("status", "plan", "prove"),
    )

    assert plan.ok is True
    assert [node.id for node in plan.nodes] == ["status", "plan", "prove"]
    assert plan.nodes[1].command == ("ethos", "plan", "--json")
    assert plan.nodes[2].depends_on == ("plan",)


def test_lifecycle_contract_reports_missing_action_and_external_fact() -> None:
    declaration = load_lifecycle_declaration()

    plan = declaration.plan(
        contract=_CONTRACT,
        facts=_FACTS,
        node_ids=("status", "plan", "missing"),
    )

    assert plan.gaps() == (
        "lifecycle_plan_action_missing:missing",
        "lifecycle_external_fact_missing:plan:openspec_carrier",
    )

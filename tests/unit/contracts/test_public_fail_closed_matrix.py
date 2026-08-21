from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.proof.plan import validate_proof_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from tests.support.semantic import commitment_fixture


def _commitment(*, scope: tuple[str, ...] = ("src/**",)) -> Commitment:
    return commitment_fixture(
        id="change:contract-matrix",
        intent="Keep public contract validation fail-closed.",
        subjects=("repository:test",),
        scope=scope,
    )


def _facts(**values: object) -> Facts:
    return Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={"changed_paths": ("src/ethos/contracts/plan.py",), **values},
    )


def _proof_plan(
    *, commitment: Commitment | None = None, facts: Facts | None = None
) -> tuple[TransitionPlan, Commitment, Facts]:
    bound_commitment = commitment or _commitment()
    bound_facts = facts or _facts(gate_ids=("check",))
    node = PlanNode(id="check", kind="check", command=("python", "-m", "check"))
    policy = {
        "gates": [
            {
                "id": "check",
                "execution_identity": ["python", "-m", "check"],
                "depends_on": [],
            }
        ],
        "gaps": [],
    }
    return (
        compile_plan(bound_commitment, bound_facts, (node,), policy=policy),
        bound_commitment,
        bound_facts,
    )


def _canonical_payload(plan: TransitionPlan, **updates: object) -> dict[str, object]:
    payload = plan.model_dump(mode="json") | updates
    gaps = payload["required_gaps"]
    payload["continuation"] = {"kind": "user-decision", "required_gaps": gaps} if gaps else None
    payload["digest"] = canonical_json_digest(
        {name: value for name, value in payload.items() if name != "digest"}
    )
    return payload


def test_transition_plan_public_projection_rejects_noncanonical_state() -> None:
    nodes = (
        PlanNode(id="check", kind="check"),
        PlanNode(id="effect", kind="effect", depends_on=("check",)),
    )
    with pytest.raises(ValueError, match="missing_node:absent"):
        TransitionPlan.closure(nodes, ("absent",))

    plan, _, _ = _proof_plan()
    second = PlanNode(id="finish", kind="effect", depends_on=("check",))
    ordered = compile_plan(
        _commitment(),
        _facts(),
        (plan.nodes[0], second),
        policy={},
    )
    reversed_nodes = [node.model_dump(mode="json") for node in reversed(ordered.nodes)]
    with pytest.raises(ValidationError, match="transition_plan_graph_invalid"):
        TransitionPlan.model_validate(_canonical_payload(ordered, nodes=reversed_nodes))

    with pytest.raises(ValidationError, match="transition_plan_verdict_invalid"):
        TransitionPlan.model_validate(
            _canonical_payload(plan, verdict="pass", required_gaps=["proof_missing"])
        )
    with pytest.raises(TypeError, match="transition_plan_facts_invalid"):
        plan.model_copy(update={"facts": ("not", "an", "object")}).validate_canonical_projection()
    with pytest.raises(ValueError, match="transition_plan_closure_invalid"):
        plan.model_copy(update={"commitment": {}}).validate_canonical_projection()


def test_git_effect_public_reader_rejects_wrong_or_blocked_plan() -> None:
    commitment = _commitment()
    facts = _facts()
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected="0" * 40, desired="1" * 40)}
    )
    wrong_kind = TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest({}),
            policy=canonical_json_digest({}),
            effect=canonical_json_digest(effect.model_dump(mode="json")),
        ),
        closure={
            "commitment": commitment.identity_projection(),
            "prior_attestations": {},
            "policy": {},
            "effect": effect.model_dump(mode="json"),
        },
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=(PlanNode(id="observe", kind="check"),),
    )
    with pytest.raises(ValueError, match="git_effect_plan_mismatch"):
        git_effect_from_plan(wrong_kind)

    admitted = compile_git_effect_plan(
        commitment,
        facts,
        prior_attestations={},
        policy={},
        effect=effect,
    )
    blocked = TransitionPlan.model_validate(
        _canonical_payload(admitted, verdict="block", required_gaps=["authority_denied"])
    )
    with pytest.raises(ValueError, match="git_effect_plan_not_admitted"):
        git_effect_from_plan(blocked)


def test_validate_proof_plan_rejects_effect_semantics_and_model_drift() -> None:
    plan, commitment, facts = _proof_plan()
    with pytest.raises(ValueError, match="transition_plan_effect_mismatch"):
        validate_proof_plan(
            plan.model_copy(update={"effect": {"operation": "other"}}), commitment, facts
        )

    with pytest.raises(ValueError, match="transition_plan_semantics_mismatch"):
        validate_proof_plan(plan, _commitment(scope=("docs/**",)), facts)

    invalid_policy = plan.model_copy(update={"policy": {"gates": {}, "gaps": []}})
    with pytest.raises(TypeError, match="transition_plan_policy_invalid"):
        validate_proof_plan(invalid_policy, commitment, facts)

    expanded_facts = _facts(gate_ids=("check",), unexpected_projection=True)
    with pytest.raises(ValueError, match="transition_plan_model_gap"):
        validate_proof_plan(plan, commitment, expanded_facts)

    mismatched_ids = _facts(gate_ids=("different",))
    with pytest.raises(ValueError, match="transition_plan_policy_node_mismatch"):
        validate_proof_plan(plan, commitment, mismatched_ids)


def test_validate_proof_plan_rejects_malformed_gate_declarations() -> None:
    plan, commitment, facts = _proof_plan()
    malformed_gate = plan.model_copy(update={"policy": {"gates": ["not-a-gate"], "gaps": []}})
    with pytest.raises(TypeError, match="transition_plan_policy_invalid"):
        validate_proof_plan(malformed_gate, commitment, facts)

    missing_fields = plan.model_copy(update={"policy": {"gates": [{"id": "check"}], "gaps": []}})
    with pytest.raises(ValueError, match="transition_plan_policy_invalid"):
        validate_proof_plan(missing_fields, commitment, facts)

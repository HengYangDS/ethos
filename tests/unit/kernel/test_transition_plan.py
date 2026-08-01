from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.contracts.plan import EMPTY_ATTESTATION_SET_DIGEST
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import Verdict

_COMMITMENT = Commitment(
    id="change:test",
    intent="Exercise one transition plan.",
    subjects=("repository:test",),
)
_FACTS = Facts(
    repository="repository:test",
    head="a" * 40,
    tree="b" * 40,
    observed_at=datetime(2026, 7, 25, tzinfo=UTC),
    values={},
)
_POLICY = {"name": "test"}
_EFFECT = {"operation": "test"}
_INPUTS = {
    "inputs": PlanInputs(
        commitment=_COMMITMENT.digest(),
        facts=_FACTS.digest(),
        prior_attestations=EMPTY_ATTESTATION_SET_DIGEST,
        policy=canonical_json_digest(_POLICY),
        effect=canonical_json_digest(_EFFECT),
    ),
    "closure": {
        "commitment": _COMMITMENT.identity_projection(),
        "prior_attestations": {},
        "policy": _POLICY,
        "effect": _EFFECT,
    },
    "facts": _FACTS.model_dump(mode="json", exclude={"observed_at"}),
}


def _plan(*, verdict: Verdict = "pass", required_gaps=(), nodes=()) -> TransitionPlan:
    return TransitionPlan.compile(
        **_INPUTS,
        verdict=verdict,
        required_gaps=required_gaps,
        nodes=nodes,
    )


def test_transition_plan_orders_dependencies_before_dependents() -> None:
    plan = _plan(
        nodes=(
            PlanNode(
                id="publish",
                kind="effect",
                command=("ethos", "publish"),
                depends_on=("prove",),
            ),
            PlanNode(id="status", kind="check", command=("ethos", "status")),
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    assert [node.id for node in plan.nodes] == ["status", "prove", "publish"]


def test_transition_plan_canonicalizes_set_like_inputs() -> None:
    commitment = _COMMITMENT.model_copy(
        update={"permissions": ("repository.read", "repository.write")}
    )
    inputs_with_permissions = _INPUTS | {
        "inputs": _INPUTS["inputs"].model_copy(update={"commitment": commitment.digest()}),
        "closure": _INPUTS["closure"] | {"commitment": commitment.identity_projection()},
    }
    inputs = (
        PlanNode(id="lint", kind="check"),
        PlanNode(id="test", kind="check"),
    )
    first = TransitionPlan.compile(
        **inputs_with_permissions,
        permissions=("repository.write", "repository.read", "repository.write"),
        nodes=(
            *inputs,
            PlanNode(
                id="publish",
                kind="effect",
                depends_on=("test", "lint", "test"),
            ),
        ),
    )
    second = TransitionPlan.compile(
        **inputs_with_permissions,
        permissions=("repository.read", "repository.write"),
        nodes=(
            *reversed(inputs),
            PlanNode(id="publish", kind="effect", depends_on=("lint", "test")),
        ),
    )

    assert first == second
    assert first.permissions == ("repository.read", "repository.write")
    assert first.nodes[-1].depends_on == ("lint", "test")


def test_proof_effect_digest_canonicalizes_dag_before_hashing() -> None:
    nodes = (
        PlanNode(id="publish", kind="effect", command=("publish",), depends_on=("prove",)),
        PlanNode(id="status", kind="check", command=("status",)),
        PlanNode(id="prove", kind="decision", command=("prove",), depends_on=("status",)),
    )
    inputs = {
        "commitment": "a" * 64,
        "facts": "b" * 64,
        "policy": "c" * 64,
    }

    assert proof_effect_digest(**inputs, nodes=nodes) == proof_effect_digest(
        **inputs, nodes=tuple(reversed(nodes))
    )


def test_transition_plan_distinguishes_all_nodes_from_an_empty_selection() -> None:
    nodes = (PlanNode(id="status", kind="check"),)

    assert TransitionPlan.closure(nodes) == nodes
    assert TransitionPlan.closure(nodes, ()) == ()


def test_transition_plan_public_projection_round_trips_through_its_model_owner() -> None:
    plan = _plan(nodes=(PlanNode(id="status", kind="check", command=("ethos", "status")),))

    payload = plan.model_dump(mode="json", by_alias=True)

    assert set(payload) == {
        "schema_version",
        "inputs",
        "commitment",
        "prior_attestations",
        "policy",
        "effect",
        "permissions",
        "facts",
        "nodes",
        "verdict",
        "required_gaps",
        "digest",
    }
    assert TransitionPlan.model_validate(payload) == plan


def test_transition_plan_facts_are_deeply_immutable() -> None:
    plan = _plan()

    with pytest.raises(TypeError):
        plan.facts["values"]["new"] = True


def test_transition_plan_rejects_missing_dependency() -> None:
    plan = _plan(
        nodes=(
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    assert plan.verdict == "block"
    assert "missing_dependency:prove->status" in plan.required_gaps


def test_transition_plan_rejects_cycle() -> None:
    plan = _plan(
        nodes=(
            PlanNode(id="a", kind="check", command=("a",), depends_on=("b",)),
            PlanNode(id="b", kind="check", command=("b",), depends_on=("a",)),
        )
    )

    assert plan.verdict == "block"
    assert "cycle_detected" in plan.required_gaps


def test_transition_plan_rejects_duplicate_node_id() -> None:
    plan = _plan(
        nodes=(
            PlanNode(id="prove", kind="check", command=("ethos", "prove")),
            PlanNode(id="prove", kind="check", command=("ethos", "prove", "--json")),
        )
    )

    assert plan.verdict == "block"
    assert "duplicate_node_id:prove" in plan.required_gaps


def test_invalid_transition_plan_still_serializes_without_recursion() -> None:
    plan = _plan(
        nodes=(
            PlanNode(
                id="prove",
                kind="decision",
                command=("ethos", "prove"),
                depends_on=("status",),
            ),
        )
    )

    payload = plan.model_dump(mode="json")

    assert payload["nodes"][0]["id"] == "prove"
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["missing_dependency:prove->status"]


def test_valid_transition_plan_has_pass_verdict() -> None:
    plan = _plan(nodes=(PlanNode(id="status", kind="check", command=("ethos", "status")),))

    assert plan.verdict == "pass"
    assert plan.model_dump(mode="json")["verdict"] == "pass"


def test_transition_plan_unknown_verdict_remains_explicit_and_non_authorizing() -> None:
    unknown = _plan(verdict="unknown")
    blocked = _plan(verdict="unknown", required_gaps=("facts_unavailable",))

    assert unknown.verdict == "unknown"
    assert not hasattr(unknown, "ok")
    assert unknown.model_dump(mode="json")["verdict"] == "unknown"
    assert blocked.verdict == "unknown"
    assert blocked.model_dump(mode="json")["verdict"] == "unknown"


def test_verdict_algebra_is_closed() -> None:
    assert Verdict.__args__ == ("pass", "block", "unknown")


def test_transition_plan_requires_all_bound_inputs() -> None:
    with pytest.raises(ValidationError):
        TransitionPlan(nodes=(PlanNode(id="status", kind="check"),))


def test_transition_plan_requires_one_complete_closure() -> None:
    without_closure = {key: value for key, value in _INPUTS.items() if key != "closure"}
    with pytest.raises(TypeError):
        TransitionPlan.compile(**without_closure)

    for field in ("commitment", "prior_attestations", "policy", "effect"):
        incomplete = dict(_INPUTS["closure"])
        incomplete.pop(field)
        with pytest.raises(ValueError, match="transition_plan_closure_invalid"):
            TransitionPlan.compile(**without_closure, closure=incomplete)


@pytest.mark.parametrize("field", ["commitment", "prior_attestations", "policy", "effect"])
def test_transition_plan_rejects_a_mismatched_closure_binding(field: str) -> None:
    closure = dict(_INPUTS["closure"])
    closure[field] = {
        "commitment": _COMMITMENT.model_copy(
            update={"intent": "Different intent."}
        ).identity_projection(),
        "prior_attestations": {"proof": "different"},
        "policy": {"name": "different"},
        "effect": {"operation": "different"},
    }[field]

    with pytest.raises(ValidationError, match="transition_plan_closure_mismatch"):
        TransitionPlan.compile(**(_INPUTS | {"closure": closure}))


def test_compile_plan_binds_commitment_subject_and_scope_to_current_facts() -> None:
    facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"changed_paths": ("src/ethos/result.py",)},
    )
    node = PlanNode(id="status", kind="check", command=("ethos", "status"))

    assert (
        compile_plan(
            commitment=Commitment(
                id="change:test",
                intent="test",
                subjects=("repository:test",),
                scope=("src/**",),
            ),
            facts=facts,
            nodes=(node,),
            policy={"digest": "c" * 64},
        ).verdict
        == "pass"
    )
    assert compile_plan(
        commitment=Commitment(
            id="change:test",
            intent="test",
            subjects=("repository:other",),
            scope=("docs/**",),
        ),
        facts=facts,
        nodes=(node,),
        policy={"digest": "c" * 64},
    ).required_gaps == ("repository_subject_mismatch", "change_scope_exceeded")


def test_repository_wide_scope_matches_root_and_nested_paths() -> None:
    commitment = Commitment(
        id="repository:test",
        intent="govern all paths",
        subjects=("repository:test",),
        scope=("**",),
    )
    facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"changed_paths": ("README.md", "src/ethos/result.py")},
    )

    assert (
        compile_plan(
            commitment=commitment, facts=facts, nodes=(), policy={"digest": "c" * 64}
        ).verdict
        == "pass"
    )


@pytest.mark.parametrize("path", [123, "/absolute.py", "../escape.py", "src\\windows.py"])
def test_compile_plan_rejects_noncanonical_changed_paths(path: object) -> None:
    commitment = Commitment(
        id="change:test",
        intent="test",
        subjects=("repository:test",),
        scope=("**",),
    )
    facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"changed_paths": (path,)},
    )

    assert compile_plan(
        commitment=commitment, facts=facts, nodes=(), policy={"digest": "c" * 64}
    ).required_gaps == ("changed_paths_invalid",)


def test_compile_plan_identity_binds_commitment_facts_and_policy() -> None:
    observed_at = datetime(2026, 7, 25, tzinfo=UTC)
    base_commitment = Commitment(
        id="change:test",
        intent="Preserve the current behavior.",
        subjects=("repository:test",),
        acceptance=("behavior_preserved",),
        permissions=("repository.read",),
    )
    base_facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=observed_at,
        values={"changed_paths": ("src/ethos/result.py",)},
    )
    node = PlanNode(id="status", kind="check", command=("ethos", "status"))

    base = compile_plan(
        commitment=base_commitment,
        facts=base_facts,
        nodes=(node,),
        policy={"digest": "c" * 64},
    )
    changed_commitment = compile_plan(
        commitment=base_commitment.model_copy(
            update={
                "intent": "Replace the current behavior.",
                "acceptance": ("replacement_proven",),
                "permissions": ("repository.write",),
            }
        ),
        facts=base_facts,
        nodes=(node,),
        policy={"digest": "c" * 64},
    )
    changed_facts = compile_plan(
        commitment=base_commitment,
        facts=base_facts.model_copy(update={"head": "d" * 40, "tree": "e" * 40}),
        nodes=(node,),
        policy={"digest": "c" * 64},
    )
    changed_policy = compile_plan(
        commitment=base_commitment,
        facts=base_facts,
        nodes=(node,),
        policy={"digest": "f" * 64},
    )

    assert (
        len(
            {
                base.digest,
                changed_commitment.digest,
                changed_facts.digest,
                changed_policy.digest,
            }
        )
        == 4
    )
    assert base.model_dump(mode="json")["inputs"] == {
        "commitment": base_commitment.digest(),
        "facts": base_facts.digest(),
        "prior_attestations": EMPTY_ATTESTATION_SET_DIGEST,
        "policy": base.inputs.policy,
        "effect": base.inputs.effect,
    }
    assert base.permissions == ("repository.read",)
    assert base.model_dump(mode="json")["permissions"] == ["repository.read"]

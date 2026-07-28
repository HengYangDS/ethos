from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import PlanVerdict
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts

_INPUTS = {
    "commitment_digest": "a" * 64,
    "facts_digest": "b" * 64,
    "policy_digest": "c" * 64,
    "facts": {
        "schema_version": 1,
        "repository": "repository:test",
        "head": "a" * 40,
        "tree": "b" * 40,
        "values": {},
        "source_refs": [],
    },
}


def _plan(
    *, initial_verdict: PlanVerdict = "pass", validation_issues=(), nodes=()
) -> TransitionPlan:
    return TransitionPlan(
        **_INPUTS,
        initial_verdict=initial_verdict,
        validation_issues=validation_issues,
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

    assert [node.id for node in plan.ordered_nodes()] == ["status", "prove", "publish"]
    assert plan.to_dict()["nodes"][0]["id"] == "status"


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

    assert plan.ok is False
    assert "missing_dependency:prove->status" in plan.gaps()


def test_transition_plan_rejects_cycle() -> None:
    plan = _plan(
        nodes=(
            PlanNode(id="a", kind="check", command=("a",), depends_on=("b",)),
            PlanNode(id="b", kind="check", command=("b",), depends_on=("a",)),
        )
    )

    assert plan.ok is False
    assert "cycle_detected" in plan.gaps()


def test_transition_plan_rejects_duplicate_node_id() -> None:
    plan = _plan(
        nodes=(
            PlanNode(id="prove", kind="check", command=("ethos", "prove")),
            PlanNode(id="prove", kind="check", command=("ethos", "prove", "--json")),
        )
    )

    assert plan.ok is False
    assert "duplicate_node_id:prove" in plan.gaps()


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

    payload = plan.to_dict()

    assert payload["nodes"][0]["id"] == "prove"
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["missing_dependency:prove->status"]


def test_valid_transition_plan_has_pass_verdict() -> None:
    plan = _plan(nodes=(PlanNode(id="status", kind="check", command=("ethos", "status")),))

    assert plan.verdict == "pass"
    assert plan.to_dict()["verdict"] == "pass"


def test_transition_plan_unknown_verdict_is_explicit_and_cannot_hide_hard_gaps() -> None:
    unknown = _plan(initial_verdict="unknown")
    blocked = _plan(initial_verdict="unknown", validation_issues=("facts_unavailable",))

    assert unknown.ok is False
    assert unknown.to_dict()["verdict"] == "unknown"
    assert blocked.verdict == "block"
    assert blocked.to_dict()["verdict"] == "block"


def test_plan_verdict_algebra_is_closed() -> None:
    assert PlanVerdict.__args__ == ("pass", "block", "unknown")


def test_transition_plan_requires_all_bound_inputs() -> None:
    with pytest.raises(ValidationError):
        TransitionPlan(nodes=(PlanNode(id="status", kind="check"),))


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
            policy_digest="c" * 64,
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
        policy_digest="c" * 64,
    ).gaps() == ("repository_subject_mismatch", "change_scope_exceeded")


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
        compile_plan(commitment=commitment, facts=facts, nodes=(), policy_digest="c" * 64).verdict
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
        commitment=commitment, facts=facts, nodes=(), policy_digest="c" * 64
    ).gaps() == ("changed_paths_invalid",)


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
        commitment=base_commitment, facts=base_facts, nodes=(node,), policy_digest="c" * 64
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
        policy_digest="c" * 64,
    )
    changed_facts = compile_plan(
        commitment=base_commitment,
        facts=base_facts.model_copy(update={"head": "d" * 40, "tree": "e" * 40}),
        nodes=(node,),
        policy_digest="c" * 64,
    )
    changed_policy = compile_plan(
        commitment=base_commitment,
        facts=base_facts,
        nodes=(node,),
        policy_digest="f" * 64,
    )

    assert (
        len(
            {
                base.digest(),
                changed_commitment.digest(),
                changed_facts.digest(),
                changed_policy.digest(),
            }
        )
        == 4
    )
    assert base.to_dict()["inputs"] == {
        "commitment": base_commitment.digest(),
        "facts": base_facts.digest(),
        "policy": "c" * 64,
    }
    assert base.permissions == ("repository.read",)
    assert base.to_dict()["permissions"] == ["repository.read"]

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from typing import NamedTuple

import pytest
from pydantic import ValidationError

from ethos.contracts.plan import EMPTY_ATTESTATION_SET_DIGEST
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.proof.plan import validate_proof_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import Verdict
from tests.support.literal_cases import literal_case

_COMMITMENT = Commitment(
    id="change:test", intent="Exercise one transition plan.", subjects=("repository:test",)
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
        **_INPUTS, verdict=verdict, required_gaps=required_gaps, nodes=nodes
    )


def _facts(*paths: object, repository: str = "repository:test") -> Facts:
    return Facts(
        repository=repository,
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"changed_paths": paths},
    )


def _commitment(
    *, subjects: tuple[str, ...] = ("repository:test",), scope: tuple[str, ...] = ("**",)
) -> Commitment:
    return Commitment(id="change:test", intent="test", subjects=subjects, scope=scope)


def _compile(
    *paths: object,
    commitment: Commitment | None = None,
    facts: Facts | None = None,
    policy: dict[str, object] | None = None,
    prior: dict[str, object] | None = None,
    nodes: tuple[PlanNode, ...] = (),
) -> TransitionPlan:
    return compile_plan(
        commitment=commitment or _commitment(),
        facts=facts or _facts(*paths),
        nodes=nodes,
        policy=policy or {"digest": "c" * 64},
        prior_attestations=prior or {},
    )


def test_git_effect_program_is_canonical_exact_and_immutable() -> None:
    effect = GitEffect(
        updates={
            "refs/heads/变更": GitRefUpdate(expected="0" * 40, desired="1" * 40),
            "refs/heads/a": GitRefUpdate(expected="2" * 40, desired="3" * 40),
        },
        assertions={"refs/heads/y": "4" * 40},
    )
    reordered = GitEffect(
        updates=dict(reversed(tuple(effect.updates.items()))),
        assertions=dict(reversed(tuple(effect.assertions.items()))),
    )
    assert effect.program() == reordered.program()
    assert b"refs/heads/\xe5\x8f\x98\xe6\x9b\xb4" in effect.program()
    assert effect.digest() == hashlib.sha256(effect.program()).hexdigest()
    with pytest.raises(TypeError):
        effect.assertions["refs/heads/y"] = "5" * 40


@pytest.mark.parametrize(
    ("ref", "assertions"),
    [
        ("refs/heads/dev", {"refs/heads/dev": "0" * 40}),
        ("refs/heads/dev", {"refs/heads/candidate/dev": "invalid"}),
        ("refs/heads/dev\nupdate refs/heads/main", {}),
    ],
)
def test_git_effect_rejects_invalid_refs_and_assertions(
    ref: str, assertions: dict[str, str]
) -> None:
    with pytest.raises(ValidationError, match="git_effect_permissions_invalid"):
        GitEffect(
            updates={ref: GitRefUpdate(expected="0" * 40, desired="1" * 40)},
            assertions=assertions,
        )


def test_transition_plan_orders_and_canonicalizes_dag() -> None:
    nodes = (
        PlanNode(id="status", kind="check", command=("status",)),
        PlanNode(id="prove", kind="decision", command=("prove",), depends_on=("status",)),
        PlanNode(id="publish", kind="effect", command=("publish",), depends_on=("prove",)),
    )
    assert [node.id for node in _plan(nodes=tuple(reversed(nodes))).nodes] == [
        "status",
        "prove",
        "publish",
    ]
    bindings = {"commitment": "a" * 64, "facts": "b" * 64, "policy": "c" * 64}
    assert proof_effect_digest(**bindings, nodes=nodes) == proof_effect_digest(
        **bindings, nodes=tuple(reversed(nodes))
    )
    assert TransitionPlan.closure(nodes) == nodes
    assert TransitionPlan.closure(nodes, ()) == ()


def test_transition_plan_canonicalizes_set_like_inputs() -> None:
    checks = (PlanNode(id="lint", kind="check"), PlanNode(id="test", kind="check"))
    first = TransitionPlan.compile(
        **_INPUTS,
        nodes=(*checks, PlanNode(id="publish", kind="effect", depends_on=("test", "lint", "test"))),
    )
    second = TransitionPlan.compile(
        **_INPUTS,
        nodes=(
            *reversed(checks),
            PlanNode(id="publish", kind="effect", depends_on=("lint", "test")),
        ),
    )
    assert first == second
    assert first.nodes[-1].depends_on == ("lint", "test")


class InvalidDagCase(NamedTuple):
    nodes: tuple[PlanNode, ...]
    gap: str
    serialize: bool = False


_INVALID_DAGS = (
    InvalidDagCase(
        (PlanNode(id="prove", kind="decision", depends_on=("status",)),),
        "missing_dependency:prove->status",
        serialize=True,
    ),
    InvalidDagCase(
        (
            PlanNode(id="a", kind="check", depends_on=("b",)),
            PlanNode(id="b", kind="check", depends_on=("a",)),
        ),
        "cycle_detected",
    ),
    InvalidDagCase(
        (PlanNode(id="prove", kind="check"), PlanNode(id="prove", kind="check")),
        "duplicate_node_id:prove",
    ),
)


@pytest.mark.parametrize("case", _INVALID_DAGS, ids=("missing", "cycle", "duplicate"))
def test_invalid_transition_plan_is_blocked_and_serializable(case: InvalidDagCase) -> None:
    plan = _plan(nodes=case.nodes)
    assert plan.verdict == "block"
    assert case.gap in plan.required_gaps
    if case.serialize:
        payload = plan.model_dump(mode="json")
        assert payload["nodes"][0]["id"] == "prove"
        assert payload["required_gaps"] == [case.gap]


def test_transition_plan_projection_immutability_and_verdict_algebra() -> None:
    plan = _plan(nodes=(PlanNode(id="status", kind="check"),))
    payload = plan.model_dump(mode="json", by_alias=True)
    assert set(payload) == {
        "schema_version",
        "inputs",
        "commitment",
        "prior_attestations",
        "policy",
        "effect",
        "facts",
        "nodes",
        "verdict",
        "required_gaps",
        "digest",
    }
    assert TransitionPlan.model_validate(payload) == plan
    with pytest.raises(TypeError):
        plan.facts["values"]["new"] = True
    unknown = _plan(verdict="unknown", required_gaps=("facts_unavailable",))
    assert (plan.verdict, unknown.verdict, hasattr(unknown, "ok")) == ("pass", "unknown", False)
    assert Verdict.__args__ == ("pass", "block", "unknown")


def test_transition_plan_requires_all_bound_inputs_and_complete_closure() -> None:
    with pytest.raises(ValidationError):
        TransitionPlan(nodes=(PlanNode(id="status", kind="check"),))
    without = {key: value for key, value in _INPUTS.items() if key != "closure"}
    with pytest.raises(TypeError):
        TransitionPlan.compile(**without)
    for field in ("commitment", "prior_attestations", "policy", "effect"):
        incomplete = dict(_INPUTS["closure"])
        incomplete.pop(field)
        with pytest.raises(ValueError, match="transition_plan_closure_invalid"):
            TransitionPlan.compile(**without, closure=incomplete)


@pytest.mark.parametrize("field", ["commitment", "prior_attestations", "policy", "effect"])
def test_transition_plan_rejects_a_mismatched_closure_binding(field: str) -> None:
    closure = dict(_INPUTS["closure"])
    closure[field] = {
        "commitment": _COMMITMENT.model_copy(update={"intent": "Different"}).identity_projection(),
        "prior_attestations": {"proof": "different"},
        "policy": {"name": "different"},
        "effect": {"operation": "different"},
    }[field]
    with pytest.raises(ValidationError, match="transition_plan_closure_mismatch"):
        TransitionPlan.compile(**(_INPUTS | {"closure": closure}))


def test_compile_plan_binds_subject_scope_and_recursive_globs() -> None:
    node = PlanNode(id="status", kind="check")
    assert _compile("src/ethos/result.py", nodes=(node,)).verdict == "pass"
    blocked = _compile(
        "src/ethos/result.py",
        commitment=_commitment(subjects=("repository:other",), scope=("docs/**",)),
        nodes=(node,),
    )
    assert blocked.required_gaps == ("repository_subject_mismatch", "change_scope_exceeded")
    archive = _compile(
        "openspec/changes/archive/2026-08-05-fixture-change/tasks.md",
        commitment=_commitment(scope=("openspec/changes/archive/*-fixture-change/**",)),
    )
    assert (archive.verdict, archive.required_gaps) == ("pass", ())


@pytest.mark.parametrize("path", [123, "/absolute.py", "../escape.py", "src\\windows.py"])
def test_compile_plan_rejects_noncanonical_changed_paths(path: object) -> None:
    assert _compile(path).required_gaps == ("changed_paths_invalid",)


def test_compile_plan_preserves_rehydrated_archive_effect_authority() -> None:
    archive_path = "openspec/changes/archive/2026-08-08-test/commitment.toml"
    spec_path = "openspec/specs/product/spec.md"
    product_path = "src/ethos/product.py"
    commitment = _commitment(scope=(product_path,))
    facts = _facts(archive_path, spec_path, product_path)
    authority = {"openspec_archive": {"authorized_paths": [archive_path, spec_path]}}
    ready = _compile(commitment=commitment, facts=facts, policy={}, prior=authority)
    rehydrated = TransitionPlan.model_validate(ready.model_dump(mode="json"))
    assert (
        _compile(
            commitment=commitment,
            facts=facts,
            policy={},
            prior=dict(rehydrated.prior_attestations),
        )
        == rehydrated
    )
    tampered = _compile(
        commitment=commitment,
        facts=_facts(archive_path, product_path),
        policy={},
        prior=dict(rehydrated.prior_attestations),
    )
    assert tampered.required_gaps == ("proof_archive_scope_stale",)
    uncovered = _compile(
        archive_path,
        spec_path,
        "outside.py",
        commitment=commitment,
        prior=authority,
    )
    assert uncovered.required_gaps == ("change_scope_exceeded",)


def test_compile_plan_identity_binds_commitment_facts_and_policy() -> None:
    commitment = Commitment(
        id="change:test",
        intent="Preserve",
        subjects=("repository:test",),
        acceptance=("behavior_preserved",),
    )
    facts = _facts("src/ethos/result.py")
    node = PlanNode(id="status", kind="check")
    base = _compile(commitment=commitment, facts=facts, nodes=(node,))
    variants = (
        _compile(
            commitment=commitment.model_copy(
                update={
                    "intent": "Replace",
                    "acceptance": ("replacement_proven",),
                }
            ),
            facts=facts,
            nodes=(node,),
        ),
        _compile(
            commitment=commitment,
            facts=facts.model_copy(update={"head": "d" * 40, "tree": "e" * 40}),
            nodes=(node,),
        ),
        _compile(commitment=commitment, facts=facts, nodes=(node,), policy={"digest": "f" * 64}),
    )
    assert len({base.digest, *(plan.digest for plan in variants)}) == 4
    assert base.model_dump(mode="json")["inputs"] == {
        "commitment": commitment.digest(),
        "facts": facts.digest(),
        "prior_attestations": EMPTY_ATTESTATION_SET_DIGEST,
        "policy": base.inputs.policy,
        "effect": base.inputs.effect,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    literal_case(
        "kernel.test_transition_plan:parametrize:test_proof_plan_rejects_policy_node_projection_divergence:0"
    ),
)
def test_proof_plan_rejects_policy_node_projection_divergence(
    field: str, value: list[object]
) -> None:
    commitment = _commitment()
    facts = Facts(
        repository="repository:test",
        head="a" * 40,
        tree="b" * 40,
        observed_at=datetime(2026, 7, 25, tzinfo=UTC),
        values={"gate_ids": ["check"]},
    )
    node = PlanNode(id="check", kind="check", command=("check",))
    policy = {
        "gates": [
            {
                "id": "check",
                "execution_identity": ["check"],
                "depends_on": [],
            }
        ],
        "gaps": [],
    }
    plan = compile_plan(commitment, facts, (node,), policy=policy)
    divergent = plan.model_copy(update={"policy": policy | {field: value}})

    with pytest.raises(ValueError, match="transition_plan_policy_node_mismatch"):
        validate_proof_plan(divergent, commitment, facts)

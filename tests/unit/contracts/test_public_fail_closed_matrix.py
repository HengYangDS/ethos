from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import cast

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
from ethos.contracts.review import ReviewFinding
from ethos.contracts.review import ReviewLens
from ethos.contracts.review import ReviewLensDeclaration
from ethos.contracts.review import ReviewResult
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_results
from ethos.contracts.review import reduce_review_results
from ethos.contracts.review import review_schema_documents
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from pathlib import Path


def _commitment(
    *, scope: tuple[str, ...] = ("src/**",), permissions: tuple[str, ...] = ()
) -> Commitment:
    return Commitment(
        id="change:contract-matrix",
        intent="Keep public contract validation fail-closed.",
        subjects=("repository:test",),
        scope=scope,
        permissions=permissions,
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
    commitment = _commitment(permissions=("git.ref.update:refs/heads/dev",))
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
        permissions=commitment.permissions,
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


def _lens(
    lens_id: str,
    *,
    requires: tuple[str, ...] = (),
    triggers: tuple[str, ...] = (),
) -> ReviewLens:
    return ReviewLens(
        id=lens_id,
        phases=("pre-implementation",),
        requires=requires,
        triggers=triggers,
        owner=f"owner:{lens_id}",
        output_schema="review-result.schema.json",
        max_tokens=0,
    )


def _review_facts(**updates: object) -> dict[str, object]:
    return {
        "head": "a" * 40,
        "tree": "b" * 40,
        "phase": "pre-implementation",
        "requirements": ["contract:closed"],
        "requirement_edges": [
            {"requirement": "contract:closed", "task": "test", "proof": "focused"}
        ],
        "risks": [],
        "affected_capabilities": [],
        "changed_paths": [],
        "ambiguities": [],
        **updates,
    }


def test_review_declaration_and_compilation_fail_closed_at_public_boundary() -> None:
    lens = _lens("base")
    with pytest.raises(ValidationError, match="review_lens_duplicate"):
        ReviewLensDeclaration(lenses=(lens, lens))

    declaration = ReviewLensDeclaration(lenses=(lens,))
    invalid_facts = cast("dict[str, object]", ["not", "an", "object"])
    with pytest.raises(TypeError, match="review_facts_invalid"):
        compile_review_plan(declaration, invalid_facts)
    with pytest.raises(ValueError, match="review_phase_invalid"):
        compile_review_plan(declaration, _review_facts(phase="retired"))

    unresolved = compile_review_plan(
        declaration,
        _review_facts(
            requirements=["contract:closed", "contract:missing"],
            conflicts=["two incompatible intents"],
            ambiguities=["which intent"],
            risks=["trust-bound-publication"],
        ),
    )
    assert unresolved.verdict == "block"
    assert unresolved.required_gaps == (
        "review_traceability_incomplete",
        "review_intent_conflict",
        "review_intent_ambiguous",
    )
    assert unresolved.escalation == (
        "unresolved-intent",
        "trust-bound-publication",
        "final-product-judgment",
    )
    assert unresolved.next_action == "resolve the selected OpenSpec intent before implementation"


def test_review_dependency_and_decision_boundaries_preserve_fail_closed_state() -> None:
    dependency = ReviewLensDeclaration(
        lenses=(
            _lens("base", triggers=("select-base-explicitly",)),
            _lens("child", requires=("base",)),
        )
    )
    dependency_plan = compile_review_plan(dependency, _review_facts())
    assert [lens.id for lens in dependency_plan.lenses] == ["base", "child"]

    missing = ReviewLensDeclaration(lenses=(_lens("child", requires=("absent",)),))
    missing_plan = compile_review_plan(missing, _review_facts())
    assert missing_plan.required_gaps == ("review_lens_dependency_missing:child:absent",)

    cyclic = ReviewLensDeclaration(
        lenses=(
            _lens("first", requires=("second",)),
            _lens("second", requires=("first",)),
        )
    )
    cycle_plan = compile_review_plan(cyclic, _review_facts())
    assert cycle_plan.required_gaps == ("review_lens_dependency_cycle",)
    assert cycle_plan.lenses == ()

    declaration = ReviewLensDeclaration(lenses=(_lens("base"),))
    plan = compile_review_plan(declaration, _review_facts())
    result = ReviewResult(
        review_plan=plan.digest,
        inputs=plan.inputs,
        head=plan.head,
        tree=plan.tree,
        phase=plan.phase,
        lens="base",
        verifier="reviewer:independent",
        verdict="block",
        findings=(
            ReviewFinding(
                code="contract:unsafe",
                message="manual judgment is required",
                repairable=False,
            ),
        ),
        next_action="stop the governed lifecycle",
    )
    decision = reduce_review_results(plan, (result,))
    assert (decision.verdict, decision.state, decision.required_gaps) == (
        "block",
        "gapped",
        (),
    )
    assert decision.next_action == "stop the governed lifecycle"


def test_review_result_loader_and_schema_reject_authority_invention(tmp_path: Path) -> None:
    invalid = tmp_path / "results.json"
    invalid.write_text(
        json.dumps(
            [
                {
                    "review_plan": "a" * 64,
                    "inputs": "b" * 64,
                    "head": "c" * 40,
                    "tree": "d" * 40,
                    "phase": "pre-implementation",
                    "lens": "base",
                    "verifier": "reviewer:independent",
                    "verdict": "pass",
                    "next_action": "continue",
                    "mints_authority": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="review_results_invalid"):
        load_review_results(invalid)

    documents = review_schema_documents()
    assert set(documents) == {"review-plan.schema.json", "review-result.schema.json"}
    for name, schema in documents.items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://ethos.local/schemas/{name}"
    result_schema = documents["review-result.schema.json"]
    assert result_schema["properties"]["mints_authority"]["const"] is False

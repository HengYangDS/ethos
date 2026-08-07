from __future__ import annotations

from pathlib import Path

import pytest

from ethos.contracts.review import ReviewPlan
from ethos.contracts.review import ReviewResult
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_lens_declaration
from ethos.contracts.review import reduce_review_results
from ethos.contracts.semantic import canonical_json_digest


def _facts(**updates: object) -> dict[str, object]:
    return {
        "head": "a" * 40,
        "tree": "b" * 40,
        "workload": "feature",
        "phase": "pre-implementation",
        "affected_capabilities": ["kernel"],
        "ambiguities": [],
        "risks": [],
        "changed_paths": ["src/ethos/contracts/review.py"],
        "requirement_edges": [
            {"requirement": "kernel:review", "task": "6.9", "proof": "unit-review"}
        ],
    } | updates


def test_review_compilation_is_deterministic_and_exact_input_bound() -> None:
    declaration = load_review_lens_declaration(Path("system/review-lenses.toml"))

    first = compile_review_plan(declaration, _facts())
    second = compile_review_plan(declaration, _facts())
    changed = compile_review_plan(declaration, _facts(head="c" * 40))

    assert first.verdict == "pass"
    assert first == second
    assert first.digest != changed.digest
    assert first.inputs == canonical_json_digest(_facts())
    assert first.head == "a" * 40
    assert first.tree == "b" * 40
    assert first.next_action.startswith("execute the compiled review lenses")
    with pytest.raises(ValueError, match="review_plan_digest_mismatch"):
        ReviewPlan.model_validate(first.model_dump(mode="json") | {"head": "d" * 40})
    assert [lens.id for lens in first.lenses] == [
        "structure",
        "traceability",
        "contradiction",
        "architecture",
    ]


def test_review_compilation_scales_post_implementation_lenses_from_risk() -> None:
    declaration = load_review_lens_declaration(Path("system/review-lenses.toml"))

    review = compile_review_plan(
        declaration,
        _facts(
            phase="post-implementation",
            risks=["security", "migration", "irreversible"],
            changed_paths=["src/ethos/adapters/mutation/landing.py"],
        ),
    )

    assert [lens.id for lens in review.lenses] == [
        "structure",
        "traceability",
        "contradiction",
        "realization",
        "reverse-discovery",
        "architecture",
        "security",
        "migration",
        "irreversibility",
    ]
    assert review.escalation == (
        "irreversible-effect",
        "final-product-judgment",
    )


def test_review_compilation_fails_closed_for_ambiguity_or_broken_declaration(
    tmp_path: Path,
) -> None:
    declaration = load_review_lens_declaration(Path("system/review-lenses.toml"))
    ambiguous = compile_review_plan(
        declaration,
        _facts(ambiguities=["choose public compatibility boundary"]),
    )
    broken_path = tmp_path / "review-lenses.toml"
    broken_path.write_text(
        Path("system/review-lenses.toml")
        .read_text(encoding="utf-8")
        .replace('requires = ["structure"]', 'requires = ["missing"]', 1),
        encoding="utf-8",
    )
    broken = compile_review_plan(load_review_lens_declaration(broken_path), _facts())

    assert ambiguous.verdict == "unknown"
    assert ambiguous.required_gaps == ("review_intent_ambiguous",)
    assert ambiguous.escalation == ("unresolved-intent", "final-product-judgment")
    assert ambiguous.user_decision_required is True
    assert broken.verdict == "block"
    assert broken.required_gaps == ("review_lens_dependency_missing:traceability:missing",)


def test_review_compilation_blocks_incomplete_requirement_traceability() -> None:
    declaration = load_review_lens_declaration(Path("system/review-lenses.toml"))

    review = compile_review_plan(
        declaration,
        _facts(requirements=["kernel:review", "kernel:recovery"]),
    )

    assert review.verdict == "block"
    assert review.required_gaps == ("review_traceability_incomplete",)
    assert review.next_action == "map every requirement to its task and proof"


def _result(plan: ReviewPlan, lens: str, **updates: object) -> ReviewResult:
    payload = {
        "review_plan": plan.digest,
        "inputs": plan.inputs,
        "head": plan.head,
        "tree": plan.tree,
        "phase": plan.phase,
        "lens": lens,
        "verifier": f"reviewer:{lens}",
        "verdict": "pass",
        "next_action": "continue",
    }
    return ReviewResult.model_validate(payload | updates)


def test_review_result_reduction_accepts_exact_complete_independent_results() -> None:
    plan = compile_review_plan(
        load_review_lens_declaration(Path("system/review-lenses.toml")),
        _facts(),
    )

    decision = reduce_review_results(
        plan,
        tuple(_result(plan, lens.id) for lens in plan.lenses),
    )

    assert decision.verdict == "pass"
    assert decision.state == "reviewed"
    assert decision.next_action == "continue the governed lifecycle"
    assert decision.required_gaps == ()
    assert decision.user_decision_required is False


def test_review_result_reduction_rejects_stale_missing_or_forged_results() -> None:
    plan = compile_review_plan(
        load_review_lens_declaration(Path("system/review-lenses.toml")),
        _facts(),
    )
    results = tuple(_result(plan, lens.id) for lens in plan.lenses)
    stale = results[0].model_copy(update={"head": "c" * 40})

    decision = reduce_review_results(plan, (stale, *results[2:]))

    assert decision.verdict == "block"
    assert decision.required_gaps == (
        "review_result_binding_mismatch:structure",
        "review_result_missing:traceability",
    )
    assert decision.next_action == "rerun the missing or stale review lenses"


def test_review_result_reduction_rejects_duplicate_or_unselected_lenses() -> None:
    plan = compile_review_plan(
        load_review_lens_declaration(Path("system/review-lenses.toml")),
        _facts(),
    )
    results = tuple(_result(plan, lens.id) for lens in plan.lenses)
    unselected = _result(plan, "security")

    duplicate = reduce_review_results(plan, (results[0], results[0], *results[1:]))
    extra = reduce_review_results(plan, (*results, unselected))

    assert duplicate.required_gaps == ("review_result_duplicate:structure",)
    assert extra.required_gaps == ("review_result_unselected:security",)


def test_review_result_reduction_routes_repair_before_human_escalation() -> None:
    plan = compile_review_plan(
        load_review_lens_declaration(Path("system/review-lenses.toml")),
        _facts(),
    )
    results = tuple(_result(plan, lens.id) for lens in plan.lenses)
    repair = results[1].model_copy(
        update={
            "verdict": "block",
            "findings": ReviewResult.model_validate(
                results[1].model_dump(mode="json")
                | {
                    "findings": [
                        {
                            "code": "traceability:missing-test",
                            "message": "Add the missing requirement test.",
                            "repairable": True,
                        }
                    ]
                }
            ).findings,
            "next_action": "add the missing requirement test",
        }
    )

    decision = reduce_review_results(plan, (results[0], repair, *results[2:]))

    assert decision.verdict == "block"
    assert decision.state == "repair"
    assert decision.next_action == "add the missing requirement test"
    assert decision.user_decision_required is False


def test_review_result_reduction_escalates_only_irreducible_judgment() -> None:
    plan = compile_review_plan(
        load_review_lens_declaration(Path("system/review-lenses.toml")),
        _facts(),
    )
    results = tuple(_result(plan, lens.id) for lens in plan.lenses)
    judgment = results[2].model_copy(
        update={
            "verdict": "unknown",
            "findings": ReviewResult.model_validate(
                results[2].model_dump(mode="json")
                | {
                    "findings": [
                        {
                            "code": "intent:valid-alternatives",
                            "message": "Two product choices preserve all invariants.",
                            "repairable": False,
                        }
                    ]
                }
            ).findings,
            "next_action": "select the intended product behavior",
        }
    )

    decision = reduce_review_results(plan, (*results[:2], judgment, *results[3:]))

    assert decision.verdict == "unknown"
    assert decision.state == "await-user"
    assert decision.next_action == "select the intended product behavior"
    assert decision.user_decision_required is True

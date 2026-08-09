from __future__ import annotations

from pathlib import Path

import pytest

from ethos.contracts.review import ReviewPlan
from ethos.contracts.review import ReviewResult
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_lens_declaration as load
from ethos.contracts.review import reduce_review_results as reduce
from ethos.contracts.semantic import canonical_json_digest
from tests.support.literal_cases import literal_case

DECLARATION = Path("system/review-lenses.toml")


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


def _result(plan: ReviewPlan, lens: str, **updates: object) -> ReviewResult:
    return ReviewResult.model_validate(
        {
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
        | updates
    )


def _plan_results() -> tuple[ReviewPlan, tuple[ReviewResult, ...]]:
    plan = compile_review_plan(load(DECLARATION), _facts())
    return plan, tuple(_result(plan, lens.id) for lens in plan.lenses)


def test_review_compilation_is_deterministic_and_input_bound() -> None:
    first, second = (compile_review_plan(load(DECLARATION), _facts()) for _ in range(2))
    changed = compile_review_plan(load(DECLARATION), _facts(head="c" * 40))
    assert first == second
    assert (first.verdict, first.inputs, first.head, first.tree) == (
        "pass",
        canonical_json_digest(_facts()),
        "a" * 40,
        "b" * 40,
    )
    assert first.digest != changed.digest
    assert [lens.id for lens in first.lenses] == [
        "structure",
        "traceability",
        "contradiction",
        "architecture",
    ]
    with pytest.raises(ValueError, match="review_plan_digest_mismatch"):
        ReviewPlan.model_validate(first.model_dump(mode="json") | {"head": "d" * 40})


def test_review_compilation_scales_post_implementation_risk_lenses() -> None:
    review = compile_review_plan(
        load(DECLARATION),
        _facts(phase="post-implementation", risks=["security", "migration", "irreversible"]),
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
    assert review.escalation == ("irreversible-effect", "final-product-judgment")


@pytest.mark.parametrize(
    ("facts", "declaration_edit", "verdict", "gaps"),
    literal_case(
        "governance.test_review_compilation:parametrize:test_review_compilation_fails_closed:0"
    ),
)
def test_review_compilation_fails_closed(
    tmp_path: Path,
    facts: dict[str, object],
    declaration_edit: tuple[str, str] | None,
    verdict: str,
    gaps: tuple[str, ...],
) -> None:
    declaration = DECLARATION
    if declaration_edit:
        declaration = tmp_path / "review.toml"
        declaration.write_text(DECLARATION.read_text().replace(*declaration_edit, 1))
    review = compile_review_plan(load(declaration), _facts(**facts))
    assert (review.verdict, review.required_gaps) == (verdict, gaps)


def test_review_result_reduction_accepts_exact_complete_results() -> None:
    plan, results = _plan_results()
    decision = reduce(plan, results)
    assert (
        decision.verdict,
        decision.state,
        decision.required_gaps,
        decision.user_decision_required,
    ) == ("pass", "reviewed", (), False)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    literal_case(
        "governance.test_review_compilation:parametrize:test_review_result_reduction_rejects_invalid_sets:1"
    ),
)
def test_review_result_reduction_rejects_invalid_sets(
    mutation: str, expected: tuple[str, ...]
) -> None:
    plan, results = _plan_results()
    supplied = {
        "stale": (results[0].model_copy(update={"head": "c" * 40}), *results[2:]),
        "duplicate": (results[0], results[0], *results[1:]),
        "unselected": (*results, _result(plan, "security")),
    }[mutation]
    assert reduce(plan, supplied).required_gaps == expected


@pytest.mark.parametrize(
    ("verdict", "finding_kind", "state", "user_mode"),
    literal_case(
        "governance.test_review_compilation:parametrize:test_review_result_reduction_routes_repair_before_judgment:2"
    ),
)
def test_review_result_reduction_routes_repair_before_judgment(
    verdict: str, finding_kind: str, state: str, user_mode: str
) -> None:
    plan, results = _plan_results()
    finding = {
        "code": "review:finding",
        "message": "resolve finding",
        "repairable": finding_kind == "repairable",
    }
    changed = ReviewResult.model_validate(
        results[1].model_dump(mode="json")
        | {"verdict": verdict, "findings": [finding], "next_action": "resolve finding"}
    )
    decision = reduce(plan, (results[0], changed, *results[2:]))
    assert (
        decision.verdict,
        decision.state,
        decision.next_action,
        decision.user_decision_required,
    ) == (verdict, state, "resolve finding", user_mode == "ask")

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from ethos.contracts.review import ReviewLensDeclaration
from ethos.contracts.review import ReviewPlan
from ethos.contracts.review import ReviewResult
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_lens_declaration
from ethos.contracts.review import load_review_results
from ethos.contracts.review import reduce_review_results
from ethos.contracts.review import review_schema_documents

DECLARATION = Path("system/review-lenses.toml")


def _facts(**updates: object) -> dict[str, object]:
    return {
        "head": "a" * 40,
        "tree": "b" * 40,
        "phase": "pre-implementation",
        "requirements": ["review:public"],
        "requirement_edges": [{"requirement": "review:public"}],
        "affected_capabilities": [],
        "changed_paths": [],
        "risks": [],
        "ambiguities": [],
    } | updates


def _results(plan: ReviewPlan) -> tuple[ReviewResult, ...]:
    return tuple(
        ReviewResult(
            review_plan=plan.digest,
            inputs=plan.inputs,
            head=plan.head,
            tree=plan.tree,
            phase=plan.phase,
            lens=lens.id,
            verifier=f"reviewer:{lens.id}",
            verdict="pass",
            next_action="continue",
        )
        for lens in plan.lenses
    )


def _declaration(tmp_path: Path, lenses: str) -> ReviewLensDeclaration:
    path = tmp_path / "review.toml"
    path.write_text(
        "schema_version = 1\nid = 'review-lenses'\n" + lenses,
        encoding="utf-8",
    )
    return load_review_lens_declaration(path)


def test_review_declaration_rejects_duplicate_public_lens_ids(tmp_path: Path) -> None:
    lens = (
        "[[lens]]\nid = 'same'\nphases = ['pre-implementation']\n"
        "owner = 'owner'\noutput_schema = 'review-result.schema.json'\nmax_tokens = 0\n"
    )

    with pytest.raises(ValueError, match="review_lens_duplicate"):
        _declaration(tmp_path, lens + lens)


def test_review_result_loader_accepts_portable_json_and_fails_closed(
    tmp_path: Path,
) -> None:
    plan = compile_review_plan(load_review_lens_declaration(DECLARATION), _facts())
    path = tmp_path / "results.json"
    path.write_text(
        json.dumps([result.model_dump(mode="json") for result in _results(plan)]),
        encoding="utf-8",
    )
    assert load_review_results(path) == _results(plan)

    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="review_results_invalid"):
        load_review_results(path)
    with pytest.raises(ValueError, match="review_results_invalid"):
        load_review_results(tmp_path / "missing.json")


def test_review_compilation_rejects_non_object_facts_and_invalid_phase() -> None:
    declaration = load_review_lens_declaration(DECLARATION)
    with pytest.raises(TypeError, match="review_facts_invalid"):
        compile_review_plan(declaration, cast("dict[str, object]", ["invalid"]))
    with pytest.raises(ValueError, match="review_phase_invalid"):
        compile_review_plan(declaration, _facts(phase="release"))


def test_review_compilation_selects_path_trigger_and_reports_traceability_conflict() -> None:
    review = compile_review_plan(
        load_review_lens_declaration(DECLARATION),
        _facts(
            changed_paths=["src/review.py"],
            requirements=["review:public", "review:missing"],
            requirement_edges=[{"requirement": "review:public"}, "invalid"],
            conflicts=["two intents"],
            risks=["trust-bound-publication"],
        ),
    )

    assert review.verdict == "block"
    assert review.required_gaps == (
        "review_traceability_incomplete",
        "review_intent_conflict",
    )
    assert review.next_action == "resolve the selected OpenSpec intent before implementation"
    assert "architecture" in {lens.id for lens in review.lenses}
    assert review.escalation == ("trust-bound-publication", "final-product-judgment")


def test_review_compilation_fails_closed_for_missing_dependency(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "[[lens]]\nid = 'dependent'\nphases = ['pre-implementation']\n"
        "requires = ['absent']\nowner = 'owner'\n"
        "output_schema = 'review-result.schema.json'\nmax_tokens = 0\n",
    )

    review = compile_review_plan(declaration, _facts())

    assert review.required_gaps == ("review_lens_dependency_missing:dependent:absent",)
    assert review.next_action == "repair the review-lens declaration"


def test_review_compilation_closes_selected_lens_dependencies(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "[[lens]]\nid = 'base'\nphases = ['pre-implementation']\ntriggers = ['base']\n"
        "owner = 'owner'\noutput_schema = 'review-result.schema.json'\nmax_tokens = 0\n"
        "[[lens]]\nid = 'dependent'\nphases = ['pre-implementation']\n"
        "requires = ['base']\nowner = 'owner'\n"
        "output_schema = 'review-result.schema.json'\nmax_tokens = 0\n",
    )

    review = compile_review_plan(declaration, _facts())

    assert [lens.id for lens in review.lenses] == ["base", "dependent"]


def test_review_compilation_fails_closed_for_dependency_cycle(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "[[lens]]\nid = 'first'\nphases = ['pre-implementation']\nrequires = ['second']\n"
        "owner = 'owner'\noutput_schema = 'review-result.schema.json'\nmax_tokens = 0\n"
        "[[lens]]\nid = 'second'\nphases = ['pre-implementation']\nrequires = ['first']\n"
        "owner = 'owner'\noutput_schema = 'review-result.schema.json'\nmax_tokens = 0\n",
    )

    review = compile_review_plan(declaration, _facts())

    assert review.required_gaps == ("review_lens_dependency_cycle",)
    assert review.lenses == ()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"inputs": "c" * 64}, "review_result_binding_mismatch:structure"),
        ({"tree": "c" * 40}, "review_result_binding_mismatch:structure"),
        ({"phase": "post-implementation"}, "review_result_binding_mismatch:structure"),
        ({"mints_authority": True}, "review_result_binding_mismatch:structure"),
    ],
)
def test_review_reduction_fails_closed_for_each_exact_binding_coordinate(
    mutation: dict[str, object], expected: str
) -> None:
    plan = compile_review_plan(load_review_lens_declaration(DECLARATION), _facts())
    results = _results(plan)
    changed = results[0].model_copy(update=mutation)

    assert reduce_review_results(plan, (changed, *results[1:])).required_gaps == (expected,)


@pytest.mark.parametrize(
    ("verdict", "state", "expected_user_mode"),
    [
        ("unknown", "await-user", "ask"),
        ("block", "gapped", "continue"),
    ],
)
def test_review_reduction_routes_unknown_and_nonrepairable_blocks(
    verdict: str, state: str, expected_user_mode: str
) -> None:
    plan = compile_review_plan(load_review_lens_declaration(DECLARATION), _facts())
    results = _results(plan)
    changed = results[0].model_copy(update={"verdict": verdict, "next_action": "decide"})

    decision = reduce_review_results(plan, (changed, *results[1:]))

    assert (decision.verdict, decision.state, decision.user_decision_required) == (
        verdict,
        state,
        expected_user_mode == "ask",
    )


def test_review_reduction_reports_every_missing_lens() -> None:
    plan = compile_review_plan(load_review_lens_declaration(DECLARATION), _facts())

    decision = reduce_review_results(plan, ())

    assert decision.required_gaps == tuple(
        f"review_result_missing:{lens.id}" for lens in plan.lenses
    )


def test_review_schema_documents_bind_public_ids_and_titles() -> None:
    documents = review_schema_documents()

    assert set(documents) == {"review-plan.schema.json", "review-result.schema.json"}
    assert documents["review-plan.schema.json"]["$id"].endswith("/review-plan.schema.json")
    assert documents["review-result.schema.json"]["title"] == "ETHOS ReviewResult"

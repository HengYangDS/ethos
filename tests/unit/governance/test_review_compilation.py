from __future__ import annotations

from pathlib import Path

import pytest

from ethos.contracts.review import ReviewPlan
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_lens_declaration
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

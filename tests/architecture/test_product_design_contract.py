from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from ethos.repository.design.integrity import design_integrity_report
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
PLAN = "docs/plans/terminal-governance-product-design.md"
AXIOMS = "system/axioms.md"
PROJECTIONS = {
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/glossary.md",
    "docs/reference/command-plane.md",
}
PUBLIC_ROOTS = {"status", "plan", "prove", "land", "publish", "adopt"}
HIDDEN_ROOTS = {"lane", "hook"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def headings(text: str) -> set[str]:
    return {
        re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", match.group(2).lower())).strip("-")
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    }


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}$", text, re.MULTILINE)
    assert match, heading
    following = re.search(r"^## [^#].+$", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


@pytest.fixture
def design_tree(tmp_path: Path) -> Path:
    for relative in {CANONICAL_OWNER, PLAN, AXIOMS, *PROJECTIONS}:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def test_design_integrity_uses_owner_relations_not_prose_equivalence() -> None:
    report = design_integrity_report(ROOT)

    assert report["ok"] is True, report["required_gaps"]
    assert report["semantic_equivalence"] == "not_evaluated"
    assert PLAN in report["references"]


@pytest.mark.parametrize(
    ("heading", "required_tokens"),
    [
        ("Semantic Kernel", {"Commitment", "Attestation", "TransitionPlan", "Facts"}),
        ("Invalid-State Taxonomy", {"open", "unknown_required_fact", "model_promotion_required"}),
        ("Git-Native Repository Substrate", {"Git-native", "compare-and-swap", "work_lane"}),
        (
            "Isomorphic Adopter Governance",
            {"same kernel", "Profiles and adapters", "not product\ncloning"},
        ),
        (
            "Feedback Intent Preservation",
            {"semantic owner", "acceptance", "proof", "absence reason"},
        ),
        ("Projection Homomorphism", {"identity", "provenance", "validity", "absence reason"}),
    ],
)
def test_canonical_contract_covers_terminal_semantics(
    heading: str, required_tokens: set[str]
) -> None:
    body = section(read(CANONICAL_OWNER), heading)
    assert all(token in body for token in required_tokens), (heading, required_tokens)


def test_canonical_contract_uses_a_closed_machine_grammar_for_model_promotion() -> None:
    contract = read(CANONICAL_OWNER)
    body = re.search(r"^### Model Promotion$(.*?)(?=^## |\Z)", contract, re.MULTILINE | re.DOTALL)

    assert body
    text = body.group(1)
    assert {"contradiction", "model_gap", "model_promotion_required"} <= set(
        re.findall(r"\b[a-z_]+\b", text)
    )
    assert all(token in text for token in ("block effects", "retirement", "Preserve", "recompile"))
    assert not {"alias", "fallback", "shim"}.isdisjoint(set(re.findall(r"\b[a-z]+\b", text)))


def test_axioms_are_a_derived_constraint_not_a_second_truth() -> None:
    axioms = read(AXIOMS)

    assert axioms.startswith("---\n")
    assert "derives: ../docs/governance/product-design-contract.md#root-constraint" in axioms
    assert "second semantic owner" in axioms
    assert "道隐无名" not in axioms
    assert {"Commitment", "Attestation", "proposition"} <= set(
        re.findall(r"\b[A-Za-z][A-Za-z-]*\b", axioms)
    )


def test_design_integrity_rejects_missing_owner_anchor(design_tree: Path) -> None:
    contract = design_tree / CANONICAL_OWNER
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("## Projection Homomorphism", "## Projection"),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert (
        "design_canonical_owner_anchor_missing:projection-homomorphism" in report["required_gaps"]
    )


def test_design_integrity_rejects_unlinked_projection(design_tree: Path) -> None:
    projection = design_tree / "docs/concepts/kernel-model.md"
    projection.write_text(
        projection.read_text(encoding="utf-8").replace(
            "../governance/product-design-contract.md#semantic-kernel",
            "../governance/product-design-contract.md",
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert (
        "design_projection_owner_link_missing:docs/concepts/kernel-model.md"
        in report["required_gaps"]
    )


def test_design_integrity_rejects_non_derived_axioms(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    axioms.write_text(
        axioms.read_text(encoding="utf-8").replace(
            "derives: ../docs/governance/product-design-contract.md#root-constraint",
            "projects: ../docs/governance/product-design-contract.md#semantic-kernel",
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert "design_axioms_derivation_metadata_invalid" in report["required_gaps"]


def test_design_integrity_rejects_duplicated_root_text(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    root_line = next(
        line.removeprefix("> ")
        for line in (design_tree / CANONICAL_OWNER).read_text(encoding="utf-8").splitlines()
        if line.startswith("> ")
    )
    axioms.write_text(
        f"{axioms.read_text(encoding='utf-8')}\n{root_line}\n",
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert "design_axioms_duplicates_root_verse" in report["required_gaps"]


def test_terminal_plan_projects_canonical_semantics_without_repeating_its_model() -> None:
    plan = read(PLAN)

    assert "product-design-contract.md#semantic-kernel" in plan
    assert "product-design-contract.md#model-promotion" in plan
    assert headings(plan) >= {
        "semantic-authority-and-projection-homomorphism",
        "model-promotion",
        "git-native-transaction-boundary",
        "adopter-isomorphism-and-first-hour-ux",
        "feedback-intent-preservation",
    }
    assert "The only durable semantic roots" not in plan


def test_first_hour_projection_is_consistent_for_people_and_adopters() -> None:
    contract = read(CANONICAL_OWNER)
    readme = read("README.md")
    glossary = read("docs/reference/glossary.md")

    for text in (contract, readme, glossary):
        assert "same kernel" in text
        assert "profiles and adapters" in text.lower()
    assert "status -> plan -> prove -> land -> publish" in contract
    assert "status -> plan -> prove -> land -> publish" in readme


def test_live_cyclopts_tree_has_exact_public_and_hidden_roots() -> None:
    load_command_groups([])
    commands = {
        name: command
        for name, command in app.resolved_commands().items()
        if not name.startswith("-")
    }

    assert {name for name, command in commands.items() if command.show} == PUBLIC_ROOTS
    assert {name for name, command in commands.items() if not command.show} == HIDDEN_ROOTS

from __future__ import annotations

import re
import shutil
import tomllib
from pathlib import Path

import pytest
import yaml

from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.design.integrity import front_matter_ok
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
PLAN = "docs/plans/terminal-governance-product-design.md"
SOURCE_CHANGE_ID = "change:terminal-convergence"
AXIOMS = "system/axioms.md"
PROJECTIONS = {
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/glossary.md",
    "docs/reference/command-plane.md",
}
PUBLIC_ROOTS = {
    "status",
    "plan",
    "prove",
    "land",
    "publish",
    "adopt",
    "migrate-local-state",
}
HIDDEN_ROOTS = {"lane", "hook"}
SUCCESSOR_OUTCOMES = {
    "accepted-spec-reconciliation",
    "portable-reference-boundary",
    "transition-invariant-proof",
    "openspec-18-cutover",
    "coordination-reconstruction",
    "integration-throughput-housekeeping",
    "repository-knowledge-grammar",
    "knowledge-evolution",
    "hermetic-quality-toolchain",
    "forge-projection-homomorphism",
    "terminal-compression",
    "adopter-product-surfaces",
    "workflow-method-evaluation",
    "terminal-local-closeout",
    "dual-provider-publication",
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def change_carrier(change_id: str) -> Path:
    carriers = tuple(
        path.parent
        for path in (ROOT / "openspec" / "changes").glob("**/commitment.toml")
        if tomllib.loads(path.read_text(encoding="utf-8"))["id"] == change_id
    )
    assert len(carriers) == 1, carriers
    return carriers[0]


def tracked_markdown(root: Path) -> tuple[str, ...]:
    return tuple(path.relative_to(root).as_posix() for path in root.rglob("*.md"))


def headings(text: str) -> set[str]:
    return {
        re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", match.group(2).lower())).strip("-")
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    }


def section(text: str, heading: str, *, level: int = 2) -> str:
    marker = "#" * level
    match = re.search(rf"^{marker} {re.escape(heading)}$", text, re.MULTILINE)
    assert match, heading
    following = re.search(rf"^#{{1,{level}}} [^#].+$", text[match.end() :], re.MULTILINE)
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
    report = design_integrity_report(
        ROOT,
        tracked_documents=tracked_markdown(ROOT),
    )

    assert report["verdict"] == "pass", report["required_gaps"]
    assert report["semantic_equivalence"] == "not_evaluated"
    assert PLAN in report["references"]


def test_design_integrity_uses_supplied_tracked_document_facts(design_tree: Path) -> None:
    """Filesystem visibility must not create a second tracked-document truth."""
    rogue = design_tree / "docs/rogue.md"
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_text(
        "[Owner](governance/product-design-contract.md#semantic-kernel)\n",
        encoding="utf-8",
    )
    tracked = tuple(
        path.relative_to(design_tree).as_posix()
        for path in design_tree.rglob("*.md")
        if path != rogue
    )

    report = design_integrity_report(design_tree, tracked_documents=tracked)

    assert "docs/rogue.md" not in report["references"]


@pytest.mark.parametrize(
    ("heading", "required_tokens"),
    [
        ("Semantic Kernel", {"Commitment", "Attestation", "TransitionPlan", "Facts"}),
        (
            "Invalid-State Taxonomy",
            {"open", "unknown_required_fact", "model_promotion_required"},
        ),
        (
            "Git-Native Repository Substrate",
            {"Git-native", "compare-and-swap", "work_lane"},
        ),
        (
            "Isomorphic Adopter Governance",
            {"same kernel", "Profiles and adapters", "not product\ncloning"},
        ),
        (
            "Feedback Intent Preservation",
            {"semantic owner", "acceptance", "proof", "absence reason"},
        ),
        (
            "Projection Homomorphism",
            {"identity", "provenance", "validity", "absence reason"},
        ),
    ],
)
def test_canonical_contract_covers_product_semantics(
    heading: str, required_tokens: set[str]
) -> None:
    body = section(read(CANONICAL_OWNER), heading)
    assert all(token in body for token in required_tokens), (heading, required_tokens)


def test_canonical_contract_uses_a_closed_machine_grammar_for_model_promotion() -> None:
    text = section(read(CANONICAL_OWNER), "Model Promotion", level=3)

    assert {"contradiction", "model_gap", "model_promotion_required"} <= set(
        re.findall(r"\b[a-z_]+\b", text)
    )
    assert all(token in text for token in ("block effects", "retirement", "Preserve", "recompile"))
    assert {"alias", "fallback", "shim"} <= set(re.findall(r"\b[a-z]+\b", text))


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

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

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

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

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

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

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

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

    assert "design_axioms_duplicates_root_verse" in report["required_gaps"]


def test_design_integrity_reports_missing_native_owner_projection_and_axioms(
    design_tree: Path,
) -> None:
    (design_tree / CANONICAL_OWNER).unlink()
    (design_tree / "README.md").unlink()
    (design_tree / AXIOMS).unlink()

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

    assert {
        f"design_canonical_owner_missing:{CANONICAL_OWNER}",
        "design_projection_missing:README.md",
        f"design_axioms_missing:{AXIOMS}",
    } <= set(report["required_gaps"])


def test_design_integrity_reports_invalid_owner_and_projection_metadata(design_tree: Path) -> None:
    owner = design_tree / CANONICAL_OWNER
    owner.write_text(
        owner.read_text(encoding="utf-8").replace("state: canonical", "state: active"),
        encoding="utf-8",
    )
    projection = design_tree / "docs/concepts/kernel-model.md"
    projection.write_text(
        projection.read_text(encoding="utf-8")
        .replace("state: active", "state: canonical")
        .replace("projects:", "canonical_for:"),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

    assert "design_canonical_owner_front_matter_invalid" in report["required_gaps"]
    assert (
        "design_projection_front_matter_invalid:docs/concepts/kernel-model.md"
        in report["required_gaps"]
    )


def test_design_integrity_reports_each_missing_axiom_boundary(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    text = axioms.read_text(encoding="utf-8")
    text = text.replace("product-design-contract.md#root-constraint", "product-design-contract.md")
    text = text.replace("second semantic owner", "parallel text")
    text = text.replace("Commitment", "Intent")
    axioms.write_text(text, encoding="utf-8")

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

    assert {
        "design_axioms_derivation_metadata_invalid",
        "design_axioms_root_constraint_link_missing",
        "design_axioms_derivation_boundary_missing",
        "design_axioms_term_missing:Commitment",
    } <= set(report["required_gaps"])


def test_design_integrity_deduplicates_forbidden_native_projection_gaps(design_tree: Path) -> None:
    forbidden = design_tree / ".claude"
    forbidden.mkdir()

    report = design_integrity_report(design_tree, tracked_documents=tracked_markdown(design_tree))

    assert report["required_gaps"].count("design_integrity_forbidden_projection_path:.claude") == 1


def test_front_matter_ok_fails_closed_for_missing_and_partial_documents(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"
    partial = tmp_path / "partial.md"
    partial.write_text("---\nsubject: example\nrole: reference\n---\n", encoding="utf-8")
    complete = tmp_path / "complete.md"
    complete.write_text(
        "---\nsubject: example\nrole: reference\nstate: active\nrelations: none\n---\n",
        encoding="utf-8",
    )

    assert front_matter_ok(missing) is False
    assert front_matter_ok(partial) is False
    assert front_matter_ok(complete) is True


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
        "campaign-projection-and-convergence-route",
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


def test_campaign_has_one_progress_owner_and_acyclic_phase_outcomes() -> None:
    contract = section(read(CANONICAL_OWNER), "Campaign And Change Granularity")
    route = section(read(PLAN), "Campaign Projection And Convergence Route", level=3)
    rows = re.findall(r"^\| `([^`]+)` \| (.+?) \| (.+?) \|$", route, re.MULTILINE)
    order = {outcome: index for index, (outcome, _dependencies, _acceptance) in enumerate(rows)}

    assert set(order) == SUCCESSOR_OUTCOMES
    assert all(acceptance.strip() for _outcome, _dependencies, acceptance in rows)
    for outcome, dependencies, _acceptance in rows:
        for dependency in re.findall(r"`([^`]+)`", dependencies):
            assert dependency in order, (outcome, dependency)
            assert order[dependency] < order[outcome], (outcome, dependency)
    assert "one task-progress owner" in contract
    assert "independently verifiable phase outcomes" in contract
    assert "Moving an obligation never counts as implementing it" in contract
    assert "no fixed global WIP number" in contract


def test_openspec_workspace_owns_atomic_change_lifecycle() -> None:
    workspace = read("openspec/README.md")

    assert "every\nmutation-capable adopter" in workspace
    assert "A Campaign has one OpenSpec task-progress owner" in workspace
    assert "migration as implementation" in workspace
    assert "terminal-convergence Campaign deliberately remains one active Change" in workspace


def test_terminal_change_keeps_every_remaining_obligation_once() -> None:
    carrier = change_carrier(SOURCE_CHANGE_ID)
    design = section(
        carrier.joinpath("design.md").read_text(encoding="utf-8"), "Campaign Dependency Graph"
    )
    tasks = carrier.joinpath("tasks.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| (.+?) \| (.+?) \| (.+?) \|$", design, re.MULTILINE)
    mapped = [
        task
        for _outcome, tasks, _dependencies, _acceptance in rows
        for task in re.findall(r"`([3-7]\.\d+)`", tasks)
    ]
    expected = [
        "3.4",
        "3.5",
        "3.6",
        *(f"4.{index}" for index in range(1, 7)),
        *(f"5.{index}" for index in range(1, 8)),
        *(f"6.{index}" for index in range(1, 11)),
        *(f"7.{index}" for index in range(1, 5)),
    ]

    assert len(rows) == len(SUCCESSOR_OUTCOMES)
    assert sorted(mapped) == sorted(expected)
    assert len(mapped) == len(set(mapped))
    assert "Migrated without implementation" not in tasks
    pre_archive = [task for task in expected if not task.startswith("7.")]
    post_archive = [task for task in expected if task.startswith("7.")]
    assert all(
        re.search(rf"^- \[x\] {re.escape(task)} ", tasks, re.MULTILINE) for task in pre_archive
    )
    assert all(
        re.search(rf"^- \*\*{re.escape(effect)}\*\* ", tasks, re.MULTILINE)
        for effect in post_archive
    )
    assert "- [ ]" not in tasks
    assert "Post-archive effects are not OpenSpec completion tasks" in tasks


def test_terminal_commitment_claims_complete_campaign_closeout() -> None:
    commitment = tomllib.loads(
        change_carrier(SOURCE_CHANGE_ID).joinpath("commitment.toml").read_text(encoding="utf-8")
    )

    assert commitment["acceptance"] == [
        "contract_attestation_plan_and_effect_chain_proven",
        "campaign_lane_records_docs_skills_and_ci_are_derived",
        "three_adopter_profiles_conform",
        "warnings_and_suppressions_zero",
        "terminal_role_local_source_budget_met",
        "local_gitlab_and_github_planes_independently_attested",
    ]
    assert "python_source_roles_do_not_compensate" in commitment["invariants"]
    assert commitment["dependencies"] == []


def test_terminal_archive_preserves_already_reconciled_specs() -> None:
    carrier = change_carrier(SOURCE_CHANGE_ID)
    metadata = yaml.safe_load(carrier.joinpath(".openspec.yaml").read_text(encoding="utf-8"))

    assert metadata["skip_specs"] is True
    assert not carrier.joinpath("specs").exists()
    assert "already carry the terminal behavior" in carrier.joinpath("README.md").read_text(
        encoding="utf-8"
    )


def test_branch_roles_and_thresholds_have_machine_owners() -> None:
    routing = tomllib.loads(read("system/routing.toml"))["branch_roles"]
    coverage = tomllib.loads(read(".config/checks/coverage/policy.toml"))
    source_budget = tomllib.loads(read(".config/checks/format/selection.toml"))["source_budget"][
        "terminal"
    ]
    release = read("docs/governance/release-governance.md")

    assert routing == {
        "release_branch": "main",
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "work_branch_prefix": "work/",
        "proposal_branch_prefix": "proposal/",
    }
    assert coverage["current_hard_floor"] == 95
    assert coverage["aspirational_floor"] == 95
    assert coverage["branch_coverage_required"] is True
    assert source_budget == {
        "python_product": 40_000,
        "python_tests": 36_000,
        "python_tools": 4_000,
        "python_other": 200,
        "global_total": 85_000,
    }
    assert "`candidate/dev` and every `work/*` branch are local-only" in release
    assert "`dev`, `main`, and `proposal/*`" in release
    assert "submit/*" not in release


def test_current_docs_do_not_depend_on_one_active_change_path() -> None:
    current_docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "docs").rglob("*.md"))
        if "history" not in path.relative_to(ROOT).parts
    )

    assert "openspec/changes/terminal-convergence" not in current_docs


def test_entrypoints_do_not_resurrect_global_authority_or_retired_kernel_names() -> None:
    agents = read("AGENTS.md")
    authority = read("docs/governance/authority.md")
    readme = read("README.md")

    assert "## Authority Order" not in agents
    assert all(token in authority for token in ("subject", "context", "valid Attestations"))
    assert all(token not in readme for token in ("ChangeContract", "RepositoryFacts", "PlanIR"))
    assert "(Commitment, Facts, prior Attestations) -> TransitionPlan" in readme
    assert "Only Commitment and Attestation persist" in readme


def test_lane_runner_bootstrap_uses_the_checkout_bound_uv_command() -> None:
    carrier = read("src/ethos/adapters/mutation/lane_start_receipt.py")

    assert '"command": "uv run --frozen --offline ethos"' in carrier
    assert "tools/ci/scripts/run-ethos-lane.sh" not in carrier
    assert not re.search(r'"command": "(?:command )?ethos(?: |")', carrier)

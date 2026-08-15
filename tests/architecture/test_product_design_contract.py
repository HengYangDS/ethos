from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

import pytest
import tomllib

from ethos.repository.design.integrity import design_integrity_report, front_matter_ok
from ethos.repository.openspec.audit import active_change_names_from_paths
from ethos.surface.cli.application import app, load_command_groups

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
PLAN = "docs/plans/terminal-governance-product-design.md"
ACTIVE_CHANGE_ID = "change:model-promotion"
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
    "attestation",
    "migrate-local-state",
}
HIDDEN_ROOTS = {"lane", "hook"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _cyclopts_app_assignment_lines(path: Path) -> tuple[int, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    app_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "cyclopts"
        for alias in node.names
        if alias.name == "App"
    }
    cyclopts_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "cyclopts"
    }
    return tuple(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and isinstance(node.value, ast.Call)
        and (
            (isinstance(node.value.func, ast.Name) and node.value.func.id in app_names)
            or (
                isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id in cyclopts_names
                and node.value.func.attr == "App"
            )
        )
    )


def active_change_carriers(root: Path = ROOT) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.joinpath("openspec", "changes").iterdir()
            if path.is_dir() and path.name != "archive"
        )
    )


def declared_change_dependencies(commitment: dict[str, object]) -> tuple[str, ...]:
    dependencies = commitment.get("dependencies", [])
    assert isinstance(dependencies, list)
    return tuple(
        target
        for dependency in dependencies
        if isinstance(dependency, dict)
        and isinstance(target := dependency.get("target"), str)
        and target.startswith("change:")
    )


def tracked_markdown(root: Path) -> tuple[str, ...]:
    return tuple(path.relative_to(root).as_posix() for path in root.rglob("*.md"))


def test_each_production_module_owns_at_most_one_cyclopts_application() -> None:
    source_root = ROOT / "src" / "ethos"
    offenders = {
        path.relative_to(ROOT).as_posix(): lines
        for path in source_root.rglob("*.py")
        if len(lines := _cyclopts_app_assignment_lines(path)) > 1
    }

    assert offenders == {}


def headings(text: str) -> set[str]:
    return {
        re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", match.group(2).lower())).strip(
            "-"
        )
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    }


def section(text: str, heading: str, *, level: int = 2) -> str:
    marker = "#" * level
    match = re.search(rf"^{marker} {re.escape(heading)}$", text, re.MULTILINE)
    assert match, heading
    following = re.search(
        rf"^#{{1,{level}}} [^#].+$", text[match.end() :], re.MULTILINE
    )
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


def test_design_integrity_uses_supplied_tracked_document_facts(
    design_tree: Path,
) -> None:
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
    assert all(
        token in text
        for token in ("block effects", "retirement", "Preserve", "recompile")
    )
    assert {"alias", "fallback", "shim"} <= set(re.findall(r"\b[a-z]+\b", text))


def test_axioms_are_a_derived_constraint_not_a_second_truth() -> None:
    axioms = read(AXIOMS)

    assert axioms.startswith("---\n")
    assert (
        "derives: ../docs/governance/product-design-contract.md#root-constraint"
        in axioms
    )
    assert "second semantic owner" in axioms
    assert "道隐无名" not in axioms
    assert {"Commitment", "Attestation", "proposition"} <= set(
        re.findall(r"\b[A-Za-z][A-Za-z-]*\b", axioms)
    )


def test_design_integrity_rejects_missing_owner_anchor(design_tree: Path) -> None:
    contract = design_tree / CANONICAL_OWNER
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            "## Projection Homomorphism", "## Projection"
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert (
        "design_canonical_owner_anchor_missing:projection-homomorphism"
        in report["required_gaps"]
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

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

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

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert "design_axioms_derivation_metadata_invalid" in report["required_gaps"]


def test_design_integrity_rejects_duplicated_root_text(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    root_line = next(
        line.removeprefix("> ")
        for line in (design_tree / CANONICAL_OWNER)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("> ")
    )
    axioms.write_text(
        f"{axioms.read_text(encoding='utf-8')}\n{root_line}\n",
        encoding="utf-8",
    )

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert "design_axioms_duplicates_root_verse" in report["required_gaps"]


def test_design_integrity_reports_missing_native_owner_projection_and_axioms(
    design_tree: Path,
) -> None:
    (design_tree / CANONICAL_OWNER).unlink()
    (design_tree / "README.md").unlink()
    (design_tree / AXIOMS).unlink()

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert {
        f"design_canonical_owner_missing:{CANONICAL_OWNER}",
        "design_projection_missing:README.md",
        f"design_axioms_missing:{AXIOMS}",
    } <= set(report["required_gaps"])


def test_design_integrity_reports_invalid_owner_and_projection_metadata(
    design_tree: Path,
) -> None:
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

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert "design_canonical_owner_front_matter_invalid" in report["required_gaps"]
    assert (
        "design_projection_front_matter_invalid:docs/concepts/kernel-model.md"
        in report["required_gaps"]
    )


def test_design_integrity_reports_each_missing_axiom_boundary(
    design_tree: Path,
) -> None:
    axioms = design_tree / AXIOMS
    text = axioms.read_text(encoding="utf-8")
    text = text.replace(
        "product-design-contract.md#root-constraint", "product-design-contract.md"
    )
    text = text.replace("second semantic owner", "parallel text")
    text = text.replace("Commitment", "Intent")
    axioms.write_text(text, encoding="utf-8")

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert {
        "design_axioms_derivation_metadata_invalid",
        "design_axioms_root_constraint_link_missing",
        "design_axioms_derivation_boundary_missing",
        "design_axioms_term_missing:Commitment",
    } <= set(report["required_gaps"])


def test_design_integrity_deduplicates_forbidden_native_projection_gaps(
    design_tree: Path,
) -> None:
    forbidden = design_tree / ".claude"
    forbidden.mkdir()

    report = design_integrity_report(
        design_tree, tracked_documents=tracked_markdown(design_tree)
    )

    assert (
        report["required_gaps"].count(
            "design_integrity_forbidden_projection_path:.claude"
        )
        == 1
    )


def test_front_matter_ok_fails_closed_for_missing_and_partial_documents(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.md"
    partial = tmp_path / "partial.md"
    partial.write_text(
        "---\nsubject: example\nrole: reference\n---\n", encoding="utf-8"
    )
    complete = tmp_path / "complete.md"
    complete.write_text(
        "---\nsubject: example\nrole: reference\nstate: active\nrelations: none\n---\n",
        encoding="utf-8",
    )

    assert front_matter_ok(missing) is False
    assert front_matter_ok(partial) is False
    assert front_matter_ok(complete) is True


def test_terminal_plan_projects_canonical_semantics_without_repeating_its_model() -> (
    None
):
    plan = read(PLAN)

    assert "product-design-contract.md#semantic-kernel" in plan
    assert "product-design-contract.md#model-promotion" in plan
    assert headings(plan) >= {
        "semantic-authority-and-projection-homomorphism",
        "model-promotion",
        "git-native-transaction-boundary",
        "adopter-isomorphism-and-first-hour-ux",
        "feedback-intent-preservation",
        "bounded-change-convergence-route",
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
    assert {
        name for name, command in commands.items() if not command.show
    } == HIDDEN_ROOTS


def test_one_bounded_active_change_owns_commitment_tasks_and_proof_mapping() -> None:
    carriers = active_change_carriers()
    assert tuple(carrier.name for carrier in carriers) == ("model-promotion",)

    carrier = carriers[0]
    assert carrier.joinpath("commitment.toml").is_file()
    assert carrier.joinpath("tasks.md").is_file()
    commitment = tomllib.loads(
        carrier.joinpath("commitment.toml").read_text(encoding="utf-8")
    )
    tasks = carrier.joinpath("tasks.md").read_text(encoding="utf-8")
    task_ids = re.findall(r"^- \[[ x]\] \*\*(\d+)\.", tasks, re.MULTILINE)
    proof_task_ids = re.findall(r"^\| .+? \| (\d+) \| `[^`]+` \|$", tasks, re.MULTILINE)

    assert commitment["id"] == ACTIVE_CHANGE_ID
    assert f"openspec/changes/{carrier.name}/**" in commitment["scope"]
    assert task_ids == ["1", "2", "3", "4", "5"]
    assert set(proof_task_ids) == set(task_ids)
    assert len(task_ids) == len(set(task_ids))
    assert "the only progress authority for this bounded model foundation" in tasks


def test_active_change_dependencies_are_acyclic_when_declared() -> None:
    commitments = {
        commitment["id"]: commitment
        for carrier in active_change_carriers()
        for commitment in [
            tomllib.loads(
                carrier.joinpath("commitment.toml").read_text(encoding="utf-8")
            )
        ]
    }

    def visit(change_id: str, path: tuple[str, ...]) -> None:
        assert change_id not in path, (*path, change_id)
        for dependency in declared_change_dependencies(commitments[change_id]):
            assert dependency in commitments, dependency
            visit(dependency, (*path, change_id))

    for change_id in commitments:
        visit(change_id, ())


def test_archived_changes_do_not_select_current_progress() -> None:
    archived = ROOT / "openspec/changes/archive/2026-08-10-terminal-convergence"
    active = (
        "openspec/changes/model-promotion/commitment.toml",
        "openspec/changes/model-promotion/tasks.md",
    )
    poisoned = (
        *active,
        "openspec/changes/archive/2026-08-10-terminal-convergence/commitment.toml",
        "openspec/changes/archive/2026-08-10-terminal-convergence/tasks.md",
        "openspec/changes/archive/contradictory-current-owner/tasks.md",
    )

    assert archived.is_dir()
    assert (
        active_change_names_from_paths("HEAD", poisoned)
        == active_change_names_from_paths("HEAD", active)
        == {
            "verdict": "pass",
            "ref": "HEAD",
            "changes": ["model-promotion"],
            "required_gaps": [],
        }
    )


def test_branch_roles_and_thresholds_have_machine_owners() -> None:
    routing = tomllib.loads(read("system/routing.toml"))["branch_roles"]
    coverage = tomllib.loads(read(".config/checks/coverage/policy.toml"))
    source_budget = tomllib.loads(read(".config/checks/format/selection.toml"))[
        "source_budget"
    ]["terminal"]
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


def test_entrypoints_do_not_resurrect_global_authority_or_retired_kernel_names() -> (
    None
):
    agents = read("AGENTS.md")
    authority = read("docs/governance/authority.md")
    readme = read("README.md")

    assert "## Authority Order" not in agents
    assert all(
        token in authority for token in ("subject", "context", "valid Attestations")
    )
    assert all(
        token not in readme for token in ("ChangeContract", "RepositoryFacts", "PlanIR")
    )
    assert "(Commitment, Facts, prior Attestations) -> TransitionPlan" in readme
    assert "Only Commitment and Attestation persist" in readme


def test_lane_runner_bootstrap_uses_the_checkout_bound_uv_command() -> None:
    carrier = read("src/ethos/adapters/mutation/lane_start_receipt.py")

    assert '"command": "uv run --frozen --offline ethos"' in carrier
    assert "tools/ci/scripts/run-ethos-lane.sh" not in carrier
    assert not re.search(r'"command": "(?:command )?ethos(?: |")', carrier)

from __future__ import annotations

import re
import shutil
import tomllib
from pathlib import Path

import pytest

from ethos.repository.design.integrity import design_integrity_report
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
PLAN = "docs/plans/terminal-governance-product-design.md"
AXIOMS = "system/axioms.md"
TERMINAL_TASKS = "openspec/changes/terminal-convergence/tasks.md"
TERMINAL_PROPOSAL = "openspec/changes/terminal-convergence/proposal.md"
TERMINAL_DESIGN = "openspec/changes/terminal-convergence/design.md"
TERMINAL_SPECS = "openspec/changes/terminal-convergence/specs"
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


def test_terminal_tasks_preserve_stable_identity_and_completed_foundations() -> None:
    tasks = read(TERMINAL_TASKS)
    rows = re.findall(r"^- \[([ x])\] ((?:F|\d+)\.\d+(?:\.\d+)?)\b", tasks, re.MULTILINE)
    identifiers = [identifier for _state, identifier in rows]
    completed = {identifier for state, identifier in rows if state == "x"}

    assert len(identifiers) == len(set(identifiers))
    assert {f"F.{index}" for index in range(1, 12)} | {"0.1"} <= completed
    assert "first unchecked item in section 0 is the critical path" in tasks.replace("\n", " ")
    assert len(re.findall(r"^\*\*Exit \d:\*\*", tasks, re.MULTILINE)) == 8
    compact = " ".join(tasks.split())
    assert "0.2.1 Add failing tests for two-root persistence" in compact
    assert "0.3.1 Map every active carrier and legacy surface" in compact
    assert "0.4 Close every independent accepted feedback obligation" in compact


def test_terminal_thresholds_and_branch_roles_have_one_exact_projection() -> None:
    proposal = read(TERMINAL_PROPOSAL)
    tasks = read(TERMINAL_TASKS)
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
    assert coverage["branch_coverage_required"] is True
    assert source_budget == {"python_total": 54_000, "global_total": 68_000}
    for text in (proposal, tasks):
        assert all(token in text for token in ("54,000", "68,000", "95"))
    assert "`candidate/dev` and every `work/*` branch are local-only" in release
    assert "`dev`, `main`, and `proposal/*`" in release
    assert "submit/*" not in release


def test_terminal_execution_contract_is_self_profile_only_and_progress_is_irreversible() -> None:
    tasks = read(TERMINAL_TASKS)
    design = read(TERMINAL_DESIGN)
    compact_tasks = " ".join(tasks.split())
    compact_design = " ".join(design.split())

    assert "For the ETHOS self-profile only" in tasks
    assert "single campaign execution" in compact_tasks
    assert "task identity" in compact_tasks
    assert "never renumber" in compact_tasks
    assert "first incomplete task is the campaign critical path" in compact_design
    assert "elapsed activity without a terminal-state delta is not progress" in compact_design
    assert "old decisions" not in tasks.lower()

    assert "never renumbers work to reset progress" in compact_tasks
    assert "block task-ID reuse, completion reset" in compact_tasks


def test_terminal_runtime_owner_is_checkout_bound_through_with_python_runtime() -> None:
    runner = read("tools/ci/scripts/run-ethos-lane.sh")
    runtime = read("tools/ci/scripts/with-python-runtime.sh")

    assert 'exec "${script_dir}/with-python-runtime.sh" --' in runner
    assert 'uv run --group dev ethos "$@"' in runner
    assert "git rev-parse --show-toplevel" in runtime
    assert 'export ETHOS_RUNTIME_ROOT="${repo_root}"' in runtime
    assert not re.search(r"(?:^|[;&|])\s*(?:command\s+)?ethos(?:\s|$)", runner, re.MULTILINE)
    assert 'PATH="${repo_root}' not in runner


def test_terminal_specs_bind_the_critical_cross_surface_semantics() -> None:
    required = {
        "repository-governance/spec.md": (
            "takeover",
            "records",
            "candidate cas",
            "local convergence completion",
        ),
        "proof-hosts/spec.md": (
            "one terminal HEAD",
            "GitLab",
            "GitHub",
            "artifact",
            "bounded formal transition model",
        ),
        "contracts/spec.md": (
            "Python SDK",
            "subprocess JSON",
            "portable contract",
        ),
        "distribution/spec.md": (
            "one portable release contract",
            "artifact",
            "offline",
        ),
        "adapters/spec.md": (
            "exact permissions",
            "exact receipt",
            "mutation",
        ),
        "quality/spec.md": (
            "54,000",
            "68,000",
            "95",
            "repository-wide",
        ),
    }
    for relative, tokens in required.items():
        body = read(f"{TERMINAL_SPECS}/{relative}")
        assert all(token.lower() in body.lower() for token in tokens), (relative, tokens)

from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
REQUIRED_DESIGN_PROJECTIONS = {
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/command-plane.md",
    "docs/reference/glossary.md",
}
PUBLIC_ROOTS = {"status", "plan", "prove", "land", "publish", "adopt"}
HIDDEN_ROOTS = {"lane", "hook"}
TERMINAL_REPOSITORY_REPLACEMENTS = {
    "Active ChangeContract Carrier Closure": 5,
    "Attested Execution Substrate Transition": 1,
    "Bounded Comparative Assurance Gate": 6,
    "ChangeContract And Attestation Admission": 3,
    "ChangeContract Hypotheses And Attested Learning": 8,
    "Exact Work Lane Lifecycle Effects": 7,
    "Exact Tracked Mutation Admission": 10,
    "Selected ChangeContract Aggregate Predicate": 3,
    "Selected ChangeContract Protected-Publication Admission": 6,
}
PRODUCT_VENDOR_TERMS = (
    "PyCharm",
    "Claude",
    "Codex",
    "OpenAI",
    "GPT",
    "IDE",
    "JetBrains",
    "Anthropic",
    "Gemini",
    "Copilot",
    "Cursor",
    "Windsurf",
)
FORBIDDEN_FINAL_CARRIERS = {
    "evolution ledger": r"\bevolution/ledger\.toml\b|\bmodel refinement/ledger\.toml\b|\bmodel refinement (?:ledger|schema|records?)\b|\bpractice-change (?:records?|schema|store)\b",
    "derived program manifest": r"\bderived terminal program manifest\b",
    "comparative command": r"\bethos (?:parity|external comparison)\b|\bexternal[-_ ]comparison command\b",
    "comparative schema or root": r"\b(?:shadow-parity|external comparison)[-_ ](?:schema|root)\b|\bevidence/parity(?:/|\b)",
    "comparative tracked plane": r"\btracked (?:parity|external comparison) evidence\b|\b(?:parity|external comparison) (?:durable )?plane\b",
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@pytest.fixture
def design_tree(tmp_path: Path) -> Path:
    paths = REQUIRED_DESIGN_PROJECTIONS | {CANONICAL_OWNER, "system/axioms.md"}
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def section(text: str, heading: str, level: int = 2) -> str:
    match = re.search(rf"^{'#' * level} {re.escape(heading)}$", text, re.MULTILINE)
    if not match:
        return ""
    following = re.search(rf"^#{{1,{level}}} [^#].+$", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


def heading_blocks(text: str, pattern: str) -> Iterator[tuple[re.Match[str], str, str]]:
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield match, text[match.start() : end], text[match.end() : end]


def requirement_counts(specs: dict[str, str]) -> Counter[str]:
    return Counter(
        heading
        for text in specs.values()
        for heading in re.findall(r"^### Requirement: (.+)$", text, re.MULTILINE)
    )


def scenario_obligations(
    capability: str,
    text: str,
    *,
    allow_duplicate_requirements: bool = False,
) -> list[tuple[str, str, str, tuple[str, ...]]]:
    parsed: list[tuple[str, str, str, tuple[str, ...]]] = []
    seen_requirements: set[str] = set()
    for requirement, _, requirement_body in heading_blocks(text, r"^### Requirement: (.+)$"):
        requirement_heading = requirement.group(1)
        if requirement_heading in seen_requirements and not allow_duplicate_requirements:
            message = f"duplicate requirement heading: {(capability, requirement_heading)}"
            raise AssertionError(message)
        seen_requirements.add(requirement_heading)
        seen_scenarios: set[str] = set()
        for scenario, _, scenario_body in heading_blocks(
            requirement_body, r"^#### Scenario: (.+)$"
        ):
            scenario_heading = scenario.group(1)
            if scenario_heading in seen_scenarios:
                message = (
                    "duplicate scenario heading: "
                    f"{(capability, requirement_heading, scenario_heading)}"
                )
                raise AssertionError(message)
            seen_scenarios.add(scenario_heading)
            obligations = tuple(
                f"{match.group(1)}: {' '.join(match.group(2).split())}"
                for match in re.finditer(
                    r"^- \*\*(GIVEN|WHEN|THEN|AND)\*\*\s*(.*?)"
                    r"(?=^- \*\*(?:GIVEN|WHEN|THEN|AND)\*\*|^#{1,4} |\Z)",
                    scenario_body,
                    re.MULTILINE | re.DOTALL,
                )
            )
            obligation_kinds = {obligation.partition(":")[0] for obligation in obligations}
            assert obligations, (capability, requirement_heading, scenario_heading)
            assert {"WHEN", "THEN"} <= obligation_kinds, (
                capability,
                requirement_heading,
                scenario_heading,
                obligations,
            )
            parsed.append((capability, requirement_heading, scenario_heading, obligations))
    return parsed


def delta_dispositions(
    text: str,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    removed = section(text, "REMOVED Requirements")
    requirement_map: dict[str, str] = {}
    removal_bodies: dict[str, str] = {}
    for match, body, _ in heading_blocks(removed, r"^### Requirement: (.+)$"):
        replacement = re.search(r"^\*\*Replacement\*\*: `?([^`\n]+)`?$", body, re.MULTILINE)
        if replacement:
            requirement_map[match.group(1)] = replacement.group(1).strip()
        removal_bodies[match.group(1)] = body
    scenario_map = {
        old.strip(" `"): new.strip(" `")
        for old, new in re.findall(
            r"^\*\*Scenario replacement\*\*: (.+?) -> (.+?)$", text, re.MULTILINE
        )
    }
    return requirement_map, scenario_map, removal_bodies


def spec_texts(openspec_root: Path) -> dict[str, str]:
    return {
        path.parent.name: path.read_text(encoding="utf-8")
        for path in sorted((openspec_root / "specs").glob("*/spec.md"))
    }


@pytest.fixture(scope="module")
def archived_openspec(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, str], dict[str, str]]:
    root = tmp_path_factory.mktemp("terminal-convergence-archive")
    shutil.copytree(ROOT / "openspec", root / "openspec")
    baseline = spec_texts(root / "openspec")
    executable = shutil.which("openspec")
    assert executable, "owner-native openspec executable is required"
    archive = subprocess.run(
        [executable, "archive", "terminal-convergence", "--yes", "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert archive.returncode == 0, archive.stdout + archive.stderr
    strict = subprocess.run(
        [executable, "validate", "--all", "--strict", "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 0, strict.stdout + strict.stderr
    return baseline, spec_texts(root / "openspec")


def test_review_f1_archive_has_unique_requirements_and_explicit_scenario_migrations(
    archived_openspec: tuple[dict[str, str], dict[str, str]],
) -> None:
    baseline, final = archived_openspec
    final_heading_counts = requirement_counts(final)
    assert [heading for heading, count in final_heading_counts.items() if count > 1] == []

    repository_baseline = baseline["repository-governance"]
    duplicate = "Work Lane Lifecycle Resolution"
    assert (
        len(re.findall(rf"^### Requirement: {duplicate}$", repository_baseline, re.MULTILINE)) == 2
    )
    assert final_heading_counts[duplicate] == 0
    assert final_heading_counts["Exact Work Lane Lifecycle Effects"] == 1

    for capability, baseline_text in baseline.items():
        baseline_inventory = scenario_obligations(
            capability,
            baseline_text,
            allow_duplicate_requirements=capability == "repository-governance",
        )
        final_inventory = scenario_obligations(capability, final[capability])
        delta_path = ROOT / "openspec/changes/terminal-convergence/specs" / capability / "spec.md"
        delta_text = delta_path.read_text(encoding="utf-8") if delta_path.exists() else ""
        requirement_map, scenario_map, _ = delta_dispositions(delta_text)
        delta_inventory = (
            scenario_obligations(capability, delta_text, allow_duplicate_requirements=True)
            if delta_text
            else []
        )

        for _, requirement, scenario, baseline_obligations in baseline_inventory:
            replacement = requirement_map.get(requirement, requirement)
            if replacement == "ChangeContract And Attestation Admission":
                assert any(record[1] == replacement for record in final_inventory)
                continue
            mapped = (
                capability,
                replacement,
                scenario_map.get(scenario, scenario),
            )
            final_matches = [record for record in final_inventory if record[:3] == mapped]
            assert len(final_matches) == 1, (mapped, final_matches)
            final_obligations = final_matches[0][3]
            if final_obligations == baseline_obligations:
                continue
            delta_matches = [record for record in delta_inventory if record[:3] == mapped]
            assert len(delta_matches) == 1, (mapped, delta_matches)
            assert delta_matches[0][3] == final_obligations, mapped

        for replacement in dict.fromkeys(requirement_map.values()):
            if replacement in {
                "Exact Work Lane Lifecycle Effects",
                "ChangeContract And Attestation Admission",
            }:
                continue
            expected = [
                scenario_map.get(scenario, scenario)
                for _, requirement, scenario, _ in baseline_inventory
                if requirement_map.get(requirement) == replacement
            ]
            actual = [
                scenario
                for _, requirement, scenario, _ in final_inventory
                if requirement == replacement
            ]
            assert Counter(actual) == Counter(expected), (capability, replacement)

    baseline_lifecycle = scenario_obligations(
        "repository-governance",
        repository_baseline,
        allow_duplicate_requirements=True,
    )
    final_lifecycle = scenario_obligations("repository-governance", final["repository-governance"])
    expected_lifecycle = [
        scenario_map.get(scenario, scenario)
        for _, requirement, scenario, _ in baseline_lifecycle
        if requirement == duplicate
    ]
    actual_lifecycle = [
        scenario
        for _, requirement, scenario, _ in final_lifecycle
        if requirement == "Exact Work Lane Lifecycle Effects"
    ]
    assert final_heading_counts["Exact Work Lane Lifecycle Effects"] == 1
    assert expected_lifecycle == actual_lifecycle * 2


def test_review_f2_archive_forbids_retired_carriers_and_has_two_persistent_owners(
    archived_openspec: tuple[dict[str, str], dict[str, str]],
) -> None:
    _, final = archived_openspec
    combined = "\n".join(final.values())
    for label, pattern in FORBIDDEN_FINAL_CARRIERS.items():
        assert not re.search(pattern, combined, re.IGNORECASE | re.MULTILINE), label

    normalized = " ".join(final["kernel"].split())
    assert "ChangeContract and Attestation are the only persistent semantic entities" in normalized
    assert "RepositoryFacts is freshly observed" in normalized
    assert "PlanIR is transient" in normalized
    owner_paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", combined)
        if "persistent semantic entit" in paragraph
    ]
    assert owner_paragraphs
    for paragraph in owner_paragraphs:
        assert "ChangeContract" in paragraph
        assert "Attestation" in paragraph
        assert "only persistent semantic entities" in paragraph
        normalized_paragraph = paragraph.lower()
        if "RepositoryFacts" in paragraph:
            assert "fresh" in normalized_paragraph
        if "PlanIR" in paragraph:
            assert "transient" in normalized_paragraph

    repository = {
        record[:3]: record[3]
        for record in scenario_obligations("repository-governance", final["repository-governance"])
    }

    def repository_scenario(requirement: str, scenario: str) -> str:
        return " ".join(repository[("repository-governance", requirement, scenario)])

    routine = repository_scenario(
        "Exact Work Lane Lifecycle Effects", "routine lifecycle remains local"
    )
    assert "ignored local coordination" in routine
    assert "postcondition receipt" in routine
    assert "produces no effect Attestation" in routine

    exceptional = repository_scenario(
        "Exact Work Lane Lifecycle Effects",
        "exceptional state does not widen lifecycle effects",
    )
    for phrase in (
        "no generic cleanup or Resolution transition",
        "observe-only and blocked",
        "holder-bound handoff",
        "future generic recovery effect",
        "selected ChangeContract",
    ):
        assert phrase in exceptional

    cohort = repository_scenario(
        "Cohort-bound full Work Lane convergence",
        "exceptional cohort resolution consumes accepted judgment",
    )
    assert "fresh RepositoryFacts" in cohort
    assert "observe-only and blocked" in cohort
    assert "authorized Lease takeover" in cohort
    assert "never falls back to raw Git deletion" in cohort

    handoff = repository_scenario(
        "Exact Work Lane Lifecycle Effects",
        "exceptional handoff is attested",
    )
    assert "exceptional handoff becomes disputed" in handoff
    assert "routine local handoff" not in handoff
    assert "ignored local postcondition receipt" not in handoff
    assert "selected ChangeContract" in handoff
    assert "judgment Attestation" in handoff
    assert "Chronicle derives" in handoff
    assert "does not authorize" in handoff

    contracts = {
        record[:3]: record[3] for record in scenario_obligations("contracts", final["contracts"])
    }
    handoff_contract = " ".join(
        contracts[("contracts", "Handoff Package Contract", "Handoff package is validated")]
    )
    assert "ChangeContract or Attestation" in handoff_contract
    assert "Chronicle" in handoff_contract
    assert "derived" in handoff_contract
    assert "not directly promoted into truth" in handoff_contract


def test_review_f3_replacements_are_narrow_and_prose_is_not_mechanically_rewritten(
    archived_openspec: tuple[dict[str, str], dict[str, str]],
) -> None:
    _, final = archived_openspec
    final_heading_counts = requirement_counts(final)
    assert final_heading_counts["Terminal Repository Compilation And Evidence"] == 0
    assert final_heading_counts["Capability-preserving Test Floor"] == 0
    assert final_heading_counts["Capability-Preserving Test Floor"] == 1

    repository_inventory = scenario_obligations(
        "repository-governance", final["repository-governance"]
    )
    repository_delta = read(
        "openspec/changes/terminal-convergence/specs/repository-governance/spec.md"
    )
    repository_map, _, _ = delta_dispositions(repository_delta)
    replacements = dict.fromkeys(repository_map.values())
    assert tuple(sorted(replacements)) == tuple(sorted(TERMINAL_REPOSITORY_REPLACEMENTS))
    added_headings = set(
        re.findall(
            r"^### Requirement: (.+)$",
            section(repository_delta, "ADDED Requirements"),
            re.MULTILINE,
        )
    )
    assert set(replacements) <= added_headings
    for replacement, expected_scenario_count in TERMINAL_REPOSITORY_REPLACEMENTS.items():
        assert final_heading_counts[replacement] == 1
        scenario_count = sum(
            requirement == replacement for _, requirement, _, _ in repository_inventory
        )
        assert scenario_count == expected_scenario_count, replacement

    for delta_path in sorted(
        (ROOT / "openspec/changes/terminal-convergence/specs").glob("*/spec.md")
    ):
        requirement_map, _, removals = delta_dispositions(delta_path.read_text(encoding="utf-8"))
        capability = delta_path.parent.name
        capability_headings = Counter(
            requirement
            for _, requirement, _, _ in scenario_obligations(capability, final[capability])
        )
        for requirement, body in removals.items():
            assert "**Reason**:" in body, (capability, requirement)
            assert "**Migration**:" in body, (capability, requirement)
            assert requirement in requirement_map, (capability, requirement)
            assert capability_headings[requirement_map[requirement]] >= 1


def test_review_f4_delta_prose_and_candidate_identity_are_exact() -> None:
    all_deltas = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "openspec/changes/terminal-convergence/specs").glob("*/spec.md"))
    )
    normalized_deltas = " ".join(all_deltas.split())
    adapters = read("openspec/changes/terminal-convergence/specs/adapters/spec.md")
    command_plane = read("openspec/changes/terminal-convergence/specs/command-plane/spec.md")
    normalized_adapters = " ".join(adapters.split())
    normalized_command_plane = " ".join(command_plane.split())

    for phrase in (
        "ETHOS verifier-bounded propositions hosted prevention",
        "bootstrap derived historical projection judgment Attestation",
        "provider-store effect Attestation",
        "PlanIR judgment Attestation is transient",
        "accepted derived historical projection has already bound",
    ):
        assert phrase not in all_deltas
    for pattern in (
        r"\bdoes not verifier\b",
        r"\ba Attestation\b",
        r"\ban model\b",
    ):
        assert not re.search(pattern, all_deltas, re.IGNORECASE)
    assert not re.search(
        r"candidate HEAD[^.\n]*(?:as|is)[^.\n]*effective ChangeContract digest",
        all_deltas,
        re.IGNORECASE,
    )
    assert "exact candidate Git HEAD and selected base ChangeContract digest" in all_deltas
    assert (
        "prewrite, PlanIR, proof, handoff, head advance, and closeout require the selected ChangeContract digest to equal that base digest"
        in normalized_deltas
    )
    assert (
        "carrier discovery or lifecycle observation is requested without a Change selector"
        in normalized_adapters
    )

    adapter_scenarios = scenario_obligations("adapters", adapters)
    lifecycle_review = " ".join(
        obligations
        for _, requirement, scenario, scenario_obligations_ in adapter_scenarios
        if requirement == "Lifecycle Review Covers Active Changes"
        and scenario == "Multiple active changes are reviewed"
        for obligations in scenario_obligations_
    )
    for phrase in (
        "every active Change returned by `openspec list --json`",
        "does not select a ChangeContract",
        "does not participate in material-write coverage",
        "does not authorize a write",
        "multiple active ChangeContracts remain ambiguous until an explicit Change selector",
    ):
        assert phrase in lifecycle_review
    assert "Only non-complete active Changes SHALL participate" not in normalized_adapters
    assert "`ethos plan --changed --json` and `ethos prove --json` SHALL consume" not in (
        normalized_adapters
    )
    intake_scenarios = [
        record for record in adapter_scenarios if record[1] == "Intake Adapter Projection Boundary"
    ]
    assert len(intake_scenarios) == 1
    assert intake_scenarios[0][2] == "Intake provider reports done state"
    intake_obligations = " ".join(intake_scenarios[0][3])
    for phrase in (
        "bounded projection evidence",
        "selected ChangeContract",
        "required Attestations",
        "owner-native OpenSpec lifecycle readiness",
        "executed proof",
    ):
        assert phrase in intake_obligations
    assert (
        "planning or proof is requested without an explicit Change selector"
        in normalized_command_plane
    )
    assert "change_contract_ambiguous" in command_plane
    assert "bind the selected base ChangeContract digest into PlanIR" in normalized_command_plane
    assert "A Codex task is taken over" not in all_deltas
    assert "one agent product is taken over by another agent product" in all_deltas


def test_round2_current_assurance_scenarios_use_attestation_or_execution_substrate_terms() -> None:
    delta = read("openspec/changes/terminal-convergence/specs/repository-governance/spec.md")
    active = "\n".join(
        (
            section(delta, "ADDED Requirements"),
            section(delta, "MODIFIED Requirements"),
        )
    )
    removed = section(delta, "REMOVED Requirements")
    replacements = {
        "Shadow parity records input identity": "Bounded Attestation binds proof inputs",
        "Shadow parity rejects external false negatives": "Attestation records missing blocking gap",
        "parity-relevant Work Lane source makes generic evidence stale": (
            "Changed proof input makes Attestation stale"
        ),
        "evidence recording commit precedes proof and land": (
            "Current Attestation is required before proof and land"
        ),
        "Reference adopter parity is closed": "Attestation establishes generic coverage",
        "Stale root environment does not block current parity": (
            "Checkout-bound execution substrate outranks stale environment"
        ),
        "refresh-base resolves parity projection-only conflicts as stale projection": (
            "refresh-base marks comparative-assurance Attestation stale after projection conflict"
        ),
    }

    for old, new in replacements.items():
        assert f"#### Scenario: {old}" not in active
        assert f"#### Scenario: {new}" in active
        assert delta.count(old) == 1
        assert f"**Scenario replacement**: {old} -> {new}" in removed


def test_review_f5_kernel_model_promotion_links_the_canonical_rule() -> None:
    kernel = read("openspec/changes/terminal-convergence/specs/kernel/spec.md")
    assert (
        "[canonical Model Promotion rule]"
        "(../../../../../docs/governance/product-design-contract.md#model-promotion)" in kernel
    )


def test_design_projection_integrity_is_structural_and_truthful() -> None:
    report = design_integrity_report(ROOT)
    assert report["ok"] is True, report["required_gaps"]
    assert report["semantic_equivalence"] == "not_evaluated"
    assert {
        "docs/plans/terminal-governance-product-design.md",
        "openspec/changes/terminal-convergence/specs/kernel/spec.md",
    } <= set(report["references"])


def test_required_projection_metadata_removal_is_caught(design_tree: Path) -> None:
    relative = "docs/concepts/kernel-model.md"
    path = design_tree / relative
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"\A---\n.*?\n---\n\n", "", text, flags=re.DOTALL), encoding="utf-8")

    report = design_integrity_report(design_tree)

    assert f"design_projection_front_matter_invalid:{relative}" in report["required_gaps"]


def test_active_openspec_change_reference_is_still_audited(design_tree: Path) -> None:
    relative = "openspec/changes/example/specs/kernel/spec.md"
    path = design_tree / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    owner_link = (
        "[canonical Model Promotion rule]"
        "(../../../../../docs/governance/product-design-contract.md#model-promotion)"
    )
    path.write_text(
        f"# Active Change Reference\n\nModel Promotion uses the {owner_link}.\n",
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert relative in report.get("references", {})
    assert f"design_reference_owner_link_missing:{relative}" not in report["required_gaps"]

    path.write_text(
        path.read_text(encoding="utf-8").replace(
            owner_link,
            "docs/governance/product-design-contract.md#model-promotion",
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert f"design_reference_owner_link_missing:{relative}" in report["required_gaps"]


def test_duplicated_root_text_in_axioms_is_caught(design_tree: Path) -> None:
    axioms = design_tree / "system/axioms.md"
    owner_lines = (design_tree / CANONICAL_OWNER).read_text(encoding="utf-8").splitlines()
    verse_line = next(line.removeprefix("> ") for line in owner_lines if line.startswith("> "))
    axioms.write_text(
        f"{axioms.read_text(encoding='utf-8')}\n{verse_line}\n",
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert "design_axioms_duplicates_root_verse" in report["required_gaps"]


def test_axioms_structural_link_and_terms_are_required(design_tree: Path) -> None:
    axioms = design_tree / "system/axioms.md"
    original = axioms.read_text(encoding="utf-8")
    without_link = re.sub(
        r"\[[^\]]+\]\(\.\./docs/governance/product-design-contract\.md#root-constraint\)",
        "Product Design Contract",
        original,
    )
    axioms.write_text(without_link, encoding="utf-8")

    report = design_integrity_report(design_tree)
    assert "design_axioms_root_constraint_link_missing" in report["required_gaps"]

    without_terms = original
    for term in ("ChangeContract", "Attestation", "proposition"):
        without_terms = without_terms.replace(term, "bounded record")
    axioms.write_text(without_terms, encoding="utf-8")

    report = design_integrity_report(design_tree)
    assert {
        "design_axioms_term_missing:ChangeContract",
        "design_axioms_term_missing:Attestation",
        "design_axioms_term_missing:proposition",
    } <= set(report["required_gaps"])


def test_live_cyclopts_tree_has_exact_public_and_hidden_roots() -> None:
    load_command_groups([])
    commands = {
        name: command
        for name, command in app.resolved_commands().items()
        if not name.startswith("-")
    }
    assert {name for name, command in commands.items() if command.show} == PUBLIC_ROOTS
    assert {name for name, command in commands.items() if not command.show} == HIDDEN_ROOTS


def test_canonical_product_docs_are_provider_neutral_and_residue_free() -> None:
    registry = build_docs_registry(ROOT)
    governed = [
        entry["path"]
        for entry in registry
        if entry["state"] in {"canonical", "active"}
        and entry["path"].startswith(
            (
                "docs/governance/",
                "docs/architecture/",
                "docs/evidence/",
                "docs/concepts/",
                "docs/reference/",
                "docs/decisions/accepted/",
            )
        )
    ]
    provider_neutral = REQUIRED_DESIGN_PROJECTIONS | {
        CANONICAL_OWNER,
        "docs/governance/conversation-ledger.md",
        "docs/architecture/agent-projections.md",
        "docs/governance/playbooks-and-skills.md",
        "docs/architecture/runner-and-mutation.md",
    }
    for path in provider_neutral:
        text = read(path)
        for term in PRODUCT_VENDOR_TERMS:
            assert term not in text, (path, term)
    for path in governed:
        text = read(path)
        if not path.startswith("docs/decisions/accepted/"):
            assert "legacy" not in text.lower(), path
        for phrase in (
            "backend selection",
            "shadow comparison",
            "retirement readiness",
            "tracked parity evidence",
            "evidence/parity",
        ):
            assert phrase not in text.lower(), (path, phrase)

    evidence_boundary = "\n".join(
        read(path)
        for path in (
            "docs/governance/config-boundary-model.md",
            "docs/architecture/generated-artifact-topology.md",
            "docs/evidence/README.md",
            "docs/decisions/accepted/DR-0001-generated-artifact-topology-contract.md",
        )
    )
    for phrase in ("evidence/attestations", "Attestations", "immutable historical evidence"):
        assert phrase in evidence_boundary
    assert (
        " ".join(evidence_boundary.split()).count(
            "`claims`, `chronicle`, and `parity` are immutable historical bytes"
        )
        == 1
    )

    removed = section(
        read("openspec/changes/terminal-convergence/specs/repository-governance/spec.md"),
        "REMOVED Requirements",
    )
    assert "### Requirement: External Retirement Readiness" in removed
    assert "**Replacement**: Attested Execution Substrate Transition" in removed


def test_low_level_active_surfaces_do_not_use_philosophy_labels() -> None:
    forbidden = ("system/tao", "tao First", "tao FP", "ETHOS Tao", "道:")
    offenders: list[str] = []
    for base in (ROOT / "src", ROOT / "system", ROOT / ".config", ROOT / ".githooks"):
        for path in base.rglob("*"):
            if not path.is_file() or path == ROOT / "system/axioms.md":
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(term in text for term in forbidden):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_canonical_contract_retains_open_taxonomy_git_and_binding_boundaries() -> None:
    contract = read(CANONICAL_OWNER)
    checks = {
        "Invalid-State Taxonomy": (
            "not a closed ontology",
            "unknown signal remains",
            "model_promotion_required",
        ),
        "Git-native repository substrate": (
            "ETHOS is Git-native",
            "not a generic VCS abstraction",
            "release_root -> accepted_root -> candidate -> work_lane -> proposal_lane",
        ),
        "Binding taxonomy": (
            "product-semantic hard bindings",
            "mandatory governance dependencies",
            "profile or adapter bindings",
        ),
        "Configuration boundaries": (
            "separation of concerns, MECE, SSOT, and DRY",
            ".config/checks/<concern>/",
            "system/tools.toml",
        ),
    }
    for heading, anchors in checks.items():
        body = section(contract, heading, level=2 if heading == "Invalid-State Taxonomy" else 3)
        body = " ".join(body.split())
        for anchor in anchors:
            assert anchor in body, (heading, anchor)


def test_governed_repository_homomorphism_and_first_hour_ux_remain_visible() -> None:
    contract = read(CANONICAL_OWNER)
    for anchor in (
        "Isomorphic Governance",
        "same kernel",
        "profiles and adapters",
        "not product cloning",
    ):
        assert anchor in contract

    for path in ("README.md", "docs/reference/glossary.md"):
        text = read(path)
        assert "Isomorphic Governance" in text
        assert "same kernel" in text
        assert "profiles and adapters" in text
        assert "product-design-contract.md#semantic-kernel" in text

    readme = read("README.md")
    quickstart = read("docs/start/quickstart.md")
    assert "status -> plan -> prove -> land -> publish" in readme
    for root in PUBLIC_ROOTS:
        assert f"ethos {root}" in readme or f"ethos {root}" in quickstart
    for retired in ("orient", "report", "doctor", "audit", "campaign", "parity", "fleet"):
        assert f"ethos {retired}" not in quickstart


def test_loss_bounded_successor_continuity_remains_in_archived_spec(
    archived_openspec: tuple[dict[str, str], dict[str, str]],
) -> None:
    _, final = archived_openspec
    heading = "Remote reconciliation continuation preserves historical carrier boundaries"
    inventory = scenario_obligations("repository-governance", final["repository-governance"])
    matching = " ".join(
        obligation
        for _, requirement, _scenario, obligations in inventory
        if requirement == heading
        for obligation in obligations
    )
    assert matching
    for anchor in (
        "effective ChangeContract digest",
        "prior Attestations",
        "current RepositoryFacts",
        "no-reconstruction boundary",
    ):
        assert anchor in matching


def test_terminal_architecture_plan_links_model_promotion_owner() -> None:
    plan = read("docs/plans/terminal-governance-product-design.md")
    body = section(plan, "Model Promotion", level=3)
    assert "product-design-contract.md#model-promotion" in body

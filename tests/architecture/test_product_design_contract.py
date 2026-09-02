"""Architecture boundaries not already owned by declarative repository gates."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ethos.contracts.semantic import Commitment
from ethos.repository.audit import REQUIRED_DOCS
from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.registry.docs.registry import front_matter

ROOT = Path(__file__).resolve().parents[2]
DESIGN_DOCUMENTS = (
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/governance/product-design-contract.md",
    "docs/reference/command-plane.md",
    "docs/reference/glossary.md",
    "system/axioms.md",
)

AGENT_ENTRY_LINKS = (
    "docs/governance/product-design-contract.md",
    "rules/README.md",
    ".agents/skills/activation.toml",
    "openspec/",
    "docs/README.md",
)


def _copy_design_documents(target: Path) -> tuple[str, ...]:
    for relative in DESIGN_DOCUMENTS:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return DESIGN_DOCUMENTS


def _active_change_carriers() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (ROOT / "openspec/changes").iterdir()
        if path.is_dir() and path.name != "archive"
    )


def test_design_integrity_uses_supplied_tracked_documents_as_authority(
    tmp_path: Path,
) -> None:
    tracked = _copy_design_documents(tmp_path)
    rogue = tmp_path / "docs/rogue.md"
    rogue.write_text(
        "[Owner](governance/product-design-contract.md#semantic-kernel)\n",
        encoding="utf-8",
    )

    report = design_integrity_report(tmp_path, tracked_documents=tracked)

    assert report["verdict"] == "pass", report["required_gaps"]
    assert "docs/rogue.md" not in report["references"]


def test_current_change_uses_only_the_official_openspec_artifact_shape() -> None:
    changes = _active_change_carriers()

    assert len(changes) <= 1
    for change in changes:
        artifacts = {
            path.relative_to(change).as_posix() for path in change.rglob("*") if path.is_file()
        }
        unsupported = {
            artifact
            for artifact in artifacts
            if artifact not in {".openspec.yaml", "proposal.md", "design.md", "tasks.md"}
            and not (artifact.startswith("specs/") and artifact.endswith(".md"))
        }
        assert not unsupported


def test_agent_entrypoint_is_thin_and_continuation_driven() -> None:
    entrypoint = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(entrypoint.split())

    assert all(target in entrypoint for target in AGENT_ENTRY_LINKS)
    assert "ethos status --json" in entrypoint
    assert "current result" in normalized
    assert "OpenSpec" in entrypoint
    assert "Commitment is transient compilation" in entrypoint
    assert entrypoint.count("ethos status --json") == 1


def test_documentation_has_one_entrypoint_without_decision_index_shells() -> None:
    """ETHOS keeps one docs root and no marker-only Decision Record index."""
    assert (ROOT / "docs/README.md").is_file()
    assert not (ROOT / "docs/index.md").exists()
    assert not (ROOT / "docs/decisions/README.md").exists()
    assert not (ROOT / "docs/decisions/index.md").exists()


def test_decision_records_are_audited_product_surfaces() -> None:
    """Every retained Decision Record participates in product-boundary audit."""
    audited = {path.relative_to(ROOT).as_posix() for path in product_surface_files(ROOT)}
    decision_paths = sorted((ROOT / "docs/decisions").glob("*.md"))
    decisions = {path.relative_to(ROOT).as_posix() for path in decision_paths}
    documentation_root = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    assert decisions
    assert decisions <= audited
    for path in decision_paths:
        assert f"(decisions/{path.name})" in documentation_root


def test_decision_records_preserve_complete_cross_change_rationale() -> None:
    """A retained decision explains the choice instead of duplicating current policy."""
    required_sections = (
        "## Context",
        "## Decision",
        "## Consequences",
        "## Rejected Alternatives",
        "## Evidence",
        "## Revisit And Retirement",
    )

    for path in sorted((ROOT / "docs/decisions").glob("*.md")):
        metadata = front_matter(path)
        text = path.read_text(encoding="utf-8")

        assert metadata["role"] == "decision", path
        assert metadata["state"] == "canonical", path
        assert "current_owner:" in metadata["relations"], path
        assert all(section in text for section in required_sections), path


def test_product_meaning_and_terminal_route_are_both_required_docs() -> None:
    """Repository audit keeps the two canonical semantic owners present."""
    assert "docs/governance/product-design-contract.md" in REQUIRED_DOCS
    assert "docs/plans/terminal-governance-product-design.md" in REQUIRED_DOCS


def test_repository_docs_taxonomy_has_no_feedback_ledger_role() -> None:
    """Conversation recovery cannot introduce a parallel durable ledger."""
    assert "ledger" not in allowed_roles(ROOT)


def test_semantic_capabilities_keep_their_existing_authority_boundaries() -> None:
    """Topology convergence does not recreate or widen semantic carriers.

    The archived lineage Change is evidence of historical design, not a current
    runtime owner.  The current kernel and official OpenSpec tree remain the
    only sources available to current planning.
    """
    assert tuple(Commitment.model_fields) == ("schema_version", "id", "acceptance")

    lineage_spec = ROOT / "openspec/changes/archive/2026-08-22-change-lineage-dag"
    assert (lineage_spec / "specs/contracts/spec.md").is_file()
    assert (lineage_spec / "specs/repository-governance/spec.md").is_file()

    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert not any(
        path.startswith("src/ethos/adapters/openspec/change_lineage/") for path in tracked
    )
    assert not any(path.startswith("src/ethos/contracts/change_lineage/") for path in tracked)
    assert not any(
        path.endswith("commitment.toml")
        for path in tracked
        if path.startswith("openspec/changes/semantic-topology-convergence/")
    )

    active_paths = {
        path.relative_to(ROOT / "openspec/changes/semantic-topology-convergence").as_posix()
        for path in (ROOT / "openspec/changes/semantic-topology-convergence").rglob("*")
        if path.is_file()
    }
    assert active_paths <= {
        ".openspec.yaml",
        "proposal.md",
        "design.md",
        "tasks.md",
    } | {path for path in active_paths if path.startswith("specs/") and path.endswith(".md")}

    registry = build_docs_registry(ROOT)
    assert not any(entry["path"].startswith("openspec/changes/archive/") for entry in registry)
    assert not any(
        path.startswith("src/ethos/")
        and any(token in path for token in ("lineage", "hypothesis", "experiment"))
        for path in tracked
    )


def test_canonical_lane_retirement_and_lease_requirements_match_the_minimal_model() -> None:
    """Canonical requirements keep Git facts outside the four-field Lease."""
    specification = (ROOT / "openspec/specs/repository-governance/spec.md").read_text(
        encoding="utf-8"
    )
    command_plane = (ROOT / "openspec/specs/command-plane/spec.md").read_text(encoding="utf-8")

    assert "### Requirement: Linked Work Lane retirement has one exact effect" in specification
    assert "### Requirement: Linked Work Lane retirement has one generation-bound effect" not in (
        specification
    )

    lease_requirement = specification.split(
        "### Requirement: Lease generation identity is complete across boundaries", 1
    )[1].split("### Requirement:", 1)[0]
    for field in ("lane ref", "holder ref", "generation", "expiry"):
        assert field in lease_requirement
    for retired_field in (
        "lease ID",
        "epoch",
        "expected head",
        "raw payload SHA-256",
        "incarnation",
        "Chronicle",
    ):
        assert retired_field not in lease_requirement

    write_requirement = command_plane.split(
        "### Requirement: Work Lane writes are exact lease-generation bound", 1
    )[1].split("### Requirement:", 1)[0]
    for field in ("lane ref", "holder ref", "generation", "expiry"):
        assert field in write_requirement
    for retired_field in ("lease ID", "epoch", "expected HEAD"):
        assert retired_field not in write_requirement
    assert "Change and Lease expected HEAD" not in command_plane

    for retired_phrase in (
        "lease's `expected_head`",
        "lease/incarnation",
        "lease ID/epoch",
        "lease epoch as a string or boolean",
    ):
        assert retired_phrase not in specification

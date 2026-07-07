from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generated_artifact_topology_docs_bind_contract_and_rollback() -> None:
    architecture = (ROOT / "docs/architecture/generated-artifact-topology.md").read_text(
        encoding="utf-8"
    )
    decision = (
        ROOT / "docs/decisions/accepted/DR-0001-generated-artifact-topology-contract.md"
    ).read_text(encoding="utf-8")
    command_plane = (ROOT / "docs/reference/command-plane.md").read_text(encoding="utf-8")

    for text in (architecture, decision):
        assert ".config/ethos/" in text
        assert "build/ethos/" in text
        assert "build/evidence/" in text
        assert "docs/evidence/" in text
        assert "adopter" in text.lower()
        assert "rollback" in text.lower()

    assert "ethos quality generated-artifacts --json" in architecture
    assert "ethos quality generated-artifacts" in command_plane
    assert "Generated Artifact Topology Contract" in command_plane


def test_generated_artifact_topology_is_in_docs_index() -> None:
    index = (ROOT / "docs/index.md").read_text(encoding="utf-8")

    assert "Generated Artifact Topology" in index
    assert "architecture/generated-artifact-topology.md" in index
    assert "Decision Records" in index
    assert "decisions/README.md" in index


def test_decision_records_surface_is_highly_isomorphic_with_governed_repositories() -> None:
    required = (
        "docs/decisions/README.md",
        "docs/decisions/decision-index.md",
        "docs/decisions/decision-dependency-map.md",
        "docs/decisions/decision-code-links.md",
        "docs/decisions/accepted/README.md",
        "docs/decisions/superseded/README.md",
        "docs/decisions/templates/README.md",
        "docs/decisions/templates/decision-record.md",
        "docs/decisions/accepted/DR-0001-generated-artifact-topology-contract.md",
    )

    for rel in required:
        assert (ROOT / rel).exists(), rel

    decision_readme = (ROOT / "docs/decisions/README.md").read_text(encoding="utf-8")
    assert "durable rulings" in decision_readme
    assert "Decision Records are not a separate truth lane" in decision_readme
    assert "accepted/DR-0001-generated-artifact-topology-contract.md" in (
        ROOT / "docs/decisions/decision-index.md"
    ).read_text(encoding="utf-8")

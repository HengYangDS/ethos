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
        assert "build/runtime/tool-cache/" in text
        assert "build/runtime/work/" in text
        assert "build/ethos/" in text
        assert "build/evidence/" in text
        assert "build/artifacts/" in text
        assert "docs/evidence/" in text
        assert "adopter" in text.lower()
        assert "rollback" in text.lower()

    docs_topology = (ROOT / "docs/architecture/docs-topology.md").read_text(encoding="utf-8")

    assert "ethos quality generated-artifacts --json" in architecture
    assert "## Promotion path" in architecture
    assert "runtime command -> build/evidence/<concern>/" in architecture
    assert "reviewed summary with command, scope, verifier, digest, HEAD" in architecture
    assert ".config/ethos/generated-artifacts.toml" in architecture
    assert "fleet retirement-readiness" in architecture
    assert "ethos quality generated-artifacts --root <repo> --json" in architecture
    assert "ethos quality generated-artifacts" in command_plane
    assert "build/runtime/tool-cache/" in command_plane
    assert "runtime caches and local artifacts are regenerated, not promoted" in command_plane
    assert "Generated Artifact Topology Contract" in command_plane
    build_command = (
        "uv build --all-packages --out-dir build/artifacts/python --clear --no-create-gitignore"
    )
    for path in (
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs/governance/capability-parity-ledger.md",
        ROOT / "docs/governance/release-governance.md",
    ):
        assert build_command in path.read_text(encoding="utf-8")
    assert "ethos quality docs-topology --json" in docs_topology
    assert "Minimal Semantic Documentation Topology Contract" in command_plane


def test_evidence_docs_bind_machine_to_curated_promotion_path() -> None:
    root_evidence = (ROOT / "evidence/README.md").read_text(encoding="utf-8")
    docs_evidence = (ROOT / "docs/evidence/README.md").read_text(encoding="utf-8")

    assert "## Promotion Path" in root_evidence
    for required in (
        "`build/evidence/`",
        "`build/ethos/`",
        "command, scope,\nverifier, digest, HEAD",
        "`docs/evidence/`",
        "`evidence/chronicle/`",
        "`evidence/parity/`",
    ):
        assert required in root_evidence
    assert "Runtime caches" in root_evidence
    assert "outside the promotion path" in root_evidence
    assert "Machine output belongs under generated homes" in docs_evidence


def test_generated_artifact_topology_is_in_docs_index() -> None:
    index = (ROOT / "docs/index.md").read_text(encoding="utf-8")

    assert "Generated Artifact Topology" in index
    assert "architecture/generated-artifact-topology.md" in index
    assert "Decision Records" in index
    assert "decisions/README.md" in index


def test_decision_records_surface_is_shared_across_governed_repositories() -> None:
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


def test_documentation_topology_docs_bind_common_kernel() -> None:
    topology = (ROOT / "docs/architecture/docs-topology.md").read_text(encoding="utf-8")
    decision = (
        ROOT / "docs/decisions/accepted/DR-0004-native-documentation-topology-contract.md"
    ).read_text(encoding="utf-8")
    superseded = (
        ROOT / "docs/decisions/superseded/DR-0002-documentation-topology-isomorphism-contract.md"
    ).read_text(encoding="utf-8")

    for text in (topology, decision):
        assert "docs/decisions" in text
        assert "docs/evidence" in text
        assert "docs/history" in text
        assert "docs/reference" in text
        assert "docs/current" in text
        assert "docs/future" in text
        assert "forbid" in text.lower() or "forbidden" in text.lower()
        assert "ethos quality docs-topology --json" in text

    for optional_root in (
        "docs/architecture",
        "docs/concepts",
        "docs/governance",
        "docs/plans",
        "docs/research",
        "docs/start",
    ):
        assert optional_root in decision
        required_section = topology.split("Required paths:", 1)[1].split("Forbidden roots:", 1)[0]
        assert optional_root not in required_section

    generated_topology = (ROOT / "docs/architecture/generated-artifact-topology.md").read_text(
        encoding="utf-8"
    )
    for semantic_root in ("docs/concepts/", "docs/research/"):
        assert semantic_root in generated_topology
    assert "not generated-output homes" in generated_topology

    assert "Status: superseded" in superseded
    assert "DR-0004" in (ROOT / "docs/decisions/decision-index.md").read_text(encoding="utf-8")
    assert "DR-0004" in (ROOT / "docs/decisions/decision-code-links.md").read_text(encoding="utf-8")

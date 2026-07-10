from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_action_graph_does_not_reintroduce_custom_dag_traversal() -> None:
    source = (ROOT / "packages/ethos-core/src/ethos_core/action_graph/core.py").read_text(
        encoding="utf-8"
    )

    forbidden_tokens = (
        "visiting",
        "visited",
        "remaining =",
        "while remaining",
        "ready =",
        "def visit(",
    )
    for token in forbidden_tokens:
        assert token not in source
    assert "GraphKernel" in source


def test_shared_graph_kernel_uses_standard_graphlib() -> None:
    source = (ROOT / "packages/ethos-core/src/ethos_core/graph/core.py").read_text(encoding="utf-8")

    assert "from graphlib import" in source
    assert "TopologicalSorter" in source


def test_workflow_runtime_projection_uses_shared_graph_kernel() -> None:
    source = (ROOT / "packages/ethos-core/src/ethos_core/contracts/workflow.py").read_text(
        encoding="utf-8"
    )

    assert "GraphKernel" in source
    assert "GraphNode" in source
    assert "TopologicalSorter" not in source
    forbidden_tokens = ("visiting", "visited", "while remaining", "def visit(")
    for token in forbidden_tokens:
        assert token not in source


def test_generated_artifact_topology_policy_is_declaration_first() -> None:
    declaration = ROOT / "system/policies/generated-artifact-topology.toml"
    package_resource = (
        ROOT / "packages/ethos-core/src/ethos_core/data/generated_artifact_topology.toml"
    )
    source = (
        ROOT / "packages/ethos-core/src/ethos_core/contracts/artifacts/topology.py"
    ).read_text(encoding="utf-8")

    assert declaration.exists()
    assert package_resource.exists()
    assert package_resource.read_text(encoding="utf-8") == declaration.read_text(encoding="utf-8")
    assert "GeneratedArtifactTopologyDeclaration" in source
    assert "system/policies/generated-artifact-topology.toml" in source
    assert "data/generated_artifact_topology.toml" in source
    assert "_ALLOWED_PREFIXES" not in source
    assert "_DENIED_ROOT_CACHE_PREFIXES" not in source
    assert "build/runtime/tool-cache/" not in source


def test_evidence_layout_policy_is_declaration_first() -> None:
    declaration = ROOT / "system/policies/evidence-layout.toml"
    package_resource = ROOT / "packages/ethos-core/src/ethos_core/data/evidence_layout.toml"
    source = (ROOT / "packages/ethos-core/src/ethos_core/contracts/evidence/layout.py").read_text(
        encoding="utf-8"
    )
    runtime = (ROOT / "packages/ethos/src/ethos/repository/evidence/topology.py").read_text(
        encoding="utf-8"
    )

    assert declaration.exists()
    assert package_resource.exists()
    assert package_resource.read_text(encoding="utf-8") == declaration.read_text(encoding="utf-8")
    assert "EvidenceLayoutDeclaration" in source
    assert "system/policies/evidence-layout.toml" in source
    assert "data/evidence_layout.toml" in source
    assert "_ALLOWED_ROOT_DIRS" not in runtime
    assert "_CURATED_PROFILE_ALLOWED_ROOT_FILES" not in runtime
    assert 'allowed_root_dirs = ["claims", "chronicle", "parity"]' in declaration.read_text(
        encoding="utf-8"
    )


def test_gate_registry_is_declaration_first() -> None:
    declaration = ROOT / "system/gates.toml"
    package_resource = ROOT / "packages/ethos-core/src/ethos_core/data/gates.toml"
    contract = (ROOT / "packages/ethos-core/src/ethos_core/contracts/gates.py").read_text(
        encoding="utf-8"
    )
    runtime = (ROOT / "packages/ethos/src/ethos/repository/policy/gates.py").read_text(
        encoding="utf-8"
    )
    quality = (ROOT / "packages/ethos-core/src/ethos_core/quality/gates.py").read_text(
        encoding="utf-8"
    )

    assert declaration.exists()
    assert package_resource.exists()
    assert package_resource.read_text(encoding="utf-8") == declaration.read_text(encoding="utf-8")
    assert "GateRegistryDeclaration" in contract
    assert "system/gates.toml" in contract
    assert "data/gates.toml" in contract
    assert '"repository-audit": Gate(' not in runtime
    assert "PRODUCT_DEFAULT_GATE_IDS = (" not in runtime
    assert "QualityGateDescriptor(" not in quality


def test_quality_command_registry_is_declaration_first() -> None:
    declaration = ROOT / "system/commands.toml"
    package_resource = ROOT / "packages/ethos-core/src/ethos_core/data/commands.toml"
    contract = (ROOT / "packages/ethos-core/src/ethos_core/contracts/commands.py").read_text(
        encoding="utf-8"
    )
    registry = (ROOT / "packages/ethos/src/ethos/surface/cli/quality/registry.py").read_text(
        encoding="utf-8"
    )
    handler_paths = (
        "packages/ethos/src/ethos/surface/cli/quality/core.py",
        "packages/ethos/src/ethos/surface/cli/quality/cutover/core.py",
        "packages/ethos/src/ethos/surface/cli/boundary/product.py",
        "packages/ethos/src/ethos/surface/cli/boundary/readiness.py",
    )

    assert declaration.exists()
    assert package_resource.exists()
    assert package_resource.read_bytes() == declaration.read_bytes()
    assert "CommandRegistryDeclaration" in contract
    assert "system/commands.toml" in contract
    assert "data/commands.toml" in contract
    assert ".command(command.import_path" in registry
    for relative in handler_paths:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "@quality_app.command" not in source
        assert "from ethos.surface.cli._base import quality_app" not in source

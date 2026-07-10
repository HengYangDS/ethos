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

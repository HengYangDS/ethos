from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE = ROOT / "packages/ethos-core/src/ethos_core"
WHEEL_PROJECTIONS = (
    ("system/commands.toml", "commands.toml"),
    ("system/gates.toml", "gates.toml"),
    ("system/invalid_states.toml", "invalid_states.toml"),
    ("system/workflows.toml", "workflows.toml"),
    ("system/policies/evidence-layout.toml", "evidence_layout.toml"),
    (
        "system/policies/generated-artifact-topology.toml",
        "generated_artifact_topology.toml",
    ),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_action_graph_does_not_reintroduce_custom_dag_traversal() -> None:
    source = _read("packages/ethos-core/src/ethos_core/action_graph/core.py")
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
    source = _read("packages/ethos-core/src/ethos_core/graph/core.py")

    assert "from graphlib import" in source
    assert "TopologicalSorter" in source


def test_workflow_runtime_projection_uses_shared_graph_kernel() -> None:
    source = _read("packages/ethos-core/src/ethos_core/contracts/workflow.py")

    assert "GraphKernel" in source
    assert "GraphNode" in source
    assert "TopologicalSorter" not in source
    for token in ("visiting", "visited", "while remaining", "def visit("):
        assert token not in source


def test_wheel_resources_are_build_projections() -> None:
    package_config = _read("packages/ethos-core/pyproject.toml")

    for canonical, resource in WHEEL_PROJECTIONS:
        assert (ROOT / canonical).is_file()
        assert not (CORE_SOURCE / "data" / resource).exists()
        assert f'"../../{canonical}" = "ethos_core/data/{resource}"' in package_config


def test_generated_artifact_topology_policy_is_declaration_first() -> None:
    declaration = ROOT / "system/policies/generated-artifact-topology.toml"
    source = _read("packages/ethos-core/src/ethos_core/contracts/artifacts/topology.py")

    assert declaration.exists()
    for token in (
        "GeneratedArtifactTopologyDeclaration",
        "TopologyCelRule",
        "evaluate_cel_predicate",
        "celpy.Environment",
        "system/policies/generated-artifact-topology.toml",
        "data/generated_artifact_topology.toml",
    ):
        assert token in source
    for token in (
        "_ALLOWED_PREFIXES",
        "_DENIED_ROOT_CACHE_PREFIXES",
        "build/runtime/tool-cache/",
        "_legacy_generated_policy",
        "_generated_denial_policy",
    ):
        assert token not in source


def test_evidence_layout_policy_is_declaration_first() -> None:
    declaration = ROOT / "system/policies/evidence-layout.toml"
    source = _read("packages/ethos-core/src/ethos_core/contracts/evidence/layout.py")
    runtime = _read("packages/ethos/src/ethos/repository/evidence/topology.py")

    assert declaration.exists()
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
    contract = _read("packages/ethos-core/src/ethos_core/contracts/gates.py")
    runtime = _read("packages/ethos/src/ethos/repository/policy/gates.py")
    quality = _read("packages/ethos-core/src/ethos_core/quality/gates.py")

    assert declaration.exists()
    assert "GateRegistryDeclaration" in contract
    assert "system/gates.toml" in contract
    assert "data/gates.toml" in contract
    assert '"repository-audit": Gate(' not in runtime
    assert "PRODUCT_DEFAULT_GATE_IDS = (" not in runtime
    assert "QualityGateDescriptor(" not in quality


def test_quality_command_registry_is_declaration_first() -> None:
    declaration = ROOT / "system/commands.toml"
    contract = _read("packages/ethos-core/src/ethos_core/contracts/commands.py")
    registry = _read("packages/ethos/src/ethos/surface/cli/quality/registry.py")
    handler_paths = (
        "packages/ethos/src/ethos/surface/cli/quality/core.py",
        "packages/ethos/src/ethos/surface/cli/quality/cutover/core.py",
        "packages/ethos/src/ethos/surface/cli/boundary/product.py",
        "packages/ethos/src/ethos/surface/cli/boundary/readiness.py",
    )

    assert declaration.exists()
    assert "CommandRegistryDeclaration" in contract
    assert "system/commands.toml" in contract
    assert "data/commands.toml" in contract
    assert ".command(command.import_path" in registry
    for relative in handler_paths:
        source = _read(relative)
        assert "@quality_app.command" not in source
        assert "from ethos.surface.cli._base import quality_app" not in source

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.gates import gate_graph
from ethos.repository.policy.gates import gate_registry

if TYPE_CHECKING:
    from pathlib import Path


def test_gate_registry_has_real_default_gates() -> None:
    registry = gate_registry()

    assert {
        "repository-audit",
        "claims",
        "docs-registry",
        "docs-topology",
        "schemas",
        "playbooks-v2",
    } <= set(registry)
    assert registry["repository-audit"].command[-4:] == ("audit", "--mode", "shape", "--json")
    assert registry["playbooks-v2"].command[-3:] == (
        "--mode",
        "v2-strict",
        "--json",
    )
    assert {
        "unit-architecture",
        "ruff",
        "build",
        "python-types",
        "docstrings",
        "module-layout",
        "product-boundary",
    } <= set(registry)
    assert registry["ruff"].command == ("tools/ci/scripts/run-python-lint.sh",)
    assert registry["ruff"].dimensions == ("lint", "format", "ratchet")
    assert registry["python-types"].command == ("ethos", "quality", "types", "--json")
    assert registry["docstrings"].command == ("tools/ci/scripts/run-docstring-coverage.sh",)
    assert registry["module-layout"].command == ("tools/ci/scripts/run-module-layout.sh",)
    assert registry["module-layout"].execution_mode == "adapter"
    assert registry["product-boundary"].command == ("tools/ci/scripts/run-product-boundary.sh",)
    assert registry["product-boundary"].execution_mode == "adapter"
    assert registry["python-types"].execution_mode == "inprocess"


def test_gate_registry_classifies_product_toolchain_profile() -> None:
    registry = gate_registry()

    for gate_id in (
        "repository-audit",
        "claims",
        "docs-registry",
        "docs-topology",
        "schemas",
        "playbooks-v2",
    ):
        assert registry[gate_id].profile == "product"
        assert registry[gate_id].toolchain == "ethos"

    for gate_id in (
        "unit-architecture",
        "ruff",
        "build",
        "python-types",
        "docstrings",
        "module-layout",
    ):
        assert registry[gate_id].profile == "product-toolchain"
        assert registry[gate_id].toolchain == "uv-python"

    assert registry["product-boundary"].profile == "product"
    assert registry["product-boundary"].toolchain == "ethos"


def test_gate_graph_can_select_requested_gates() -> None:
    graph = gate_graph(("repository-audit", "claims"))

    assert [node.id for node in graph.nodes] == ["repository-audit", "claims"]
    assert graph.validate().ok is True


def test_default_gate_graph_includes_ci_owner_quality_floor() -> None:
    graph = gate_graph()
    node_ids = [node.id for node in graph.nodes]

    assert node_ids == [
        "repository-audit",
        "claims",
        "evidence-freshness",
        "docs-registry",
        "docs-topology",
        "schemas",
        "playbooks-v2",
        "generated-artifacts",
        "product-boundary",
        "unit-architecture",
        "ruff",
        "python-types",
        "docstrings",
        "module-layout",
        "python-size",
        "toml-config",
        "yaml-config",
        "shell-lint",
        "format-policy",
    ]
    nodes = {node.id: node for node in graph.nodes}
    assert nodes["evidence-freshness"].to_dict()["command"] == [
        "ethos",
        "quality",
        "evidence-freshness",
        "--json",
    ]
    assert nodes["ruff"].to_dict()["command"] == ["tools/ci/scripts/run-python-lint.sh"]
    assert nodes["module-layout"].to_dict()["command"] == ["tools/ci/scripts/run-module-layout.sh"]
    assert nodes["product-boundary"].to_dict()["command"] == [
        "tools/ci/scripts/run-product-boundary.sh"
    ]
    assert nodes["python-size"].to_dict()["command"] == [
        "ethos",
        "quality",
        "code-size",
        "--json",
    ]
    assert nodes["toml-config"].to_dict()["command"] == ["tools/ci/scripts/run-config-lint.sh"]
    assert nodes["shell-lint"].to_dict()["command"] == ["tools/ci/scripts/run-shell-lint.sh"]


def test_adopter_profile_gate_graph_uses_profile_safe_default_floor(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """schema_version = 1
profile_id = \"sample-adopter\"
profile_version = \"1\"
ethos_contract_version = \"1\"

[repository]
kind = \"software\"
root_subject = \"sample\"
""",
        encoding="utf-8",
    )

    graph = gate_graph(root=tmp_path)
    node_ids = [node.id for node in graph.nodes]

    assert node_ids == [
        "repository-audit",
        "claims",
        "evidence-freshness",
        "docs-topology",
        "schemas",
        "playbooks-v2",
        "generated-artifacts",
        "format-policy",
        "asset-determinism",
        "schema-contracts",
        "proof-policy",
    ]
    commands = [node.to_dict()["command"] for node in graph.nodes]
    assert ["tools/ci/scripts/run-python-lint.sh"] not in commands
    assert ["tools/ci/scripts/run-python-tests.sh"] not in commands
    assert ["tools/ci/scripts/run-docstring-coverage.sh"] not in commands
    assert ["tools/ci/scripts/run-module-layout.sh"] not in commands


def test_full_gate_graph_includes_build_after_tests_and_lint() -> None:
    graph = gate_graph(full=True)
    nodes = {node.id: node for node in graph.nodes}

    assert "build" in nodes
    assert "docstrings" in nodes
    assert nodes["build"].depends_on == ("unit-architecture", "ruff")
    assert nodes["ruff"].to_dict()["command"] == ["tools/ci/scripts/run-python-lint.sh"]
    assert nodes["build"].to_dict()["command"] == ["uv", "build", "--all-packages"]
    assert {"markdown-structure", "format-policy", "asset-determinism"} <= nodes.keys()
    assert {"schema-contracts", "proof-policy"} <= nodes.keys()
    assert nodes["python-types"].to_dict()["command"] == ["ethos", "quality", "types", "--json"]
    assert nodes["module-layout"].to_dict()["command"] == ["tools/ci/scripts/run-module-layout.sh"]
    assert nodes["product-boundary"].to_dict()["command"] == [
        "tools/ci/scripts/run-product-boundary.sh"
    ]


def test_gate_registry_includes_product_boundary_gate() -> None:
    gate = gate_registry()["product-boundary"]

    assert gate.command == ("tools/ci/scripts/run-product-boundary.sh",)
    assert gate.trust_bearing is True
    assert "product-boundary" in gate.dimensions
    assert "identity" in gate.dimensions
    assert "distribution-boundary" in gate.dimensions
    assert "product-boundary" in [node.id for node in gate_graph().nodes]


def test_gate_registry_includes_generated_artifacts_gate() -> None:
    gate = gate_registry()["generated-artifacts"]

    assert gate.command[2:] == ("ethos.cli", "quality", "generated-artifacts", "--json")
    assert gate.trust_bearing is True
    assert "path-topology" in gate.dimensions
    assert "generated-artifacts" in gate.asset_classes
    assert "generated-artifacts" in [node.id for node in gate_graph().nodes]


def test_gate_registry_includes_docs_topology_gate() -> None:
    gate = gate_registry()["docs-topology"]

    assert gate.command[2:] == ("ethos.cli", "quality", "docs-topology", "--json")
    assert gate.trust_bearing is True
    assert "adopter-isomorphism" in gate.dimensions
    assert "decision-records" in gate.asset_classes
    assert "docs-topology" in [node.id for node in gate_graph().nodes]

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.repository.profile import load_repository_profile
from ethos_core.action_graph import ActionGraph
from ethos_core.action_graph import ActionNode
from ethos_core.quality.gates import quality_gate_registry

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class Gate:
    id: str
    kind: str
    command: tuple[str, ...]
    policy: str = "required"
    profile: str = "product"
    toolchain: str = "ethos"
    depends_on: tuple[str, ...] = ()
    asset_classes: tuple[str, ...] = ()
    dimensions: tuple[str, ...] = ()
    execution_mode: str = "inprocess"
    evidence_class: str = "contract"
    trust_bearing: bool = False
    tool_adapter: str = "ethos"
    writes_files: bool = False
    network_policy: str = "offline"
    version_source: str = "product"

    def to_node(self) -> ActionNode:
        return ActionNode(
            id=self.id,
            kind=self.kind,
            command=self.command,
            policy=self.policy,
            tool="ethos",
            depends_on=self.depends_on,
            metadata={
                "asset_classes": list(self.asset_classes),
                "dimensions": list(self.dimensions),
                "execution_mode": self.execution_mode,
                "evidence_class": self.evidence_class,
                "trust_bearing": self.trust_bearing,
                "tool_adapter": self.tool_adapter,
                "writes_files": self.writes_files,
                "network_policy": self.network_policy,
                "version_source": self.version_source,
            },
        )


def gate_registry() -> dict[str, Gate]:
    python = sys.executable
    registry = {
        "repository-audit": Gate(
            id="repository-audit",
            kind="governance",
            command=(python, "-m", "ethos.cli", "audit", "--mode", "shape", "--json"),
            asset_classes=("evidence",),
            dimensions=("governance", "determinism"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-repository-audit",
        ),
        "claims": Gate(
            id="claims",
            kind="governance",
            command=(python, "-m", "ethos.cli", "quality", "claims", "--json"),
            asset_classes=("evidence",),
            dimensions=("digest", "freshness", "provenance"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-claims",
        ),
        "docs-registry": Gate(
            id="docs-registry",
            kind="docs",
            command=(python, "-m", "ethos.cli", "quality", "docs-registry", "--json"),
            asset_classes=("markdown-docs",),
            dimensions=("front-matter", "command-examples", "links"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-docs-registry",
        ),
        "generated-artifacts": Gate(
            id="generated-artifacts",
            kind="governance",
            command=(python, "-m", "ethos.cli", "quality", "generated-artifacts", "--json"),
            asset_classes=("generated-artifacts", "evidence", "local-state"),
            dimensions=("path-topology", "drift", "rollback"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-generated-artifacts",
        ),
        "schemas": Gate(
            id="schemas",
            kind="schema",
            command=(python, "-m", "ethos.cli", "quality", "schemas", "--json"),
            asset_classes=("json-contracts",),
            dimensions=("schema", "stable-ordering"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="jsonschema",
        ),
        "playbooks-v2": Gate(
            id="playbooks-v2",
            kind="governance",
            command=(
                python,
                "-m",
                "ethos.cli",
                "playbooks",
                "check",
                "--mode",
                "v2-strict",
                "--json",
            ),
            asset_classes=("playbooks", "assistant-projections"),
            dimensions=("projection", "activation", "schema"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-playbooks",
        ),
        "openspec": Gate(
            id="openspec",
            kind="governance",
            command=("openspec", "validate", "--all", "--strict", "--json"),
            depends_on=("schemas",),
            asset_classes=("markdown-docs", "json-contracts"),
            dimensions=("specification", "schema"),
            execution_mode="adapter",
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="openspec",
            version_source="host-toolchain",
        ),
        "unit-architecture": Gate(
            id="unit-architecture",
            kind="test",
            profile="product-toolchain",
            toolchain="uv-python",
            command=(".config/ci/scripts/run-python-tests.sh",),
            asset_classes=("python-code",),
            dimensions=("test", "coverage"),
            execution_mode="adapter",
            evidence_class="proof",
            trust_bearing=True,
            tool_adapter="pytest",
            version_source="locked-toolchain",
        ),
        "ruff": Gate(
            id="ruff",
            kind="lint",
            profile="product-toolchain",
            toolchain="uv-python",
            command=(".config/ci/scripts/run-python-lint.sh",),
            asset_classes=("python-code",),
            dimensions=("lint", "format", "ratchet"),
            execution_mode="adapter",
            evidence_class="diagnostic",
            trust_bearing=False,
            tool_adapter="ruff",
            version_source="locked-toolchain",
        ),
        "docstrings": Gate(
            id="docstrings",
            kind="docs",
            profile="product-toolchain",
            toolchain="uv-python",
            command=(".config/ci/scripts/run-docstring-coverage.sh",),
            asset_classes=("python-code",),
            dimensions=("documentation", "intent"),
            execution_mode="inprocess",
            evidence_class="diagnostic",
            trust_bearing=True,
            tool_adapter="ethos-docstrings-google",
            version_source="product",
        ),
        "build": Gate(
            id="build",
            kind="package",
            profile="product-toolchain",
            toolchain="uv-python",
            command=("uv", "build", "--all-packages"),
            depends_on=("unit-architecture", "ruff"),
            asset_classes=("release-artifacts",),
            dimensions=("reproducibility", "attestation"),
            execution_mode="adapter",
            evidence_class="proof",
            trust_bearing=True,
            tool_adapter="uv-build",
            writes_files=True,
            version_source="locked-toolchain",
        ),
    }
    for gate in quality_gate_registry().values():
        if gate.id not in registry:
            registry[gate.id] = Gate(
                id=gate.id,
                kind=gate.kind,
                command=gate.command,
                policy=gate.policy,
                profile=gate.profile,
                toolchain=gate.toolchain,
                depends_on=gate.depends_on,
                asset_classes=gate.asset_classes,
                dimensions=gate.dimensions,
                execution_mode=gate.execution_mode,
                evidence_class=gate.evidence_class,
                trust_bearing=gate.trust_bearing,
                tool_adapter=gate.tool_adapter,
                writes_files=gate.writes_files,
                network_policy=gate.network_policy,
                version_source=gate.version_source,
            )
    return registry


PRODUCT_DEFAULT_GATE_IDS = (
    "repository-audit",
    "claims",
    "docs-registry",
    "schemas",
    "playbooks-v2",
    "generated-artifacts",
    "unit-architecture",
    "ruff",
    "python-types",
    "docstrings",
    "toml-config",
    "yaml-config",
    "shell-lint",
    "format-policy",
)

PRODUCT_FULL_GATE_IDS = (
    "repository-audit",
    "claims",
    "docs-registry",
    "schemas",
    "playbooks-v2",
    "generated-artifacts",
    "openspec",
    "unit-architecture",
    "ruff",
    "python-types",
    "docstrings",
    "build",
    "markdown-links",
    "shell-lint",
    "toml-config",
    "yaml-config",
    "markdown-structure",
    "format-policy",
    "asset-determinism",
    "schema-contracts",
    "proof-policy",
    "python-size",
    "npm-pack",
)

DEFAULT_GATE_IDS = PRODUCT_DEFAULT_GATE_IDS


ADOPTER_DEFAULT_GATE_IDS = (
    "repository-audit",
    "claims",
    "schemas",
    "playbooks-v2",
    "generated-artifacts",
    "format-policy",
    "asset-determinism",
    "schema-contracts",
    "proof-policy",
)


def _has_repository_profile(root: Path | None) -> bool:
    if root is None:
        return False
    return load_repository_profile(root).exists


def default_gate_ids(*, full: bool = False, root: Path | None = None) -> tuple[str, ...]:
    if _has_repository_profile(root):
        # Adopted repositories expose their proof depth through `.ethos/profile.toml`
        # and repository-native gates. The product code-correctness floor must not
        # assume product-owned `.config/ci/scripts/*` exist in every adopter.
        return ADOPTER_DEFAULT_GATE_IDS
    if full:
        return PRODUCT_FULL_GATE_IDS
    # The product default proof floor is the CODE-CORRECTNESS core (tests + lint +
    # types) alongside governance self-checks. "proven" must mean the ETHOS product
    # code actually passes; adopter roots get the profile floor above instead.
    return PRODUCT_DEFAULT_GATE_IDS


def gate_graph(
    gate_ids: tuple[str, ...] = (),
    *,
    full: bool = False,
    root: Path | None = None,
) -> ActionGraph:
    registry = gate_registry()
    selected = gate_ids or default_gate_ids(full=full, root=root)
    nodes = []
    for gate_id in selected:
        gate = registry[gate_id]
        nodes.append(gate.to_node())
    return ActionGraph(nodes=tuple(nodes))

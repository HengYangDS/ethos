from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.profile import load_repository_profile
from ethos_core.action_graph.core import ActionGraph
from ethos_core.action_graph.core import ActionNode
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
        "evidence-freshness": Gate(
            id="evidence-freshness",
            kind="governance",
            command=("ethos", "quality", "evidence-freshness", "--json"),
            depends_on=("claims",),
            asset_classes=("evidence",),
            dimensions=("digest", "freshness", "chronicle", "evolution"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-evidence-freshness",
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
        "docs-topology": Gate(
            id="docs-topology",
            kind="docs",
            command=(python, "-m", "ethos.cli", "quality", "docs-topology", "--json"),
            asset_classes=("markdown-docs", "decision-records", "evidence"),
            dimensions=("information-architecture", "decisions", "adopter-isomorphism"),
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-docs-topology",
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
        "product-boundary": Gate(
            id="product-boundary",
            kind="governance",
            command=("tools/ci/scripts/run-product-boundary.sh",),
            asset_classes=("markdown-docs", "config", "tests", "release-artifacts"),
            dimensions=(
                "product-boundary",
                "identity",
                "adopter-neutrality",
                "distribution-boundary",
            ),
            execution_mode="adapter",
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-product-boundary",
            version_source="product",
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
            command=("tools/ci/scripts/run-python-tests.sh",),
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
            command=("tools/ci/scripts/run-python-lint.sh",),
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
            command=("tools/ci/scripts/run-docstring-coverage.sh",),
            asset_classes=("python-code",),
            dimensions=("documentation", "intent"),
            execution_mode="inprocess",
            evidence_class="diagnostic",
            trust_bearing=True,
            tool_adapter="ethos-docstrings-google",
            version_source="product",
        ),
        "module-layout": Gate(
            id="module-layout",
            kind="architecture",
            profile="product-toolchain",
            toolchain="uv-python",
            command=("tools/ci/scripts/run-module-layout.sh",),
            asset_classes=("python-code",),
            dimensions=("module-layout", "semantic-subpackages", "import-discipline"),
            execution_mode="adapter",
            evidence_class="diagnostic",
            trust_bearing=True,
            tool_adapter="ethos-module-layout",
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
)

PRODUCT_FULL_GATE_IDS = (
    "repository-audit",
    "claims",
    "evidence-freshness",
    "docs-registry",
    "docs-topology",
    "schemas",
    "playbooks-v2",
    "generated-artifacts",
    "product-boundary",
    "openspec",
    "unit-architecture",
    "ruff",
    "python-types",
    "docstrings",
    "module-layout",
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
    "evidence-freshness",
    "docs-topology",
    "schemas",
    "playbooks-v2",
    "generated-artifacts",
    "format-policy",
    "asset-determinism",
    "schema-contracts",
    "proof-policy",
)


def _is_product_root(root: Path) -> bool:
    """Return True when ``root`` is the ETHOS product repository itself.

    Mirrors ethos.repository.context.is_product_root by the same two anchor files, but
    inlined to keep gates.py off context.py's heavier import chain. The product repo
    must never be treated as an adopter (which would drop its own code-correctness
    floor), even if it grew a `.ethos/profile.toml`.
    """
    return (root / "packages" / "ethos" / "README.md").exists() and (
        root / "system" / "schemas" / "kernel"
    ).exists()


def _adopter_native_code_correctness_gates(profile: object) -> tuple[str, ...]:
    """Gate ids an adopter's profile declares as its native code-correctness proof.

    An adopter drops the product's code-correctness gates (they run product-owned
    `tools/ci/scripts/*`), so it MUST declare equivalents under
    `[proof] code_correctness_gates = [...]`. Promotion completeness then requires
    those gate ids to have run — an adopter proof with no code-correctness dimension is
    NOT complete (a contentless proof must not promote).
    """
    tables = getattr(profile, "tables", {})
    proof_table = tables.get("proof", {}) if isinstance(tables, dict) else {}
    declared = proof_table.get("code_correctness_gates") if isinstance(proof_table, dict) else None
    if not isinstance(declared, list):
        return ()
    return tuple(str(gate_id) for gate_id in declared if str(gate_id))


def _adopter_profile_active(root: Path | None) -> bool:
    """Return True only for a VALID adopter profile on a non-product root.

    Keying the floor on bare `.exists` let any `.ethos/profile.toml` — 0-byte, invalid
    TOML, or the product repo's own — downgrade the 19-gate product floor to the 11-gate
    adopter floor, dropping every code-correctness gate with no forgery. Require the
    profile to exist, PARSE (`valid`), and the root to not be the product itself.
    """
    if root is None:
        return False
    if _is_product_root(root):
        return False
    profile = load_repository_profile(root)
    return profile.exists and profile.valid


ADOPTER_MISSING_CODE_CORRECTNESS_GATE = "adopter_profile_missing_code_correctness_gates"


def adopter_code_correctness_gap(root: Path | None) -> str:
    """Return a completeness gap when an active adopter declares no native
    code-correctness gates, else ''.

    Separate from `default_gate_ids` (which drives BOTH proof execution and the
    completeness floor, so it may only contain registry-executable gate ids). The
    "an adopter proof must carry a code-correctness dimension" rule is a COMPLETENESS
    requirement, surfaced here and folded into promotion_completeness_gaps — it must not
    put a non-executable sentinel into the executable floor.
    """
    if not _adopter_profile_active(root):
        return ""
    profile = load_repository_profile(cast("Path", root))
    if _adopter_native_code_correctness_gates(profile):
        return ""
    return ADOPTER_MISSING_CODE_CORRECTNESS_GATE


def default_gate_ids(*, full: bool = False, root: Path | None = None) -> tuple[str, ...]:
    if _adopter_profile_active(root):
        # Adopted repositories expose their proof depth through `.ethos/profile.toml`
        # and repository-native gates. The product code-correctness floor must not
        # assume product-owned `tools/ci/scripts/*` exist in every adopter — but the
        # adopter's DECLARED native code-correctness gates join the executable floor so
        # promotion completeness requires them. The "declared none" case is enforced by
        # adopter_code_correctness_gap (a completeness gap), NOT by a non-executable
        # sentinel here — this set must stay registry-executable for gate_graph.
        profile = load_repository_profile(cast("Path", root))
        native = _adopter_native_code_correctness_gates(profile)
        return (*ADOPTER_DEFAULT_GATE_IDS, *native)
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

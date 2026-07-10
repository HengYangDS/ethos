from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ethos.repository.profile import load_repository_profile
from ethos_core.action_graph.core import ActionGraph
from ethos_core.action_graph.core import ActionNode
from ethos_core.quality.gates import quality_gate_registry


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
        "no-compat": Gate(
            id="no-compat",
            kind="architecture",
            command=("tools/ci/scripts/run-no-compat.sh",),
            asset_classes=("python-code", "markdown-docs", "governance"),
            dimensions=("compatibility-residue", "semantic-cutover", "product-boundary"),
            execution_mode="adapter",
            evidence_class="contract",
            trust_bearing=True,
            tool_adapter="ethos-no-compat",
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
    "no-compat",
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
    "no-compat",
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


def promotion_required_gate_ids(root: Path | None = None) -> tuple[str, ...]:
    """The gate ids a promotion proof must fully cover for this root (the LAND floor).

    Public alias of `default_gate_ids(full=False, root=root)` — the single definition
    the completeness check, the policy digest, and the executable graph all resolve, so
    they never drift.
    """
    return default_gate_ids(full=False, root=root)


_PYTHON_INTERPRETER_RE = re.compile(r"^python(3(\.\d+)?)?$")


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Collapse the host python-interpreter path in a gate command to the literal
    `"python"`, leaving every other token verbatim.

    A gate's command embeds `sys.executable` at registry-build time (gate_registry does
    `python = sys.executable`), so the SAME gate records a different absolute interpreter
    path on every host/venv. The policy identity must be stable across environments
    (B10): only the interpreter BASENAME family is normalized, unconditionally — never
    gated on equality to the live sys.executable, since the recording interpreter differs
    from the validating interpreter in exactly the cross-environment case B10 exercises.
    Repo-relative script tokens (tools/ci/scripts/*.sh) are kept verbatim so a command
    change (B11) or a script-content change (B12, via policy_source_digest) still moves
    the digest.
    """
    if not command:
        return command
    head, *rest = command
    if _PYTHON_INTERPRETER_RE.match(Path(head).name):
        return ("python", *rest)
    return command


def _gate_policy_source_digest(gate: Gate, root: Path) -> str:
    """Digest of a script-type gate's on-disk source, or '' for in-process gates.

    B12: a gate whose command is a repo-relative script (same path, tampered content)
    must change the policy digest. Hash the file bytes under `root`. In-process gates
    (python -m ethos.cli ...) and the `ethos` entrypoint carry no repo-owned script, so
    they contribute ''. `root` must be the tree the proof was recorded against; the
    caller (gate_policy_digest) owns that consistency.
    """
    canonical = canonical_gate_command(gate.command)
    if not canonical:
        return ""
    head = canonical[0]
    if head in ("python", "ethos") or "/" not in head:
        return ""
    script = root / head
    if not script.is_file():
        return ""
    return hashlib.sha256(script.read_bytes()).hexdigest()


def gate_policy_fields(gate: Gate, root: Path) -> dict[str, object]:
    """The cross-environment-stable policy identity of a single gate."""
    return {
        "gate_id": gate.id,
        "canonical_command": list(canonical_gate_command(gate.command)),
        "trust_bearing": gate.trust_bearing,
        "evidence_class": gate.evidence_class,
        "execution_mode": gate.execution_mode,
        "tool_adapter": gate.tool_adapter,
        "policy_source_digest": _gate_policy_source_digest(gate, root),
        "profile_binding": gate.profile,
        "layer": gate.kind,
    }


def gate_policy_digest(root: Path) -> str:
    """A stable digest of the required gate set's policy identity for `root`.

    Binds a proof/marker to WHAT the required gates ARE (canonical command, trust
    classification, evidence class, script content, …), not just to the proof's own
    bytes. If a gate's canonical command or classification changes, or a script gate's
    content is tampered, this digest changes and an old proof is stale (B11/B12); a mere
    interpreter-path change does not (B10). Covers the registry-resolvable required ids
    in floor order; an adopter's declared native gates that are not in the product
    registry are governed by the completeness floor, not this digest.
    """
    registry = gate_registry()
    fields = [
        gate_policy_fields(registry[gate_id], root)
        for gate_id in promotion_required_gate_ids(root)
        if gate_id in registry
    ]
    canonical = json.dumps({"gates": fields}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def gate_policy_conformance_gaps(runs: object, root: Path) -> list[str]:
    """Gaps where an executed run does not conform to its gate's policy identity.

    Defeats a same-UID forged proof that covers the required action_ids with runs that
    never ran the real gate: a `command=('/bin/true',)` run, or a run mislabeled
    `trust_bearing`/`evidence_class`. For each required gate present in the registry,
    the matching run's CANONICAL command must equal the gate's canonical command
    (canonical-to-canonical, so a legitimate interpreter difference is not flagged) and
    its trust_bearing/evidence_class must match the gate definition.
    """
    if not isinstance(runs, list):
        return []
    by_action: dict[str, dict[str, object]] = {}
    for run in runs:
        if isinstance(run, dict):
            by_action.setdefault(str(run.get("action_id", "")), run)
    registry = gate_registry()
    gaps: list[str] = []
    for gate_id in promotion_required_gate_ids(root):
        gate = registry.get(gate_id)
        if gate is None:
            continue
        run = by_action.get(gate_id)
        if run is None:
            continue  # absence is the completeness check's concern, not conformance
        run_command = run.get("command")
        command = (
            tuple(str(token) for token in run_command)
            if isinstance(run_command, (list, tuple))
            else ()
        )
        conforms = (
            canonical_gate_command(command) == canonical_gate_command(gate.command)
            and run.get("trust_bearing") == gate.trust_bearing
            and run.get("evidence_class") == gate.evidence_class
        )
        if not conforms:
            gaps.append(f"proof_gate_not_policy_conformant:{gate_id}")
    return gaps


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

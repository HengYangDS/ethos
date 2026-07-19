"""Typed declaration contract for ETHOS gate registries."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos_core._resources import declaration_text
from ethos_core._resources import resolve_declaration_path
from ethos_core.action_graph.core import ActionNode

DECLARATION_PATH = Path("system/gates.toml")
_DECLARATION_RESOURCE = "data/gates.toml"
RegistryName = Literal["runtime", "quality"]
_DUPLICATE_GATE_ID = "duplicate gate id"
_DUPLICATE_GATE_COMMAND = "duplicate gate command"
_UNAVAILABLE_GATE_DEPENDENCY = "unavailable gate dependency"
_PRODUCT_FULL_MISSING_DEFAULT = "product full missing default"
_UNKNOWN_PROOF_GATE = "unknown proof gate"
_DUPLICATE_PROOF_GATE = "duplicate proof gate"


class GateDescriptor(BaseModel):
    """Immutable gate descriptor shared by runtime and quality projections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    command: tuple[str, ...] = Field(min_length=1)
    policy: str = "required"
    profile: str = "product"
    toolchain: str = "quality-adapter"
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

    def resolved_command(self, python_executable: str) -> tuple[str, ...]:
        """Resolve declaration placeholders from an explicit runtime fact."""
        return tuple(python_executable if part == "{python}" else part for part in self.command)

    def bind_python(self, python_executable: str) -> Self:
        """Return a copy whose Python placeholder is bound to the runtime executable."""
        return self.model_copy(update={"command": self.resolved_command(python_executable)})

    def to_dict(self) -> dict[str, object]:
        """Project the descriptor to the stable public quality-gate shape."""
        return self.model_dump(mode="json")

    def to_node(self) -> ActionNode:
        """Compile this declaration into its ActionGraph node projection."""
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


class GateEntry(GateDescriptor):
    """Gate declaration record with explicit registry projections."""

    registries: tuple[RegistryName, ...] = Field(min_length=1)

    def descriptor(self, *, python_executable: str | None = None) -> GateDescriptor:
        """Compile this declaration entry into an immutable descriptor."""
        descriptor = GateDescriptor.model_validate(self.model_dump(exclude={"registries"}))
        return descriptor.bind_python(python_executable) if python_executable else descriptor


class GateProofSets(BaseModel):
    """Ordered proof floors compiled from the gate registry declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    product_default: tuple[str, ...]
    product_full: tuple[str, ...]
    adopter_default: tuple[str, ...]


class GateRegistryDeclaration(BaseModel):
    """Validated source declaration for gate descriptors and proof floors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
    proof_sets: GateProofSets
    gates: tuple[GateEntry, ...]

    @model_validator(mode="after")
    def validate_references(self) -> GateRegistryDeclaration:
        """Reject dangling or incomplete registry and proof declarations."""
        gate_ids = [gate.id for gate in self.gates]
        if len(gate_ids) != len(set(gate_ids)):
            raise ValueError(_DUPLICATE_GATE_ID)
        commands = [gate.command for gate in self.gates]
        if len(commands) != len(set(commands)):
            raise ValueError(_DUPLICATE_GATE_COMMAND)
        runtime_ids = _validate_registry("runtime", self.gates)
        _validate_registry("quality", self.gates)
        _validate_proof_sets(self.proof_sets, runtime_ids)
        return self

    def registry(
        self,
        name: RegistryName,
        *,
        python_executable: str | None = None,
    ) -> dict[str, GateDescriptor]:
        """Compile an ordered registry view from gate declarations."""
        descriptors = (
            gate.descriptor(python_executable=python_executable)
            for gate in self.gates
            if name in gate.registries
        )
        return {descriptor.id: descriptor for descriptor in descriptors}


def _validate_registry(name: RegistryName, gates: tuple[GateEntry, ...]) -> set[str]:
    """Return emitted ids after validating one registry projection."""
    emitted: set[str] = set()
    for gate in _registry_entries(name, gates):
        _validate_dependencies(gate, emitted)
        emitted.add(gate.id)
    return emitted


def _registry_entries(name: RegistryName, gates: tuple[GateEntry, ...]) -> tuple[GateEntry, ...]:
    """Return declarations projected into a registry in declaration order."""
    return tuple(gate for gate in gates if name in gate.registries)


def _validate_dependencies(gate: GateEntry, emitted: set[str]) -> None:
    """Require dependencies to be available earlier in the same registry."""
    dangling = set(gate.depends_on) - emitted
    if dangling:
        raise ValueError(_UNAVAILABLE_GATE_DEPENDENCY)


def _validate_proof_sets(proof_sets: GateProofSets, runtime_ids: set[str]) -> None:
    """Validate proof floors against the runtime gate registry."""
    _validate_proof_floor(proof_sets.product_default, runtime_ids)
    _validate_proof_floor(proof_sets.product_full, runtime_ids)
    _validate_proof_floor(proof_sets.adopter_default, runtime_ids)
    if not set(proof_sets.product_default) <= set(proof_sets.product_full):
        raise ValueError(_PRODUCT_FULL_MISSING_DEFAULT)


def _validate_proof_floor(gate_ids: tuple[str, ...], runtime_ids: set[str]) -> None:
    """Reject duplicate or unknown ids in one proof floor."""
    missing = set(gate_ids) - runtime_ids
    if missing:
        raise ValueError(_UNKNOWN_PROOF_GATE)
    if len(gate_ids) != len(set(gate_ids)):
        raise ValueError(_DUPLICATE_PROOF_GATE)


def _declaration_text(path: Path) -> str:
    return declaration_text(path, resource=_DECLARATION_RESOURCE, canonical=DECLARATION_PATH)


def load_gate_registry_declaration(
    path: Path | str | None = None,
) -> GateRegistryDeclaration:
    """Load and validate the tracked gate registry declaration."""
    declaration_path = resolve_declaration_path(
        path, canonical=DECLARATION_PATH, module_file=__file__
    )
    payload = tomllib.loads(_declaration_text(declaration_path))
    return GateRegistryDeclaration.model_validate(payload)

"""Typed declaration contract for ETHOS gate registries."""

import tomllib
from graphlib import CycleError
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos._resources import declaration_text
from ethos._resources import resolve_declaration_path
from ethos.contracts.value import FrozenTuple

DECLARATION_PATH = Path("system/gates.toml")
_DECLARATION_RESOURCE = "data/gates.toml"
RegistryName = Literal["runtime", "quality"]
_DUPLICATE_GATE_ID = "duplicate gate id"
_DUPLICATE_GATE_COMMAND = "duplicate gate command"
_GATE_EXECUTOR_INVALID = "gate executor invalid"
_UNAVAILABLE_GATE_DEPENDENCY = "unavailable gate dependency"
_FULL_MISSING_DEFAULT = "full proof set missing default"
_UNKNOWN_PROOF_GATE = "unknown proof gate"
_DUPLICATE_PROOF_GATE = "duplicate proof gate"


class Gate(BaseModel):
    """One immutable gate declaration and executable projection."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    command: FrozenTuple[str] = ()
    providers: FrozenTuple[str] = ()
    policy: str = "required"
    profile: str = "product"
    toolchain: str = "quality-adapter"
    depends_on: FrozenTuple[str] = ()
    asset_classes: FrozenTuple[str] = ()
    dimensions: FrozenTuple[str] = ()
    execution_mode: str = "inprocess"
    evidence_class: str = "contract"
    trust_bearing: bool = False
    tool_adapter: str = "ethos"
    writes_files: bool = False
    network_policy: str = "offline"
    version_source: str = "product"
    registries: FrozenTuple[RegistryName] = Field(default=("runtime",), min_length=1)

    @model_validator(mode="after")
    def validate_executor(self) -> Self:
        """Require exactly one executable adapter form per gate."""
        if bool(self.command) == bool(self.providers):
            raise ValueError(_GATE_EXECUTOR_INVALID)
        if len(self.providers) != len(set(self.providers)) or any(
            not reference.startswith("ethos.")
            or reference.count(":") != 1
            or not all(reference.partition(":")[::2])
            for reference in self.providers
        ):
            raise ValueError(_GATE_EXECUTOR_INVALID)
        return self

    def to_dict(self) -> dict[str, object]:
        """Project the descriptor to the stable public quality-gate shape."""
        payload = self.model_dump(
            mode="json",
            exclude={"command", "providers", "registries"},
        )
        payload["command" if self.command else "providers"] = list(self.command or self.providers)
        return payload


class GateProofSets(BaseModel):
    """Ordered proof floors compiled from the gate registry declaration."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    default: FrozenTuple[str]
    full: FrozenTuple[str]


class GateRegistryDeclaration(BaseModel):
    """Validated source declaration for gate descriptors and proof floors."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str = Field(min_length=1)
    schema_version: int = 1
    source_refs: FrozenTuple[str] = ()
    proof_sets: GateProofSets
    gates: FrozenTuple[Gate]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        """Reject dangling or incomplete registry and proof declarations."""
        gate_ids = [gate.id for gate in self.gates]
        if len(gate_ids) != len(set(gate_ids)):
            raise ValueError(_DUPLICATE_GATE_ID)
        commands = [gate.command for gate in self.gates if gate.command]
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
    ) -> dict[str, Gate]:
        """Compile an ordered registry view from gate declarations."""
        gates = (
            gate.model_copy(
                update={
                    "command": tuple(
                        python_executable if part == "{python}" else part for part in gate.command
                    )
                }
            )
            if python_executable
            else gate
            for gate in self.gates
            if name in gate.registries
        )
        return {gate.id: gate for gate in gates}

    def proof_gates(
        self,
        gate_ids: tuple[str, ...] = (),
        *,
        full: bool = False,
        python_executable: str | None = None,
    ) -> tuple[Gate, ...]:
        """Return one stable runtime proof closure in dependency-first order."""
        registry = self.registry("runtime", python_executable=python_executable)
        selected = gate_ids or (self.proof_sets.full if full else self.proof_sets.default)
        missing = set(selected) - registry.keys()
        if missing:
            raise ValueError(_UNKNOWN_PROOF_GATE)
        required = set(selected)
        pending = list(selected)
        while pending:
            gate = registry[pending.pop()]
            for dependency in gate.depends_on:
                if dependency not in required:
                    required.add(dependency)
                    pending.append(dependency)
        order = TopologicalSorter(
            {
                gate_id: tuple(
                    dependency
                    for dependency in registry[gate_id].depends_on
                    if dependency in required
                )
                for gate_id in sorted(required)
            }
        ).static_order()
        return tuple(registry[gate_id] for gate_id in order)


def _validate_registry(name: RegistryName, gates: tuple[Gate, ...]) -> set[str]:
    """Return emitted ids after validating one registry projection."""
    entries = tuple(gate for gate in gates if name in gate.registries)
    emitted = {gate.id for gate in entries}
    if any(set(gate.depends_on) - emitted for gate in entries):
        raise ValueError(_UNAVAILABLE_GATE_DEPENDENCY)
    try:
        tuple(TopologicalSorter({gate.id: gate.depends_on for gate in entries}).static_order())
    except CycleError as exc:
        raise ValueError(_UNAVAILABLE_GATE_DEPENDENCY) from exc
    return emitted


def _validate_proof_sets(proof_sets: GateProofSets, runtime_ids: set[str]) -> None:
    """Validate proof floors against the runtime gate registry."""
    _validate_proof_floor(proof_sets.default, runtime_ids)
    _validate_proof_floor(proof_sets.full, runtime_ids)
    if not set(proof_sets.default) <= set(proof_sets.full):
        raise ValueError(_FULL_MISSING_DEFAULT)


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

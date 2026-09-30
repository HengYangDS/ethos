"""Typed declaration contract for ETHOS gate registries."""

import re
import tomllib
from importlib import resources
from pathlib import Path
from typing import Annotated
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import GetJsonSchemaHandler
from pydantic import model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import FrozenMapping
from ethos.contracts.value import FrozenTuple

DECLARATION_PATH = Path("system/gates.toml")
_DECLARATION_RESOURCE = "data/gates.toml"
_DUPLICATE_GATE_ID = "duplicate gate id"
_DUPLICATE_GATE_COMMAND = "duplicate gate command"
_GATE_EXECUTOR_INVALID = "gate executor invalid"
_UNAVAILABLE_GATE_DEPENDENCY = "unavailable gate dependency"
_FULL_MISSING_DEFAULT = "full proof set missing default"
_UNKNOWN_PROOF_GATE = "unknown proof gate"
_DUPLICATE_PROOF_GATE = "duplicate proof gate"
_GATE_RESOURCES_INVALID = "gate resources invalid"
_RESOURCE_NAME = re.compile(r"^(?:\*|[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*)$")
_NATIVE_PATH = re.compile(
    r"^(?![A-Za-z]:)(?!(?:[\s\S]*/)?\.{1,2}(?:/|$))[^/\\\x00]+(?:/[^/\\\x00]+)*$"
)
NativePath = Annotated[str, Field(pattern=_NATIVE_PATH)]


class NativeReportSource(BaseModel):
    """One standard native report delivered by the gate's sole execution owner."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    format: Literal["go-test-json", "go-coverage", "junit", "lcov", "sarif"]
    channel: Literal["stdout", "stderr", "file"]
    path: NativePath | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def validate_destination(self) -> Self:
        """Files live below the attempt root; captured streams have no file path."""
        if (self.channel == "file") != (self.path is not None):
            message = "native report destination invalid"
            raise ValueError(message)
        return self

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Project the same channel-to-file relation into the public descriptor."""
        schema = super().__get_pydantic_json_schema__(core_schema, handler)
        schema["allOf"] = [
            {
                "if": {"properties": {"channel": {"const": "file"}}, "required": ["channel"]},
                "then": {"required": ["path"], "properties": {"path": {"type": "string"}}},
                "else": {"properties": {"path": {"type": "null"}}},
            }
        ]
        return schema


def bind_gate_command(command: tuple[str, ...], python_executable: str) -> tuple[str, ...]:
    """Interpret declared runtime placeholders identically for execution and observation."""
    return tuple(python_executable if part == "{python}" else part for part in command)


class Gate(BaseModel):
    """One immutable gate declaration and executable projection."""

    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", json_schema_serialization_defaults_required=True
    )

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    command: FrozenTuple[str] = ()
    providers: FrozenTuple[str] = ()
    verification_providers: FrozenTuple[str] = ()
    source_inputs: FrozenTuple[NativePath] = Field(default=(), exclude_if=lambda values: not values)
    native_reports: FrozenTuple[NativeReportSource] = Field(
        default=(), exclude_if=lambda values: not values
    )
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
    cpu_reservation: int = Field(default=1, ge=1, exclude_if=lambda value: value == 1)
    resource_locks: FrozenMapping[Literal["shared", "exclusive"]] | None = Field(
        default=None,
        json_schema_extra={"propertyNames": {"pattern": _RESOURCE_NAME.pattern}},
    )
    network_policy: str = "offline"
    version_source: str = "product"

    @model_validator(mode="after")
    def validate_executor(self) -> Self:
        """Require exactly one executable adapter form per gate."""
        if bool(self.command) == bool(self.providers) or (
            self.verification_providers and not self.command
        ):
            raise ValueError(_GATE_EXECUTOR_INVALID)
        if any(
            len(references) != len(set(references))
            or any(
                not reference.startswith("ethos.")
                or reference.count(":") != 1
                or not all(reference.partition(":")[::2])
                for reference in references
            )
            for references in (self.providers, self.verification_providers)
        ):
            raise ValueError(_GATE_EXECUTOR_INVALID)
        if self.resource_locks is not None and (
            any(_RESOURCE_NAME.fullmatch(name) is None for name in self.resource_locks)
            or (self.writes_files and "exclusive" not in self.resource_locks.values())
        ):
            raise ValueError(_GATE_RESOURCES_INVALID)
        if len(self.source_inputs) != len(set(self.source_inputs)):
            message = "native gate source inputs repeated"
            raise ValueError(message)
        if self.native_reports and (
            not self.command
            or not self.verification_providers
            or not self.source_inputs
            or len({report.format for report in self.native_reports}) != len(self.native_reports)
        ):
            message = "native gate report contract invalid"
            raise ValueError(message)
        return self

    @classmethod
    def public_schema(cls) -> JsonSchemaValue:
        """Derive the serialized public descriptor without a second contract owner."""
        schema = cls.model_json_schema(mode="serialization")
        schema.update(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://ethos.local/schemas/gate.schema.json",
                "title": "ETHOS Gate",
            }
        )
        optional = {
            "command",
            "providers",
            "verification_providers",
            "source_inputs",
            "native_reports",
            "cpu_reservation",
            "resource_locks",
        }
        schema["required"] = [name for name in schema["required"] if name not in optional]
        schema["oneOf"] = [
            {"required": [selected], "not": {"required": [other]}}
            for selected, other in (("command", "providers"), ("providers", "command"))
        ]
        for name in (
            "command",
            "providers",
            "verification_providers",
            "source_inputs",
            "native_reports",
        ):
            schema["properties"][name]["minItems"] = 1
        for name in ("providers", "verification_providers"):
            schema["properties"][name].update(
                {
                    "uniqueItems": True,
                    "items": {"type": "string", "pattern": r"^ethos\.[^:]+:[^:]+$"},
                }
            )
        schema["properties"]["source_inputs"]["uniqueItems"] = True
        formats = schema["$defs"]["NativeReportSource"]["properties"]["format"]["enum"]
        schema["properties"]["native_reports"]["allOf"] = [
            {
                "contains": {"properties": {"format": {"const": value}}, "required": ["format"]},
                "minContains": 0,
                "maxContains": 1,
            }
            for value in formats
        ]
        schema["allOf"] = [
            {"if": {"required": ["verification_providers"]}, "then": {"required": ["command"]}},
            {
                "if": {"required": ["native_reports"]},
                "then": {"required": ["command", "verification_providers", "source_inputs"]},
            },
        ]
        return schema

    def conflicts_with(self, other: Self) -> bool:
        """Compare complete exclusion domains; unknown writers retain global exclusion."""
        left, right = (
            gate.resource_locks
            if gate.resource_locks is not None
            else {"*": "exclusive" if gate.writes_files else "shared"}
            for gate in (self, other)
        )
        if left.get("*") == "exclusive" or right.get("*") == "exclusive":
            return True
        return any(
            "exclusive" in (first_mode, second_mode)
            and (
                first == "*"
                or second == "*"
                or first == second
                or first.startswith(second + "/")
                or second.startswith(first + "/")
            )
            for first, first_mode in left.items()
            for second, second_mode in right.items()
        )

    def to_dict(self) -> dict[str, object]:
        """Project the descriptor to the stable public quality-gate shape."""
        payload = self.model_dump(
            mode="json",
            exclude={"command", "providers", "verification_providers"},
            exclude_none=True,
        )
        payload["command" if self.command else "providers"] = list(self.command or self.providers)
        if self.verification_providers:
            payload["verification_providers"] = list(self.verification_providers)
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
    schema_version: int = Field(default=1, ge=1, le=1)
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
        gate_ids = _validate_gate_graph(self.gates)
        _validate_proof_sets(self.proof_sets, gate_ids)
        return self

    def registry(
        self,
        *,
        python_executable: str | None = None,
    ) -> dict[str, Gate]:
        """Compile an ordered registry view from gate declarations."""
        gates = (
            gate.model_copy(update={"command": bind_gate_command(gate.command, python_executable)})
            if python_executable
            else gate
            for gate in self.gates
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
        registry = self.registry(python_executable=python_executable)
        selected = gate_ids or (self.proof_sets.full if full else self.proof_sets.default)
        missing = set(selected) - registry.keys()
        if missing:
            raise ValueError(_UNKNOWN_PROOF_GATE)
        nodes = tuple(
            PlanNode(id=gate.id, kind="check", command=gate.command, depends_on=gate.depends_on)
            for gate in registry.values()
        )
        return tuple(registry[node.id] for node in TransitionPlan.closure(nodes, selected))


def _validate_gate_graph(gates: tuple[Gate, ...]) -> set[str]:
    """Return gate ids after validating the one declared dependency graph."""
    emitted = {gate.id for gate in gates}
    if any(set(gate.depends_on) - emitted for gate in gates):
        raise ValueError(_UNAVAILABLE_GATE_DEPENDENCY)
    try:
        TransitionPlan.closure(
            tuple(
                PlanNode(
                    id=gate.id,
                    kind="check",
                    command=gate.command,
                    depends_on=gate.depends_on,
                )
                for gate in gates
            )
        )
    except ValueError as exc:
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


def load_gate_registry_declaration(
    path: Path | str | None = None,
) -> GateRegistryDeclaration:
    """Read explicit gate input or the current interpreter's source/package default."""
    if path is not None:
        text = Path(path).read_text(encoding="utf-8")
    else:
        source = Path(__file__).resolve().parents[3] / DECLARATION_PATH
        text = (
            source.read_text(encoding="utf-8")
            if source.is_file()
            else resources.files("ethos")
            .joinpath(_DECLARATION_RESOURCE)
            .read_text(encoding="utf-8")
        )
    return GateRegistryDeclaration.model_validate(tomllib.loads(text))

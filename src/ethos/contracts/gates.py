"""Typed declaration contract for ETHOS gate registries."""

import re
import tomllib
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import FrozenMapping
from ethos.contracts.value import FrozenTuple
from ethos.repository.release.resources import canonical_resource

DECLARATION_PATH = Path("system/gates.toml")
_DUPLICATE_GATE_ID = "duplicate gate id"
_DUPLICATE_GATE_COMMAND = "duplicate gate command"
_GATE_EXECUTOR_INVALID = "gate executor invalid"
_UNAVAILABLE_GATE_DEPENDENCY = "unavailable gate dependency"
_FULL_MISSING_DEFAULT = "full proof set missing default"
_UNKNOWN_PROOF_GATE = "unknown proof gate"
_DUPLICATE_PROOF_GATE = "duplicate proof gate"
_GATE_RESOURCES_INVALID = "gate resources invalid"
_RESOURCE_NAME = re.compile(r"^(?:\*|[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*)$")


def bind_gate_command(command: tuple[str, ...], python_executable: str) -> tuple[str, ...]:
    """Interpret declared runtime placeholders identically for execution and observation."""
    return tuple(python_executable if part == "{python}" else part for part in command)


class NativeOutput(BaseModel):
    """A native report's producer and exact path within one owned attempt."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"format": {"const": "python-runtime-json"}}},
                    "then": {
                        "required": ["python", "configuration", "dependency_groups"],
                        "properties": {
                            "python": {"minLength": 1, "pattern": r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$"},
                            "configuration": {"minLength": 1},
                            "dependency_groups": {"type": "array", "uniqueItems": True},
                        },
                    },
                    "else": {
                        "not": {"required": ["dependency_groups"]},
                        "properties": {"python": {"const": ""}, "configuration": {"const": ""}},
                    },
                }
            ],
        },
    )

    path: str = Field(min_length=1)
    # Tool-neutral reports, then optional Python producer reports checked only when declared.
    format: Literal[
        "junit-xml",
        "cobertura-xml",
        "lcov",
        "sarif",
        "nox-json",
        "pytest-jsonl",
        "python-runtime-json",
    ]
    sessions: FrozenTuple[str] = Field(json_schema_extra={"uniqueItems": True, "minItems": 1})
    python: str = ""
    configuration: str = ""
    dependency_groups: FrozenTuple[str] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_output(self) -> Self:
        """Native paths and session instances are complete, portable identities."""
        path = PurePosixPath(self.path)
        if (
            path.is_absolute()
            or path.as_posix() != self.path
            or not path.parts
            or any(part in {".", ".."} or ":" in part for part in path.parts)
            or "\\" in self.path
            or not self.sessions
            or any(not session for session in self.sessions)
            or len(set(self.sessions)) != len(self.sessions)
            or (self.format == "python-runtime-json") != bool(self.python)
            or (self.format == "python-runtime-json") != bool(self.configuration)
            or (
                self.configuration
                and (
                    PurePosixPath(self.configuration).is_absolute()
                    or PurePosixPath(self.configuration).as_posix() != self.configuration
                    or any(
                        part in {".", ".."} or ":" in part
                        for part in PurePosixPath(self.configuration).parts
                    )
                    or "\\" in self.configuration
                )
            )
            or (self.format == "python-runtime-json") != (self.dependency_groups is not None)
            or (
                self.dependency_groups is not None
                and (
                    len(set(self.dependency_groups)) != len(self.dependency_groups)
                    or any(not group for group in self.dependency_groups)
                )
            )
            or (self.format != "nox-json" and len(self.sessions) != 1)
            or (self.python and re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", self.python) is None)
        ):
            msg = "native_output_invalid"
            raise ValueError(msg)
        return self


class Gate(BaseModel):
    """One immutable gate declaration and executable projection."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    command: FrozenTuple[str] = ()
    providers: FrozenTuple[str] = ()
    verification_providers: FrozenTuple[str] = ()
    native_outputs: FrozenTuple[NativeOutput] = Field(
        default=(), exclude_if=lambda value: not value
    )
    policy: str = "required"
    profile: str = "product"
    toolchain: str = "quality-adapter"
    depends_on: FrozenTuple[str] = ()
    asset_classes: FrozenTuple[str] = ()
    required_for_paths: FrozenTuple[str] = Field(default=(), exclude_if=lambda value: not value)
    dimensions: FrozenTuple[str] = ()
    execution_mode: str = "inprocess"
    evidence_class: str = "contract"
    trust_bearing: bool = False
    tool_adapter: str = "ethos"
    writes_files: bool = False
    timeout_seconds: int | None = Field(default=None, ge=1, exclude_if=lambda value: value is None)
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
        if self.native_outputs:
            paths = tuple(output.path for output in self.native_outputs)
            producers = tuple(
                (output.format, session)
                for output in self.native_outputs
                for session in output.sessions
            )
            reports = tuple(output for output in self.native_outputs if output.format == "nox-json")
            report_arguments = tuple(
                self.command[index + 1]
                if item == "--report" and index + 1 < len(self.command)
                else item.partition("=")[2]
                for index, item in enumerate(self.command)
                if item == "--report" or item.startswith("--report=")
            )
            # A Nox report is optional; when declared it names every producing session.
            if (
                not self.command
                or not self.verification_providers
                or len(set(paths)) != len(paths)
                or len(set(producers)) != len(producers)
                or len(reports) > 1
                or (reports and report_arguments != ("{native_output}/" + reports[0].path,))
                or any(
                    not set(output.sessions) <= set(report.sessions)
                    for report in reports
                    for output in self.native_outputs
                )
                or any(
                    first.startswith(second + "/")
                    for first in paths
                    for second in paths
                    if first != second
                )
            ):
                msg = "native_output_contract_invalid"
                raise ValueError(msg)
        return self

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
        text = canonical_resource(DECLARATION_PATH.as_posix()).read_text(encoding="utf-8")
    return GateRegistryDeclaration.model_validate(tomllib.loads(text))

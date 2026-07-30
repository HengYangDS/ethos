"""Transient, deterministic TransitionPlan compiled from repository declarations."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from graphlib import CycleError
from graphlib import TopologicalSorter
from pathlib import PurePosixPath
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field
from pydantic import field_serializer
from pydantic import model_validator

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts

PlanVerdict = Literal["pass", "block", "unknown"]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class _PlanModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class PlanNode(_PlanModel):
    """One pure Check, Decision, or Effect description."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    id: str = Field(min_length=1)
    kind: Literal["check", "decision", "effect"]
    command: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = Field(default=(), json_schema_extra={"uniqueItems": True})

    def normalized(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "command": list(self.command),
            "depends_on": sorted(self.depends_on),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.normalized()


class PlanInputs(_PlanModel):
    """Exact inputs bound by one public TransitionPlan projection."""

    commitment: Digest
    facts: Digest
    policy: Digest


class GitRefUpdate(_PlanModel):
    """One exact compare-and-swap ref transition."""

    expected: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    desired: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


class GitEffect(_PlanModel):
    """One typed, permission-bounded Git ref transaction."""

    id: str = Field(min_length=1)
    plan_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    updates: dict[str, GitRefUpdate] = Field(min_length=1)
    assertions: dict[str, str] = Field(default_factory=dict)

    @property
    def permissions(self) -> tuple[str, ...]:
        """Derive the exact permission set from the mutated refs."""
        return tuple(f"git.ref.update:{ref}" for ref in self.updates)

    @model_validator(mode="after")
    def bind_permissions(self) -> Self:
        refs_valid = all(
            ref.startswith("refs/")
            and not any(char.isspace() or not char.isprintable() for char in ref)
            for ref in (*self.updates, *self.assertions)
        )
        assertions_valid = all(
            len(value) in {40, hashlib.sha256().digest_size * 2}
            and not set(value) - set("0123456789abcdef")
            for value in self.assertions.values()
        )
        if not refs_valid or set(self.assertions) & set(self.updates) or not assertions_valid:
            message = "git_effect_permissions_invalid"
            raise ValueError(message)
        return self

    def digest(self) -> str:
        """Return the deterministic identity of this exact effect content."""
        return hashlib.sha256(_stable_json(self.model_dump(mode="json")).encode()).hexdigest()


def _ordered_ids(nodes: tuple[PlanNode, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    ids = {node.id for node in nodes}
    gaps: list[str] = []
    for node in nodes:
        if node.id in seen:
            duplicates.add(node.id)
        seen.add(node.id)
        gaps.extend(
            f"missing_dependency:{node.id}->{dependency}"
            for dependency in node.depends_on
            if dependency not in ids
        )
    gaps = [*(f"duplicate_node_id:{node_id}" for node_id in sorted(duplicates)), *gaps]
    stable = tuple(sorted(node.id for node in nodes))
    if gaps:
        return stable, tuple(dict.fromkeys(gaps))
    sorter = TopologicalSorter(
        {
            node.id: tuple(sorted(node.depends_on))
            for node in sorted(nodes, key=lambda item: item.id)
        }
    )
    try:
        ordered = tuple(sorter.static_order())
    except CycleError:
        return stable, ("cycle_detected",)
    return ordered, ()


class TransitionPlan(_PlanModel):
    """Hashable transient plan; it owns no repository truth or mutation."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        title="ETHOS TransitionPlan",
        json_schema_serialization_defaults_required=True,
    )

    commitment_digest: str = Field(pattern=r"^[a-f0-9]{64}$", exclude=True)
    facts_digest: str = Field(pattern=r"^[a-f0-9]{64}$", exclude=True)
    policy_digest: str = Field(pattern=r"^[a-f0-9]{64}$", exclude=True)
    permissions: tuple[str, ...] = Field(default=(), json_schema_extra={"uniqueItems": True})
    facts: dict[str, Any] = Field(default_factory=dict)
    nodes: tuple[PlanNode, ...] = ()
    initial_verdict: PlanVerdict = Field(default="pass", exclude=True)
    validation_issues: tuple[str, ...] = Field(default=(), exclude=True)

    @computed_field
    @property
    def schema_version(self) -> Literal[1]:
        return 1

    @computed_field
    @property
    def inputs(self) -> PlanInputs:
        return PlanInputs(
            commitment=self.commitment_digest,
            facts=self.facts_digest,
            policy=self.policy_digest,
        )

    def gaps(self) -> tuple[str, ...]:
        _, gaps = _ordered_ids(self.nodes)
        return tuple(dict.fromkeys((*self.validation_issues, *gaps)))

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"

    @computed_field
    @property
    def verdict(self) -> PlanVerdict:
        """Return the closed transition verdict; hard gaps always block."""
        return "block" if self.gaps() else self.initial_verdict

    @computed_field(alias="required_gaps")
    @property
    def public_gaps(self) -> tuple[str, ...]:
        return self.gaps()

    @computed_field(alias="digest")
    @property
    def public_digest(self) -> Digest:
        return self.digest()

    def ordered_nodes(self) -> tuple[PlanNode, ...]:
        ordered, _ = _ordered_ids(self.nodes)
        by_id = {node.id: node for node in self.nodes}
        return tuple(by_id[node_id] for node_id in ordered if node_id in by_id)

    @field_serializer("nodes", when_used="json")
    def serialize_nodes(self, _: tuple[PlanNode, ...]) -> tuple[PlanNode, ...]:
        return self.ordered_nodes()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    def digest(self) -> str:
        payload: dict[str, Any] = {
            "inputs": {
                "commitment": self.commitment_digest,
                "facts": self.facts_digest,
                "policy": self.policy_digest,
            },
            "permissions": sorted(self.permissions),
            "facts": self.facts,
            "nodes": [node.normalized() for node in self.ordered_nodes()],
        }
        if self.initial_verdict != "pass":
            payload["initial_verdict"] = self.initial_verdict
        if self.validation_issues:
            payload["validation_issues"] = list(self.validation_issues)
        return hashlib.sha256(_stable_json(payload).encode()).hexdigest()


def compile_plan(
    commitment: Commitment,
    facts: Facts,
    nodes: tuple[PlanNode, ...],
    *,
    policy_digest: str,
    validation_issues: tuple[str, ...] = (),
) -> TransitionPlan:
    """Compile one effective commitment and current fact snapshot into TransitionPlan."""
    issues = list(validation_issues)
    if commitment.subjects and facts.repository not in commitment.subjects:
        issues.append("repository_subject_mismatch")
    if commitment.scope:
        changed_paths = facts.values.get("changed_paths", ())
        if not isinstance(changed_paths, tuple | list) or any(
            not _valid_relative_path(path) for path in changed_paths
        ):
            issues.append("changed_paths_invalid")
        elif any(
            not any(_path_matches(path, pattern) for pattern in commitment.scope)
            for path in changed_paths
            if isinstance(path, str)
        ):
            issues.append("change_scope_exceeded")
    return TransitionPlan(
        commitment_digest=commitment.digest(),
        facts_digest=facts.digest(),
        policy_digest=policy_digest,
        permissions=commitment.permissions,
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=nodes,
        validation_issues=tuple(dict.fromkeys(issues)),
    )


def terminal_schema_documents() -> dict[str, dict[str, Any]]:
    """Generate the language-neutral terminal contracts from their model owners."""
    contracts = {
        "commitment.schema.json": Commitment,
        "attestation.schema.json": Attestation,
        "facts.schema.json": Facts,
        "transition-plan.schema.json": TransitionPlan,
    }
    schemas: dict[str, dict[str, Any]] = {}
    for name, model in contracts.items():
        schema = model.model_json_schema(mode="serialization", by_alias=True)
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://ethos.local/schemas/{name}"
        schema["title"] = f"ETHOS {model.__name__.removesuffix('Document')}"
        schemas[name] = schema
    return schemas


def _path_matches(path: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    prefix = pattern.removesuffix("/**")
    if pattern.endswith("/**"):
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def _valid_relative_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and "\\" not in path
        and not PurePosixPath(path).is_absolute()
        and ".." not in PurePosixPath(path).parts
    )

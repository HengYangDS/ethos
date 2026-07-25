"""Transient, deterministic PlanIR compiled from repository declarations."""

from __future__ import annotations

import hashlib
import json
from graphlib import CycleError
from graphlib import TopologicalSorter
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

if TYPE_CHECKING:
    from ethos.contracts.semantic import ChangeContract
    from ethos.contracts.semantic import RepositoryFacts

PlanVerdict = Literal["pass", "block", "unknown"]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class _PlanModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class PlanNode(_PlanModel):
    """One pure Check, Decision, or Effect description."""

    id: str
    kind: Literal["check", "decision", "effect"]
    command: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()

    def normalized(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "command": list(self.command),
            "depends_on": sorted(self.depends_on),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.normalized()


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
            ref.startswith("refs/") and not any(char.isspace() or ord(char) < 32 for char in ref)
            for ref in (*self.updates, *self.assertions)
        )
        assertions_valid = all(
            len(value) in {40, 64} and not set(value) - set("0123456789abcdef")
            for value in self.assertions.values()
        )
        if not refs_valid or set(self.assertions) & set(self.updates) or not assertions_valid:
            raise ValueError("git_effect_permissions_invalid")
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


class PlanIR(_PlanModel):
    """Hashable transient plan; it owns no repository truth or mutation."""

    nodes: tuple[PlanNode, ...] = ()
    initial_verdict: PlanVerdict = "pass"
    validation_issues: tuple[str, ...] = ()

    def gaps(self) -> tuple[str, ...]:
        _, gaps = _ordered_ids(self.nodes)
        return tuple(dict.fromkeys((*self.validation_issues, *gaps)))

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"

    @property
    def verdict(self) -> PlanVerdict:
        """Return the closed transition verdict; hard gaps always block."""
        return "block" if self.gaps() else self.initial_verdict

    def ordered_nodes(self) -> tuple[PlanNode, ...]:
        ordered, _ = _ordered_ids(self.nodes)
        by_id = {node.id: node for node in self.nodes}
        return tuple(by_id[node_id] for node_id in ordered if node_id in by_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "nodes": [node.to_dict() for node in self.ordered_nodes()],
            "verdict": self.verdict,
            "required_gaps": list(self.gaps()),
            "digest": self.digest(),
        }

    def digest(self) -> str:
        payload: dict[str, Any] = {"nodes": [node.normalized() for node in self.ordered_nodes()]}
        if self.initial_verdict != "pass":
            payload["initial_verdict"] = self.initial_verdict
        if self.validation_issues:
            payload["validation_issues"] = list(self.validation_issues)
        return hashlib.sha256(_stable_json(payload).encode()).hexdigest()


def compile_plan(
    contract: ChangeContract,
    facts: RepositoryFacts,
    nodes: tuple[PlanNode, ...],
    *,
    validation_issues: tuple[str, ...] = (),
) -> PlanIR:
    """Compile one effective contract and current fact snapshot into PlanIR."""
    issues = list(validation_issues)
    if contract.subjects and facts.repository not in contract.subjects:
        issues.append("repository_subject_mismatch")
    if contract.scope:
        changed_paths = facts.values.get("changed_paths", ())
        if not isinstance(changed_paths, tuple | list):
            issues.append("changed_paths_invalid")
        elif any(
            not any(_path_matches(path, pattern) for pattern in contract.scope)
            for path in changed_paths
            if isinstance(path, str)
        ):
            issues.append("change_scope_exceeded")
    return PlanIR(nodes=nodes, validation_issues=tuple(dict.fromkeys(issues)))


def _path_matches(path: str, pattern: str) -> bool:
    prefix = pattern.removesuffix("/**")
    return path == prefix or (pattern.endswith("/**") and path.startswith(f"{prefix}/"))

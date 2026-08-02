"""Transient, deterministic TransitionPlan compiled from repository declarations."""

import fnmatch
import hashlib
from datetime import UTC
from datetime import datetime
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
from pydantic import model_validator

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import FrozenMapping
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
EMPTY_ATTESTATION_SET_DIGEST = canonical_json_digest({})


class _PlanModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
    )


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
    command: FrozenTuple[str] = ()
    depends_on: FrozenTuple[str] = Field(default=(), json_schema_extra={"uniqueItems": True})


class PlanInputs(_PlanModel):
    """Exact inputs bound by one public TransitionPlan projection."""

    commitment: Digest
    facts: Digest
    prior_attestations: Digest = EMPTY_ATTESTATION_SET_DIGEST
    policy: Digest
    effect: Digest


class GitRefUpdate(_PlanModel):
    """One exact compare-and-swap ref transition."""

    expected: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    desired: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


class GitEffect(_PlanModel):
    """One typed, permission-bounded Git ref transaction."""

    updates: FrozenMapping[GitRefUpdate] = Field(min_length=1)
    assertions: FrozenMapping[str] = Field(default_factory=dict)

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
        """Return the identity of the exact canonical update-ref program bytes."""
        return hashlib.sha256(self.program()).hexdigest()

    def program(self) -> bytes:
        """Render the exact deterministic update-ref transaction program."""
        return "\0".join(
            (
                "start",
                *(
                    token
                    for ref in sorted(self.assertions)
                    for token in (f"update {ref}", self.assertions[ref], self.assertions[ref])
                ),
                *(
                    token
                    for ref in sorted(self.updates)
                    for token in (
                        f"update {ref}",
                        self.updates[ref].desired,
                        self.updates[ref].expected,
                    )
                ),
                "prepare",
                "commit",
                "",
            )
        ).encode()


class TransitionPlan(_PlanModel):
    """Hashable transient plan; it owns no repository truth or mutation."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        title="ETHOS TransitionPlan",
        json_schema_serialization_defaults_required=True,
    )

    schema_version: Literal[1] = Field(default=1, json_schema_extra={"readOnly": True})
    inputs: PlanInputs = Field(json_schema_extra={"readOnly": True})
    commitment: JsonObject
    prior_attestations: JsonObject
    policy: JsonObject
    effect: JsonObject
    permissions: FrozenTuple[str] = Field(default=(), json_schema_extra={"uniqueItems": True})
    facts: JsonObject = Field(default_factory=dict)
    nodes: FrozenTuple[PlanNode] = ()
    verdict: Verdict = Field(json_schema_extra={"readOnly": True})
    required_gaps: FrozenTuple[str] = Field(json_schema_extra={"readOnly": True})
    digest: Digest = Field(json_schema_extra={"readOnly": True})

    @staticmethod
    def _resolve_nodes(
        nodes: tuple[PlanNode, ...], selected: tuple[str, ...] | None = None
    ) -> tuple[tuple[PlanNode, ...], tuple[str, ...]]:
        duplicates: set[str] = set()
        by_id: dict[str, PlanNode] = {}
        normalized = tuple(
            node.model_copy(update={"depends_on": tuple(sorted(set(node.depends_on)))})
            for node in nodes
        )
        for node in normalized:
            if node.id in by_id:
                duplicates.add(node.id)
            by_id[node.id] = node
        gaps = [f"duplicate_node_id:{node_id}" for node_id in sorted(duplicates)]
        required = set(by_id if selected is None else selected)
        pending = list(required)
        while pending:
            node_id = pending.pop()
            node = by_id.get(node_id)
            if node is None:
                gaps.append(f"missing_node:{node_id}")
                continue
            for dependency in node.depends_on:
                if dependency not in by_id:
                    gaps.append(f"missing_dependency:{node.id}->{dependency}")
                elif dependency not in required:
                    required.add(dependency)
                    pending.append(dependency)
        selected_nodes = tuple(node for node in normalized if node.id in required)
        stable = tuple(
            sorted(
                selected_nodes,
                key=lambda node: (node.id, node.kind, node.command, node.depends_on),
            )
        )
        if gaps:
            return stable, tuple(dict.fromkeys(gaps))
        sorter = TopologicalSorter(
            {
                node.id: tuple(sorted(node.depends_on))
                for node in sorted(selected_nodes, key=lambda item: item.id)
            }
        )
        try:
            order = tuple(sorter.static_order())
        except CycleError:
            return stable, ("cycle_detected",)
        return tuple(by_id[node_id] for node_id in order), ()

    @classmethod
    def closure(
        cls, nodes: tuple[PlanNode, ...], selected: tuple[str, ...] | None = None
    ) -> tuple[PlanNode, ...]:
        """Return one dependency-complete canonical DAG closure."""
        ordered, gaps = cls._resolve_nodes(nodes, selected)
        if gaps:
            raise ValueError(gaps[0])
        return ordered

    @classmethod
    def compile(
        cls,
        *,
        inputs: PlanInputs,
        closure: JsonObject,
        permissions: tuple[str, ...] = (),
        facts: JsonObject,
        nodes: tuple[PlanNode, ...] = (),
        verdict: Verdict = "pass",
        required_gaps: tuple[str, ...] = (),
    ) -> Self:
        """Compile one canonical immutable DAG projection from exact inputs."""
        ordered, graph_gaps = cls._resolve_nodes(nodes)
        gaps = tuple(dict.fromkeys((*required_gaps, *graph_gaps)))
        carried = mutable_json(closure)
        if not isinstance(carried, dict) or set(carried) != {
            "commitment",
            "prior_attestations",
            "policy",
            "effect",
        }:
            message = "transition_plan_closure_invalid"
            raise ValueError(message)
        carried = {str(name): value for name, value in carried.items()}
        payload: dict[str, Any] = {
            "schema_version": 1,
            "inputs": inputs.model_dump(mode="json"),
            "commitment": carried["commitment"],
            "prior_attestations": carried["prior_attestations"],
            "policy": carried["policy"],
            "effect": carried["effect"],
            "permissions": sorted(set(permissions)),
            "facts": mutable_json(facts),
            "nodes": [node.model_dump(mode="json") for node in ordered],
            "verdict": close_verdict(verdict, gaps),
            "required_gaps": list(gaps),
        }
        return cls.model_validate(payload | {"digest": canonical_json_digest(payload)})

    @model_validator(mode="after")
    def validate_canonical_projection(self) -> Self:
        """Reject noncanonical order, open verdicts, graph gaps, or stale identity."""
        ordered, graph_gaps = self._resolve_nodes(self.nodes)
        if ordered != self.nodes or any(gap not in self.required_gaps for gap in graph_gaps):
            message = "transition_plan_graph_invalid"
            raise ValueError(message)
        if close_verdict(self.verdict, self.required_gaps) != self.verdict:
            message = "transition_plan_verdict_invalid"
            raise ValueError(message)
        fact_values = mutable_json(self.facts)
        if not isinstance(fact_values, dict):
            message = "transition_plan_facts_invalid"
            raise TypeError(message)
        try:
            commitment = Commitment.model_validate(mutable_json(self.commitment), strict=False)
            facts = Facts.model_validate(
                {
                    **{str(name): value for name, value in fact_values.items()},
                    "observed_at": datetime(1970, 1, 1, tzinfo=UTC),
                },
                strict=False,
            )
            effect_digest = (
                GitEffect.model_validate(mutable_json(self.effect), strict=False).digest()
                if self.nodes
                == (
                    PlanNode(
                        id="git.ref.compare-and-swap",
                        kind="effect",
                        command=("git", "update-ref", "--stdin", "-z"),
                    ),
                )
                else canonical_json_digest(self.effect)
            )
        except (TypeError, ValueError) as error:
            message = "transition_plan_closure_invalid"
            raise ValueError(message) from error
        if self.inputs != PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(self.prior_attestations),
            policy=canonical_json_digest(self.policy),
            effect=effect_digest,
        ) or self.permissions != tuple(sorted(set(commitment.permissions))):
            message = "transition_plan_closure_mismatch"
            raise ValueError(message)
        payload = self.model_dump(mode="json", exclude={"digest"})
        if self.digest != canonical_json_digest(payload):
            message = "transition_plan_digest_mismatch"
            raise ValueError(message)
        return self


def compile_git_effect_plan(
    commitment: Commitment,
    facts: Facts,
    *,
    prior_attestations: JsonObject,
    policy: JsonObject,
    effect: GitEffect,
) -> TransitionPlan:
    """Compile one self-contained plan around one exact Git CAS effect."""
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(prior_attestations),
            policy=canonical_json_digest(policy),
            effect=effect.digest(),
        ),
        closure={
            "commitment": commitment.identity_projection(),
            "prior_attestations": prior_attestations,
            "policy": policy,
            "effect": effect.model_dump(mode="json"),
        },
        permissions=commitment.permissions,
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=(
            PlanNode(
                id="git.ref.compare-and-swap",
                kind="effect",
                command=("git", "update-ref", "--stdin", "-z"),
            ),
        ),
    )


def git_effect_from_plan(plan: TransitionPlan) -> GitEffect:
    """Return the exact Git effect after validating its carried plan closure."""
    try:
        validated = TransitionPlan.model_validate(plan.model_dump(mode="json"))
        effect = GitEffect.model_validate(mutable_json(validated.effect), strict=False)
    except (TypeError, ValueError) as error:
        message = (
            "git_effect_plan_mismatch"
            if "transition_plan_closure_mismatch" in str(error)
            or "transition_plan_digest_mismatch" in str(error)
            else "git_effect_plan_invalid"
        )
        raise ValueError(message) from error
    if validated.nodes != (
        PlanNode(
            id="git.ref.compare-and-swap",
            kind="effect",
            command=("git", "update-ref", "--stdin", "-z"),
        ),
    ):
        message = "git_effect_plan_mismatch"
        raise ValueError(message)
    if validated.verdict != "pass":
        message = "git_effect_plan_not_admitted"
        raise ValueError(message)
    return effect


def compile_plan(
    commitment: Commitment,
    facts: Facts,
    nodes: tuple[PlanNode, ...],
    *,
    policy: JsonObject,
    required_gaps: tuple[str, ...] = (),
) -> TransitionPlan:
    """Compile one effective commitment and current fact snapshot into TransitionPlan."""
    gaps = list(required_gaps)
    if commitment.subjects and facts.repository not in commitment.subjects:
        gaps.append("repository_subject_mismatch")
    if commitment.scope:
        changed_paths = facts.values.get("changed_paths", ())
        if not isinstance(changed_paths, tuple | list) or any(
            not _valid_relative_path(path) for path in changed_paths
        ):
            gaps.append("changed_paths_invalid")
        elif any(
            not any(_path_matches(path, pattern) for pattern in commitment.scope)
            for path in changed_paths
            if isinstance(path, str)
        ):
            gaps.append("change_scope_exceeded")
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=EMPTY_ATTESTATION_SET_DIGEST,
            policy=canonical_json_digest(policy),
            effect=proof_effect_digest(
                commitment=commitment.digest(),
                facts=facts.digest(),
                policy=canonical_json_digest(policy),
                nodes=nodes,
            ),
        ),
        closure={
            "commitment": commitment.identity_projection(),
            "prior_attestations": {},
            "policy": policy,
            "effect": proof_effect_projection(
                commitment=commitment.digest(),
                facts=facts.digest(),
                policy=canonical_json_digest(policy),
                nodes=nodes,
            ),
        },
        permissions=commitment.permissions,
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=nodes,
        required_gaps=tuple(dict.fromkeys(gaps)),
    )


def proof_effect_digest(
    *, commitment: str, facts: str, policy: str, nodes: tuple[PlanNode, ...]
) -> str:
    """Return the canonical identity of one proof execution closure."""
    return canonical_json_digest(
        proof_effect_projection(
            commitment=commitment,
            facts=facts,
            policy=policy,
            nodes=nodes,
        )
    )


def proof_effect_projection(
    *, commitment: str, facts: str, policy: str, nodes: tuple[PlanNode, ...]
) -> JsonObject:
    """Return the exact proof operation carried by its TransitionPlan."""
    ordered = TransitionPlan.closure(nodes)
    return {
        "operation": "proof.execute",
        "commitment": commitment,
        "facts": facts,
        "policy": policy,
        "nodes": [node.model_dump(mode="json") for node in ordered],
    }


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

"""Transient, deterministic TransitionPlan compiled from repository declarations."""

import hashlib
from datetime import UTC
from datetime import datetime
from graphlib import CycleError
from graphlib import TopologicalSorter
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.proof.plan import commitment_fact_gaps
from ethos.contracts.proof.plan import validate_proof_plan
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


def dependency_cycle(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return the stable members of one dependency cycle, or an empty tuple."""
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as error:
        return tuple(sorted(set(error.args[1])))
    return ()


def dependency_order(graph: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Return one stable topological order or raise on a dependency cycle."""
    if dependency_cycle(graph):
        message = "cycle_detected"
        raise ValueError(message)
    return tuple(TopologicalSorter(graph).static_order())


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
    """Canonical immutable receipt for one exact repository transition."""

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        title="ETHOS TransitionPlan",
        json_schema_serialization_defaults_required=True,
    )

    schema_version: Literal[1] = Field(default=1, json_schema_extra={"readOnly": True})
    inputs: PlanInputs = Field(json_schema_extra={"readOnly": True})
    request: JsonObject
    authority: JsonObject
    commitment: JsonObject
    prior_attestations: JsonObject
    policy: JsonObject
    effect: JsonObject
    facts: JsonObject = Field(default_factory=dict)
    nodes: FrozenTuple[PlanNode] = ()
    compensations: FrozenTuple[PlanNode] = ()
    postconditions: FrozenTuple[PlanNode] = ()
    verdict: Verdict = Field(json_schema_extra={"readOnly": True})
    required_gaps: FrozenTuple[str] = Field(json_schema_extra={"readOnly": True})
    continuation: JsonObject | None = None
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
        graph = {
            node.id: tuple(sorted(node.depends_on))
            for node in sorted(selected_nodes, key=lambda item: item.id)
        }
        if dependency_cycle(graph):
            return stable, ("cycle_detected",)
        order = dependency_order(graph)
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
        facts: JsonObject,
        nodes: tuple[PlanNode, ...] = (),
        compensations: tuple[PlanNode, ...] = (),
        postconditions: tuple[PlanNode, ...] = (),
        verdict: Verdict = "pass",
        required_gaps: tuple[str, ...] = (),
    ) -> Self:
        """Compile one canonical immutable transition receipt from exact inputs."""
        ordered, graph_gaps = cls._resolve_nodes(nodes)
        ordered_compensations, compensation_gaps = cls._resolve_nodes(compensations)
        ordered_postconditions, postcondition_gaps = cls._resolve_nodes(postconditions)
        gaps = tuple(
            dict.fromkeys((*required_gaps, *graph_gaps, *compensation_gaps, *postcondition_gaps))
        )
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
        request, authority = cls._operation_bindings(inputs, carried, facts)
        payload: dict[str, Any] = {
            "schema_version": 1,
            "inputs": inputs.model_dump(mode="json"),
            "request": request,
            "authority": authority,
            "commitment": carried["commitment"],
            "prior_attestations": carried["prior_attestations"],
            "policy": carried["policy"],
            "effect": carried["effect"],
            "facts": mutable_json(facts),
            "nodes": [node.model_dump(mode="json") for node in ordered],
            "compensations": [node.model_dump(mode="json") for node in ordered_compensations],
            "postconditions": [node.model_dump(mode="json") for node in ordered_postconditions],
            "verdict": close_verdict(verdict, gaps),
            "required_gaps": list(gaps),
            "continuation": (
                {"kind": "user-decision", "required_gaps": list(gaps)} if gaps else None
            ),
        }
        return cls.model_validate(payload | {"digest": canonical_json_digest(payload)})

    @staticmethod
    def _operation_bindings(
        inputs: PlanInputs, closure: dict[str, object], facts: JsonObject
    ) -> tuple[dict[str, object], dict[str, object]]:
        """Derive request and exact authority from the already-bound closure."""
        commitment = Commitment.model_validate(closure["commitment"], strict=False)
        fact_value = mutable_json(facts)
        policy = mutable_json(closure["policy"])
        if not isinstance(fact_value, dict) or not isinstance(policy, dict):
            message = "transition_plan_closure_invalid"
            raise TypeError(message)
        operation = str(policy.get("transition") or policy.get("operation") or "transition")
        effect_digest = inputs.effect
        request = {
            "operation": operation,
            "repository": str(fact_value.get("repository") or ""),
            "subject": commitment.id,
            "head": str(fact_value.get("head") or ""),
            "tree": str(fact_value.get("tree") or ""),
            "effect_digest": effect_digest,
        }
        authority = {
            "operation": operation,
            "actor": str(policy.get("actor") or ""),
            "subject": commitment.id,
            "commitment_digest": inputs.commitment,
            "facts_digest": inputs.facts,
            "policy_digest": inputs.policy,
            "effect_digest": effect_digest,
        }
        return request, authority

    @model_validator(mode="after")
    def validate_canonical_projection(self) -> Self:
        """Reject noncanonical order, open verdicts, graph gaps, or stale identity."""
        ordered, graph_gaps = self._resolve_nodes(self.nodes)
        compensations, compensation_gaps = self._resolve_nodes(self.compensations)
        postconditions, postcondition_gaps = self._resolve_nodes(self.postconditions)
        if (
            ordered != self.nodes
            or compensations != self.compensations
            or postconditions != self.postconditions
            or any(
                gap not in self.required_gaps
                for gap in (*graph_gaps, *compensation_gaps, *postcondition_gaps)
            )
        ):
            message = "transition_plan_graph_invalid"
            raise ValueError(message)
        if close_verdict(self.verdict, self.required_gaps) != self.verdict:
            message = "transition_plan_verdict_invalid"
            raise ValueError(message)
        expected_continuation = (
            {"kind": "user-decision", "required_gaps": list(self.required_gaps)}
            if self.required_gaps
            else None
        )
        if mutable_json(self.continuation) != expected_continuation:
            message = "transition_plan_continuation_invalid"
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
        validate_proof_plan(self, commitment, facts)
        if self.inputs != PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(self.prior_attestations),
            policy=canonical_json_digest(self.policy),
            effect=effect_digest,
        ):
            message = "transition_plan_closure_mismatch"
            raise ValueError(message)
        request, authority = self._operation_bindings(
            self.inputs,
            {
                "commitment": mutable_json(self.commitment),
                "prior_attestations": mutable_json(self.prior_attestations),
                "policy": mutable_json(self.policy),
                "effect": mutable_json(self.effect),
            },
            mutable_json(self.facts),
        )
        if mutable_json(self.request) != request or mutable_json(self.authority) != authority:
            message = "transition_plan_operation_binding_mismatch"
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
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=(
            PlanNode(
                id="git.ref.compare-and-swap",
                kind="effect",
                command=("git", "update-ref", "--stdin", "-z"),
            ),
        ),
        compensations=(
            PlanNode(
                id="git.ref.compare-and-swap.compensate",
                kind="effect",
                command=("git", "update-ref", "--stdin", "-z"),
            ),
        ),
        postconditions=(
            PlanNode(
                id="git.ref.compare-and-swap.observe",
                kind="check",
                command=("git", "show-ref", "--verify"),
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
    if (
        validated.nodes
        != (
            PlanNode(
                id="git.ref.compare-and-swap",
                kind="effect",
                command=("git", "update-ref", "--stdin", "-z"),
            ),
        )
        or validated.compensations
        != (
            PlanNode(
                id="git.ref.compare-and-swap.compensate",
                kind="effect",
                command=("git", "update-ref", "--stdin", "-z"),
            ),
        )
        or validated.postconditions
        != (
            PlanNode(
                id="git.ref.compare-and-swap.observe",
                kind="check",
                command=("git", "show-ref", "--verify"),
            ),
        )
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
    prior_attestations: JsonObject | None = None,
    required_gaps: tuple[str, ...] = (),
) -> TransitionPlan:
    """Compile one effective commitment and current fact snapshot into TransitionPlan."""
    attestations = prior_attestations or {}
    gaps = [*required_gaps, *commitment_fact_gaps(commitment, facts, attestations)]
    return TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment.digest(),
            facts=facts.digest(),
            prior_attestations=canonical_json_digest(attestations),
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
            "prior_attestations": attestations,
            "policy": policy,
            "effect": proof_effect_projection(
                commitment=commitment.digest(),
                facts=facts.digest(),
                policy=canonical_json_digest(policy),
                nodes=nodes,
            ),
        },
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

"""Immutable operation declarations and the pure transition receipt reducer."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Annotated
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.policy.cel import CelEvaluationError
from ethos.contracts.policy.cel import evaluate_cel_predicate
from ethos.contracts.policy.cel import validate_cel_expression
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class _OperationModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
        json_schema_serialization_defaults_required=True,
    )


class OperationAction(_OperationModel):
    """One declared adapter action with immutable portable inputs."""

    id: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    payload: JsonObject = Field(default_factory=dict)


class OperationContinuation(_OperationModel):
    """The sole public continuation for a blocked or partial transition."""

    kind: Literal["resume", "compensate", "user-decision"]
    command: FrozenTuple[str] = Field(min_length=1)


class AuthorityRule(_OperationModel):
    """One declaration-owned CEL predicate for operation authority."""

    id: str = Field(min_length=1)
    expression: str = Field(min_length=1)
    gap: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_expression(self) -> Self:
        validate_cel_expression(self.expression)
        return self


class OperationDeclaration(_OperationModel):
    """Tracked, adopter-neutral declaration for one public operation."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    authority_rules: FrozenTuple[AuthorityRule]
    preconditions: FrozenTuple[OperationAction] = ()
    effects: FrozenTuple[OperationAction] = Field(min_length=1)
    compensations: FrozenTuple[OperationAction] = ()
    postconditions: FrozenTuple[OperationAction] = Field(min_length=1)
    blocked: OperationContinuation

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.id != f"operation:{self.operation}":
            message = "operation_declaration_identity_mismatch"
            raise ValueError(message)
        ids = tuple(
            item.id
            for item in (
                *self.authority_rules,
                *self.preconditions,
                *self.effects,
                *self.compensations,
                *self.postconditions,
            )
        )
        if len(ids) != len(set(ids)):
            message = "operation_declaration_id_duplicate"
            raise ValueError(message)
        return self

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class OperationRequest(_OperationModel):
    """Context-independent request naming every authoritative coordinate."""

    schema_version: Literal[1] = 1
    operation: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    coordinates: JsonObject
    effect: JsonObject

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))


class OperationInputs(_OperationModel):
    """Canonical identities of every reducer input."""

    request: Digest
    commitment: Digest
    facts: Digest
    prior_attestations: Digest
    declaration: Digest
    effect: Digest


class OperationAuthority(_OperationModel):
    """Authority derived for one exact operation and effect only."""

    operation: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    commitment_digest: Digest
    facts_digest: Digest
    declaration_digest: Digest
    effect_digest: Digest
    rule_ids: FrozenTuple[str]


class TransitionReceipt(_OperationModel):
    """Canonical immutable output of the pure operation reducer."""

    schema_version: Literal[1] = 1
    request: OperationRequest
    inputs: OperationInputs
    authority: OperationAuthority
    preconditions: FrozenTuple[OperationAction]
    effects: FrozenTuple[OperationAction]
    compensations: FrozenTuple[OperationAction]
    postconditions: FrozenTuple[OperationAction]
    verdict: Verdict
    required_gaps: FrozenTuple[str]
    continuation: OperationContinuation | None = None
    digest: Digest

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @model_validator(mode="after")
    def validate_canonical_receipt(self) -> Self:
        if self.required_gaps != tuple(sorted(set(self.required_gaps))):
            message = "transition_receipt_gaps_not_canonical"
            raise ValueError(message)
        if close_verdict(self.verdict, self.required_gaps) != self.verdict:
            message = "transition_receipt_verdict_invalid"
            raise ValueError(message)
        if (self.verdict == "pass") != (self.continuation is None):
            message = "transition_receipt_continuation_invalid"
            raise ValueError(message)
        payload = self.model_dump(mode="json", exclude={"digest"})
        if self.digest != canonical_json_digest(payload):
            message = "transition_receipt_digest_mismatch"
            raise ValueError(message)
        return self


class OperationResult(_OperationModel):
    """Closed public execution result for one immutable receipt."""

    verdict: Verdict
    state: Literal["ready", "applied", "partial", "blocked", "done"]
    required_gaps: FrozenTuple[str]
    receipt_digest: Digest
    attestation_id: Digest | None = None
    continuation: OperationContinuation | None = None

    @model_validator(mode="after")
    def validate_closed_result(self) -> Self:
        if close_verdict(self.verdict, self.required_gaps) != self.verdict:
            message = "operation_result_verdict_invalid"
            raise ValueError(message)
        if self.state == "partial" and self.continuation is None:
            message = "operation_result_partial_continuation_missing"
            raise ValueError(message)
        if self.state in {"applied", "done"} and self.attestation_id is None:
            message = "operation_result_terminal_attestation_missing"
            raise ValueError(message)
        if self.state != "partial" and self.continuation is not None:
            message = "operation_result_continuation_invalid"
            raise ValueError(message)
        return self


def reduce_operation(
    *,
    request: OperationRequest,
    commitment: Commitment,
    facts: Facts,
    prior_attestations: JsonObject | dict[str, Attestation],
    declaration: OperationDeclaration,
) -> TransitionReceipt:
    """Purely reduce exact immutable inputs into one canonical transition receipt."""
    prior = mutable_json(prior_attestations)
    if not isinstance(prior, dict):
        message = "operation_prior_attestations_invalid"
        raise TypeError(message)
    effect_digest = canonical_json_digest(request.effect)
    inputs = OperationInputs(
        request=request.digest(),
        commitment=commitment.digest(),
        facts=facts.digest(),
        prior_attestations=canonical_json_digest(prior),
        declaration=declaration.digest(),
        effect=effect_digest,
    )
    gaps = list(_binding_gaps(request, commitment, facts, declaration))
    fact_values = mutable_json(facts.values)
    coordinates = mutable_json(request.coordinates)
    if not isinstance(fact_values, Mapping) or not isinstance(coordinates, Mapping):
        message = "operation_reducer_inputs_invalid"
        raise TypeError(message)
    activation = {
        **{str(key): value for key, value in fact_values.items()},
        "repository": facts.repository,
        "head": facts.head,
        "tree": facts.tree,
    }
    rule = {
        "actor": request.actor,
        "subject": request.subject,
        **{str(key): value for key, value in coordinates.items()},
    }
    for authority_rule in declaration.authority_rules:
        try:
            admitted = evaluate_cel_predicate(
                authority_rule.expression,
                facts=activation,
                policy={},
                rule=rule,
            )
        except (CelEvaluationError, TypeError, ValueError):
            gaps.append(f"operation_authority_unavailable:{authority_rule.id}")
        else:
            if not admitted:
                gaps.append(authority_rule.gap)
    required_gaps = tuple(sorted(set(gaps)))
    verdict: Verdict = close_verdict("pass", required_gaps)
    authority = OperationAuthority(
        operation=request.operation,
        actor=request.actor,
        subject=request.subject,
        commitment_digest=commitment.digest(),
        facts_digest=facts.digest(),
        declaration_digest=declaration.digest(),
        effect_digest=effect_digest,
        rule_ids=tuple(rule.id for rule in declaration.authority_rules),
    )
    payload = {
        "schema_version": 1,
        "request": request.model_dump(mode="json"),
        "inputs": inputs.model_dump(mode="json"),
        "authority": authority.model_dump(mode="json"),
        "preconditions": tuple(item.model_dump(mode="json") for item in declaration.preconditions),
        "effects": tuple(item.model_dump(mode="json") for item in declaration.effects),
        "compensations": tuple(item.model_dump(mode="json") for item in declaration.compensations),
        "postconditions": tuple(
            item.model_dump(mode="json") for item in declaration.postconditions
        ),
        "verdict": verdict,
        "required_gaps": required_gaps,
        "continuation": declaration.blocked.model_dump(mode="json") if required_gaps else None,
    }
    return TransitionReceipt.model_validate(payload | {"digest": canonical_json_digest(payload)})


def _binding_gaps(
    request: OperationRequest,
    commitment: Commitment,
    facts: Facts,
    declaration: OperationDeclaration,
) -> tuple[str, ...]:
    gaps = []
    if request.operation != declaration.operation:
        gaps.append("operation_declaration_mismatch")
    if request.repository != facts.repository:
        gaps.append("operation_repository_mismatch")
    if request.subject not in {commitment.id, *commitment.subjects}:
        gaps.append("operation_subject_mismatch")
    if declaration.source_ref not in commitment.authority_refs:
        gaps.append("operation_declaration_not_authorized")
    return tuple(gaps)

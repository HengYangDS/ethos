"""Pure contextual authority extraction and resolution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from typing import Literal

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

CarrierRole = Literal["native", "projection", "adapter", "fact", "history"]
Verdict = Literal["pass", "block", "unknown"]
_PREDICATE_PATTERN = r"^[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)+$"


class _AuthorityModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class AuthorityQuery(_AuthorityModel):
    """One local authority question; queries are never globally ranked."""

    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1, pattern=_PREDICATE_PATTERN)
    scope: tuple[str, ...] = Field(min_length=1)
    plane: str = Field(min_length=1)
    validity: AwareDatetime
    context: tuple[tuple[str, str], ...] = ()


class CarrierDescriptor(_AuthorityModel):
    """Transient carrier meaning extracted for one exact query."""

    role: CarrierRole
    query: AuthorityQuery
    assertion: Any
    bindings: tuple[tuple[str, str], ...]
    source: str = Field(min_length=1)
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None


class ExtractionResult(_AuthorityModel):
    """Lossless descriptor extraction or an explicit model gap."""

    descriptor: CarrierDescriptor | None = None
    required_gaps: tuple[str, ...] = ()


class AuthorityResolution(_AuthorityModel):
    """Fail-closed result for one contextual authority query."""

    verdict: Verdict
    descriptors: tuple[CarrierDescriptor, ...] = ()
    required_gaps: tuple[str, ...] = ()


def query_from_attestation(
    attestation: object,
    *,
    validity: AwareDatetime,
) -> AuthorityQuery | None:
    """Extract the exact query carried by one Attestation, or preserve a model gap."""
    from ethos.contracts.semantic import Attestation

    if not isinstance(attestation, Attestation):
        return None
    scope = attestation.statement.get("scope")
    plane = attestation.statement.get("plane")
    context = attestation.statement.get("context")
    if (
        not isinstance(scope, list | tuple)
        or not scope
        or not all(isinstance(item, str) and item for item in scope)
        or not isinstance(plane, str)
        or not plane
        or not isinstance(context, Mapping)
        or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in context.items()
        )
    ):
        return None
    return AuthorityQuery(
        subject=attestation.subject,
        predicate=attestation.predicate,
        scope=tuple(scope),
        plane=plane,
        validity=validity,
        context=tuple(sorted(context.items())),
    )


def descriptor_from_attestation(
    attestation: object,
    *,
    validity: AwareDatetime,
) -> ExtractionResult:
    """Extract a fact descriptor from an Attestation without implicit defaults."""
    from ethos.contracts.semantic import Attestation

    if (
        not isinstance(attestation, Attestation)
        or (query := query_from_attestation(attestation, validity=validity)) is None
    ):
        return ExtractionResult(required_gaps=("model_gap",))
    return ExtractionResult(
        descriptor=CarrierDescriptor(
            role="fact",
            query=query,
            assertion=attestation.statement,
            bindings=tuple(
                (name, value)
                for name in (
                    "commitment_digest",
                    "facts_digest",
                    "plan_digest",
                    "policy_digest",
                    "effect_digest",
                )
                if (value := getattr(attestation, name))
            ),
            source=f"attestation:{attestation.id}",
            valid_from=attestation.valid_from or attestation.issued_at,
            valid_until=attestation.valid_until,
        )
    )


def extract_carrier_descriptor(payload: object) -> ExtractionResult:
    """Extract one descriptor without guessing absent authority semantics."""
    if not isinstance(payload, dict):
        return ExtractionResult(required_gaps=("model_gap",))
    try:
        return ExtractionResult(descriptor=CarrierDescriptor.model_validate(payload))
    except (TypeError, ValueError):
        return ExtractionResult(required_gaps=("model_gap",))


def resolve_authority(
    query: AuthorityQuery,
    descriptors: tuple[CarrierDescriptor, ...],
) -> AuthorityResolution:
    """Resolve exact-query authority; ambiguity and missing facts block."""
    relevant = tuple(descriptor for descriptor in descriptors if descriptor.query == query)
    candidates = tuple(
        descriptor
        for descriptor in relevant
        if descriptor.role in {"native", "fact"} and _valid_at(descriptor, query.validity)
    )
    if not candidates:
        return AuthorityResolution(
            verdict="block",
            descriptors=relevant,
            required_gaps=("unknown_required_fact",),
        )
    meanings = {(repr(descriptor.assertion), descriptor.bindings) for descriptor in candidates}
    if len(meanings) > 1:
        return AuthorityResolution(
            verdict="block",
            descriptors=candidates,
            required_gaps=("contradiction",),
        )
    return AuthorityResolution(verdict="pass", descriptors=candidates)


def _valid_at(descriptor: CarrierDescriptor, instant: AwareDatetime) -> bool:
    return not (
        (descriptor.valid_from is not None and instant < descriptor.valid_from)
        or (descriptor.valid_until is not None and instant > descriptor.valid_until)
        or (
            descriptor.role == "fact"
            and descriptor.valid_from is None
            and descriptor.valid_until is None
        )
    )

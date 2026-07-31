"""Pure contextual authority extraction and resolution."""

from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.value import JsonValue
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

CarrierRole = Literal["native", "projection", "adapter", "fact", "history"]
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
    assertion: JsonValue
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

    @model_validator(mode="after")
    def reject_false_pass(self) -> Self:
        require_closed_verdict(self.verdict, self.required_gaps)
        return self


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
            verdict="unknown",
            descriptors=relevant,
            required_gaps=("unknown_required_fact",),
        )
    meanings = {repr(descriptor.assertion) for descriptor in candidates}
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

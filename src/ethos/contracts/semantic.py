"""Persistent Commitment and Attestation envelopes plus transient Facts."""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

if TYPE_CHECKING:
    from pathlib import Path


_KIND_PATTERN = r"^[a-z][a-z0-9-]*(?::[a-z0-9][a-z0-9-]*)+$"
_DIGEST_PATTERN = r"^[a-f0-9]{64}$"
_SEMANTIC_ID_PATTERN = r"^(?:[a-z][a-z0-9-]*(?::[a-z0-9][a-z0-9-]*)+|[a-f0-9]{64})$"
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_SEMANTIC_COLLECTION_DUPLICATE = "semantic_collection_duplicate"
_SEMANTIC_COLLECTION_ORDER_INVALID = "semantic_collection_order_invalid"
_SEMANTIC_INTEGER_OUT_OF_RANGE = "semantic_integer_out_of_range"
_SEMANTIC_JSON_VALUE_INVALID = "semantic_json_value_invalid"
_SEMANTIC_JSON_NONCANONICAL = "semantic_json_noncanonical"
_SEMANTIC_OBJECT_KEY_INVALID = "semantic_object_key_invalid"
_SEMANTIC_OBJECT_KEY_DUPLICATE = "semantic_object_key_duplicate"
_SEMANTIC_STRING_SURROGATE_INVALID = "semantic_string_surrogate_invalid"
_COMMITMENT_DIGEST_INVALID = "commitment_digest_invalid"
_COMMITMENT_HYPOTHESIS_ID_DUPLICATE = "commitment_hypothesis_id_duplicate"
_COMMITMENT_HYPOTHESIS_REFERENCE_MISSING = "commitment_hypothesis_reference_missing"
_COMMITMENT_STRING_VALUE_INVALID = "commitment_string_value_invalid"
_ATTESTATION_BINDING_MISSING = "attestation_binding_missing"
_ATTESTATION_IDENTITY_MISMATCH = "attestation_identity_mismatch"
_ATTESTATION_RELATION_IDENTITY_DUPLICATE = "attestation_relation_identity_duplicate"
_ATTESTATION_VALIDITY_INVALID = "attestation_validity_invalid"


def _utf16_key(value: str) -> bytes:
    try:
        return value.encode("utf-16-be")
    except UnicodeEncodeError as exc:
        raise ValueError(_SEMANTIC_STRING_SURROGATE_INVALID) from exc


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise ValueError(_SEMANTIC_INTEGER_OUT_OF_RANGE)
        return value
    if isinstance(value, str):
        _utf16_key(value)
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError(_SEMANTIC_OBJECT_KEY_INVALID)
        return {key: _canonical_value(value[key]) for key in sorted(value, key=_utf16_key)}
    if isinstance(value, tuple | list):
        return [_canonical_value(item) for item in value]
    raise TypeError(_SEMANTIC_JSON_VALUE_INVALID)


def _canonical_json(value: object) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _reject_json_constant(_value: str) -> object:
    raise ValueError(_SEMANTIC_JSON_VALUE_INVALID)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_SEMANTIC_OBJECT_KEY_DUPLICATE)
        result[key] = value
    return result


def _parse_json(data: str | bytes | bytearray) -> object:
    return json.loads(
        data,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
        parse_float=_reject_json_constant,
    )


def canonical_utc_time(value: datetime) -> str:
    """Project one UTC datetime into the sole canonical ``Z`` representation."""
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(_ATTESTATION_VALIDITY_INVALID)
    fraction = f".{value.microsecond:06d}".rstrip("0") if value.microsecond else ""
    return value.strftime(f"%Y-%m-%dT%H:%M:%S{fraction}Z")


def _validate_canonical_time(value: object) -> object:
    if isinstance(value, datetime):
        canonical_utc_time(value)
        return value
    if not isinstance(value, str):
        raise TypeError(_ATTESTATION_VALIDITY_INVALID)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(_ATTESTATION_VALIDITY_INVALID) from exc
    canonical_utc_time(parsed)
    return parsed


def canonical_json_digest(value: object) -> str:
    """Digest one JSON value after canonical ETHOS normalization."""
    encoded = json.dumps(mutable_json(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class _SemanticModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        strict=True,
        extra="forbid",
    )


class _CanonicalSemanticModel(_SemanticModel):
    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: str | None = None,
        context: object | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        del strict, extra, by_alias, by_name
        try:
            value = cls.model_validate(
                _parse_json(json_data),
                strict=True,
                extra="forbid",
                context=context,
            )
            canonical = value.canonical_json().encode()  # ty: ignore[unresolved-attribute]
        except TypeError as error:
            raise ValueError(str(error)) from error
        raw = json_data.encode() if isinstance(json_data, str) else bytes(json_data)
        if raw != canonical:
            raise ValueError(_SEMANTIC_JSON_NONCANONICAL)
        return value


def _canonical_set[T](values: tuple[T, ...], *, identity) -> tuple[T, ...]:
    identities = tuple(identity(value) for value in values)
    if len(identities) != len(set(identities)):
        raise ValueError(_SEMANTIC_COLLECTION_DUPLICATE)
    if identities != tuple(sorted(identities)):
        raise ValueError(_SEMANTIC_COLLECTION_ORDER_INVALID)
    return values


def _require_nonblank_string(value: str) -> str:
    if not value.strip():
        raise ValueError(_COMMITMENT_STRING_VALUE_INVALID)
    return value


class _DependencyValue(_SemanticModel):
    kind: str = Field(pattern=_KIND_PATTERN)
    target: str = Field(min_length=1)
    attributes: JsonObject

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        return _require_nonblank_string(value)

    @model_validator(mode="after")
    def validate_attributes(self) -> Self:
        _canonical_json(self.attributes)
        return self


class _HypothesisValue(_SemanticModel):
    id: str = Field(pattern=_KIND_PATTERN)
    kind: str = Field(pattern=_KIND_PATTERN)
    body: JsonObject

    @model_validator(mode="after")
    def validate_body(self) -> Self:
        _canonical_json(self.body)
        return self


class _FalsifierValue(_SemanticModel):
    id: str = Field(pattern=_KIND_PATTERN)
    hypothesis_id: str = Field(pattern=_KIND_PATTERN)
    kind: str = Field(pattern=_KIND_PATTERN)
    body: JsonObject

    @model_validator(mode="after")
    def validate_body(self) -> Self:
        _canonical_json(self.body)
        return self


class _ExperimentProtocolValue(_SemanticModel):
    id: str = Field(pattern=_KIND_PATTERN)
    hypothesis_ids: FrozenTuple[str]
    kind: str = Field(pattern=_KIND_PATTERN)
    body: JsonObject

    @field_validator("hypothesis_ids")
    @classmethod
    def validate_hypothesis_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_set(values, identity=lambda value: _canonical_json(value).encode())

    @model_validator(mode="after")
    def validate_body(self) -> Self:
        _canonical_json(self.body)
        return self


class Commitment(_CanonicalSemanticModel):
    """Immutable normative promise for one bounded transition."""

    schema_version: Literal[2]
    id: str = Field(pattern=_KIND_PATTERN)
    intent: str = Field(min_length=1)
    subjects: FrozenTuple[str] = Field(min_length=1)
    scope: FrozenTuple[str]
    invariants: FrozenTuple[str]
    acceptance: FrozenTuple[str]
    risks: FrozenTuple[str]
    authority_refs: FrozenTuple[str]
    predecessors: FrozenTuple[str]
    selected_attestations: FrozenTuple[str]
    dependencies: FrozenTuple[_DependencyValue]
    hypotheses: FrozenTuple[_HypothesisValue]
    falsifiers: FrozenTuple[_FalsifierValue]
    experiment_protocols: FrozenTuple[_ExperimentProtocolValue]

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        return _require_nonblank_string(value)

    @field_validator(
        "subjects",
        "invariants",
        "acceptance",
        "risks",
        "authority_refs",
    )
    @classmethod
    def validate_string_set(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() or value == "repository:self" for value in values):
            raise ValueError(_COMMITMENT_STRING_VALUE_INVALID)
        return _canonical_set(
            values,
            identity=lambda value: _canonical_json(value).encode(),
        )

    @field_validator("predecessors", "selected_attestations")
    @classmethod
    def validate_digest_set(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
            for value in values
        ):
            raise ValueError(_COMMITMENT_DIGEST_INVALID)
        return _canonical_set(values, identity=lambda value: value)

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, scope: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in scope:
            if (
                not pattern.strip()
                or pattern.startswith("/")
                or "\\" in pattern
                or any(part in {"", ".", ".."} for part in PurePosixPath(pattern).parts)
            ):
                msg = "change_scope_invalid"
                raise ValueError(msg)
        return _canonical_set(
            scope,
            identity=lambda value: _canonical_json(value).encode(),
        )

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(
        cls, values: tuple[_DependencyValue, ...]
    ) -> tuple[_DependencyValue, ...]:
        keys = tuple((value.kind, value.target) for value in values)
        if len(keys) != len(set(keys)):
            raise ValueError(_SEMANTIC_COLLECTION_DUPLICATE)
        return _canonical_set(
            values,
            identity=lambda value: (
                value.kind,
                value.target,
                _canonical_json(value.attributes),
            ),
        )

    @field_validator("hypotheses")
    @classmethod
    def validate_hypotheses(
        cls, values: tuple[_HypothesisValue, ...]
    ) -> tuple[_HypothesisValue, ...]:
        ids = tuple(value.id for value in values)
        if len(ids) != len(set(ids)):
            raise ValueError(_COMMITMENT_HYPOTHESIS_ID_DUPLICATE)
        return _canonical_set(
            values,
            identity=lambda value: (value.id, value.kind, _canonical_json(value.body)),
        )

    @field_validator("falsifiers")
    @classmethod
    def validate_falsifiers(
        cls, values: tuple[_FalsifierValue, ...]
    ) -> tuple[_FalsifierValue, ...]:
        ids = tuple(value.id for value in values)
        if len(ids) != len(set(ids)):
            raise ValueError(_SEMANTIC_COLLECTION_DUPLICATE)
        return _canonical_set(
            values,
            identity=lambda value: (
                value.hypothesis_id,
                value.id,
                value.kind,
                _canonical_json(value.body),
            ),
        )

    @field_validator("experiment_protocols")
    @classmethod
    def validate_experiment_protocols(
        cls, values: tuple[_ExperimentProtocolValue, ...]
    ) -> tuple[_ExperimentProtocolValue, ...]:
        ids = tuple(value.id for value in values)
        if len(ids) != len(set(ids)):
            raise ValueError(_SEMANTIC_COLLECTION_DUPLICATE)
        return _canonical_set(
            values,
            identity=lambda value: (
                value.id,
                value.kind,
                _canonical_json(value.hypothesis_ids),
                _canonical_json(value.body),
            ),
        )

    @model_validator(mode="after")
    def validate_hypothesis_references(self) -> Self:
        hypothesis_ids = {value.id for value in self.hypotheses}
        references = {value.hypothesis_id for value in self.falsifiers} | {
            hypothesis_id
            for protocol in self.experiment_protocols
            for hypothesis_id in protocol.hypothesis_ids
        }
        if not references <= hypothesis_ids:
            raise ValueError(_COMMITMENT_HYPOTHESIS_REFERENCE_MISSING)
        return self

    def identity_projection(self) -> dict[str, object]:
        """Return the schema-versioned portable identity projection."""
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return hashlib.sha256(b"ethos.commitment.v2\0" + self.canonical_json().encode()).hexdigest()

    def canonical_json(self) -> str:
        return _canonical_json(self.identity_projection())


def load_commitment_bytes(raw: bytes) -> Commitment:
    """Load one strict Commitment from exact TOML bytes."""
    return Commitment.model_validate(tomllib.loads(raw.decode("utf-8")))


def load_commitment_file(path: Path) -> Commitment:
    """Load one strict Commitment TOML carrier."""
    return load_commitment_bytes(path.read_bytes())


class _AttestationPayload(_SemanticModel):
    kind: str = Field(pattern=_KIND_PATTERN)
    body: JsonObject

    @model_validator(mode="after")
    def validate_body(self) -> Self:
        _canonical_json(self.body)
        return self


class _AttestationRelation(_SemanticModel):
    kind: str = Field(pattern=_KIND_PATTERN)
    target_kind: str = Field(pattern=_KIND_PATTERN)
    target_id: str = Field(pattern=_SEMANTIC_ID_PATTERN)
    attributes: JsonObject

    @model_validator(mode="after")
    def validate_attributes(self) -> Self:
        _canonical_json(self.attributes)
        return self


class Attestation(_CanonicalSemanticModel):
    """Immutable open-predicate input that never mints authority."""

    schema_version: Literal[2]
    id: str = Field(pattern=_DIGEST_PATTERN)
    predicate: str = Field(pattern=_KIND_PATTERN)
    verifier: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    issued_at: AwareDatetime
    valid_from: AwareDatetime | None
    valid_until: AwareDatetime | None
    verdict: Verdict
    payload: _AttestationPayload
    relations: FrozenTuple[_AttestationRelation]
    advisories: FrozenTuple[str]
    evidence_refs: FrozenTuple[str]
    commitment_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    facts_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    plan_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    policy_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    effect_digest: str | None = Field(pattern=_DIGEST_PATTERN)
    mints_authority: Literal[False]

    @field_validator("verifier", "subject")
    @classmethod
    def validate_required_string(cls, value: str) -> str:
        return _require_nonblank_string(value)

    @field_validator("issued_at", "valid_from", "valid_until", mode="before")
    @classmethod
    def validate_time(cls, value: object) -> object:
        return None if value is None else _validate_canonical_time(value)

    @field_validator("advisories", "evidence_refs")
    @classmethod
    def validate_string_set(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError(_COMMITMENT_STRING_VALUE_INVALID)
        return _canonical_set(
            values,
            identity=lambda value: _canonical_json(value).encode(),
        )

    @field_validator("relations")
    @classmethod
    def validate_relations(
        cls, values: tuple[_AttestationRelation, ...]
    ) -> tuple[_AttestationRelation, ...]:
        keys = tuple((value.kind, value.target_kind, value.target_id) for value in values)
        if len(keys) != len(set(keys)):
            raise ValueError(_ATTESTATION_RELATION_IDENTITY_DUPLICATE)
        return _canonical_set(
            values,
            identity=lambda value: (
                value.kind,
                value.target_kind,
                value.target_id,
                _canonical_json(value.attributes),
            ),
        )

    @classmethod
    def issue(cls, payload: Mapping[str, object]) -> Self:
        """Issue one content-addressed Attestation from one semantic payload."""
        if not isinstance(payload, Mapping):
            msg = "attestation_issue_payload_invalid"
            raise TypeError(msg)
        derived = {"id"}
        if invalid := sorted(str(key) for key in payload.keys() & derived):
            message = f"attestation_issue_derived_field:{invalid[0]}"
            raise ValueError(message)
        return cls.model_validate(
            {"id": "0" * 64, **payload},
            context={"issue_attestation": True},
        )

    @model_validator(mode="after")
    def validate_identity(self, info: ValidationInfo) -> Self:
        raw_gaps = self.payload.body.get("required_gaps", ())
        raw_warnings = self.payload.body.get("warnings", ())
        required_gaps = tuple(str(item) for item in raw_gaps) if isinstance(raw_gaps, tuple) else ()
        warnings = (
            tuple(str(item) for item in raw_warnings) if isinstance(raw_warnings, tuple) else ()
        )
        require_closed_verdict(self.verdict, required_gaps, warnings)
        if not any(
            (
                self.commitment_digest,
                self.facts_digest,
                self.plan_digest,
                self.policy_digest,
                self.effect_digest,
                self.evidence_refs,
                self.relations,
            )
        ):
            raise ValueError(_ATTESTATION_BINDING_MISSING)
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError(_ATTESTATION_VALIDITY_INVALID)
        issuing = bool(info.context and info.context.get("issue_attestation"))
        identity = hashlib.sha256(
            b"ethos.attestation.v2\0" + self.canonical_json(exclude_id=True).encode()
        ).hexdigest()
        if not issuing and self.id != identity:
            raise ValueError(_ATTESTATION_IDENTITY_MISMATCH)
        object.__setattr__(self, "id", identity)
        return self

    def identity_projection(self) -> dict[str, object]:
        projection = self.model_dump(mode="json", exclude={"id"})
        projection.update(
            issued_at=canonical_utc_time(self.issued_at),
            valid_from=canonical_utc_time(self.valid_from) if self.valid_from else None,
            valid_until=canonical_utc_time(self.valid_until) if self.valid_until else None,
        )
        return projection

    def canonical_json(self, *, exclude_id: bool = False) -> str:
        projection = self.identity_projection()
        if not exclude_id:
            projection = {"id": self.id, **projection}
        return _canonical_json(projection)

    def digest(self) -> str:
        return self.id


def validate_attestation_selector(
    field: Literal["id", "predicate", "verifier", "subject", "payload_kind"],
    value: str,
) -> str:
    """Validate one non-empty query selector against Attestation field truth."""
    if not value:
        return value
    try:
        if field in {"verifier", "subject"}:
            return Attestation.validate_required_string(value)
        model_field = (
            _AttestationPayload.model_fields["kind"]
            if field == "payload_kind"
            else Attestation.model_fields[field]
        )
        return TypeAdapter(model_field.rebuild_annotation()).validate_python(
            value,
            strict=True,
        )
    except ValueError as error:
        message = f"attestation_selector_invalid:{field}"
        raise ValueError(message) from error


class Facts(_SemanticModel):
    """Fresh observation input; this value is derived and never persisted as truth."""

    schema_version: Literal[1] = 1
    repository: str = Field(min_length=1)
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    observed_at: AwareDatetime
    values: JsonObject
    source_refs: tuple[str, ...] = ()

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json", exclude={"observed_at"}))

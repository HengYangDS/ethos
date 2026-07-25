"""Minimal persistent and derived contracts for repository change."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PlainSerializer
from pydantic import WithJsonSchema
from pydantic import model_validator


def _mutable_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _mutable_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_mutable_json(item) for item in value]
    return value


def _immutable_json(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable_json(item) for key, item in value.items()})
    if isinstance(value, tuple | list):
        return tuple(_immutable_json(item) for item in value)
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    message = "json_value_invalid"
    raise TypeError(message)


def _immutable_json_object(value: object) -> object:
    if not isinstance(value, Mapping):
        message = "json_object_invalid"
        raise TypeError(message)
    if not all(isinstance(key, str) for key in value):
        message = "json_object_key_invalid"
        raise TypeError(message)
    return _immutable_json(dict(value))


JsonObject = Annotated[
    Any,
    BeforeValidator(_immutable_json_object),
    PlainSerializer(_mutable_json, return_type=Any, when_used="always"),
    WithJsonSchema({"type": "object", "additionalProperties": {}}),
]


def _digest(value: object) -> str:
    payload = json.dumps(_mutable_json(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class _SemanticModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        strict=True,
        extra="forbid",
    )

    def digest(self) -> str:
        """Return the deterministic content digest."""
        return _digest(self.model_dump(mode="json"))


class ChangeContract(_SemanticModel):
    """Immutable base intent for one governed repository transition."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    subjects: tuple[str, ...] = Field(min_length=1)
    scope: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    acceptance: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    campaign: str = ""
    collaboration: Literal["cooperative", "competitive", "single"] = "single"
    compatibility: Literal["none", "bounded"] = "none"
    publication: Literal["local", "gitlab", "github", "dual"] = "local"


class Attestation(_SemanticModel):
    """Immutable evidence-bearing observation or judgment."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    issued_at: AwareDatetime
    sequence: int = Field(default=0, ge=0)
    content: JsonObject
    content_digest: str = Field(default="", pattern=r"^(?:[a-f0-9]{64})?$")
    evidence_refs: tuple[str, ...] = ()
    prior_digest: str = Field(default="", pattern=r"^(?:[a-f0-9]{64})?$")
    mints_authority: Literal[False] = False

    @model_validator(mode="after")
    def bind_content_digest(self) -> Self:
        """Bind content to an explicit digest and reject forged bindings."""
        digest = _digest(self.content)
        if self.content_digest and self.content_digest != digest:
            message = "attestation_content_digest_mismatch"
            raise ValueError(message)
        if not self.content_digest:
            object.__setattr__(self, "content_digest", digest)
        return self


class RepositoryFacts(_SemanticModel):
    """Fresh observation input; this value is derived and never persisted as truth."""

    schema_version: Literal[1] = 1
    repository: str = Field(min_length=1)
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    observed_at: AwareDatetime
    values: JsonObject
    source_refs: tuple[str, ...] = ()


def semantic_schema_documents() -> dict[str, dict[str, Any]]:
    """Generate the language-neutral schemas owned by terminal contracts."""
    contracts = {
        "change-contract.schema.json": ChangeContract,
        "attestation.schema.json": Attestation,
        "repository-facts.schema.json": RepositoryFacts,
    }
    schemas: dict[str, dict[str, Any]] = {}
    for name, model in contracts.items():
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://ethos.local/schemas/{name}"
        schema["title"] = f"ETHOS {model.__name__}"
        schemas[name] = schema
    return schemas


def apply_amendments(
    contract: ChangeContract,
    attestations: tuple[Attestation, ...],
) -> ChangeContract:
    """Fold chronologically ordered, digest-bound amendment attestations."""
    effective = contract
    ordered = sorted(attestations, key=lambda item: (item.issued_at, item.sequence, item.id))
    order_keys = [(item.issued_at, item.sequence) for item in ordered]
    if len(order_keys) != len(set(order_keys)):
        message = "amendment_order_ambiguous"
        raise ValueError(message)
    for attestation in ordered:
        if attestation.kind != "amendment":
            message = "attestation_not_amendment"
            raise ValueError(message)
        if attestation.subject != contract.id:
            message = "amendment_subject_mismatch"
            raise ValueError(message)
        if attestation.prior_digest != effective.digest():
            message = "amendment_prior_digest_mismatch"
            raise ValueError(message)
        patch = attestation.content.get("patch")
        if not isinstance(patch, Mapping):
            message = "amendment_patch_invalid"
            raise TypeError(message)
        payload = effective.model_dump()
        for key, value in patch.items():
            field = ChangeContract.model_fields.get(key)
            if field is None:
                message = f"amendment_field_unknown:{key}"
                raise ValueError(message)
            payload[key] = tuple(value) if isinstance(value, list) else value
        effective = ChangeContract.model_validate(payload)
    return effective

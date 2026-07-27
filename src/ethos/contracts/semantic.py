"""Minimal persistent and derived contracts for repository change."""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from collections.abc import Mapping
from datetime import datetime
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING
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
from pydantic import ValidationInfo
from pydantic import WithJsonSchema
from pydantic import field_validator
from pydantic import model_validator

if TYPE_CHECKING:
    from pathlib import Path


def _mutable_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _mutable_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_mutable_json(item) for item in value]
    return value


def _immutable_json(value: object) -> object:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            message = "json_object_key_invalid"
            raise TypeError(message)
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

AttestationKind = Literal[
    "observation",
    "judgment",
    "proof",
    "effect",
    "external-assurance",
    "amendment",
]


def _canonical_json(value: object) -> str:
    return json.dumps(_mutable_json(value), sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


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

    def canonical_json(self) -> str:
        """Return deterministic language-neutral JSON."""
        return _canonical_json(self.model_dump(mode="json"))


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

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, scope: tuple[str, ...]) -> tuple[str, ...]:
        """Keep repository coverage portable, relative, and unambiguous."""
        for pattern in scope:
            if (
                not pattern
                or pattern.startswith("/")
                or "\\" in pattern
                or any(part in {"", ".", ".."} for part in PurePosixPath(pattern).parts)
            ):
                message = "change_scope_invalid"
                raise ValueError(message)
        if len(scope) != len(set(scope)):
            message = "change_scope_duplicate"
            raise ValueError(message)
        return scope


_CHANGE_CONTRACT_TUPLE_FIELDS = {
    "subjects",
    "scope",
    "invariants",
    "acceptance",
    "risks",
    "authority_refs",
    "permissions",
    "hypotheses",
    "dependencies",
}


def load_change_contract_file(path: Path, *, repository_id: str = "") -> ChangeContract:
    """Load one strict ChangeContract TOML carrier."""
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    normalized = {
        key: tuple(value)
        if key in _CHANGE_CONTRACT_TUPLE_FIELDS and isinstance(value, list)
        else value
        for key, value in payload.items()
    }
    if repository_id:
        normalized["subjects"] = tuple(
            repository_id if subject == "repository:self" else subject
            for subject in normalized.get("subjects", ())
        )
    return ChangeContract.model_validate(normalized)


class Attestation(_SemanticModel):
    """Immutable evidence-bearing observation or judgment."""

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: AttestationKind
    issuer: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    issued_at: AwareDatetime
    verdict: Literal["pass", "block", "unknown"]
    advisories: tuple[str, ...] = ()
    sequence: int = Field(default=0, ge=0)
    content: JsonObject
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_refs: tuple[str, ...] = ()
    change_contract_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    repository_facts_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    plan_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    policy_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    effect_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    mints_authority: Literal[False] = False

    @model_validator(mode="after")
    def validate_kind_contract(self) -> Self:
        """Enforce one small typed algebra inside the single Attestation envelope."""
        if error := _attestation_kind_error(self):
            raise ValueError(error)
        return self

    @classmethod
    def issue(cls, payload: Mapping[str, object]) -> Self:
        """Issue one content-addressed Attestation from one semantic payload."""
        if not isinstance(payload, Mapping):
            message = "attestation_issue_payload_invalid"
            raise TypeError(message)
        derived = {"id", "content_digest", "mints_authority", "schema_version"}
        if invalid := sorted(str(key) for key in payload.keys() & derived):
            message = f"attestation_issue_derived_field:{invalid[0]}"
            raise ValueError(message)
        placeholder = "0" * 64
        bindings = {
            "change_contract_digest": "",
            "repository_facts_digest": "",
            "plan_digest": "",
            "policy_digest": "",
            "effect_digest": "",
        }
        return cls.model_validate(
            {
                "id": placeholder,
                **bindings,
                **payload,
                "content_digest": placeholder,
                "mints_authority": False,
            },
            context={"issue_attestation": True},
        )

    @model_validator(mode="after")
    def validate_digests(self, info: ValidationInfo) -> Self:
        """Bind content and envelope identity and reject forged durable payloads."""
        issuing = bool(info.context and info.context.get("issue_attestation"))
        content_digest = _digest(self.content)
        if not issuing and self.content_digest != content_digest:
            message = "attestation_content_digest_mismatch"
            raise ValueError(message)
        object.__setattr__(self, "content_digest", content_digest)
        identity = _digest(self.model_dump(mode="json", exclude={"id"}))
        if not issuing and self.id != identity:
            message = "attestation_identity_mismatch"
            raise ValueError(message)
        object.__setattr__(self, "id", identity)
        return self

    def digest(self) -> str:
        """Return the content-addressed Attestation identity."""
        return self.id


class RepositoryFacts(_SemanticModel):
    """Fresh observation input; this value is derived and never persisted as truth."""

    schema_version: Literal[1] = 1
    repository: str = Field(min_length=1)
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    observed_at: AwareDatetime
    values: JsonObject
    source_refs: tuple[str, ...] = ()

    def digest(self) -> str:
        """Bind facts without making observation time part of semantic identity."""
        return _digest(self.model_dump(mode="json", exclude={"observed_at"}))


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
        if model is Attestation:
            schema["allOf"] = _attestation_kind_schema()
        schemas[name] = schema
    return schemas


def _content_text(content: Mapping[str, object], *names: str) -> bool:
    return all(
        isinstance(content.get(name), str) and bool(str(content[name]).strip()) for name in names
    )


def _aware_iso_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _attestation_bound(attestation: Attestation) -> bool:
    return any(
        (
            attestation.change_contract_digest,
            attestation.repository_facts_digest,
            attestation.plan_digest,
            attestation.policy_digest,
            attestation.effect_digest,
            attestation.evidence_refs,
        )
    )


def _observation_valid(attestation: Attestation) -> bool:
    return bool(attestation.content) and _attestation_bound(attestation)


def _judgment_valid(attestation: Attestation) -> bool:
    return _content_text(attestation.content, "judgment", "basis") and _attestation_bound(
        attestation
    )


def _proof_valid(attestation: Attestation) -> bool:
    return (
        _content_text(attestation.content, "head", "tree")
        and isinstance(attestation.content.get("gate_ids"), tuple | list)
        and isinstance(attestation.content.get("artifact"), Mapping)
        and all(
            (
                attestation.change_contract_digest,
                attestation.repository_facts_digest,
                attestation.plan_digest,
                attestation.policy_digest,
                attestation.effect_digest,
                attestation.evidence_refs,
            )
        )
    )


def _effect_valid(attestation: Attestation) -> bool:
    return _content_text(attestation.content, "state") and all(
        (
            attestation.change_contract_digest,
            attestation.repository_facts_digest,
            attestation.plan_digest,
            attestation.policy_digest,
            attestation.effect_digest,
        )
    )


def _external_assurance_valid(attestation: Attestation) -> bool:
    valid_until = str(attestation.content.get("valid_until") or "")
    return (
        _content_text(attestation.content, "provider", "verification_method", "valid_until")
        and _aware_iso_datetime(valid_until)
        and bool(attestation.evidence_refs)
        and bool(attestation.effect_digest)
    )


def _amendment_valid(attestation: Attestation) -> bool:
    return (
        isinstance(attestation.content.get("patch"), Mapping)
        and bool(attestation.change_contract_digest)
        and attestation.verdict == "pass"
    )


_ATTESTATION_KIND_VALIDATORS = {
    "observation": _observation_valid,
    "judgment": _judgment_valid,
    "proof": _proof_valid,
    "effect": _effect_valid,
    "external-assurance": _external_assurance_valid,
    "amendment": _amendment_valid,
}


def _attestation_kind_error(attestation: Attestation) -> str:
    if _ATTESTATION_KIND_VALIDATORS[attestation.kind](attestation):
        return ""
    return f"attestation_{attestation.kind.replace('-', '_')}_content_invalid"


def _content_schema(required: tuple[str, ...], properties: dict[str, object]) -> dict[str, object]:
    return {
        "required": list(required),
        "properties": properties,
        "minProperties": 1,
    }


def _attestation_kind_schema() -> list[dict[str, object]]:
    content_by_kind = {
        "observation": _content_schema((), {}),
        "judgment": _content_schema(
            ("judgment", "basis"),
            {
                "judgment": {"type": "string", "minLength": 1},
                "basis": {"type": "string", "minLength": 1},
            },
        ),
        "proof": _content_schema(
            ("head", "tree", "gate_ids", "artifact"),
            {
                "head": {"type": "string", "minLength": 1},
                "tree": {"type": "string", "minLength": 1},
                "gate_ids": {"type": "array", "items": {"type": "string"}},
                "artifact": {"type": "object"},
            },
        ),
        "effect": _content_schema(("state",), {"state": {"type": "string", "minLength": 1}}),
        "external-assurance": _content_schema(
            ("provider", "verification_method", "valid_until"),
            {
                "provider": {"type": "string", "minLength": 1},
                "verification_method": {"type": "string", "minLength": 1},
                "valid_until": {"type": "string", "format": "date-time"},
            },
        ),
        "amendment": _content_schema(("patch",), {"patch": {"type": "object"}}),
    }
    return [
        {
            "if": {"properties": {"kind": {"const": kind}}, "required": ["kind"]},
            "then": {"properties": {"content": content_schema}},
        }
        for kind, content_schema in content_by_kind.items()
    ]


def _amendment_patch(
    attestation: Attestation,
    issuer_permissions: Mapping[str, tuple[str, ...]] | None,
) -> Mapping[str, object]:
    patch = attestation.content.get("patch")
    if not isinstance(patch, Mapping):
        message = "amendment_patch_invalid"
        raise TypeError(message)
    if issuer_permissions is None:
        message = "amendment_authority_missing"
        raise ValueError(message)
    allowed_fields = issuer_permissions.get(attestation.issuer)
    if allowed_fields is None:
        message = "amendment_issuer_unauthorized"
        raise ValueError(message)
    unauthorized = next((key for key in patch if key not in allowed_fields), None)
    if unauthorized is not None:
        message = f"amendment_field_unauthorized:{unauthorized}"
        raise ValueError(message)
    return patch


def _ordered_unique_attestations(
    attestations: tuple[Attestation, ...],
) -> tuple[Attestation, ...]:
    by_identity: dict[str, Attestation] = {}
    for attestation in attestations:
        previous = by_identity.get(attestation.id)
        if previous is not None:
            if previous.canonical_json() != attestation.canonical_json():
                message = "attestation_identity_collision"
                raise ValueError(message)
            message = "attestation_duplicate"
            raise ValueError(message)
        by_identity[attestation.id] = attestation
    ordered = tuple(sorted(attestations, key=lambda item: (item.issued_at, item.sequence, item.id)))
    order_keys = [(item.issued_at, item.sequence) for item in ordered]
    if len(order_keys) != len(set(order_keys)):
        message = "amendment_order_ambiguous"
        raise ValueError(message)
    return ordered


def apply_amendments(
    contract: ChangeContract,
    attestations: tuple[Attestation, ...],
    *,
    issuer_permissions: Mapping[str, tuple[str, ...]] | None = None,
) -> ChangeContract:
    """Fold chronologically ordered, digest-bound amendment attestations."""
    effective = contract
    for attestation in _ordered_unique_attestations(attestations):
        if attestation.kind != "amendment":
            message = "attestation_not_amendment"
            raise ValueError(message)
        if attestation.verdict != "pass":
            message = f"amendment_verdict_{attestation.verdict}"
            raise ValueError(message)
        if attestation.subject != contract.id:
            message = "amendment_subject_mismatch"
            raise ValueError(message)
        if attestation.change_contract_digest != effective.digest():
            message = "amendment_change_contract_digest_mismatch"
            raise ValueError(message)
        patch = _amendment_patch(attestation, issuer_permissions)
        payload = effective.model_dump()
        for key, value in patch.items():
            field = ChangeContract.model_fields.get(key)
            if field is None:
                message = f"amendment_field_unknown:{key}"
                raise ValueError(message)
            payload[key] = tuple(value) if isinstance(value, list) else value
        effective = ChangeContract.model_validate(payload)
    return effective

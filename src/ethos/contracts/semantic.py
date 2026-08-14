"""Persistent Commitment and Attestation envelopes plus transient Facts."""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationInfo
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.value import JsonObject
from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

if TYPE_CHECKING:
    from pathlib import Path


def _canonical_json(value: object) -> str:
    return json.dumps(mutable_json(value), sort_keys=True, separators=(",", ":"))


def canonical_json_digest(value: object) -> str:
    """Digest one JSON value after canonical ETHOS normalization."""
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


class _SemanticModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
        strict=True,
        extra="forbid",
    )

    def digest(self) -> str:
        return canonical_json_digest(self.model_dump(mode="json"))

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class Commitment(_SemanticModel):
    """Immutable normative promise for one bounded transition."""

    schema_version: Literal[1] = 1
    id: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    subjects: tuple[str, ...] = Field(min_length=1)
    scope: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    acceptance: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    authority_refs: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, scope: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in scope:
            if (
                not pattern
                or pattern.startswith("/")
                or "\\" in pattern
                or any(part in {"", ".", ".."} for part in PurePosixPath(pattern).parts)
            ):
                msg = "change_scope_invalid"
                raise ValueError(msg)
        if len(scope) != len(set(scope)):
            msg = "change_scope_duplicate"
            raise ValueError(msg)
        return scope

    def identity_projection(self) -> dict[str, object]:
        """Return the schema-versioned portable identity projection."""
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "intent": self.intent,
            "subjects": list(self.subjects),
            "scope": list(self.scope),
            "invariants": list(self.invariants),
            "acceptance": list(self.acceptance),
            "risks": list(self.risks),
            "authority_refs": list(self.authority_refs),
            "hypotheses": list(self.hypotheses),
            "dependencies": list(self.dependencies),
        }

    def digest(self) -> str:
        return canonical_json_digest(self.identity_projection())


_COMMITMENT_TUPLE_FIELDS = {
    "subjects",
    "scope",
    "invariants",
    "acceptance",
    "risks",
    "authority_refs",
    "hypotheses",
    "dependencies",
}


def load_commitment_file(path: Path, *, repository_id: str = "") -> Commitment:
    """Load one strict Commitment TOML carrier."""
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    normalized = {
        key: tuple(value) if key in _COMMITMENT_TUPLE_FIELDS and isinstance(value, list) else value
        for key, value in payload.items()
    }
    if repository_id:
        normalized["subjects"] = tuple(
            repository_id if subject == "repository:self" else subject
            for subject in normalized.get("subjects", ())
        )
    return Commitment.model_validate(normalized)


class Attestation(_SemanticModel):
    """Immutable open-predicate statement with explicit evidence bindings."""

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-f0-9]{64}$")
    predicate: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)+$")
    verifier: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    issued_at: AwareDatetime
    verdict: Verdict
    statement: JsonObject
    statement_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    advisories: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    commitment_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    facts_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    plan_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    policy_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    effect_digest: str = Field(pattern=r"^(?:[a-f0-9]{64})?$")
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None

    @classmethod
    def issue(cls, payload: Mapping[str, object]) -> Self:
        """Issue one content-addressed Attestation from one semantic payload."""
        if not isinstance(payload, Mapping):
            msg = "attestation_issue_payload_invalid"
            raise TypeError(msg)
        derived = {"id", "statement_digest", "schema_version"}
        if invalid := sorted(str(key) for key in payload.keys() & derived):
            message = f"attestation_issue_derived_field:{invalid[0]}"
            raise ValueError(message)
        placeholder = "0" * 64
        bindings = {
            "commitment_digest": "",
            "facts_digest": "",
            "plan_digest": "",
            "policy_digest": "",
            "effect_digest": "",
        }
        return cls.model_validate(
            {"id": placeholder, **bindings, **payload, "statement_digest": placeholder},
            context={"issue_attestation": True},
        )

    @model_validator(mode="after")
    def validate_statement_and_identity(self, info: ValidationInfo) -> Self:
        raw_gaps = self.statement.get("required_gaps", ())
        raw_warnings = self.statement.get("warnings", ())
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
            )
        ):
            msg = "attestation_binding_missing"
            raise ValueError(msg)
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            msg = "attestation_validity_invalid"
            raise ValueError(msg)
        issuing = bool(info.context and info.context.get("issue_attestation"))
        statement_digest = canonical_json_digest(self.statement)
        if not issuing and self.statement_digest != statement_digest:
            msg = "attestation_statement_digest_mismatch"
            raise ValueError(msg)
        object.__setattr__(self, "statement_digest", statement_digest)
        identity = canonical_json_digest(self.model_dump(mode="json", exclude={"id"}))
        if not issuing and self.id != identity:
            msg = "attestation_identity_mismatch"
            raise ValueError(msg)
        object.__setattr__(self, "id", identity)
        return self

    def digest(self) -> str:
        return self.id


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

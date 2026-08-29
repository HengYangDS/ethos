"""Typed local coordination contracts.

These values identify one cooperative local executor and one Work Lane lease.
They do not model users, teams, permissions, or durable repository truth.
"""

import json
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import JsonValue
from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic import field_validator

from ethos.contracts.semantic import Attestation
from ethos.contracts.value import FrozenTuple

_HOLDER_REF_PART_COUNT = 4
_LANE_LEASE_PAYLOAD_FIELDS_INVALID = "lane_lease_payload_fields_invalid"
_LANE_LEASE_PAYLOAD_TYPE_INVALID = "lane_lease_payload_type_invalid"
_JSON_OBJECT = TypeAdapter(dict[str, JsonValue], config=ConfigDict(strict=True))


_REPOSITORY_RELATIVE_PATH_PATTERN = (
    r"^(?:"
    r"[^./\\\x00:][^/\\\x00:]*"
    r"|\.[^./\\\x00:][^/\\\x00:]*"
    r"|\.\.[^/\\\x00:][^/\\\x00]*"
    r")"
    r"(?:/(?:"
    r"[^./\\\x00][^/\\\x00]*"
    r"|\.[^./\\\x00][^/\\\x00]*"
    r"|\.\.[^/\\\x00][^/\\\x00]*"
    r"))*$"
)
RepositoryRelativePath = Annotated[str, Field(pattern=_REPOSITORY_RELATIVE_PATH_PATTERN)]


class HolderRef(BaseModel):
    """Provider-neutral reference to one concrete local execution instance."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    kind: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    namespace: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    instance_kind: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    opaque_id: str = Field(min_length=1, pattern=r"^[^\s:]+$")
    mints_authority: bool = False

    @classmethod
    def parse(cls, value: str) -> Self:
        """Parse ``kind:namespace:instance-kind:opaque-id`` without role semantics."""
        if value != value.strip():
            msg = "holder_ref must not contain surrounding whitespace"
            raise ValueError(msg)
        parts = value.split(":")
        if len(parts) != _HOLDER_REF_PART_COUNT or any(not part for part in parts):
            msg = "holder_ref must have four non-empty segments"
            raise ValueError(msg)
        return cls(
            kind=parts[0],
            namespace=parts[1],
            instance_kind=parts[2],
            opaque_id=parts[3],
        )

    def serialize(self) -> str:
        """Return the stable equality serialization."""
        return f"{self.kind}:{self.namespace}:{self.instance_kind}:{self.opaque_id}"


class LaneLease(BaseModel):
    """One expiring lane-to-holder coordination relation."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    lane_ref: str = Field(min_length=1)
    holder_ref: HolderRef
    generation: int = Field(ge=1)
    expires_at: AwareDatetime

    @field_validator("holder_ref", mode="before")
    @classmethod
    def parse_holder_ref(cls, value: object) -> object:
        return HolderRef.parse(value) if isinstance(value, str) else value

    def to_payload(self) -> dict[str, Any]:
        """Return the minimal canonical persisted Lease payload."""
        return {
            "lane_ref": self.lane_ref,
            "holder_ref": self.holder_ref.serialize(),
            "generation": self.generation,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Self:
        """Parse only the strict terminal persisted Lease wire."""
        if set(payload) != set(cls.model_fields):
            raise ValueError(_LANE_LEASE_PAYLOAD_FIELDS_INVALID)
        try:
            _JSON_OBJECT.validate_python(payload, strict=True)
        except (TypeError, ValidationError) as exc:
            raise TypeError(_LANE_LEASE_PAYLOAD_TYPE_INVALID) from exc
        try:
            return cls.model_validate_json(json.dumps(payload))
        except ValidationError as exc:
            if any(str(error["type"]).endswith("_type") for error in exc.errors()):
                raise TypeError(_LANE_LEASE_PAYLOAD_TYPE_INVALID) from exc
            raise


class HandoffArtifact(BaseModel):
    """One canonical content-addressed handoff package member."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: RepositoryRelativePath
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: Literal["git_bundle", "context"]


class CrossHostHandoff(BaseModel):
    """Content-addressed transfer contract between Git common directories."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source_lane_ref: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    source_tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    target_holder_ref: HolderRef
    context_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    dirty_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_lease_generation: int = Field(ge=1)
    source_lease_expires_at: str = Field(min_length=1)
    source_holder_ref: HolderRef
    artifacts: FrozenTuple[HandoffArtifact] = ()

    def to_payload(self) -> dict[str, Any]:
        """Project transferable Git/context facts without the source lease."""
        return {
            "source_lane_ref": self.source_lane_ref,
            "source_head": self.source_head,
            "source_tree": self.source_tree,
            "target_holder_ref": self.target_holder_ref.serialize(),
            "context_digest": self.context_digest,
            "dirty_content_sha256": self.dirty_content_sha256,
            "source_lease_binding": {
                "lane_ref": self.source_lane_ref,
                "holder_ref": self.source_holder_ref.serialize(),
                "generation": self.source_lease_generation,
                "expires_at": self.source_lease_expires_at,
            },
            "artifacts": [artifact.model_dump(mode="json") for artifact in self.artifacts],
        }


class CrossHostHandoffExportRequest(BaseModel):
    """Exact source-lane admission inputs for one portable handoff package."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: str
    branch: str = Field(min_length=1)
    holder_ref: str = Field(min_length=1)
    target_holder_ref: str = Field(min_length=1)
    generation: int = Field(ge=1)
    expires_at: str = Field(min_length=1)
    expect_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    context_text: str = ""
    context_file: str | None = None
    output_root: str | None = None
    apply: bool = False


class CrossHostHandoffImportRequest(BaseModel):
    """Exact destination admission inputs for one verified handoff package."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: str
    package: str
    target_holder_ref: str = Field(min_length=1)
    apply: bool = False


class CrossHostHandoffSourceRevocationRequest(BaseModel):
    """Exact source-lease revocation inputs after destination acknowledgement."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: str
    package: str
    acknowledgement: str
    holder_ref: str = Field(min_length=1)
    generation: int = Field(ge=1)
    expires_at: str = Field(min_length=1)
    expect_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    apply: bool = False


class LeaseOperationRequest(BaseModel):
    """One exact request for a local Lease operation."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    operation: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    holder_ref: str = Field(min_length=1)
    generation: int = Field(ge=1)
    expires_at: str = Field(min_length=1)
    apply: bool = False
    ttl_seconds: int = Field(gt=0, default=86_400)
    target_holder_ref: str = ""
    contrary_decision: bool = False

    @field_validator("holder_ref", "target_holder_ref")
    @classmethod
    def validate_holder_refs(cls, value: str) -> str:
        return HolderRef.parse(value).serialize() if value else value


class LeaseTakeoverRequest(BaseModel):
    """Exact accepted authorization for one exceptional Lease holder change."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    branch: str = Field(min_length=1)
    source_holder_ref: str = Field(min_length=1)
    target_holder_ref: str = Field(min_length=1)
    generation: int = Field(ge=1)
    expires_at: str = Field(min_length=1)
    source_state: Literal["quiesced", "source_lost"]
    authorization: Attestation
    ttl_seconds: int = Field(gt=0, default=86_400)
    apply: bool = False

    @field_validator("source_holder_ref", "target_holder_ref")
    @classmethod
    def validate_holder_ref(cls, value: str) -> str:
        return HolderRef.parse(value).serialize()

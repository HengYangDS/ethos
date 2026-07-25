"""Typed local coordination contracts.

These values identify one cooperative local executor and one Work Lane lease.
They do not model users, teams, permissions, or durable repository truth.
"""

from __future__ import annotations

from typing import Any
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class HolderRef(BaseModel):
    """Provider-neutral reference to one concrete local execution instance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    namespace: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    instance_kind: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    opaque_id: str = Field(min_length=1, pattern=r"^[^\s:]+$")
    mints_authority: bool = False

    @classmethod
    def parse(cls, value: str) -> Self:
        """Parse ``kind:namespace:instance-kind:opaque-id`` without role semantics."""
        if value != value.strip():
            raise ValueError("holder_ref must not contain surrounding whitespace")  # noqa: EM101, RUF100, TRY003 - machine-readable gap token is the exception contract
        parts = value.split(":")
        if len(parts) != 4 or any(not part for part in parts):  # noqa: PLR2004, RUF100 - fixed wire-format arity is a protocol invariant
            raise ValueError("holder_ref must have four non-empty segments")  # noqa: EM101, RUF100, TRY003 - machine-readable gap token is the exception contract
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
    """One current cooperative writer lease in one Git common directory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lane_incarnation_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    lane_ref: str = Field(min_length=1)
    holder_ref: HolderRef
    epoch: int = Field(ge=1)
    issued_at: AwareDatetime
    renewed_at: AwareDatetime
    expires_at: AwareDatetime
    expected_head: str = ""
    claim_id: str = ""
    path_scope: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_times(self) -> LaneLease:
        """Keep renewal and expiry ordered without claiming clock authority."""
        if self.renewed_at < self.issued_at:
            raise ValueError("renewed_at must not precede issued_at")  # noqa: EM101, RUF100, TRY003 - machine-readable gap token is the exception contract
        if self.expires_at < self.renewed_at:
            raise ValueError("expires_at must not precede renewed_at")  # noqa: EM101, RUF100, TRY003 - machine-readable gap token is the exception contract
        return self

    def to_payload(self) -> dict[str, Any]:
        """Project the local contract with explicit non-authority boundaries."""
        return {
            "lane_incarnation_id": self.lane_incarnation_id,
            "lease_id": self.lease_id,
            "lane_ref": self.lane_ref,
            "holder_ref": self.holder_ref.serialize(),
            "epoch": self.epoch,
            "issued_at": self.issued_at.isoformat(),
            "renewed_at": self.renewed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "expected_head": self.expected_head,
            "claim_id": self.claim_id,
            "path_scope": list(self.path_scope),
            "coordination_scope": "git_common_directory",
            "mints_authority": False,
            "filesystem_fence": False,
            "distributed_lock": False,
        }


class HandoffArtifact(BaseModel):
    """One canonical content-addressed handoff package member."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    kind: Literal["git_bundle", "context"]

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Reject absolute, URI-like, and parent-traversing artifact paths."""
        parts = value.split("/")
        if value.startswith("/") or ":" in parts[0] or ".." in parts:
            raise ValueError("handoff artifact path must stay package-relative")  # noqa: EM101, RUF100, TRY003 - wire contract failure text
        return value


class CrossHostHandoff(BaseModel):
    """Content-addressed transfer contract between Git common directories."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    source_lane_ref: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    source_tree: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    target_holder_ref: HolderRef
    context_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    dirty_content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_lease_id: str = Field(min_length=1)
    source_lease_epoch: int = Field(ge=1)
    source_lease_expires_at: str = Field(min_length=1)
    source_lease_payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_holder_ref: HolderRef
    artifacts: tuple[HandoffArtifact, ...] = ()

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
                "lease_id": self.source_lease_id,
                "epoch": self.source_lease_epoch,
                "holder_ref": self.source_holder_ref.serialize(),
                "expected_head": self.source_head,
                "expires_at": self.source_lease_expires_at,
                "payload_sha256": self.source_lease_payload_sha256,
            },
            "artifacts": [artifact.model_dump(mode="json") for artifact in self.artifacts],
            "transfers_source_lease": False,
            "destination_creates_local_incarnation": True,
            "truth_boundary": "content_addressed_context_until_promoted",
        }

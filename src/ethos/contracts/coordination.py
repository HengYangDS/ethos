"""Typed local coordination contracts.

These values identify one cooperative local executor and one Work Lane lease.
They do not model users, teams, permissions, or durable repository truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Self

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

_HOLDER_REF_PART_COUNT = 4


@dataclass(frozen=True, slots=True)
class LeaseOperation:
    """Exact coordination semantics for one public Lease operation."""

    effect_fields: tuple[str, ...]
    kind: Literal["refresh", "offer", "accept"]
    actor_field: Literal["holder_ref", "target_holder_ref"]
    applied_state: str
    require_expired: bool = False


LEASE_OPERATIONS = {
    "renew": LeaseOperation(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "ttl_seconds",
        ),
        kind="refresh",
        actor_field="holder_ref",
        applied_state="renewed",
    ),
    "resume": LeaseOperation(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "ttl_seconds",
        ),
        kind="refresh",
        actor_field="holder_ref",
        applied_state="resumed",
        require_expired=True,
    ),
    "handoff_offer": LeaseOperation(
        effect_fields=(
            "holder_ref",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "target_holder_ref",
        ),
        kind="offer",
        actor_field="holder_ref",
        applied_state="handoff_offered",
    ),
    "handoff_accept": LeaseOperation(
        effect_fields=(
            "holder_ref",
            "target_holder_ref",
            "offer_id",
            "expected_epoch",
            "expected_expires_at",
            "expected_payload_sha256",
            "holder_quiesced",
            "ttl_seconds",
        ),
        kind="accept",
        actor_field="target_holder_ref",
        applied_state="handoff_accepted",
    ),
}


def lease_operation(identifier: str) -> LeaseOperation:
    """Return one exact supported Lease operation or fail closed."""
    try:
        return LEASE_OPERATIONS[identifier]
    except KeyError:
        message = f"lease_operation_unknown:{identifier}"
        raise ValueError(message) from None


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


class LeaseHandoffOffer(BaseModel):
    """One exact pending holder transfer offer inside a Lane Lease."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    offer_id: str = Field(min_length=1)
    target_holder_ref: str = Field(min_length=1)
    offered_at: AwareDatetime

    @field_validator("target_holder_ref")
    @classmethod
    def validate_target_holder_ref(cls, value: str) -> str:
        return HolderRef.parse(value).serialize()


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
    expected_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    base_commitment_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    path_scope: tuple[str, ...] = ()
    handoff: LeaseHandoffOffer | None = None

    @field_validator("holder_ref", mode="before")
    @classmethod
    def parse_holder_ref(cls, value: object) -> object:
        return HolderRef.parse(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_times(self) -> LaneLease:
        """Keep renewal and expiry ordered without claiming clock authority."""
        if self.renewed_at < self.issued_at:
            msg = "renewed_at must not precede issued_at"
            raise ValueError(msg)
        if self.expires_at < self.renewed_at:
            msg = "expires_at must not precede renewed_at"
            raise ValueError(msg)
        return self

    def to_payload(self) -> dict[str, Any]:
        """Return the complete canonical persisted Lease payload."""
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
            "base_commitment_digest": self.base_commitment_digest,
            "path_scope": list(self.path_scope),
            "handoff": self.handoff.model_dump(mode="json") if self.handoff else None,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Self:
        """Parse only the strict terminal persisted Lease wire."""
        expected = {
            "lane_incarnation_id",
            "lease_id",
            "lane_ref",
            "holder_ref",
            "epoch",
            "issued_at",
            "renewed_at",
            "expires_at",
            "expected_head",
            "base_commitment_digest",
            "path_scope",
            "handoff",
        }
        if set(payload) != expected:
            msg = "lane_lease_payload_fields_invalid"
            raise ValueError(msg)
        string_fields = expected - {"epoch", "path_scope", "handoff"}
        if any(not isinstance(payload[field], str) for field in string_fields):
            msg = "lane_lease_payload_type_invalid"
            raise ValueError(msg)
        epoch = payload["epoch"]
        path_scope = payload["path_scope"]
        handoff = payload["handoff"]
        if isinstance(epoch, bool) or not isinstance(epoch, int):
            msg = "lane_lease_payload_type_invalid"
            raise TypeError(msg)
        if not isinstance(path_scope, list) or any(
            not isinstance(path, str) for path in path_scope
        ):
            msg = "lane_lease_payload_type_invalid"
            raise TypeError(msg)
        if handoff is not None and not isinstance(handoff, dict):
            msg = "lane_lease_payload_type_invalid"
            raise TypeError(msg)
        return cls(
            lane_incarnation_id=payload["lane_incarnation_id"],
            lease_id=payload["lease_id"],
            lane_ref=payload["lane_ref"],
            holder_ref=HolderRef.parse(payload["holder_ref"]),
            epoch=epoch,
            issued_at=payload["issued_at"],
            renewed_at=payload["renewed_at"],
            expires_at=payload["expires_at"],
            expected_head=payload["expected_head"],
            base_commitment_digest=payload["base_commitment_digest"],
            path_scope=tuple(path_scope),
            handoff=handoff,
        )


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
            msg = "handoff artifact path must stay package-relative"
            raise ValueError(msg)
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
    base_commitment_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
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
            "base_commitment_digest": self.base_commitment_digest,
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


class CrossHostHandoffExportRequest(BaseModel):
    """Exact source-lane admission inputs for one portable handoff package."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: str
    branch: str = Field(min_length=1)
    holder_ref: str = Field(min_length=1)
    target_holder_ref: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    epoch: int = Field(ge=1)
    expected_expires_at: str = Field(min_length=1)
    expected_payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
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
    lease_id: str = Field(min_length=1)
    epoch: int = Field(ge=1)
    expected_expires_at: str = Field(min_length=1)
    expected_payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expect_head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
    apply: bool = False


class MutationAdmissionRequest(BaseModel):
    """Bound inputs used to project one mutation admission decision."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    expected_state: dict[str, object]
    verdict: Verdict
    required_gaps: tuple[str, ...] = ()
    why: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    state: str = ""
    identity_basis: str = "not_evaluated"
    evidence_boundary: str = "current_local_observation"
    enforcement_boundary: str = "local_process_guard"
    verifier_provenance: str = "current_runner"

    @model_validator(mode="after")
    def reject_false_pass(self) -> MutationAdmissionRequest:
        require_closed_verdict(self.verdict, self.required_gaps)
        return self


class LeaseOperationRequest(BaseModel):
    """One exact request for a local Lease operation."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    operation: str = Field(min_length=1)
    branch: str
    holder_ref: str
    lease_id: str
    expected_epoch: int | None
    expect_head: str
    expected_expires_at: str = Field(min_length=1)
    expected_payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    apply: bool = False
    ttl_seconds: int = 86_400
    target_holder_ref: str = ""
    offer_id: str = ""
    holder_quiesced: bool = False
    contrary_decision: bool = False

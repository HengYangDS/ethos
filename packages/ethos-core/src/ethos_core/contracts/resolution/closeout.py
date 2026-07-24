"""Immutable completion and recovery contracts for Work Lane resolution."""

from __future__ import annotations

import hashlib
import uuid
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos_core.contracts.coordination import HolderRef

LaneResolutionState = Literal[
    "blocked_by_decision", "preserved", "retired", "preserved_and_retired"
]
OwnerlessCloseoutPhase = Literal["reserved", "effect", "postcondition", "receipt", "unknown"]
OwnerlessCloseoutRecoveryState = Literal[
    "reserved_no_effect",
    "worktree_removed_ref_present",
    "effect_complete_receipt_missing",
    "postcondition_failed",
    "transition_unknown",
]

_RECOVERY_PHASES: dict[OwnerlessCloseoutRecoveryState, OwnerlessCloseoutPhase] = {
    "reserved_no_effect": "reserved",
    "worktree_removed_ref_present": "effect",
    "effect_complete_receipt_missing": "receipt",
    "postcondition_failed": "postcondition",
    "transition_unknown": "unknown",
}
_GIT_OID_PATTERN = r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$"
_SHA256_PATTERN = r"^[a-f0-9]{64}$"
_OPTIONAL_SHA256_PATTERN = r"^(?:[a-f0-9]{64})?$"


class OwnerlessCloseoutBinding(BaseModel):
    """Complete native admission and postcondition binding for ownerless closeout."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    executor_ref: str = Field(min_length=1)
    decision_sha256: str = Field(pattern=_SHA256_PATTERN)
    accepted_branch: str = Field(min_length=1)
    accepted_head: str = Field(pattern=_GIT_OID_PATTERN)
    target_digest: str = Field(pattern=_SHA256_PATTERN)
    target_binding_digest: str = Field(pattern=_SHA256_PATTERN)
    postcondition_digest: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("executor_ref")
    @classmethod
    def validate_executor_ref(cls, value: str) -> str:
        """Apply the provider-neutral holder identity wire contract."""
        return HolderRef.parse(value).serialize()


class LaneResolutionReceipt(BaseModel):
    """Immutable local completion record for one lane-resolution decision."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[3]
    receipt_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    completed: bool = Field(strict=True)
    state: LaneResolutionState
    observation_digest: str = Field(pattern=_SHA256_PATTERN)
    reconciliation_required: bool
    lane_ref: str = Field(min_length=1)
    head: str = Field(pattern=_GIT_OID_PATTERN)
    preservation_package: str
    preservation_manifest_sha256: str = Field(pattern=_OPTIONAL_SHA256_PATTERN)
    ownerless_closeout_binding: OwnerlessCloseoutBinding | None = None
    mints_authority: bool = Field(strict=True)

    @field_validator("completed")
    @classmethod
    def validate_completed(cls, value: object) -> bool:
        """Require a completed receipt rather than a coercible truthy value."""
        if value is not True:
            raise ValueError("lane-resolution receipt must be completed")
        return True

    @field_validator("mints_authority")
    @classmethod
    def validate_non_authoritative(cls, value: object) -> bool:
        """Prevent completion evidence from minting authority."""
        if value is not False:
            raise ValueError("lane-resolution receipt cannot mint authority")
        return False

    def to_payload(self) -> dict[str, object]:
        """Return the canonical JSON-compatible receipt payload."""
        return self.model_dump(mode="json", exclude_none=True)


class OwnerlessCloseoutReservation(BaseModel):
    """Durable exact-target reservation and visible recovery state."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[2]
    decision_id: str = Field(min_length=1)
    lane_ref: str = Field(min_length=1)
    head: str = Field(pattern=_GIT_OID_PATTERN)
    executor_ref: str = Field(min_length=1)
    decision_sha256: str = Field(pattern=_SHA256_PATTERN)
    accepted_branch: str = Field(min_length=1)
    accepted_head: str = Field(pattern=_GIT_OID_PATTERN)
    target_digest: str = Field(pattern=_SHA256_PATTERN)
    target_binding_digest: str = Field(pattern=_SHA256_PATTERN)
    phase: OwnerlessCloseoutPhase
    recovery_state: OwnerlessCloseoutRecoveryState
    postcondition_digest: str = Field(pattern=_OPTIONAL_SHA256_PATTERN)

    @field_validator("decision_id")
    @classmethod
    def validate_decision_id(cls, value: str) -> str:
        """Require the canonical lane-decision UUID wire form."""
        prefix = "lane-decision:"
        if not value.startswith(prefix):
            raise ValueError("invalid lane-resolution decision id")
        try:
            parsed = uuid.UUID(value.removeprefix(prefix))
        except ValueError as error:
            raise ValueError("invalid lane-resolution decision id") from error
        if value != f"{prefix}{parsed}":
            raise ValueError("invalid lane-resolution decision id")
        return value

    @field_validator("executor_ref")
    @classmethod
    def validate_executor_ref(cls, value: str) -> str:
        """Apply the provider-neutral holder identity wire contract."""
        return HolderRef.parse(value).serialize()

    @model_validator(mode="after")
    def validate_target_and_recovery_state(self) -> Self:
        """Bind the target digest and preserve the phase/recovery state matrix."""
        expected_target = hashlib.sha256(f"{self.lane_ref}\0{self.head}".encode()).hexdigest()
        if self.target_digest != expected_target:
            raise ValueError("ownerless closeout target digest mismatch")
        if self.phase != _RECOVERY_PHASES[self.recovery_state]:
            raise ValueError("ownerless closeout phase and recovery state mismatch")
        completed_effect = self.recovery_state == "effect_complete_receipt_missing"
        if completed_effect != bool(self.postcondition_digest):
            raise ValueError("ownerless closeout postcondition digest mismatch")
        return self

    def to_payload(self) -> dict[str, object]:
        """Return the canonical JSON-compatible reservation payload."""
        return self.model_dump(mode="json")


class LaneResolutionClearReceipt(BaseModel):
    """Immutable local record for one approved recovery-package removal."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal[1]
    clear_receipt_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=_SHA256_PATTERN)
    chronicle_ref: str = Field(min_length=1)
    chronicle_digest: str = Field(pattern=_SHA256_PATTERN)
    reason: str = Field(min_length=1)
    completed: bool = Field(strict=True)
    mints_authority: bool = Field(strict=True)

    @field_validator("completed")
    @classmethod
    def validate_completed(cls, value: object) -> bool:
        """Require a completed clear receipt rather than a coercible truthy value."""
        if value is not True:
            raise ValueError("lane-resolution clear receipt must be completed")
        return True

    @field_validator("mints_authority")
    @classmethod
    def validate_non_authoritative(cls, value: object) -> bool:
        """Prevent clear evidence from minting authority."""
        if value is not False:
            raise ValueError("lane-resolution clear receipt cannot mint authority")
        return False

    def to_payload(self) -> dict[str, object]:
        """Return the canonical JSON-compatible clear-receipt payload."""
        return self.model_dump(mode="json")

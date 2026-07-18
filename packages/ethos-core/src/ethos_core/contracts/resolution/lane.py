"""Exceptional Work Lane resolution contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

LaneDisposition = Literal["block", "preserve", "retire", "preserve-retire"]


class LaneObservation(BaseModel):
    """Exact Git/local-state observation used by one exceptional judgment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lane_ref: str = Field(min_length=1)
    head: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    lane_incarnation_id: str = Field(min_length=1)
    holder_ref: str = ""
    path: str = Field(min_length=1)
    dirty: bool
    foreign: bool
    orphan: bool
    ambiguous: bool
    tracked_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    untracked_digest: str = Field(pattern=r"^[a-f0-9]{64}$")

    def digest(self) -> str:
        body = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


class LaneResolutionDecision(BaseModel):
    """Accepted first-phase judgment bound to one exact observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(min_length=1)
    disposition: LaneDisposition
    observation: LaneObservation
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    chronicle_ref: str = Field(min_length=1)
    chronicle_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    recovery_plan: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    break_glass: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "decision_id": self.decision_id,
            "disposition": self.disposition,
            "observation": self.observation.model_dump(mode="json"),
            "observation_digest": self.observation.digest(),
            "evidence_refs": list(self.evidence_refs),
            "chronicle_ref": self.chronicle_ref,
            "chronicle_digest": self.chronicle_digest,
            "recovery_plan": self.recovery_plan,
            "reason": self.reason,
            "break_glass": self.break_glass,
            "recompute_before_effect": True,
            "reusable_authorization": False,
            "mints_authority": False,
        }


class LaneResolutionReceipt(BaseModel):
    """Immutable local completion record for one lane-resolution decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    receipt_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    disposition: LaneDisposition
    completed: Literal[True]
    state: str = Field(min_length=1)
    observation_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reconciliation_required: bool
    lane_ref: str = Field(min_length=1)
    head: str = Field(pattern=r"^[a-f0-9]{40,64}$")
    preservation_package: str = ""
    preservation_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$|^$")
    mints_authority: Literal[False]

    def to_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class LaneResolutionClearReceipt(BaseModel):
    """Immutable local record for one approved recovery-package removal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clear_receipt_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    chronicle_ref: str = Field(min_length=1)
    chronicle_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1)
    completed: Literal[True]
    mints_authority: Literal[False]

    def to_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")

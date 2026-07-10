"""Exceptional Work Lane resolution contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

LaneDisposition = Literal["block", "preserve", "retire"]


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
            "reason": self.reason,
            "break_glass": self.break_glass,
            "recompute_before_effect": True,
            "reusable_authorization": False,
            "mints_authority": False,
        }

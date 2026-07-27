"""Exceptional Work Lane resolution contracts."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

LaneDisposition = Literal["block", "preserve", "retire", "preserve-retire"]


@dataclass(frozen=True, slots=True)
class LaneResolutionPlanRequest:
    """Immutable inputs for one first-phase exceptional lane judgment."""

    branch: str
    disposition: str
    reason: str
    evidence_refs: tuple[str, ...]
    chronicle_ref: str
    recovery_plan: str
    decision_path: str
    break_glass: bool
    apply: bool


def is_lane_decision_id(value: str) -> bool:
    """Return whether the identifier is exactly lane-decision:<canonical UUID>."""
    prefix = "lane-decision:"
    if not value.startswith(prefix):
        return False
    try:
        parsed = uuid.UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return value == f"{prefix}{parsed}"


class LaneObservation(BaseModel):
    """Exact Git/local-state observation used by one exceptional judgment."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    lane_ref: str = Field(min_length=1)
    head: str = Field(pattern=r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
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
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class LaneResolutionDecision(BaseModel):
    """Accepted first-phase judgment bound to one exact observation."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

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
        payload = self.model_dump(mode="json")
        payload.update(
            schema_version=1,
            observation_digest=self.observation.digest(),
            recompute_before_effect=True,
            reusable_authorization=False,
            mints_authority=False,
        )
        return payload

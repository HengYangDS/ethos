"""Exact fence facts and immutable admission shape for ownerless closeout."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

    import ethos.adapters.mutation.resolution.observation as git
    import ethos.contracts.branch.roles as roles
    import ethos.contracts.resolution.lane as lane
    from ethos.contracts.resolution.closeout import OwnerlessCloseoutReservation

_BindingAuthority = tuple[str, str, str, str]


class OwnerlessCloseoutAdmissionError(ValueError):
    """Stable native-admission gap with separate non-authoritative detail."""

    def __init__(self, gap: str, detail: str = "") -> None:
        super().__init__(f"{gap}:{detail}" if detail else gap)
        self.gap = gap
        self.detail = detail


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutAdmission:
    """Immutable fact snapshot admitted before ownerless closeout fencing."""

    root: Path
    decision_path: Path
    decision: lane.LaneResolutionDecision
    decision_bytes: bytes
    decision_sha256: str
    observation: lane.LaneObservation
    registration_token: git.GitWorktreeRegistrationToken
    executor_ref: str
    policy: roles.BranchRolePolicy
    accepted_branch: str
    accepted_head: str
    target_digest: str
    target_binding_digest: str
    existing_reservation: OwnerlessCloseoutReservation | None


def ownerless_fence_binding(
    *,
    model: lane.LaneResolutionDecision,
    observation: lane.LaneObservation,
    authority: _BindingAuthority,
) -> dict[str, Any]:
    """Render the stable target binding from exact admission facts."""
    executor_ref, accepted_branch, accepted_head, decision_sha256 = authority
    return {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": model.decision_id,
        "executor_ref": executor_ref,
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "payload": {
            "target_path": observation.path,
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": decision_sha256,
            "chronicle_digest": model.chronicle_digest,
        },
    }


def ownerless_fence_digest(binding: dict[str, object]) -> str:
    """Hash one exact native closeout binding."""
    return hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def ownerless_closeout_fence(
    model: lane.LaneResolutionDecision,
    observation: lane.LaneObservation,
    authority: _BindingAuthority,
    acquisition_id: str,
) -> dict[str, object]:
    """Render one exact acquisition fence."""
    binding = ownerless_fence_binding(model=model, observation=observation, authority=authority)
    binding["payload"] = {**binding["payload"], "acquisition_id": acquisition_id}
    return {**binding, "target_binding_digest": ownerless_fence_digest(binding)}


def ownerless_admission_fence(
    admission: OwnerlessCloseoutAdmission, acquisition_id: str
) -> dict[str, object]:
    """Render the exact fence tied to one admitted target."""
    authority = (
        admission.executor_ref,
        admission.accepted_branch,
        admission.accepted_head,
        admission.decision_sha256,
    )
    return ownerless_closeout_fence(
        admission.decision, admission.observation, authority, acquisition_id
    )


def ownerless_retry_fence(
    *,
    admission: OwnerlessCloseoutAdmission,
    reservation: OwnerlessCloseoutReservation,
    acquisition_id: str,
) -> dict[str, object]:
    """Render the exact retained no-effect fence from durable reservation facts."""
    authority = (
        reservation.executor_ref,
        reservation.accepted_branch,
        reservation.accepted_head,
        reservation.decision_sha256,
    )
    return ownerless_closeout_fence(
        admission.decision, admission.observation, authority, acquisition_id
    )

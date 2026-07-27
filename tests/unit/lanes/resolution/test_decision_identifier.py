from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from ethos.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos.contracts.resolution.lane import is_lane_decision_id

_CANONICAL_DECISION_ID = "lane-decision:123e4567-e89b-12d3-a456-426614174000"


def _reservation(decision_id: str) -> OwnerlessCloseoutReservation:
    lane_ref = "work/example"
    head = "a" * 40
    return OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=decision_id,
        lane_ref=lane_ref,
        head=head,
        executor_ref="agent:test:case:owner",
        decision_sha256="b" * 64,
        accepted_branch="dev",
        accepted_head="c" * 40,
        target_digest=hashlib.sha256(f"{lane_ref}\0{head}".encode()).hexdigest(),
        target_binding_digest="d" * 64,
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    )


def test_is_lane_decision_id_accepts_only_the_canonical_lane_decision_uuid_wire_form() -> None:
    assert is_lane_decision_id(_CANONICAL_DECISION_ID)
    assert _reservation(_CANONICAL_DECISION_ID).decision_id == _CANONICAL_DECISION_ID

    for invalid in (
        "lane-decision:123E4567-E89B-12D3-A456-426614174000",
        "lane-decision:{123e4567-e89b-12d3-a456-426614174000}",
        "lane-decision:not-a-uuid",
        "decision:123e4567-e89b-12d3-a456-426614174000",
        "lane-decision:123e4567e89b12d3a456426614174000",
    ):
        assert not is_lane_decision_id(invalid)
        with pytest.raises(ValidationError, match="invalid lane-resolution decision id"):
            _reservation(invalid)

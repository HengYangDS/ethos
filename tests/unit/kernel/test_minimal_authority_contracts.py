"""Terminal authority contracts reject duplicated intent and repository facts."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.contracts.coordination import LaneLease
from ethos.contracts.semantic import Commitment


def test_commitment_contains_only_change_identity_and_acceptance() -> None:
    payload = {
        "schema_version": 3,
        "id": "change:repository-effect-transaction-closure",
        "acceptance": (
            "repository-transaction:Official OpenSpec is the sole tracked intent carrier",
            "repository-transaction:Acceptance intent is compiled",
        ),
    }

    commitment = Commitment.model_validate(payload)

    assert set(commitment.model_dump()) == {"schema_version", "id", "acceptance"}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Commitment.model_validate(payload | {"parallel_authority": "forbidden"})


def test_lane_lease_contains_only_lane_holder_generation_and_expiry() -> None:
    payload = {
        "lane_ref": "refs/heads/work/terminal-authority",
        "holder_ref": "agent:codex:task:terminal-authority",
        "generation": 1,
        "expires_at": datetime(2026, 8, 29, tzinfo=UTC),
    }

    lease = LaneLease.model_validate(payload)

    assert set(lease.model_dump()) == {"lane_ref", "holder_ref", "generation", "expires_at"}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        LaneLease.model_validate(payload | {"parallel_authority": "forbidden"})

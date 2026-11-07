"""A holder reads its Lease from the inline status summary and is pointed at its renewal."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.application.inspection import lease_summary
from ethos.application.inspection import renewal_action
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.result import EthosResult
from ethos.result import apply_payload_budget

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 11, 5, 14, 0, tzinfo=UTC)
AUTHORITY = {
    "generation": 4,
    "expires_at": "2026-11-05T15:00:00+00:00",
    "holder_ref": "agent:x:y:z",
}


def test_a_work_lane_summary_names_its_lease() -> None:
    """Generation, expiry and seconds left; another role, or no Lease, names none."""
    assert lease_summary(AUTHORITY, role=ROLE_WORK_LANE, now=NOW) == {
        "lease_generation": 4,
        "lease_expires_at": "2026-11-05T15:00:00+00:00",
        "lease_seconds_left": 3600,
    }
    assert lease_summary(AUTHORITY, role=ROLE_ACCEPTED_ROOT, now=NOW) == {}
    assert lease_summary({"generation": 0, "expires_at": ""}, role=ROLE_WORK_LANE, now=NOW) == {}


@pytest.mark.parametrize(
    ("left", "verb"), [(3600, "renew"), (7199, "renew"), (7200, ""), (0, "resume"), (-5, "resume")]
)
def test_the_lease_action_follows_the_time_left(tmp_path: Path, left: int, verb: str) -> None:
    """Under two hours the renewal preview is next; once expired, the resumption preview."""
    action = renewal_action({"lease_seconds_left": left}, root=tmp_path)
    assert action == (f"ethos lane lease {verb} --root {tmp_path.as_posix()}" if verb else "")
    assert renewal_action({}, root=tmp_path) == ""


def test_the_lease_summary_survives_the_payload_budget(tmp_path: Path) -> None:
    """Oversized detail moves to an artifact; the summary, with the Lease, stays inline."""
    summary = {"branch": "work/example", "lease_generation": 4, "lease_seconds_left": 3600}
    result = EthosResult(
        command="status", verdict="pass", state="ready", summary=summary, data={"x": "y" * 40_000}
    )
    bounded = apply_payload_budget(result, root=tmp_path)
    assert "x" not in bounded.data
    assert bounded.bound["detail"]
    assert bounded.summary == summary

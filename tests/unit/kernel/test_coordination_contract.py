from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease

if TYPE_CHECKING:
    from pathlib import Path


def test_holder_ref_is_provider_neutral_and_carries_no_privilege() -> None:
    holder = HolderRef.parse("agent:codex:thread:019f46b5")

    assert holder.kind == "agent"
    assert holder.namespace == "codex"
    assert holder.instance_kind == "thread"
    assert holder.opaque_id == "019f46b5"
    assert holder.serialize() == "agent:codex:thread:019f46b5"
    assert holder.mints_authority is False


@pytest.mark.parametrize(
    "value",
    ["codex", "agent:codex", "agent:codex:thread", "agent::thread:id", " agent:x:y:z"],
)
def test_holder_ref_rejects_provider_only_or_ambiguous_values(value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        HolderRef.parse(value)


def test_lane_lease_binds_local_incarnation_holder_generation_and_head(tmp_path: Path) -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC)
    lease = LaneLease(
        lane_incarnation_id="lane-incarnation:01",
        lease_id="lease:01",
        lane_ref="work/example",
        holder_ref=HolderRef.parse("agent:claude:session:abc"),
        epoch=3,
        issued_at=now,
        renewed_at=now,
        expires_at=now,
        expected_head="a" * 40,
        base_commitment_digest="b" * 64,
        path_scope=("packages/example.py",),
    )

    payload = lease.to_payload()
    assert set(payload) == {
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
    assert payload["holder_ref"] == "agent:claude:session:abc"
    assert payload["epoch"] == 3
    assert payload["expected_head"] == "a" * 40
    assert payload["base_commitment_digest"] == "b" * 64
    assert payload["handoff"] is None
    assert LaneLease.model_validate(payload) == lease
    database = tmp_path / "state.sqlite"
    acquire_lease(database, lease=lease)
    with closing(sqlite3.connect(database)) as connection:
        persisted = connection.execute("select payload_json from leases").fetchone()[0]
    assert persisted == (
        '{"base_commitment_digest": "' + "b" * 64 + '", '
        '"epoch": 3, "expected_head": "'
        + "a"
        * 40
        + '", "expires_at": "2026-07-10T00:00:00+00:00", "handoff": null, '
        '"holder_ref": "agent:claude:session:abc", '
        '"issued_at": "2026-07-10T00:00:00+00:00", '
        '"lane_incarnation_id": "lane-incarnation:01", "lane_ref": "work/example", '
        '"lease_id": "lease:01", "path_scope": ["packages/example.py"], '
        '"renewed_at": "2026-07-10T00:00:00+00:00"}'
    )


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing-base-digest"),
        pytest.param({"base_commitment_digest": "not-a-digest"}, id="bad-base-digest"),
        pytest.param(
            {"base_commitment_digest": "b" * 64, "claim_id": "retired"},
            id="retired-claim-field",
        ),
        pytest.param(
            {"base_commitment_digest": "b" * 64, "path": "/tmp/worktree"},
            id="redundant-worktree-path",
        ),
    ],
)
def test_lane_lease_rejects_missing_malformed_or_legacy_wire_fields(
    payload: dict[str, object],
) -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC)
    candidate = {
        "lane_incarnation_id": "lane-incarnation:01",
        "lease_id": "lease:01",
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "epoch": 1,
        "issued_at": now.isoformat(),
        "renewed_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "expected_head": "a" * 40,
        "path_scope": [],
        "handoff": None,
        **payload,
    }

    with pytest.raises(ValidationError):
        LaneLease.model_validate(candidate)

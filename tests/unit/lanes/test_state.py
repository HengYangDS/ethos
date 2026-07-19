from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.store.state.lease.lifecycle.core import accept_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.lifecycle.core import initialize_lease_state
from ethos.adapters.store.state.lease.lifecycle.core import offer_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.lifecycle.core import resume_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import active_leases

if TYPE_CHECKING:
    from pathlib import Path


def test_state_initialization_creates_only_consumed_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"

    initialize_lease_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
    assert tables == {"leases"}


def test_acquire_lease_leaves_current_lease_schema_unchanged(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    db_path = tmp_path / "state.sqlite"
    first = acquire_lease(db_path, subject="work/current", holder_ref="agent:test:case:agent-a")

    second = acquire_lease(db_path, subject="work/next", holder_ref="agent:test:case:agent-b")

    leases = active_leases(db_path)
    assert {item["subject"] for item in leases} == {"work/current", "work/next"}
    assert first["subject"] == "work/current"
    assert second["subject"] == "work/next"


def test_acquire_lease_rejects_duplicate_current_lane_incarnation(
    tmp_path: Path,
) -> None:
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    db_path = tmp_path / "state.sqlite"
    first = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={
            "lane_incarnation_id": "lane-incarnation:one",
            "expected_head": "a" * 40,
        },
    )

    with pytest.raises(ValueError, match="lane_lease_conflict"):
        acquire_lease(
            db_path,
            subject="work/current",
            holder_ref="agent:claude:session:second",
            payload={
                "lane_incarnation_id": first["payload"]["lane_incarnation_id"],
                "expected_head": "a" * 40,
            },
        )


def test_acquire_lease_normalizes_holder_generation_and_timestamps(
    tmp_path: Path,
) -> None:
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    lease = acquire_lease(
        tmp_path / "state.sqlite",
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": "a" * 40, "claim_id": "claim-current"},
    )

    assert lease["lane_incarnation_id"].startswith("lane-incarnation:")
    assert lease["lease_id"] == lease["id"]
    assert lease["lane_ref"] == "work/current"
    assert lease["holder_ref"] == "agent:codex:thread:first"
    assert lease["epoch"] == 1
    assert lease["issued_at"]
    assert lease["renewed_at"] == lease["issued_at"]
    assert lease["expected_head"] == "a" * 40
    assert lease["claim_id"] == "claim-current"


def test_renew_and_resume_require_current_generation_and_same_holder(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        ttl_seconds=60,
        payload={"expected_head": "a" * 40},
    )

    renewed = renew_lease(
        db_path,
        subject="work/current",
        holder_ref=lease["holder_ref"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        expected_head="a" * 40,
        ttl_seconds=120,
    )

    assert renewed["lease_id"] == lease["lease_id"]
    assert renewed["epoch"] == lease["epoch"]
    assert renewed["renewed_at"] != lease["renewed_at"]

    with pytest.raises(ValueError, match="lease_epoch_stale"):
        renew_lease(
            db_path,
            subject="work/current",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=99,
            expected_head="a" * 40,
        )

    expired_db = tmp_path / "expired.sqlite"
    expired = acquire_lease(
        expired_db,
        subject="work/expired",
        holder_ref="agent:codex:thread:first",
        ttl_seconds=-1,
        payload={"expected_head": "b" * 40},
    )
    resumed = resume_lease(
        expired_db,
        subject="work/expired",
        holder_ref=expired["holder_ref"],
        expected_lease_id=expired["lease_id"],
        expected_epoch=expired["epoch"],
        expected_head="b" * 40,
    )
    assert resumed["lease_id"] == expired["lease_id"]
    assert resumed["epoch"] == expired["epoch"]


def test_handoff_offer_accept_changes_holder_and_increments_epoch(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": "a" * 40},
    )
    offer = offer_lease_handoff(
        db_path,
        subject="work/current",
        holder_ref=lease["holder_ref"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        target_holder_ref="agent:claude:session:second",
        expected_head="a" * 40,
    )

    accepted = accept_lease_handoff(
        db_path,
        subject="work/current",
        target_holder_ref="agent:claude:session:second",
        offer_id=offer["offer_id"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        expected_head="a" * 40,
        holder_quiesced=True,
    )

    assert accepted["holder_ref"] == "agent:claude:session:second"
    assert accepted["epoch"] == lease["epoch"] + 1
    assert accepted["lease_id"] == lease["lease_id"]
    assert accepted["payload"]["handoff_state"] == "accepted"


def test_revoke_lease_is_generation_and_head_bound(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/example",
        holder_ref="agent:test:case:source",
        payload={"expected_head": "a" * 40},
    )

    removed = revoke_lease(
        db_path,
        subject="work/example",
        holder_ref="agent:test:case:source",
        expected_lease_id=str(lease["lease_id"]),
        expected_epoch=int(lease["epoch"]),
        expected_head="a" * 40,
    )

    assert removed["revoked"] is True
    assert active_leases(db_path) == []


def test_advance_lease_head_is_generation_bound_compare_and_swap(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": "a" * 40},
    )

    advanced = advance_lease_head(
        db_path,
        subject="work/current",
        holder_ref=lease["holder_ref"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        old_head="a" * 40,
        new_head="b" * 40,
    )
    assert advanced["expected_head"] == "b" * 40

    with pytest.raises(ValueError, match="lease_head_stale"):
        advance_lease_head(
            db_path,
            subject="work/current",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            old_head="a" * 40,
            new_head="c" * 40,
        )


def test_delete_lease_removes_lease_so_recreated_subject_cannot_inherit(
    tmp_path: Path,
) -> None:
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
    from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease

    db_path = tmp_path / "state.sqlite"
    acquire_lease(db_path, subject="work/feature", holder_ref="agent:test:case:agent-a")
    assert any(lease["subject"] == "work/feature" for lease in active_leases(db_path))

    removed = delete_lease(db_path, subject="work/feature")

    assert removed == 1
    assert all(lease["subject"] != "work/feature" for lease in active_leases(db_path))
    # A recreated same-named subject starts with no inherited lease.
    assert delete_lease(db_path, subject="work/feature") == 0


def test_active_leases_uses_read_only_fallback_when_default_connect_cannot_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from datetime import UTC
    from datetime import datetime
    from datetime import timedelta

    import ethos.adapters.store.state.lease.lifecycle.core as state
    import ethos.adapters.store.state.lease.projection as state_read

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    lease = state.acquire_lease(
        db_path, subject="work/feature", holder_ref="agent:test:case:agent-test"
    )
    real_connect = sqlite3.connect

    def flaky_connect(target, *args, **kwargs):
        if target == db_path:
            message = "unable to open database file"
            raise sqlite3.OperationalError(message)
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr(state_read.sqlite3, "connect", flaky_connect)

    leases = state_read.active_leases(db_path)

    assert [item["id"] for item in leases] == [lease["id"]]
    assert leases[0]["subject"] == "work/feature"
    assert datetime.fromisoformat(leases[0]["expires_at"]) > datetime.now(UTC) - timedelta(
        seconds=1
    )


def test_active_leases_returns_empty_when_all_sqlite_reads_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import ethos.adapters.store.state.lease.lifecycle.core as state
    import ethos.adapters.store.state.lease.projection as state_read

    db_path = tmp_path / "state.sqlite"
    state.acquire_lease(db_path, subject="work/feature", holder_ref="agent:test:case:agent-test")

    def always_fails(*_args: object, **_kwargs: object) -> object:
        message = "sqlite unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(state_read.sqlite3, "connect", always_fails)

    assert state_read.active_leases(db_path) == []

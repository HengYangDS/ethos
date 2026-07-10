from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.store.state.events import append_chronicle_event
from ethos.adapters.store.state.events import append_event
from ethos.adapters.store.state.events import initialize_state
from ethos.adapters.store.state.events import list_chronicle_events
from ethos.adapters.store.state.events import list_events
from ethos.adapters.store.state.lease import accept_lease_handoff
from ethos.adapters.store.state.lease import acquire_lease
from ethos.adapters.store.state.lease import active_leases
from ethos.adapters.store.state.lease import advance_lease_head
from ethos.adapters.store.state.lease import normalize_lease
from ethos.adapters.store.state.lease import offer_lease_handoff
from ethos.adapters.store.state.lease import renew_lease
from ethos.adapters.store.state.lease import resume_lease
from ethos.adapters.store.state.lease import revoke_lease

if TYPE_CHECKING:
    from pathlib import Path


def test_state_initialization_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"

    initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
    assert {
        "schema_migrations",
        "events",
        "chronicle_events",
        "sessions",
        "leases",
        "gate_runs",
        "action_runs",
        "evidence_index",
    } <= tables


def test_chronicle_append_is_transactional(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)

    append_chronicle_event(
        db_path,
        event_type="repository.audit",
        subject="repo:ethos",
        payload={"ok": True},
    )

    events = list_chronicle_events(db_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "repository.audit"
    assert events[0]["payload"] == {"ok": True}


def test_event_append_is_transactional(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)

    append_event(
        db_path,
        event_type="quality.claims",
        subject="repo:ethos",
        payload={"ok": True},
    )

    events = list_events(db_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "quality.claims"
    assert events[0]["payload"] == {"ok": True}


def test_active_leases_ignores_retired_lease_table_shape(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                resource text not null default '',
                expires_at text not null default '',
                created_at text not null
            )
            """
        )
        connection.commit()

    assert active_leases(db_path) == []


def test_active_leases_rejects_retired_lease_rows_with_resource_column(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                resource text not null default '',
                expires_at text not null default '',
                created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values ('lease:old', 'agent', 'repo', '2099-07-01T00:00:00+00:00',
                    '2026-07-01T00:00:00+00:00')
            """
        )
        connection.commit()

    assert active_leases(db_path) == []


def test_acquire_lease_migrates_retired_resource_column_schema(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease import acquire_lease

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table schema_migrations (
                version integer primary key,
                applied_at text not null
            )
            """
        )
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                resource text not null default '',
                expires_at text not null default '',
                created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values ('lease:old', 'agent-old', 'work/old',
                    '2099-07-01T00:00:00+00:00',
                    '2026-07-01T00:00:00+00:00')
            """
        )
        connection.commit()

    lease = acquire_lease(
        db_path,
        subject="work/new",
        holder_ref="agent:test:case:agent-new",
        ttl_seconds=60,
        payload={"path": "lane"},
    )

    leases = active_leases(db_path)
    assert lease["subject"] == "work/new"
    assert {item["subject"] for item in leases} == {"work/old", "work/new"}
    legacy = next(item for item in leases if item["subject"] == "work/old")
    assert legacy["holder_ref"] == ""
    assert legacy["normalization_state"] == "legacy_ambiguous"


def test_acquire_lease_leaves_current_lease_schema_unchanged(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease import acquire_lease

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
    from ethos.adapters.store.state.lease import acquire_lease

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
    from ethos.adapters.store.state.lease import acquire_lease

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


def test_normalize_lease_requires_same_legacy_holder_and_expected_head(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.sqlite"
    legacy = _insert_legacy_lease(
        db_path,
        subject="work/current",
        owner="agent:codex:thread:first",
    )

    normalized = normalize_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        expected_lease_id=legacy,
        expected_head="a" * 40,
    )

    assert normalized["normalization_state"] == "normalized"
    assert normalized["holder_ref"] == "agent:codex:thread:first"
    assert normalized["epoch"] == 1
    assert normalized["expected_head"] == "a" * 40

    with pytest.raises(ValueError, match="lease_holder_mismatch"):
        normalize_lease(
            db_path,
            subject="work/current",
            holder_ref="agent:claude:session:other",
            expected_lease_id=legacy,
            expected_head="a" * 40,
        )


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


def _insert_legacy_lease(db_path: Path, *, subject: str, owner: str) -> str:
    initialize_state(db_path)
    lease_id = "lease:legacy"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, ?, ?, ?)
            """,
            (lease_id, subject, owner, "2099-07-01T00:00:00+00:00", "{}"),
        )
        connection.commit()
    return lease_id


def test_acquire_lease_skips_empty_retired_resource_rows(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease import acquire_lease

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                resource text not null default '',
                expires_at text not null default '',
                created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values ('lease:blank', 'agent-old', '',
                    '2099-07-01T00:00:00+00:00',
                    '2026-07-01T00:00:00+00:00')
            """
        )
        connection.commit()

    acquire_lease(
        db_path,
        subject="work/new",
        holder_ref="agent:test:case:agent-new",
        ttl_seconds=60,
    )

    leases = active_leases(db_path)
    assert {item["subject"] for item in leases} == {"work/new"}


def test_initialize_state_leaves_unknown_lease_schema_unmigrated(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                expires_at text not null default ''
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, expires_at)
            values ('lease:unknown', 'agent-old', '2099-07-01T00:00:00+00:00')
            """
        )
        connection.commit()

    initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        columns = {row[1] for row in connection.execute("pragma table_info(leases)").fetchall()}
        rows = connection.execute("select id, owner, expires_at from leases").fetchall()
    assert columns == {"id", "owner", "expires_at"}
    assert rows == [("lease:unknown", "agent-old", "2099-07-01T00:00:00+00:00")]


def test_delete_lease_ignores_retired_resource_column_schema(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease import delete_lease

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            create table leases (
                id text primary key,
                owner text not null default '',
                resource text not null default '',
                expires_at text not null default '',
                created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values ('lease:old', 'agent', 'work/feature',
                    '2099-07-01T00:00:00+00:00',
                    '2026-07-01T00:00:00+00:00')
            """
        )
        connection.commit()

    assert delete_lease(db_path, subject="work/feature") == 0


def test_delete_lease_removes_lease_so_recreated_subject_cannot_inherit(
    tmp_path: Path,
) -> None:
    from ethos.adapters.store.state.lease import acquire_lease
    from ethos.adapters.store.state.lease import delete_lease

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

    import ethos.adapters.store.state.lease as state

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

    monkeypatch.setattr(state.sqlite3, "connect", flaky_connect)

    leases = state.active_leases(db_path)

    assert [item["id"] for item in leases] == [lease["id"]]
    assert leases[0]["subject"] == "work/feature"
    assert datetime.fromisoformat(leases[0]["expires_at"]) > datetime.now(UTC) - timedelta(
        seconds=1
    )


def test_active_leases_returns_empty_when_all_sqlite_reads_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import ethos.adapters.store.state.lease as state

    db_path = tmp_path / "state.sqlite"
    state.acquire_lease(db_path, subject="work/feature", holder_ref="agent:test:case:agent-test")

    def always_fails(*_args: object, **_kwargs: object) -> object:
        message = "sqlite unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(state.sqlite3, "connect", always_fails)

    assert state.active_leases(db_path) == []

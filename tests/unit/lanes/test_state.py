from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.store.state.lease.lifecycle.core import accept_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.lifecycle.core import offer_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.lifecycle.core import resume_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.schema import SCHEMA_VERSION
from ethos.adapters.store.state.schema import initialize_state

if TYPE_CHECKING:
    from pathlib import Path


def test_lease_initialization_uses_the_versioned_state_owner(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"

    acquire_lease(db_path, subject="work/current", holder_ref="agent:test:case:owner")

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
        versions = connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall()
    assert tables == {"leases", "schema_migrations"}
    assert versions == [(SCHEMA_VERSION,)]


def test_explicit_state_initialization_creates_only_owned_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"

    initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
    assert tables == {"leases", "schema_migrations"}
    assert SCHEMA_VERSION == 2


def _create_v1_state(db_path: Path, *, cache_rows: int = 0) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript(
            """
            create table schema_migrations (
              version integer primary key,
              applied_at text not null
            );
            insert into schema_migrations(version, applied_at)
            values (1, '2026-07-18T00:00:00+00:00');
            create table cache_entries (
              cache_key text primary key,
              payload_json text not null
            );
            create table leases (
              id text primary key,
              subject text not null,
              owner text not null,
              expires_at text not null,
              payload_json text not null
            );
            insert into leases(id, subject, owner, expires_at, payload_json)
            values ('lease:current', 'work/current', 'agent:test:case:owner',
                    '2099-07-01T00:00:00+00:00', '{}');
            create table unrelated_state (
              id integer primary key,
              payload_json text not null
            );
            insert into unrelated_state(id, payload_json) values (1, '{}');
            """
        )
        for index in range(cache_rows):
            connection.execute(
                "insert into cache_entries(cache_key, payload_json) values (?, '{}')",
                (f"cache:{index}",),
            )
        connection.commit()


def test_initialize_state_migrates_empty_cache_without_deleting_existing_state(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    _create_v1_state(db_path)

    initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
        versions = connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall()
        leases = connection.execute("select id, subject from leases").fetchall()
        unrelated_state = connection.execute(
            "select id, payload_json from unrelated_state"
        ).fetchall()
    assert "cache_entries" not in tables
    assert versions == [(1,), (2,)]
    assert leases == [("lease:current", "work/current")]
    assert unrelated_state == [(1, "{}")]


def test_initialize_state_fails_closed_when_retired_cache_is_not_empty(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    _create_v1_state(db_path, cache_rows=1)

    with pytest.raises(RuntimeError, match="state_schema_v2_cache_entries_not_empty"):
        initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("select count(*) from cache_entries").fetchone() == (1,)
        assert connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall() == [(1,)]


def test_initialize_state_rolls_back_schema_and_preserves_journal_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    _create_v1_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        previous_mode = str(connection.execute("pragma journal_mode").fetchone()[0])

    def fail_timestamp() -> str:
        msg = "clock unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr("ethos.adapters.store.state.schema.now", fail_timestamp)

    with pytest.raises(RuntimeError, match="clock unavailable"):
        initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
        versions = connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall()
        current_mode = str(connection.execute("pragma journal_mode").fetchone()[0])
    assert "cache_entries" in tables
    assert versions == [(1,)]
    assert current_mode == previous_mode == "delete"


def test_initialize_state_v2_is_idempotent_and_preserves_leases(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values ('lease:current', 'work/current', 'agent:test:case:owner',
                    '2099-07-01T00:00:00+00:00', '{}')
            """
        )
        connection.commit()

    initialize_state(db_path)
    initialize_state(db_path)

    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute(
            "select version from schema_migrations order by version"
        ).fetchall() == [(2,)]
        assert connection.execute("select id, subject from leases").fetchall() == [
            ("lease:current", "work/current")
        ]


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


def test_active_leases_reads_through_the_read_only_state_uri(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import ethos.adapters.store.state.lease.lifecycle.core as state
    import ethos.adapters.store.state.lease.projection as state_read

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    lease = state.acquire_lease(
        db_path, subject="work/feature", holder_ref="agent:test:case:agent-test"
    )
    real_connect = sqlite3.connect
    connections: list[tuple[str, bool]] = []

    def recording_connect(target, *args, **kwargs):
        connections.append((str(target), kwargs.get("uri") is True))
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr(state_read.sqlite3, "connect", recording_connect)

    leases = state_read.active_leases(db_path)

    assert [item["id"] for item in leases] == [lease["id"]]
    assert leases[0]["subject"] == "work/feature"
    assert connections
    assert all(is_uri and "mode=ro" in target for target, is_uri in connections)


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

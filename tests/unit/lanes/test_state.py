from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.schema as state_schema
from ethos.adapters.store.state.lease.lifecycle.core import accept_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.lifecycle.core import offer_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.lifecycle.core import resume_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.effects import update_lease_payload
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.schema import initialize_state
from ethos.adapters.store.state.schema import initialize_state_connection

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
    assert tables == {"leases"}


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
        subject_unique_indexes = [
            row[1]
            for row in connection.execute("pragma index_list(leases)")
            if row[2]
            and [
                column[0]
                for column in connection.execute(
                    "select name from pragma_index_info(?) order by seqno", (row[1],)
                )
            ]
            == ["subject"]
        ]
    assert tables == {"leases"}
    assert subject_unique_indexes == ["leases_subject_unique"]


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "create unique index invalid on leases(subject) where owner = 'agent:test:case:owner'",
        "create unique index invalid on leases(subject collate nocase)",
    ],
)
def test_initialize_state_rejects_noncanonical_subject_uniqueness(
    tmp_path: Path, replacement: str
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("drop index leases_subject_unique")
        if replacement:
            connection.execute(replacement)
        connection.commit()
    with pytest.raises(RuntimeError, match="state_schema_lease_subject_unique_missing"):
        initialize_state(db_path)


def test_initialize_state_rejects_nonprimary_lease_id(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript("""
            create table leases(id text, subject text not null, owner text not null, expires_at text not null, payload_json text not null);
            create unique index leases_subject_unique on leases(subject);
        """)
        connection.commit()
    with pytest.raises(RuntimeError, match="state_schema_lease_table_definition_mismatch"):
        initialize_state(db_path)


def test_initialize_state_rejects_lease_trigger_that_mutates_foreign_table(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            "create table legacy_state(id integer primary key, touched integer not null default 0)"
        )
        connection.execute(
            """
            create trigger leases_touch_legacy
            after insert on leases
            begin
                update legacy_state set touched = touched + 1;
            end
            """
        )
        connection.commit()
    with pytest.raises(RuntimeError, match="state_schema_lease_trigger_present"):
        initialize_state(db_path)


def test_initialize_state_preserves_foreign_shared_state_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("create table legacy_state(id integer primary key)")
        connection.commit()
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("select count(*) from legacy_state").fetchone() == (0,)


def test_initialize_state_rejects_retired_resource_lease_schema(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    db_path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript(
            "create table leases(id text primary key, owner text, resource text, expires_at text, created_at text); insert into leases values ('lease:old', 'owner', 'work/old', '2099-01-01T00:00:00+00:00', '2026-07-01T00:00:00+00:00');"
        )
        connection.commit()
    with pytest.raises(RuntimeError, match="state_schema_lease_table_definition_mismatch"):
        initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("select id, resource from leases").fetchall() == [
            ("lease:old", "work/old")
        ]


def test_initialize_state_rolls_back_schema_and_preserves_journal_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    monkeypatch.setattr(state_schema, "SCHEMA", (*state_schema.SCHEMA, "invalid sql"))
    with pytest.raises(sqlite3.OperationalError, match="syntax error"):
        initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
        current_mode = str(connection.execute("pragma journal_mode").fetchone()[0])
    assert tables == set()
    assert current_mode == "delete"


def test_initialize_state_v3_is_idempotent_and_preserves_leases(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            "\n            insert into leases(id, subject, owner, expires_at, payload_json)\n            values ('lease:current', 'work/current', 'agent:test:case:owner',\n                    '2099-07-01T00:00:00+00:00', '{}')\n            "
        )
        connection.commit()
    initialize_state(db_path)
    initialize_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
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


def test_acquire_lease_sets_wal_before_transaction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_connect = sqlite3.connect
    events: list[str] = []

    class Connection:
        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def execute(self, sql, *args):
            events.append(sql.strip().lower())
            return self.connection.execute(sql, *args)

    monkeypatch.setattr(
        "ethos.adapters.store.state.lease.lifecycle.core.sqlite3.connect",
        lambda path: Connection(real_connect(path)),
    )
    acquire_lease(
        tmp_path / "state.sqlite", subject="work/current", holder_ref="agent:test:case:owner"
    )
    assert events.index("pragma journal_mode = wal") < events.index("begin immediate")


def test_acquire_lease_wal_failure_precedes_persistence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "state.sqlite"
    real_connect = sqlite3.connect

    class Connection:
        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def execute(self, sql, *args):
            if sql.strip().lower() == "pragma journal_mode = wal":
                message = "wal unavailable"
                raise sqlite3.OperationalError(message)
            return self.connection.execute(sql, *args)

    monkeypatch.setattr(
        "ethos.adapters.store.state.lease.lifecycle.core.sqlite3.connect",
        lambda path: Connection(real_connect(path)),
    )
    with pytest.raises(sqlite3.OperationalError, match="wal unavailable"):
        acquire_lease(db_path, subject="work/current", holder_ref="agent:test:case:owner")
    with closing(real_connect(db_path)) as connection:
        assert (
            connection.execute("select name from sqlite_master where name = 'leases'").fetchone()
            is None
        )


def test_acquire_lease_rejects_duplicate_current_lane_incarnation(tmp_path: Path) -> None:
    from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease

    db_path = tmp_path / "state.sqlite"
    first = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"lane_incarnation_id": "lane-incarnation:one", "expected_head": "a" * 40},
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
    with closing(sqlite3.connect(db_path)) as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into leases values ('lease:duplicate', 'work/current', 'agent:test:case:other', '2099-01-01T00:00:00+00:00', '{}')"
        )


def test_acquire_lease_normalizes_holder_generation_and_timestamps(tmp_path: Path) -> None:
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


def test_renew_and_resume_require_current_generation_and_same_holder(tmp_path: Path) -> None:
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
        expected_expires_at=lease["expires_at"],
        expected_payload_sha256=lease["payload_sha256"],
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
            expected_expires_at=renewed["expires_at"],
            expected_payload_sha256=renewed["payload_sha256"],
        )
    with pytest.raises(ValueError, match="lease_not_expired"):
        resume_lease(
            db_path,
            subject="work/current",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            expected_head="a" * 40,
            expected_expires_at=renewed["expires_at"],
            expected_payload_sha256=renewed["payload_sha256"],
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
        expected_expires_at=expired["expires_at"],
        expected_payload_sha256=expired["payload_sha256"],
    )
    assert resumed["lease_id"] == expired["lease_id"]
    assert resumed["epoch"] == expired["epoch"]


def test_handoff_offer_accept_changes_holder_and_increments_epoch(tmp_path: Path) -> None:
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
        expected_expires_at=lease["expires_at"],
        expected_payload_sha256=lease["payload_sha256"],
    )
    offered = active_leases(db_path)[0]
    accepted = accept_lease_handoff(
        db_path,
        subject="work/current",
        holder_ref=lease["holder_ref"],
        target_holder_ref="agent:claude:session:second",
        offer_id=offer["offer_id"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        expected_head="a" * 40,
        expected_expires_at=offered["expires_at"],
        expected_payload_sha256=offered["payload_sha256"],
        holder_quiesced=True,
    )
    assert accepted["holder_ref"] == "agent:claude:session:second"
    assert accepted["epoch"] == lease["epoch"] + 1
    assert accepted["lease_id"] == lease["lease_id"]
    assert accepted["payload"]["handoff_state"] == "accepted"


def test_handoff_offer_rejects_empty_current_holder(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": "a" * 40},
    )
    with pytest.raises(ValueError, match="lease_holder_mismatch"):
        offer_lease_handoff(
            db_path,
            subject="work/current",
            holder_ref="",
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            target_holder_ref="agent:claude:session:second",
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        )


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
        expected_expires_at=lease["expires_at"],
        expected_payload_sha256=lease["payload_sha256"],
    )
    assert removed["revoked"] is True
    assert active_leases(db_path) == []


@pytest.mark.parametrize("mutation", ["renew", "offer"])
def test_revoke_lease_rejects_stale_exact_candidate(tmp_path: Path, mutation: str) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/example",
        holder_ref="agent:test:case:source",
        payload={"expected_head": "a" * 40},
    )
    if mutation == "renew":
        renew_lease(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
            ttl_seconds=120,
        )
    else:
        offer_lease_handoff(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            target_holder_ref="agent:test:case:target",
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        )
    with pytest.raises(ValueError, match="lease_maintenance_candidate_drift"):
        revoke_lease(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        )
    assert active_leases(db_path)[0]["subject"] == "work/example"


@pytest.mark.parametrize("mutation", ["renew", "offer", "revoke"])
def test_lease_mutation_validates_schema_inside_its_writer_transaction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str
) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/example",
        holder_ref="agent:test:case:source",
        payload={"expected_head": "a" * 40},
    )
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("drop index leases_subject_unique")
        connection.commit()
    called = False

    def validated(connection: sqlite3.Connection) -> None:
        nonlocal called
        called = True
        assert connection.in_transaction
        initialize_state_connection(connection)

    monkeypatch.setattr(
        "ethos.adapters.store.state.lease.lifecycle.core.initialize_state_connection", validated
    )
    monkeypatch.setattr(
        "ethos.adapters.store.state.lease.lifecycle.effects.initialize_state_connection", validated
    )
    operation = {
        "renew": lambda: renew_lease(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        ),
        "offer": lambda: offer_lease_handoff(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            target_holder_ref="agent:test:case:target",
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        ),
        "revoke": lambda: revoke_lease(
            db_path,
            subject="work/example",
            holder_ref=lease["holder_ref"],
            expected_lease_id=lease["lease_id"],
            expected_epoch=lease["epoch"],
            expected_head="a" * 40,
            expected_expires_at=lease["expires_at"],
            expected_payload_sha256=lease["payload_sha256"],
        ),
    }[mutation]
    with pytest.raises(RuntimeError, match="state_schema_lease_subject_unique_missing"):
        operation()
    assert called
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute("select id from leases").fetchall() == [(lease["lease_id"],)]


def test_advance_lease_head_is_generation_bound_compare_and_swap(tmp_path: Path) -> None:
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
        expected_expires_at=lease["expires_at"],
        expected_payload_sha256=lease["payload_sha256"],
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
            expected_expires_at=advanced["expires_at"],
            expected_payload_sha256=advanced["payload_sha256"],
        )


def test_update_lease_payload_requires_the_complete_current_generation(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    lease = acquire_lease(
        db_path,
        subject="work/current",
        holder_ref="agent:codex:thread:first",
        payload={"expected_head": "a" * 40},
    )
    renewed = renew_lease(
        db_path,
        subject="work/current",
        holder_ref=lease["holder_ref"],
        expected_lease_id=lease["lease_id"],
        expected_epoch=lease["epoch"],
        expected_head="a" * 40,
        expected_expires_at=lease["expires_at"],
        expected_payload_sha256=lease["payload_sha256"],
    )
    with pytest.raises(ValueError, match="lease_maintenance_candidate_drift"):
        update_lease_payload(db_path, candidate=lease, payload={"claim_id": "stale"})
    updated = update_lease_payload(db_path, candidate=renewed, payload={"claim_id": "current"})
    assert updated["claim_id"] == "current"


def test_active_leases_reads_through_the_read_only_state_uri(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
    assert all((is_uri and "mode=ro" in target for target, is_uri in connections))


def test_active_leases_propagates_sqlite_read_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ethos.adapters.store.state.lease.lifecycle.core as state
    import ethos.adapters.store.state.lease.projection as state_read

    db_path = tmp_path / "state.sqlite"
    state.acquire_lease(db_path, subject="work/feature", holder_ref="agent:test:case:agent-test")

    def always_fails(*_args: object, **_kwargs: object) -> object:
        message = "sqlite unavailable"
        raise sqlite3.OperationalError(message)

    monkeypatch.setattr(state_read.sqlite3, "connect", always_fails)
    with pytest.raises(sqlite3.OperationalError, match="sqlite unavailable"):
        state_read.active_leases(db_path)


def test_active_leases_rejects_noncanonical_v3_schema(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    acquire_lease(db_path, subject="work/current", holder_ref="agent:test:case:owner")
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("drop index leases_subject_unique")
        connection.commit()
    with pytest.raises(RuntimeError, match="state_schema_lease_subject_unique_missing"):
        active_leases(db_path)

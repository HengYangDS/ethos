from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

from ethos.adapters.store.state import active_leases
from ethos.adapters.store.state import append_chronicle_event
from ethos.adapters.store.state import append_event
from ethos.adapters.store.state import initialize_state
from ethos.adapters.store.state import list_chronicle_events
from ethos.adapters.store.state import list_events

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_delete_lease_removes_lease_so_recreated_subject_cannot_inherit(
    tmp_path: Path,
) -> None:
    from ethos.adapters.store.state import acquire_lease
    from ethos.adapters.store.state import delete_lease

    db_path = tmp_path / "state.sqlite"
    acquire_lease(db_path, subject="work/feature", owner="agent-a")
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

    from ethos.adapters.store import state

    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    lease = state.acquire_lease(db_path, subject="work/feature", owner="agent:test")
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

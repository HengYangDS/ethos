"""Ignored SQLite Chronicle and event-log owner."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = 1

# Whitelist of event tables. SQL below interpolates the table name (an internal
# constant, never external input); this allowlist makes that guarantee explicit
# and defensive — any other value raises before a query is built.
SCHEMA = (
    """
    create table if not exists schema_migrations (
      version integer primary key,
      applied_at text not null
    )
    """,
    """
    create table if not exists events (
      id integer primary key autoincrement,
      created_at text not null,
      event_type text not null,
      subject text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists chronicle_events (
      id integer primary key autoincrement,
      created_at text not null,
      event_type text not null,
      subject text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists sessions (
      id text primary key,
      owner text not null,
      state text not null,
      created_at text not null,
      updated_at text not null
    )
    """,
    """
    create table if not exists leases (
      id text primary key,
      subject text not null,
      owner text not null,
      expires_at text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists gate_runs (
      id text primary key,
      gate text not null,
      state text not null,
      started_at text not null,
      finished_at text,
      payload_json text not null
    )
    """,
    """
    create table if not exists action_runs (
      id text primary key,
      action_id text not null,
      state text not null,
      started_at text not null,
      finished_at text,
      payload_json text not null
    )
    """,
    """
    create table if not exists evidence_index (
      id text primary key,
      evidence_ref text not null,
      digest text,
      head text,
      payload_json text not null
    )
    """,
)


def _migrate_retired_lease_schema(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "leases"):
        return
    columns = {str(row[1]) for row in connection.execute("pragma table_info(leases)").fetchall()}
    current = {"id", "subject", "owner", "expires_at", "payload_json"}
    retired = {"id", "owner", "resource", "expires_at", "created_at"}
    if current.issubset(columns):
        return
    if not retired.issubset(columns):
        return
    rows = connection.execute(
        """
        select id, resource, owner, expires_at
        from leases
        order by id
        """
    ).fetchall()
    connection.execute("alter table leases rename to leases_retired_resource")
    connection.execute(
        """
        create table leases (
          id text primary key,
          subject text not null,
          owner text not null,
          expires_at text not null,
          payload_json text not null
        )
        """
    )
    for row in rows:
        subject = str(row[1] or "")
        if not subject:
            continue
        connection.execute(
            """
            insert or replace into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, ?, ?, ?)
            """,
            (row[0], subject, row[2], row[3], "{}"),
        )
    connection.execute("drop table leases_retired_resource")


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type = 'table' and name = ?",
        (table,),
    ).fetchone()
    return row is not None


def now() -> str:
    return datetime.now(UTC).isoformat()


def initialize_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma foreign_keys = on")
        _migrate_retired_lease_schema(connection)
        for statement in SCHEMA:
            connection.execute(statement)
        connection.execute(
            "insert or ignore into schema_migrations(version, applied_at) values (?, ?)",
            (SCHEMA_VERSION, now()),
        )
        connection.commit()


_EVENT_TABLES = frozenset({"chronicle_events", "events"})
_INSERT_EVENT_SQL = {
    "chronicle_events": """
    insert into chronicle_events(created_at, event_type, subject, payload_json)
    values (?, ?, ?, ?)
    """,
    "events": """
    insert into events(created_at, event_type, subject, payload_json)
    values (?, ?, ?, ?)
    """,
}
_SELECT_EVENT_SQL = {
    "chronicle_events": """
    select id, created_at, event_type, subject, payload_json
    from chronicle_events
    order by id
    """,
    "events": """
    select id, created_at, event_type, subject, payload_json
    from events
    order by id
    """,
}


def safe_table(table: str) -> str:
    if table not in _EVENT_TABLES:
        msg = f"unknown event table: {table!r}"
        raise ValueError(msg)
    return table


def insert_event_sql(table: str) -> str:
    return _INSERT_EVENT_SQL[safe_table(table)]


def select_event_sql(table: str) -> str:
    return _SELECT_EVENT_SQL[safe_table(table)]


def append_chronicle_event(
    db_path: Path,
    *,
    event_type: str,
    subject: str,
    payload: dict[str, Any],
) -> None:
    initialize_state(db_path)
    _append_event_row(
        db_path,
        table="chronicle_events",
        event_type=event_type,
        subject=subject,
        payload=payload,
    )


def append_event(
    db_path: Path,
    *,
    event_type: str,
    subject: str,
    payload: dict[str, Any],
) -> None:
    initialize_state(db_path)
    _append_event_row(
        db_path,
        table="events",
        event_type=event_type,
        subject=subject,
        payload=payload,
    )


def _append_event_row(
    db_path: Path,
    *,
    table: str,
    event_type: str,
    subject: str,
    payload: dict[str, Any],
) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            insert_event_sql(table),
            (now(), event_type, subject, json.dumps(payload, sort_keys=True)),
        )
        connection.commit()


def list_chronicle_events(db_path: Path) -> list[dict[str, Any]]:
    return _list_event_rows(db_path, table="chronicle_events")


def list_events(db_path: Path) -> list[dict[str, Any]]:
    return _list_event_rows(db_path, table="events")


def _list_event_rows(db_path: Path, *, table: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute(select_event_sql(table)).fetchall()
    return [
        {
            "id": row[0],
            "created_at": row[1],
            "event_type": row[2],
            "subject": row[3],
            "payload": json.loads(row[4]),
        }
        for row in rows
    ]

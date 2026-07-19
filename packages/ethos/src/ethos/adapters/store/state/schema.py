"""Shared ignored SQLite state schema and migration owner."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = 2

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


def _migrate_to_schema_v2(connection: sqlite3.Connection) -> None:
    versions = {
        int(row[0])
        for row in connection.execute("select version from schema_migrations").fetchall()
    }
    if SCHEMA_VERSION in versions:
        return
    if _table_exists(connection, "cache_entries"):
        row = connection.execute("select count(*) from cache_entries").fetchone()
        if row is None or int(row[0]) != 0:
            message = "state_schema_v2_cache_entries_not_empty"
            raise RuntimeError(message)
        connection.execute("drop table cache_entries")
    connection.execute(
        "insert into schema_migrations(version, applied_at) values (?, ?)",
        (SCHEMA_VERSION, now()),
    )


def now() -> str:
    return datetime.now(UTC).isoformat()


def initialize_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma foreign_keys = on")
        try:
            connection.execute("begin immediate")
            _migrate_retired_lease_schema(connection)
            for statement in SCHEMA:
                connection.execute(statement)
            _migrate_to_schema_v2(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

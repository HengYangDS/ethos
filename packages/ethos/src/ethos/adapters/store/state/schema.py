"""Shared ignored SQLite state schema and migration owner."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = 2

SCHEMA = (
    """
    create table if not exists schema_migrations (
      version integer primary key,
      applied_at text not null
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
)


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


def read_only_state_uri(db_path: Path) -> str:
    """Return a SQLite URI that cannot create or mutate state sidecars."""
    return f"{db_path.resolve().as_uri()}?mode=ro"


def initialize_state_connection(connection: sqlite3.Connection) -> None:
    """Apply state schema migrations inside the caller's active transaction."""
    for statement in SCHEMA:
        connection.execute(statement)
    _migrate_to_schema_v2(connection)


def initialize_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        try:
            connection.execute("begin immediate")
            initialize_state_connection(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        connection.execute("pragma journal_mode = wal")


def state_database_inventory(db_path: Path) -> dict[str, Any]:
    """Return a read-only digest and schema inventory for one state database."""
    if not db_path.exists():
        return {
            "path": db_path.as_posix(),
            "exists": False,
            "digest": "",
            "schema_versions": [],
            "target_schema_version": SCHEMA_VERSION,
            "cache_entries": {"exists": False, "row_count": 0},
        }
    try:
        with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "select name from sqlite_master where type = 'table'"
                ).fetchall()
            }
            versions = (
                [
                    int(row[0])
                    for row in connection.execute(
                        "select version from schema_migrations order by version"
                    ).fetchall()
                ]
                if "schema_migrations" in tables
                else []
            )
            cache_count = (
                int(connection.execute("select count(*) from cache_entries").fetchone()[0])
                if "cache_entries" in tables
                else 0
            )
            digest = hashlib.sha256(connection.serialize()).hexdigest()
    except sqlite3.Error as exc:
        return {
            "path": db_path.as_posix(),
            "exists": True,
            "digest": "",
            "schema_versions": [],
            "target_schema_version": SCHEMA_VERSION,
            "cache_entries": {"exists": False, "row_count": 0},
            "error": exc.__class__.__name__,
        }
    return {
        "path": db_path.as_posix(),
        "exists": True,
        "digest": digest,
        "schema_versions": versions,
        "target_schema_version": SCHEMA_VERSION,
        "cache_entries": {
            "exists": "cache_entries" in tables,
            "row_count": cache_count,
        },
    }

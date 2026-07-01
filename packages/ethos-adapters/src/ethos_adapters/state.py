from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


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
    """
    create table if not exists cache_entries (
      cache_key text primary key,
      action_id text not null,
      created_at text not null,
      payload_json text not null
    )
    """,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def initialize_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma foreign_keys = on")
        for statement in SCHEMA:
            connection.execute(statement)
        connection.execute(
            "insert or ignore into schema_migrations(version, applied_at) values (?, ?)",
            (SCHEMA_VERSION, _now()),
        )
        connection.commit()


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


def acquire_lease(
    db_path: Path,
    *,
    subject: str,
    owner: str,
    ttl_seconds: int = 86_400,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initialize_state(db_path)
    lease_id = f"lease:{uuid.uuid4()}"
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    payload_json = json.dumps(payload or {}, sort_keys=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, ?, ?, ?)
            """,
            (lease_id, subject, owner, expires_at.isoformat(), payload_json),
        )
        connection.commit()
    return {
        "id": lease_id,
        "subject": subject,
        "owner": owner,
        "expires_at": expires_at.isoformat(),
        "payload": payload or {},
    }


def update_lease_payload(
    db_path: Path,
    *,
    subject: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    initialize_state(db_path)
    matching = [
        lease
        for lease in active_leases(db_path)
        if lease["subject"] == subject
    ]
    if not matching:
        return {}
    lease = matching[-1]
    merged_payload = dict(lease["payload"])
    merged_payload.update(payload)
    with sqlite3.connect(db_path) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            """
            update leases
            set payload_json = ?
            where id = ?
            """,
            (json.dumps(merged_payload, sort_keys=True), lease["id"]),
        )
        connection.commit()
    updated = dict(lease)
    updated["payload"] = merged_payload
    return updated


def active_leases(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    now = datetime.now(UTC)
    with sqlite3.connect(db_path) as connection:
        columns = _table_columns(connection, "leases")
        if not {"id", "subject", "owner", "expires_at", "payload_json"}.issubset(
            columns
        ):
            return []
        rows = connection.execute(
            """
            select id, subject, owner, expires_at, payload_json
            from leases
            order by subject, id
            """,
        ).fetchall()
    leases: list[dict[str, Any]] = []
    for row in rows:
        try:
            expires_at = datetime.fromisoformat(row[3])
        except (TypeError, ValueError):
            continue
        if expires_at <= now:
            continue
        leases.append(
            {
                "id": row[0],
                "subject": row[1],
                "owner": row[2],
                "expires_at": row[3],
                "payload": _json_object(row[4]),
            }
        )
    return leases


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"pragma table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def _json_object(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _append_event_row(
    db_path: Path,
    *,
    table: str,
    event_type: str,
    subject: str,
    payload: dict[str, Any],
) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            f"""
            insert into {table}(created_at, event_type, subject, payload_json)
            values (?, ?, ?, ?)
            """,
            (_now(), event_type, subject, json.dumps(payload, sort_keys=True)),
        )
        connection.commit()


def list_chronicle_events(db_path: Path) -> list[dict[str, Any]]:
    return _list_event_rows(db_path, table="chronicle_events")


def list_events(db_path: Path) -> list[dict[str, Any]]:
    return _list_event_rows(db_path, table="events")


def _list_event_rows(db_path: Path, *, table: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            f"""
            select id, created_at, event_type, subject, payload_json
            from {table}
            order by id
            """
        ).fetchall()
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

"""Ignored SQLite Chronicle and event-log owner."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.schema import initialize_state
from ethos.adapters.store.state.schema import now

if TYPE_CHECKING:
    from pathlib import Path

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

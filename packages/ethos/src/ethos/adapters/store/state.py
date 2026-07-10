from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = 1

# Whitelist of event tables. SQL below interpolates the table name (an internal
# constant, never external input); this allowlist makes that guarantee explicit
# and defensive — any other value raises before a query is built.
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


def _safe_table(table: str) -> str:
    if table not in _EVENT_TABLES:
        msg = f"unknown event table: {table!r}"
        raise ValueError(msg)
    return table


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
    columns = _table_columns(connection, "leases")
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


def _now() -> str:
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
    supplied_payload = dict(payload or {})
    current = [lease for lease in active_leases(db_path) if lease["subject"] == subject]
    if current:
        raise ValueError(f"lane_lease_conflict:{subject}")
    lane_incarnation_id = str(
        supplied_payload.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"
    )
    holder_ref = _holder_ref(owner)
    normalized_payload = {
        **supplied_payload,
        "lane_incarnation_id": lane_incarnation_id,
        "lease_id": lease_id,
        "lane_ref": subject,
        "holder_ref": holder_ref,
        "epoch": int(supplied_payload.get("epoch") or 1),
        "issued_at": str(supplied_payload.get("issued_at") or now.isoformat()),
        "renewed_at": str(supplied_payload.get("renewed_at") or now.isoformat()),
        "expected_head": str(supplied_payload.get("expected_head") or ""),
        "claim_id": str(supplied_payload.get("claim_id") or ""),
        "path_scope": _string_list(supplied_payload.get("path_scope")),
        "coordination_scope": "git_common_directory",
        "mints_authority": False,
        "filesystem_fence": False,
        "distributed_lock": False,
    }
    if not holder_ref:
        normalized_payload["legacy_holder"] = owner
        normalized_payload["normalization_state"] = "legacy_holder_unverified"
    else:
        normalized_payload["normalization_state"] = "normalized"
    payload_json = json.dumps(normalized_payload, sort_keys=True)
    with closing(sqlite3.connect(db_path)) as connection:
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
        **_lease_contract_fields(normalized_payload),
        "payload": normalized_payload,
    }


def update_lease_payload(
    db_path: Path,
    *,
    subject: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    initialize_state(db_path)
    matching = [lease for lease in active_leases(db_path) if lease["subject"] == subject]
    if len(matching) != 1:
        return {}
    lease = matching[0]
    merged_payload = dict(lease["payload"])
    merged_payload.update(payload)
    with closing(sqlite3.connect(db_path)) as connection:
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


def delete_lease(db_path: Path, *, subject: str) -> int:
    """Delete all leases for a subject (work-lane branch). Returns the count removed.

    Called on lane retirement so a lease cannot outlive its lane — a destroyed and
    later recreated same-named branch must not present a resolvable stale lease
    (a truth store that cannot be proved is not a trustworthy store).
    """
    if not db_path.exists():
        return 0
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        columns = _table_columns(connection, "leases")
        if "subject" not in columns:
            return 0
        cursor = connection.execute(
            "delete from leases where subject = ?",
            (subject,),
        )
        connection.commit()
        return cursor.rowcount


def active_leases(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    now = datetime.now(UTC)
    try:
        rows = _lease_rows(db_path)
    except sqlite3.Error:
        return []
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
                **_lease_contract_fields(_json_object(row[4])),
                "payload": _json_object(row[4]),
            }
        )
    return leases


def _lease_rows(db_path: Path) -> list[sqlite3.Row | tuple[Any, ...]]:
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            return _select_lease_rows(connection)
    except sqlite3.Error:
        uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            return _select_lease_rows(connection)


def _select_lease_rows(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row | tuple[Any, ...]]:
    columns = _table_columns(connection, "leases")
    if not {"id", "subject", "owner", "expires_at", "payload_json"}.issubset(columns):
        return []
    return connection.execute(
        """
        select id, subject, owner, expires_at, payload_json
        from leases
        order by subject, id
        """,
    ).fetchall()


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if table != "leases":
        msg = f"unknown state table: {table!r}"
        raise ValueError(msg)
    rows = connection.execute("pragma table_info(leases)").fetchall()
    return {str(row[1]) for row in rows}


def _json_object(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _holder_ref(value: str) -> str:
    try:
        return HolderRef.parse(value).serialize()
    except ValueError:
        return ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if str(item)]


def _lease_contract_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane_incarnation_id": str(payload.get("lane_incarnation_id") or ""),
        "lease_id": str(payload.get("lease_id") or ""),
        "lane_ref": str(payload.get("lane_ref") or ""),
        "holder_ref": str(payload.get("holder_ref") or ""),
        "epoch": int(payload.get("epoch") or 0),
        "issued_at": str(payload.get("issued_at") or ""),
        "renewed_at": str(payload.get("renewed_at") or ""),
        "expected_head": str(payload.get("expected_head") or ""),
        "claim_id": str(payload.get("claim_id") or ""),
        "path_scope": _string_list(payload.get("path_scope")),
        "normalization_state": str(payload.get("normalization_state") or "legacy_ambiguous"),
    }


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
            _insert_event_sql(table),
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
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute(_select_event_sql(table)).fetchall()
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


def _insert_event_sql(table: str) -> str:
    return _INSERT_EVENT_SQL[_safe_table(table)]


def _select_event_sql(table: str) -> str:
    return _SELECT_EVENT_SQL[_safe_table(table)]

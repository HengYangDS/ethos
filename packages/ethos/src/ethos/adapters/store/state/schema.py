"""Shared ignored SQLite state schema owner."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import git_common_dir

SCHEMA = (
    """
    create table if not exists leases (
      id text primary key,
      subject text not null,
      owner text not null,
      expires_at text not null,
      payload_json text not null
    )
    """,
    "create unique index leases_subject_unique on leases(subject)",
)
CLOSEOUT_FENCE_SCHEMA = (
    """
    create table if not exists closeout_fences (
      subject text not null,
      expected_head text not null,
      decision_id text not null,
      executor_ref text not null,
      accepted_branch text not null,
      accepted_head text not null,
      target_binding_digest text not null,
      payload_json text not null
    )
    """,
    "create unique index closeout_fences_subject_unique on closeout_fences(subject)",
)
_CANONICAL_LEASE_TABLE_SQL = (
    "CREATE TABLE leases (\n"
    "      id text primary key,\n"
    "      subject text not null,\n"
    "      owner text not null,\n"
    "      expires_at text not null,\n"
    "      payload_json text not null\n"
    "    )"
)
_CANONICAL_SUBJECT_INDEX_SQL = "CREATE UNIQUE INDEX leases_subject_unique on leases(subject)"
_CANONICAL_CLOSEOUT_FENCE_TABLE_SQL = (
    "CREATE TABLE closeout_fences (\n"
    "      subject text not null,\n"
    "      expected_head text not null,\n"
    "      decision_id text not null,\n"
    "      executor_ref text not null,\n"
    "      accepted_branch text not null,\n"
    "      accepted_head text not null,\n"
    "      target_binding_digest text not null,\n"
    "      payload_json text not null\n"
    "    )"
)
_CANONICAL_CLOSEOUT_FENCE_INDEX_SQL = (
    "CREATE UNIQUE INDEX closeout_fences_subject_unique on closeout_fences(subject)"
)

_TABLE_COLUMNS = {
    "leases": (
        ("id", "TEXT", 0, None, 1, 0),
        ("subject", "TEXT", 1, None, 0, 0),
        ("owner", "TEXT", 1, None, 0, 0),
        ("expires_at", "TEXT", 1, None, 0, 0),
        ("payload_json", "TEXT", 1, None, 0, 0),
    ),
    "closeout_fences": (
        ("subject", "TEXT", 1, None, 0, 0),
        ("expected_head", "TEXT", 1, None, 0, 0),
        ("decision_id", "TEXT", 1, None, 0, 0),
        ("executor_ref", "TEXT", 1, None, 0, 0),
        ("accepted_branch", "TEXT", 1, None, 0, 0),
        ("accepted_head", "TEXT", 1, None, 0, 0),
        ("target_binding_digest", "TEXT", 1, None, 0, 0),
        ("payload_json", "TEXT", 1, None, 0, 0),
    ),
}


def _lease_table_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'leases'"
        ).fetchone()
        is not None
    )


def _normalized_sql(sql: str) -> str:
    return " ".join(sql.upper().split())


def _subject_unique_indexes(connection: sqlite3.Connection) -> list[tuple[bool, str, bool]]:
    indexes: list[tuple[bool, str, bool]] = []
    for row in connection.execute("pragma index_list(leases)"):
        if not row[2]:
            continue
        keys = [
            column
            for column in connection.execute(
                "select seqno, cid, name, desc, coll, key "
                "from pragma_index_xinfo(?) order by seqno",
                (row[1],),
            )
            if column[5]
        ]
        if len(keys) == 1 and str(keys[0][2]) == "subject":
            indexes.append((bool(row[4]), str(keys[0][4]).upper(), bool(keys[0][3])))
    return indexes


def _require_canonical_lease_objects(connection: sqlite3.Connection) -> None:
    table = connection.execute(
        "select sql from sqlite_master where type = 'table' and name = 'leases'"
    ).fetchone()
    index = connection.execute(
        "select sql from sqlite_master where type = 'index' and name = 'leases_subject_unique'"
    ).fetchone()
    if table is None or _normalized_sql(str(table[0])) != _normalized_sql(
        _CANONICAL_LEASE_TABLE_SQL
    ):
        message = "state_schema_lease_table_definition_mismatch"
        raise RuntimeError(message)
    if index is None or _normalized_sql(str(index[0])) != _normalized_sql(
        _CANONICAL_SUBJECT_INDEX_SQL
    ):
        message = "state_schema_lease_subject_unique_missing"
        raise RuntimeError(message)


def _require_exact_subject_uniqueness(connection: sqlite3.Connection) -> None:
    indexes = _subject_unique_indexes(connection)
    if indexes != [(False, "BINARY", False)]:
        message = "state_schema_lease_subject_unique_missing"
        raise RuntimeError(message)


def _require_exact_lease_table(connection: sqlite3.Connection) -> None:
    actual = tuple(
        (
            str(row[1]),
            str(row[2]).upper(),
            int(row[3]),
            row[4],
            int(row[5]),
            int(row[6]),
        )
        for row in connection.execute("pragma table_xinfo(leases)")
    )
    if actual != _TABLE_COLUMNS["leases"]:
        message = "state_schema_lease_table_definition_mismatch"
        raise RuntimeError(message)


def _require_no_lease_triggers(connection: sqlite3.Connection) -> None:
    if connection.execute(
        "select 1 from sqlite_master where type = 'trigger' and tbl_name = 'leases'"
    ).fetchone():
        message = "state_schema_lease_trigger_present"
        raise RuntimeError(message)


def read_only_state_uri(db_path: Path) -> str:
    """Return a SQLite URI that cannot create or mutate state sidecars."""
    return f"{db_path.resolve().as_uri()}?mode=ro"


def state_database(root: Path) -> Path:
    """Return the one repository-local state database shared by all worktrees."""
    common = git_common_dir(root)
    if not common:
        message = "git_common_directory_unavailable"
        raise ValueError(message)
    return Path(common).parent / ".ethos" / "state" / "state.sqlite"


def initialize_state_connection(connection: sqlite3.Connection) -> None:
    """Create or validate the lease-owned subset of shared local state."""
    if not connection.in_transaction:
        message = "state_schema_transaction_required"
        raise RuntimeError(message)
    if not _lease_table_exists(connection):
        for statement in SCHEMA:
            connection.execute(statement)
        return
    _require_exact_lease_table(connection)
    _require_canonical_lease_objects(connection)
    _require_exact_subject_uniqueness(connection)
    _require_no_lease_triggers(connection)


def validate_current_lease_schema(connection: sqlite3.Connection) -> bool:
    """Validate an existing lease table; report absence as an empty projection."""
    if not _lease_table_exists(connection):
        return False
    _require_exact_lease_table(connection)
    _require_canonical_lease_objects(connection)
    _require_exact_subject_uniqueness(connection)
    _require_no_lease_triggers(connection)
    return True


def _closeout_fence_table_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'closeout_fences'"
        ).fetchone()
        is not None
    )


def validate_current_closeout_fence_schema(connection: sqlite3.Connection) -> bool:
    """Validate the optional exact closeout-fence table without creating it."""
    if not _closeout_fence_table_exists(connection):
        return False
    actual = tuple(
        (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]), int(row[6]))
        for row in connection.execute("pragma table_xinfo(closeout_fences)")
    )
    table = connection.execute(
        "select sql from sqlite_master where type = 'table' and name = 'closeout_fences'"
    ).fetchone()
    index = connection.execute(
        "select sql from sqlite_master where type = 'index' "
        "and name = 'closeout_fences_subject_unique'"
    ).fetchone()
    if (
        actual != _TABLE_COLUMNS["closeout_fences"]
        or table is None
        or _normalized_sql(str(table[0])) != _normalized_sql(_CANONICAL_CLOSEOUT_FENCE_TABLE_SQL)
    ):
        message = "state_schema_closeout_fence_table_definition_mismatch"
        raise RuntimeError(message)
    if index is None or _normalized_sql(str(index[0])) != _normalized_sql(
        _CANONICAL_CLOSEOUT_FENCE_INDEX_SQL
    ):
        message = "state_schema_closeout_fence_subject_unique_missing"
        raise RuntimeError(message)
    if connection.execute(
        "select 1 from sqlite_master where type = 'trigger' and tbl_name = 'closeout_fences'"
    ).fetchone():
        message = "state_schema_closeout_fence_trigger_present"
        raise RuntimeError(message)
    return True


def initialize_closeout_fence_connection(connection: sqlite3.Connection) -> None:
    """Create or validate the optional closeout-fence table inside a writer transaction."""
    if not connection.in_transaction:
        message = "state_schema_transaction_required"
        raise RuntimeError(message)
    if validate_current_closeout_fence_schema(connection):
        return
    for statement in CLOSEOUT_FENCE_SCHEMA:
        connection.execute(statement)


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


def _closeout_fence_payload(raw: object) -> dict[str, Any]:
    payload = json.loads(str(raw))
    if not isinstance(payload, dict):
        message = "state_closeout_fence_payload_invalid"
        raise TypeError(message)
    return payload


def state_database_inventory(db_path: Path) -> dict[str, Any]:
    """Return a read-only digest and schema inventory for one state database."""
    if not db_path.exists():
        return {
            "path": db_path.as_posix(),
            "exists": False,
            "digest": "",
            "lease_schema": "absent",
            "closeout_fence_schema": "absent",
            "closeout_fence_count": 0,
            "closeout_fences": [],
        }
    try:
        with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
            lease_schema = "current" if validate_current_lease_schema(connection) else "absent"
            closeout_fence_schema = (
                "current" if validate_current_closeout_fence_schema(connection) else "absent"
            )
            try:
                closeout_fences = (
                    [
                        {
                            "subject": str(row[0]),
                            "expected_head": str(row[1]),
                            "decision_id": str(row[2]),
                            "executor_ref": str(row[3]),
                            "accepted_branch": str(row[4]),
                            "accepted_head": str(row[5]),
                            "target_binding_digest": str(row[6]),
                            "payload": _closeout_fence_payload(row[7]),
                        }
                        for row in connection.execute(
                            """select subject, expected_head, decision_id, executor_ref,
                            accepted_branch, accepted_head, target_binding_digest, payload_json
                            from closeout_fences order by subject"""
                        )
                    ]
                    if closeout_fence_schema == "current"
                    else []
                )
            except (RecursionError, TypeError, ValueError, sqlite3.Error) as exc:
                return {
                    "path": db_path.as_posix(),
                    "exists": True,
                    "digest": "",
                    "lease_schema": lease_schema,
                    "closeout_fence_schema": "invalid",
                    "closeout_fence_count": 0,
                    "closeout_fences": [],
                    "error": exc.__class__.__name__,
                }
            digest = hashlib.sha256(connection.serialize()).hexdigest()
    except (RuntimeError, json.JSONDecodeError, sqlite3.Error) as exc:
        return {
            "path": db_path.as_posix(),
            "exists": True,
            "digest": "",
            "lease_schema": "invalid",
            "closeout_fence_schema": "invalid",
            "closeout_fence_count": 0,
            "closeout_fences": [],
            "error": exc.__class__.__name__,
        }
    return {
        "path": db_path.as_posix(),
        "exists": True,
        "digest": digest,
        "lease_schema": lease_schema,
        "closeout_fence_schema": closeout_fence_schema,
        "closeout_fence_count": len(closeout_fences),
        "closeout_fences": closeout_fences,
    }

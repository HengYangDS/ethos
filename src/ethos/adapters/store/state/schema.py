"""Shared ignored SQLite state schema owner."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import git_common_dir
from ethos.contracts.coordination import LaneLease

SCHEMA = (
    """
    create table if not exists leases (
      lane_ref text primary key,
      holder_ref text not null,
      generation integer not null check (generation >= 1),
      expires_at text not null
    )
    """,
)
_COLUMNS = ("lane_ref", "holder_ref", "generation", "expires_at")
_LEGACY_COLUMNS = ("id", "subject", "owner", "expires_at", "payload_json")


def _lease_table_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'leases'"
        ).fetchone()
        is not None
    )


def _column_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in connection.execute("pragma table_xinfo(leases)"))


def _legacy_lease_schema(connection: sqlite3.Connection) -> bool:
    if _column_names(connection) != _LEGACY_COLUMNS:
        return False
    indexes = {
        (str(row[1]), bool(row[2]), str(row[3]), bool(row[4]))
        for row in connection.execute("pragma index_list(leases)")
    }
    if indexes != {
        ("leases_subject_unique", True, "c", False),
        ("sqlite_autoindex_leases_1", True, "pk", False),
    }:
        return False
    keys = tuple(
        (str(row[2]), bool(row[3]), str(row[4]).upper())
        for row in connection.execute("pragma index_xinfo(leases_subject_unique)")
        if row[5]
    )
    return (
        keys == (("subject", False, "BINARY"),)
        and not connection.execute(
            "select 1 from sqlite_master where type = 'trigger' and tbl_name = 'leases'"
        ).fetchone()
    )


def _validate_lease_schema(connection: sqlite3.Connection) -> None:
    if _column_names(connection) != _COLUMNS:
        msg = "state_schema_lease_table_definition_mismatch"
        raise RuntimeError(msg)
    indexes = tuple(
        (bool(row[2]), str(row[3]), bool(row[4]))
        for row in connection.execute("pragma index_list(leases)")
    )
    if indexes != ((True, "pk", False),):
        msg = "state_schema_lease_index_present"
        raise RuntimeError(msg)
    if connection.execute(
        "select 1 from sqlite_master where type = 'trigger' and tbl_name = 'leases'"
    ).fetchone():
        msg = "state_schema_lease_trigger_present"
        raise RuntimeError(msg)


def read_only_state_uri(db_path: Path) -> str:
    """Return a SQLite URI that cannot create or mutate state sidecars."""
    return f"{db_path.resolve().as_uri()}?mode=ro"


def local_state_root(root: Path) -> Path:
    """Return the Git-common state root inside the Git common directory."""
    common = git_common_dir(root)
    if not common:
        msg = "git_common_directory_unavailable"
        raise ValueError(msg)
    return Path(common) / "ethos"


def state_database(root: Path) -> Path:
    """Return the one repository-local state database shared by all worktrees."""
    return local_state_root(root) / "state.sqlite"


def initialize_state_connection(connection: sqlite3.Connection) -> None:
    """Create or validate the one minimal Lease relation inside a transaction."""
    if not connection.in_transaction:
        msg = "state_schema_transaction_required"
        raise RuntimeError(msg)
    if not _lease_table_exists(connection):
        connection.execute(SCHEMA[0])
    _validate_lease_schema(connection)


def state_schema_state(connection: sqlite3.Connection) -> str:
    """Classify the only admitted current and previous Lease schemas."""
    if not _lease_table_exists(connection):
        return "absent"
    try:
        _validate_lease_schema(connection)
    except RuntimeError:
        return "legacy" if _legacy_lease_schema(connection) else "incompatible"
    return "current"


def state_schema_report(root: Path) -> dict[str, object]:
    """Observe the exact Git-common Lease schema without mutating it."""
    database = state_database(root)
    report: dict[str, object] = {
        "path": database.as_posix(),
        "expected_state": "current",
        "expected_columns": list(_COLUMNS),
    }
    if not database.exists():
        return report | {
            "observed_state": "absent",
            "observed_columns": [],
            "row_count": 0,
        }
    try:
        with closing(sqlite3.connect(read_only_state_uri(database), uri=True)) as connection:
            observed = state_schema_state(connection)
            columns = list(_column_names(connection)) if _lease_table_exists(connection) else []
            row_count = (
                int(connection.execute("select count(*) from leases").fetchone()[0])
                if _lease_table_exists(connection)
                else 0
            )
    except sqlite3.Error as error:
        return report | {
            "observed_state": "unreadable",
            "observed_columns": [],
            "row_count": 0,
            "error": str(error) or error.__class__.__name__,
        }
    return report | {
        "observed_state": observed,
        "observed_columns": columns,
        "row_count": row_count,
    }


def prepare_state_transition(
    connection: sqlite3.Connection, *, reset: bool = False
) -> dict[str, object]:
    """Stage one terminal Lease schema transition inside the caller transaction."""
    if not connection.in_transaction:
        msg = "state_schema_transaction_required"
        raise RuntimeError(msg)
    before = state_schema_state(connection)
    if before == "current":
        row_count = int(connection.execute("select count(*) from leases").fetchone()[0])
        return {"before": before, "after": "current", "state": "recognized", "row_count": row_count}
    if before == "absent":
        connection.execute(SCHEMA[0])
        _validate_lease_schema(connection)
        return {"before": before, "after": "current", "state": "initialized", "row_count": 0}
    if reset:
        connection.execute("drop table leases")
        connection.execute(SCHEMA[0])
        _validate_lease_schema(connection)
        return {"before": before, "after": "current", "state": "reset", "row_count": 0}
    if before != "legacy":
        msg = "state_schema_migration_requires_reset"
        raise RuntimeError(msg)
    rows = _legacy_projection(connection)
    connection.execute("drop table leases")
    connection.execute(SCHEMA[0])
    connection.executemany(
        "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
        rows,
    )
    _validate_lease_schema(connection)
    return {"before": before, "after": "current", "state": "migrated", "row_count": len(rows)}


def _legacy_projection(connection: sqlite3.Connection) -> list[tuple[str, str, int, str]]:
    projected: list[tuple[str, str, int, str]] = []
    try:
        rows = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases order by subject"
        )
        for lease_id, subject, owner, expires_at, payload_json in rows:
            payload = json.loads(str(payload_json))
            _reject_legacy_row(invalid=not isinstance(payload, dict))
            generation = payload.get("epoch")
            _reject_legacy_row(
                invalid=payload.get("lease_id") not in {None, lease_id}
                or payload.get("lane_ref") != subject
                or payload.get("holder_ref") != owner
                or payload.get("expires_at") != expires_at
                or isinstance(generation, bool)
                or not isinstance(generation, int)
            )
            lease = LaneLease.model_validate(
                {
                    "lane_ref": subject,
                    "holder_ref": owner,
                    "generation": generation,
                    "expires_at": datetime.fromisoformat(str(expires_at)),
                }
            )
            projected.append(
                (
                    lease.lane_ref,
                    lease.holder_ref.serialize(),
                    lease.generation,
                    lease.expires_at.isoformat(),
                )
            )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        msg = "state_schema_migration_requires_reset"
        raise RuntimeError(msg) from error
    return projected


def _reject_legacy_row(*, invalid: bool) -> None:
    if invalid:
        raise TypeError


def validate_current_lease_schema(connection: sqlite3.Connection) -> bool:
    """Validate an existing terminal Lease table without mutating it."""
    if not _lease_table_exists(connection):
        return False
    if _legacy_lease_schema(connection):
        msg = "state_schema_migration_required"
        raise RuntimeError(msg)
    _validate_lease_schema(connection)
    return True

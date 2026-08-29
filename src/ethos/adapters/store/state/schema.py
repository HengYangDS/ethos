"""Shared ignored SQLite state schema owner."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir

if TYPE_CHECKING:
    import sqlite3

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


def _lease_table_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'leases'"
        ).fetchone()
        is not None
    )


def _column_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in connection.execute("pragma table_xinfo(leases)"))


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


def validate_current_lease_schema(connection: sqlite3.Connection) -> bool:
    """Validate an existing terminal Lease table without mutating it."""
    if not _lease_table_exists(connection):
        return False
    _validate_lease_schema(connection)
    return True

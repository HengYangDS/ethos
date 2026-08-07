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
      id text primary key,
      subject text not null,
      owner text not null,
      expires_at text not null,
      payload_json text not null
    )
    """,
    "create unique index leases_subject_unique on leases(subject)",
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

_TABLE_COLUMNS = {
    "leases": (
        ("id", "TEXT", 0, None, 1, 0),
        ("subject", "TEXT", 1, None, 0, 0),
        ("owner", "TEXT", 1, None, 0, 0),
        ("expires_at", "TEXT", 1, None, 0, 0),
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


def local_state_root(root: Path) -> Path:
    """Return the repository-family state root inside the Git common directory."""
    common = git_common_dir(root)
    if not common:
        message = "git_common_directory_unavailable"
        raise ValueError(message)
    return Path(common) / "ethos"


def state_database(root: Path) -> Path:
    """Return the one repository-local state database shared by all worktrees."""
    return local_state_root(root) / "state.sqlite"


def observed_state_database(root: Path) -> Path:
    """Return the sole initialized Lease authority visible before migration."""
    current = state_database(root)
    if current.is_file() and current.stat().st_size:
        return current
    common = git_common_dir(root)
    if not common:
        return current
    legacy = Path(common).parent / ".ethos" / "state" / "state.sqlite"
    return legacy if legacy.is_file() and legacy.stat().st_size else current


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

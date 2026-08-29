from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.schema as schema

if TYPE_CHECKING:
    from pathlib import Path


def _canonical_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("begin immediate")
    schema.initialize_state_connection(connection)
    connection.commit()
    return connection


def test_state_schema_public_paths_are_git_common_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    common = tmp_path / ".git"
    monkeypatch.setattr(schema, "git_common_dir", lambda _root: common.as_posix())

    database = schema.state_database(tmp_path)

    assert database == common / "ethos/state.sqlite"
    assert schema.read_only_state_uri(database).endswith("/.git/ethos/state.sqlite?mode=ro")


def test_state_schema_fails_closed_without_a_git_common_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(schema, "git_common_dir", lambda _root: "")

    with pytest.raises(ValueError, match="git_common_directory_unavailable"):
        schema.local_state_root(tmp_path)


def test_state_schema_initialization_requires_a_transaction_and_validates_absence() -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        assert schema.validate_current_lease_schema(connection) is False
        with pytest.raises(RuntimeError, match="state_schema_transaction_required"):
            schema.initialize_state_connection(connection)

        connection.execute("begin immediate")
        schema.initialize_state_connection(connection)
        connection.commit()

        assert schema.validate_current_lease_schema(connection) is True


@pytest.mark.parametrize(
    "mutation",
    [
        "create table leases (id text primary key, subject text not null)",
        (
            "create table leases ("
            "lane_ref text primary key, holder_ref text not null, "
            "generation integer not null, expires_at text not null, extra text)"
        ),
    ],
)
def test_state_schema_rejects_noncanonical_table(mutation: str) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(mutation)
        with pytest.raises(RuntimeError, match="state_schema_lease_table_definition_mismatch"):
            schema.validate_current_lease_schema(connection)


@pytest.mark.parametrize("mutation", ["extra-index", "trigger"])
def test_state_schema_rejects_extra_subject_authority_or_triggers(
    tmp_path: Path, mutation: str
) -> None:
    with closing(_canonical_connection(tmp_path / "state.sqlite")) as connection:
        if mutation == "extra-index":
            connection.execute("create index extra_holder on leases(holder_ref)")
            expected = "state_schema_lease_index_present"
        else:
            connection.execute(
                "create trigger lease_guard after insert on leases begin select 1; end"
            )
            expected = "state_schema_lease_trigger_present"
        with pytest.raises(RuntimeError, match=expected):
            schema.validate_current_lease_schema(connection)


def test_state_schema_rejects_columns_hidden_behind_canonical_catalog_sql() -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute(
            "create table leases ("
            "lane_ref text primary key, holder_ref text not null, "
            "generation integer not null, expires_at text not null, extra text)"
        )
        connection.execute("pragma writable_schema = on")
        connection.execute(
            "update sqlite_master set sql = ? where type = 'table' and name = 'leases'",
            (
                (
                    "CREATE TABLE leases (\n"
                    "      lane_ref text primary key,\n"
                    "      holder_ref text not null,\n"
                    "      generation integer not null,\n"
                    "      expires_at text not null,\n"
                    "    )"
                ),
            ),
        )
        connection.execute("pragma writable_schema = off")

        with pytest.raises(RuntimeError, match="state_schema_lease_table_definition_mismatch"):
            schema.validate_current_lease_schema(connection)

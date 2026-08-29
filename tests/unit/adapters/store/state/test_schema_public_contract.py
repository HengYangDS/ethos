from __future__ import annotations

import json
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


def _legacy_connection(path: Path, *, payload: dict[str, object]) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "create table leases ("
        "id text primary key, subject text not null, owner text not null, "
        "expires_at text not null, payload_json text not null)"
    )
    connection.execute("create unique index leases_subject_unique on leases(subject)")
    connection.execute(
        "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)",
        (
            "lease:legacy",
            "work/example",
            "agent:test:case:owner",
            "2026-08-31T00:00:00+00:00",
            json.dumps(payload, sort_keys=True),
        ),
    )
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


def test_state_schema_report_exposes_observed_and_expected_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    common = tmp_path / ".git"
    common.mkdir()
    monkeypatch.setattr(schema, "git_common_dir", lambda _root: common.as_posix())
    payload = {
        "lane_ref": "work/example",
        "holder_ref": "agent:test:case:owner",
        "epoch": 3,
        "expires_at": "2026-08-31T00:00:00+00:00",
    }
    connection = _legacy_connection(schema.state_database(tmp_path), payload=payload)
    connection.close()

    assert schema.state_schema_report(tmp_path) == {
        "path": (common / "ethos/state.sqlite").as_posix(),
        "expected_state": "current",
        "expected_columns": ["lane_ref", "holder_ref", "generation", "expires_at"],
        "observed_state": "legacy",
        "observed_columns": ["id", "subject", "owner", "expires_at", "payload_json"],
        "row_count": 1,
    }


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


def test_state_transition_projects_the_exact_previous_lease_relation(tmp_path: Path) -> None:
    payload = {
        "lane_incarnation_id": "lane:legacy",
        "lease_id": "lease:legacy",
        "lane_ref": "work/example",
        "holder_ref": "agent:test:case:owner",
        "epoch": 7,
        "issued_at": "2026-08-29T00:00:00+00:00",
        "renewed_at": "2026-08-29T00:00:00+00:00",
        "expires_at": "2026-08-31T00:00:00+00:00",
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
        "path_scope": ["src/**"],
        "handoff": None,
    }
    with closing(_legacy_connection(tmp_path / "state.sqlite", payload=payload)) as connection:
        connection.execute("begin immediate")

        transition = schema.prepare_state_transition(connection)

        assert transition == {
            "before": "legacy",
            "after": "current",
            "state": "migrated",
            "row_count": 1,
        }
        assert connection.execute(
            "select lane_ref, holder_ref, generation, expires_at from leases"
        ).fetchall() == [
            (
                "work/example",
                "agent:test:case:owner",
                7,
                "2026-08-31T00:00:00+00:00",
            )
        ]
        assert schema.validate_current_lease_schema(connection) is True


def test_state_transition_requires_explicit_reset_for_contradictory_legacy_row(
    tmp_path: Path,
) -> None:
    payload = {
        "lane_ref": "work/other",
        "holder_ref": "agent:test:case:owner",
        "epoch": 7,
        "expires_at": "2026-08-31T00:00:00+00:00",
    }
    database = tmp_path / "state.sqlite"
    with closing(_legacy_connection(database, payload=payload)) as connection:
        connection.execute("begin immediate")
        with pytest.raises(RuntimeError, match="state_schema_migration_requires_reset"):
            schema.prepare_state_transition(connection)
        connection.rollback()

        connection.execute("begin immediate")
        transition = schema.prepare_state_transition(connection, reset=True)
        assert transition == {
            "before": "legacy",
            "after": "current",
            "state": "reset",
            "row_count": 0,
        }
        assert connection.execute("select * from leases").fetchall() == []

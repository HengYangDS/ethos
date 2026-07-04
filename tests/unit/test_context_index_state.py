from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from ethos.adapters.context_index import default_retrieval_db_path
from ethos.adapters.context_index import initialize_context_index
from ethos.adapters.context_index import purge_context_index

if TYPE_CHECKING:
    from pathlib import Path


def test_context_index_initialization_creates_retrieval_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "retrieval.sqlite"

    initialize_context_index(db_path)
    initialize_context_index(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type in ('table', 'virtual table')"
            )
        }

    assert {
        "schema_migrations",
        "index_manifests",
        "files",
        "source_spans",
        "doc_chunks",
        "code_symbols",
        "edges",
        "evidence_refs",
        "query_runs",
        "access_audit",
        "tombstones",
        "doc_chunks_fts",
        "code_symbols_fts",
    } <= tables


def test_default_retrieval_db_path_lives_under_ignored_state(tmp_path: Path) -> None:
    assert default_retrieval_db_path(tmp_path) == tmp_path / ".ethos" / "state" / "retrieval.sqlite"


def test_context_index_purge_is_dry_run_until_authorized(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "retrieval.sqlite"
    initialize_context_index(db_path)

    dry_run = purge_context_index(tmp_path, apply=False, authorized=False)
    unauthorized = purge_context_index(tmp_path, apply=True, authorized=False)

    assert dry_run["state"] == "dry_run"
    assert db_path.exists()
    assert unauthorized["state"] == "blocked"
    assert "context_purge_requires_authorization" in unauthorized["required_gaps"]
    assert db_path.exists()

    applied = purge_context_index(tmp_path, apply=True, authorized=True)

    assert applied["state"] == "purged"
    assert not db_path.exists()

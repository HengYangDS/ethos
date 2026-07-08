"""DDL constants and schema initialization for the retrieval SQLite index.

Applies the full schema including FTS5 virtual tables and records a migration
row so future schema changes can be versioned.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

from ethos.adapters.store.retrieval.common import _now

if TYPE_CHECKING:
    from pathlib import Path

RETRIEVAL_SCHEMA_VERSION = 1

SCHEMA = (
    """
    create table if not exists schema_migrations (
      version integer primary key,
      applied_at text not null
    )
    """,
    """
    create table if not exists index_manifests (
      id text primary key,
      root text not null,
      head text not null,
      schema_version integer not null,
      policy_digest text not null,
      created_at text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists files (
      id text primary key,
      manifest_id text not null,
      path text not null,
      digest text not null,
      size_bytes integer not null,
      mtime_ns integer not null,
      language text not null,
      kind text not null,
      indexed_at text not null
    )
    """,
    """
    create table if not exists source_spans (
      id text primary key,
      file_id text not null,
      path text not null,
      start_line integer not null,
      end_line integer not null,
      start_byte integer not null,
      end_byte integer not null,
      digest text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists doc_chunks (
      id text primary key,
      manifest_id text not null,
      file_id text not null,
      span_id text not null,
      chunk_ordinal integer not null,
      title text not null,
      text text not null,
      token_estimate integer not null,
      payload_json text not null
    )
    """,
    """
    create virtual table if not exists doc_chunks_fts
    using fts5(id unindexed, title, text)
    """,
    """
    create table if not exists code_symbols (
      id text primary key,
      manifest_id text not null,
      file_id text not null,
      span_id text not null,
      name text not null,
      qualified_name text not null,
      symbol_kind text not null,
      language text not null,
      signature text not null,
      payload_json text not null
    )
    """,
    """
    create virtual table if not exists code_symbols_fts
    using fts5(id unindexed, name, qualified_name, signature)
    """,
    """
    create table if not exists edges (
      id text primary key,
      manifest_id text not null,
      source_type text not null,
      source_id text not null,
      target_type text not null,
      target_id text not null,
      edge_kind text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists evidence_refs (
      id text primary key,
      manifest_id text not null,
      target_type text not null,
      target_id text not null,
      evidence_ref text not null,
      digest text,
      head text,
      payload_json text not null
    )
    """,
    """
    create table if not exists query_runs (
      id text primary key,
      manifest_id text not null,
      query text not null,
      query_digest text not null,
      policy_digest text not null,
      created_at text not null,
      result_count integer not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists access_audit (
      id text primary key,
      query_run_id text,
      source_type text not null,
      source_id text not null,
      path text not null,
      span_id text,
      accessed_at text not null,
      reason text not null,
      payload_json text not null
    )
    """,
    """
    create table if not exists tombstones (
      id text primary key,
      manifest_id text,
      path text not null,
      digest text,
      tombstoned_at text not null,
      reason text not null,
      payload_json text not null
    )
    """,
)


def initialize_context_index(db_path: Path) -> None:
    """Create or migrate the retrieval SQLite index at *db_path*.

    Idempotent: safe to call on an already-initialized database. Creates all
    tables and FTS5 virtual tables defined by :data:`SCHEMA`, then records the
    current schema version in ``schema_migrations`` if not already present.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma foreign_keys = on")
        for statement in SCHEMA:
            connection.execute(statement)
        connection.execute(
            "insert or ignore into schema_migrations(version, applied_at) values (?, ?)",
            (RETRIEVAL_SCHEMA_VERSION, _now()),
        )
        connection.commit()

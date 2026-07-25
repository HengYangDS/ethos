"""Context index rebuild and purge lifecycle.

Provides the public :func:`rebuild_context_index` and :func:`purge_context_index`
entry points plus private helpers for source ingestion, chunking, AST symbol
extraction, span insertion, and tombstoning.
"""

from __future__ import annotations

import ast
import json
import sqlite3
import uuid
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.retrieval.common import context_index_files
from ethos.adapters.store.retrieval.common import current_timestamp
from ethos.adapters.store.retrieval.common import default_retrieval_db_path
from ethos.adapters.store.retrieval.common import git_head
from ethos.adapters.store.retrieval.common import sha256_bytes
from ethos.adapters.store.retrieval.common import sha256_text
from ethos.adapters.store.retrieval.schema import RETRIEVAL_SCHEMA_VERSION
from ethos.adapters.store.retrieval.schema import initialize_context_index
from ethos.adapters.store.retrieval.sources import allowed_sources
from ethos.adapters.store.retrieval.sources import dirty_allowed_sources
from ethos.adapters.store.retrieval.sources import source_manifest_digest
from ethos.adapters.store.retrieval.sources import unsafe_source_reason
from ethos.contracts.context.projection import looks_secret_like

if TYPE_CHECKING:
    from pathlib import Path


def rebuild_context_index(root: Path, *, apply: bool, authorized: bool) -> dict[str, Any]:
    """Rebuild the local SQLite context index for the given repository root.

    Dry-run by default (``apply=False``). Requires ``authorized=True`` to
    actually write data. Blocks when any allowed source is locally dirty.
    """
    repo = root.resolve()
    db_path = default_retrieval_db_path(repo)
    sources = allowed_sources(repo)
    if not apply:
        return {
            "ok": True,
            "state": "dry_run",
            "summary": {
                "storage": db_path.as_posix(),
                "source_count": len(sources),
            },
            "required_gaps": [],
            "data": {"sources": [path.as_posix() for path in sources]},
        }
    if not authorized:
        return {
            "ok": False,
            "state": "blocked",
            "summary": {"storage": db_path.as_posix()},
            "required_gaps": ["context_index_requires_authorization"],
            "data": {},
        }
    dirty_sources = dirty_allowed_sources(repo)
    if dirty_sources:
        return {
            "ok": False,
            "state": "blocked",
            "summary": {
                "storage": db_path.as_posix(),
                "dirty_source_count": len(dirty_sources),
            },
            "required_gaps": ["context_index_dirty_sources"],
            "data": {"dirty_sources": dirty_sources},
        }
    for path in context_index_files(db_path):
        if path.exists():
            path.unlink()
    initialize_context_index(db_path)
    head = git_head(repo)
    manifest_id = f"manifest:{uuid.uuid4()}"
    policy_digest = sha256_text("default-context-policy-v1")
    source_manifest_sha256 = source_manifest_digest(repo, sources, head)
    now = current_timestamp()
    counts = {"source_count": 0, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            "insert into index_manifests("
            "id, root, head, schema_version, policy_digest, created_at, payload_json"
            ") values (?, ?, ?, ?, ?, ?, ?)",
            (
                manifest_id,
                repo.as_posix(),
                head,
                RETRIEVAL_SCHEMA_VERSION,
                policy_digest,
                now,
                json.dumps(
                    {
                        "repo_id": f"repo:{sha256_text(repo.as_posix())[:16]}",
                        "source_manifest_digest": source_manifest_sha256,
                        "privacy_ceiling": "repo_local",
                        "dirty": False,
                        "extractors": [
                            {"name": "markdown", "version": "1"},
                            {"name": "json", "version": "1"},
                            {"name": "toml", "version": "1"},
                            {"name": "python-ast", "version": "1"},
                        ],
                    },
                    sort_keys=True,
                ),
            ),
        )
        for source in sources:
            file_counts = index_source(connection, repo, manifest_id, source, head)
            for key, value in file_counts.items():
                counts[key] += value
        connection.commit()
    return {
        "ok": True,
        "state": "indexed",
        "summary": {
            **counts,
            "storage": db_path.as_posix(),
            "manifest_id": manifest_id,
            "source_manifest_digest": source_manifest_sha256,
        },
        "required_gaps": [],
        "data": {
            "manifest_id": manifest_id,
            "head": head,
            "source_manifest_digest": source_manifest_sha256,
        },
    }


def purge_context_index(root: Path, *, apply: bool, authorized: bool) -> dict[str, Any]:
    """Remove all files that make up the local context index.

    Dry-run by default (``apply=False``). Requires ``authorized=True`` to
    actually delete files.
    """
    repo = root.resolve()
    db_path = default_retrieval_db_path(repo)
    exists = db_path.exists()
    if not apply:
        return {
            "ok": True,
            "state": "dry_run",
            "summary": {"storage": db_path.as_posix(), "exists": exists},
            "required_gaps": [],
            "data": {},
        }
    if not authorized:
        return {
            "ok": False,
            "state": "blocked",
            "summary": {"storage": db_path.as_posix(), "exists": exists},
            "required_gaps": ["context_purge_requires_authorization"],
            "data": {},
        }
    removed = []
    for path in context_index_files(db_path):
        if path.exists():
            path.unlink()
            removed.append(path.name)
    return {
        "ok": True,
        "state": "purged",
        "summary": {"storage": db_path.as_posix(), "removed": removed},
        "required_gaps": [],
        "data": {"tombstone_count": len(removed)},
    }


def index_source(
    connection: sqlite3.Connection,
    root: Path,
    manifest_id: str,
    source: Path,
    head: str,
) -> dict[str, int]:
    """Index a single source file into the open SQLite connection.

    Inserts a tombstone for unsafe or secret-like sources; otherwise inserts
    file metadata, doc-chunks (with FTS), and Python AST symbols (with FTS).
    Returns per-category insertion counts.
    """
    rel = source.relative_to(root).as_posix()
    unsafe_reason = unsafe_source_reason(root, source)
    if unsafe_reason:
        _insert_tombstone(
            connection,
            manifest_id=manifest_id,
            rel=rel,
            digest=sha256_text(f"{rel}:{unsafe_reason}"),
            reason=unsafe_reason,
            head=head,
        )
        return {"source_count": 1, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    payload = source.read_bytes()
    text = payload.decode("utf-8", errors="replace")
    stat = source.stat()
    file_id = f"file:{sha256_text(rel)[:16]}"
    digest = sha256_bytes(payload)
    language = language_for(source)
    kind = kind_for(rel, source)
    if looks_secret_like(text):
        _insert_tombstone(
            connection,
            manifest_id=manifest_id,
            rel=rel,
            digest=digest,
            reason="secret_like_content",
            head=head,
        )
        return {"source_count": 1, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    connection.execute(
        "insert into files("
        "id, manifest_id, path, digest, size_bytes, mtime_ns, language, kind, indexed_at"
        ") values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            file_id,
            manifest_id,
            rel,
            digest,
            len(payload),
            stat.st_mtime_ns,
            language,
            kind,
            current_timestamp(),
        ),
    )
    counts = {"source_count": 1, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    for ordinal, chunk in enumerate(chunks_for(rel, text), start=1):
        span_id = _insert_span(connection, file_id, rel, chunk, {"head": head})
        chunk_key = f"{rel}:{ordinal}:{chunk['start_line']}"
        chunk_id = f"chunk:{sha256_text(chunk_key)[:16]}"
        connection.execute(
            "insert into doc_chunks("
            "id, manifest_id, file_id, span_id, chunk_ordinal, title, text, "
            "token_estimate, payload_json) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chunk_id,
                manifest_id,
                file_id,
                span_id,
                ordinal,
                chunk["title"],
                chunk["text"],
                max(1, len(chunk["text"].split())),
                json.dumps({"kind": kind, "head": head}, sort_keys=True),
            ),
        )
        connection.execute(
            "insert into doc_chunks_fts(id, title, text) values (?, ?, ?)",
            (chunk_id, chunk["title"], chunk["text"]),
        )
        counts["span_count"] += 1
        counts["chunk_count"] += 1
    if source.suffix == ".py":
        for symbol in python_symbols(text):
            span_id = _insert_span(connection, file_id, rel, symbol, {"head": head})
            symbol_key = f"{rel}:{symbol['name']}:{symbol['start_line']}"
            symbol_id = f"symbol:{sha256_text(symbol_key)[:16]}"
            connection.execute(
                "insert into code_symbols("
                "id, manifest_id, file_id, span_id, name, qualified_name, symbol_kind, "
                "language, signature, payload_json) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    symbol_id,
                    manifest_id,
                    file_id,
                    span_id,
                    symbol["name"],
                    symbol["qualified_name"],
                    symbol["symbol_kind"],
                    "python",
                    symbol["signature"],
                    json.dumps({"head": head}, sort_keys=True),
                ),
            )
            connection.execute(
                "insert into code_symbols_fts(id, name, qualified_name, signature) "
                "values (?, ?, ?, ?)",
                (symbol_id, symbol["name"], symbol["qualified_name"], symbol["signature"]),
            )
            counts["span_count"] += 1
            counts["symbol_count"] += 1
    return counts


def _insert_span(
    connection: sqlite3.Connection,
    file_id: str,
    rel: str,
    item: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    span_text = item["text"]
    span_key = f"{rel}:{item['start_line']}:{item['end_line']}:{span_text}"
    span_id = f"span:{sha256_text(span_key)[:16]}"
    connection.execute(
        "insert or ignore into source_spans("
        "id, file_id, path, start_line, end_line, start_byte, end_byte, digest, payload_json"
        ") values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            span_id,
            file_id,
            rel,
            int(item["start_line"]),
            int(item["end_line"]),
            0,
            len(span_text.encode("utf-8")),
            sha256_text(span_text),
            json.dumps(payload, sort_keys=True),
        ),
    )
    return span_id


def _insert_tombstone(
    connection: sqlite3.Connection,
    *,
    manifest_id: str,
    rel: str,
    digest: str,
    reason: str,
    head: str,
) -> None:
    connection.execute(
        "insert into tombstones("
        "id, manifest_id, path, digest, tombstoned_at, reason, payload_json"
        ") values (?, ?, ?, ?, ?, ?, ?)",
        (
            f"tombstone:{sha256_text(f'{manifest_id}:{rel}:{reason}')[:16]}",
            manifest_id,
            rel,
            digest,
            current_timestamp(),
            reason,
            json.dumps({"head": head}, sort_keys=True),
        ),
    )


def chunks_for(rel: str, text: str) -> list[dict[str, Any]]:
    """Split file text into heading-bounded doc chunks for FTS indexing.

    Each chunk captures the text between Markdown headings (lines starting with
    ``#``). Returns a single empty-text chunk for empty files.
    """
    lines = text.splitlines()
    if not lines:
        return [{"title": rel, "text": "", "start_line": 1, "end_line": 1}]
    chunks: list[dict[str, Any]] = []
    start = 0
    title = rel
    for index, line in enumerate(lines):
        if line.startswith("#") and index != start:
            chunks.append(
                {
                    "title": title,
                    "text": "\n".join(lines[start:index]),
                    "start_line": start + 1,
                    "end_line": index,
                }
            )
            start = index
            title = line.lstrip("#").strip() or rel
    chunks.append(
        {
            "title": title,
            "text": "\n".join(lines[start:]),
            "start_line": start + 1,
            "end_line": len(lines),
        }
    )
    return [chunk for chunk in chunks if chunk["text"].strip()]


def python_symbols(text: str) -> list[dict[str, Any]]:
    """Extract top-level and nested Python symbols from source text via AST.

    Returns an empty list for files that fail to parse. Each entry contains
    ``name``, ``qualified_name``, ``symbol_kind``, ``signature``, ``text``,
    ``start_line``, and ``end_line``.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines()
    symbols: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            name = node.name
            symbol_kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbols.append(
                {
                    "name": name,
                    "qualified_name": name,
                    "symbol_kind": symbol_kind,
                    "signature": signature_for(node),
                    "text": "\n".join(lines[start - 1 : end]),
                    "start_line": start,
                    "end_line": end,
                }
            )
    return symbols


def signature_for(node: ast.AST) -> str:
    """Return a short human-readable signature string for an AST node.

    Returns ``""`` for non-callable nodes (e.g., assignments).
    """
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ", ".join(arg.arg for arg in node.args.args)
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({args})"
    return ""


def language_for(source: Path) -> str:
    """Map a source file extension to a language label string."""
    return {
        ".py": "python",
        ".md": "markdown",
        ".json": "json",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(source.suffix, "text")


def kind_for(rel: str, source: Path) -> str:
    """Classify a source file by its repository-relative path and extension."""
    if rel.startswith("evidence/claims/"):
        return "claim"
    if rel.startswith("openspec/"):
        return "openspec"
    if rel.startswith("schemas/"):
        return "schema"
    if source.suffix == ".py":
        return "python_symbol"
    return "tracked_file"

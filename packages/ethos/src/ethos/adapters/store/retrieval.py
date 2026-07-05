from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import subprocess
import uuid
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos_core.contracts.context_projection import looks_secret_like
from ethos_core.contracts.context_projection import redact_secret_like

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


def default_retrieval_db_path(root: Path) -> Path:
    return root / ".ethos" / "state" / "retrieval.sqlite"


def initialize_context_index(db_path: Path) -> None:
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


def rebuild_context_index(
    root: Path,
    *,
    apply: bool,
    authorized: bool,
) -> dict[str, Any]:
    repo = root.resolve()
    db_path = default_retrieval_db_path(repo)
    sources = _allowed_sources(repo)
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
    dirty_sources = _dirty_allowed_sources(repo)
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
    for path in _context_index_files(db_path):
        if path.exists():
            path.unlink()
    initialize_context_index(db_path)
    head = _git_head(repo)
    manifest_id = f"manifest:{uuid.uuid4()}"
    policy_digest = _sha256_text("default-context-policy-v1")
    source_manifest_digest = _source_manifest_digest(repo, sources, head)
    now = _now()
    counts = {"source_count": 0, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            """
            insert into index_manifests(
              id, root, head, schema_version, policy_digest, created_at, payload_json
            )
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest_id,
                repo.as_posix(),
                head,
                RETRIEVAL_SCHEMA_VERSION,
                policy_digest,
                now,
                json.dumps(
                    {
                        "repo_id": f"repo:{_sha256_text(repo.as_posix())[:16]}",
                        "source_manifest_digest": source_manifest_digest,
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
            file_counts = _index_source(connection, repo, manifest_id, source, head)
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
            "source_manifest_digest": source_manifest_digest,
        },
        "required_gaps": [],
        "data": {
            "manifest_id": manifest_id,
            "head": head,
            "source_manifest_digest": source_manifest_digest,
        },
    }


def purge_context_index(
    root: Path,
    *,
    apply: bool,
    authorized: bool,
) -> dict[str, Any]:
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
    for path in _context_index_files(db_path):
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


def search_context_index(root: Path, query: str, *, limit: int = 10) -> dict[str, Any]:
    repo = root.resolve()
    db_path = default_retrieval_db_path(repo)
    safe_query = _redacted_query()
    query_digest = _query_digest(query)
    if not db_path.exists():
        return {
            "ok": False,
            "state": "gapped",
            "selection": _empty_selection(
                safe_query,
                query_digest=query_digest,
                diagnostics=[{"kind": "context_index_missing"}],
            ),
            "required_gaps": ["context_index_missing"],
            "summary": {"result_count": 0, "verified_count": 0},
        }
    dirty_sources = _dirty_allowed_sources(repo)
    if dirty_sources:
        return {
            "ok": False,
            "state": "blocked",
            "selection": _empty_selection(
                safe_query,
                query_digest=query_digest,
                diagnostics=[{"kind": "context_index_dirty_sources"}],
            ),
            "required_gaps": ["context_index_dirty_sources"],
            "summary": {"result_count": 0, "verified_count": 0},
            "data": {"dirty_sources": dirty_sources},
        }
    manifest_id = _latest_manifest_id(db_path)
    manifest_head = _latest_manifest_head(db_path)
    current_head = _git_head(repo)
    if manifest_head != current_head:
        return {
            "ok": False,
            "state": "stale",
            "selection": _empty_selection(
                safe_query,
                query_digest=query_digest,
                diagnostics=[
                    {
                        "kind": "context_index_stale_head",
                        "manifest_head": manifest_head,
                        "current_head": current_head,
                    }
                ],
            ),
            "required_gaps": ["context_index_stale_head"],
            "summary": {"result_count": 0, "verified_count": 0},
        }
    raw = _query_candidates(db_path, query, limit=limit)
    verified: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for candidate in raw:
        result = _verify_candidate(repo, candidate)
        if result["verification"]["status"] == "verified":
            verified.append(result)
        else:
            status = str(result["verification"]["status"])
            diagnostics.append(
                {
                    "kind": "stale_candidate" if status == "stale" else "unverified_candidate",
                    "reason": result["verification"]["reason"],
                    "path": candidate["path"],
                    "span_id": candidate["span_id"],
                }
            )
    selection = {
        "manifest_id": manifest_id,
        "query": safe_query,
        "query_digest": query_digest,
        "result_count": len(verified),
        "verified_count": len(verified),
        "untrusted_context_label": "UNTRUSTED CONTEXT",
        "diagnostics": diagnostics,
        "results": verified,
    }
    return {
        "ok": True,
        "state": "ready",
        "selection": selection,
        "summary": {
            "result_count": len(verified),
            "verified_count": len(verified),
        },
        "required_gaps": [],
    }


def context_eval_report(
    root: Path,
    *,
    suite: str,
    fixtures: tuple[dict[str, object], ...] = (),
) -> dict[str, Any]:
    db_path = default_retrieval_db_path(root.resolve())
    if not db_path.exists():
        return {
            "ok": False,
            "state": "gapped",
            "summary": {"suite": suite, "index_exists": False},
            "required_gaps": ["context_index_missing"],
            "data": {"metrics": {}},
        }
    if suite != "smoke":
        return {
            "ok": False,
            "state": "gapped",
            "summary": {"suite": suite, "index_exists": True},
            "required_gaps": ["context_eval_suite_missing"],
            "data": {"metrics": {}},
        }
    smoke_fixtures = fixtures or (
        {
            "id": "default-smoke",
            "query": "ETHOS",
            "expected_paths": (),
        },
    )
    fixture_reports: list[dict[str, object]] = []
    unsupported_count = 0
    critical_stale_hits = 0
    for fixture in smoke_fixtures:
        expected_paths = tuple(str(path) for path in fixture.get("expected_paths", ()))
        query = str(fixture["query"])
        search = search_context_index(root, query, limit=10)
        if not search["ok"]:
            critical_stale_hits += 1
        result_paths = {
            str(result["source_ref"]["path"]) for result in search["selection"]["results"]
        }
        missing_paths = sorted(set(expected_paths) - result_paths)
        stale_hits = [
            item
            for item in search["selection"]["diagnostics"]
            if item.get("kind") == "stale_candidate"
        ]
        critical_stale_hits += len(stale_hits)
        if not search["summary"]["verified_count"] or missing_paths:
            unsupported_count += 1
        fixture_reports.append(
            {
                "id": fixture["id"],
                "query": _redacted_query(),
                "query_digest": _query_digest(query),
                "expected_paths": list(expected_paths),
                "verified_count": search["summary"]["verified_count"],
                "missing_paths": missing_paths,
                "stale_hit_count": len(stale_hits),
            }
        )
    unsupported_answer_rate = unsupported_count / len(smoke_fixtures)
    ok = unsupported_answer_rate == 0 and critical_stale_hits == 0
    return {
        "ok": ok,
        "state": "ready" if ok else "gapped",
        "summary": {
            "suite": suite,
            "index_exists": True,
            "query_count": len(smoke_fixtures),
        },
        "required_gaps": []
        if unsupported_answer_rate == 0 and critical_stale_hits == 0
        else ["context_eval_smoke_failed"],
        "data": {
            "metrics": {
                "unsupported_answer_rate": unsupported_answer_rate,
                "critical_stale_hits": critical_stale_hits,
            },
            "fixtures": fixture_reports,
        },
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _context_index_files(db_path: Path) -> tuple[Path, ...]:
    return (
        db_path,
        db_path.with_suffix(".sqlite-wal"),
        db_path.with_suffix(".sqlite-shm"),
    )


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "untracked"


def _tracked_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [root / line for line in completed.stdout.splitlines() if line.strip()]


def _tracked_source_paths(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in _tracked_files(root)}


def _allowed_sources(root: Path) -> list[Path]:
    allowed: list[Path] = []
    for path in _tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if _is_allowed_source_rel(rel):
            allowed.append(path)
    return sorted(allowed)


def _is_allowed_source_rel(rel: str) -> bool:
    if rel.startswith(".ethos/state/"):
        return False
    if rel in {"AGENTS.md", "CONTRIBUTING.md", "README.md", "pyproject.toml"}:
        return True
    if rel.endswith("/README.md") and rel.startswith("packages/"):
        return True
    if rel.startswith(("docs/", "openspec/", "evidence/claims/", "schemas/")):
        return True
    return rel.startswith("packages/") and Path(rel).suffix == ".py"


def _dirty_allowed_sources(root: Path) -> list[str]:
    allowed_paths = {source.relative_to(root).as_posix() for source in _allowed_sources(root)}
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    dirty: list[str] = []
    for line in completed.stdout.splitlines():
        for rel in _porcelain_paths(line[3:].strip()):
            if rel in allowed_paths or _is_allowed_source_rel(rel):
                dirty.append(rel)
    return sorted(dirty)


def _porcelain_paths(pathspec: str) -> tuple[str, ...]:
    paths = pathspec.split(" -> ") if " -> " in pathspec else [pathspec]
    return tuple(path.strip().strip('"') for path in paths if path.strip())


def _source_manifest_digest(root: Path, sources: list[Path], head: str) -> str:
    source_manifest = {
        "head": head,
        "sources": [source.relative_to(root).as_posix() for source in sources],
    }
    return _sha256_text(json.dumps(source_manifest, sort_keys=True))


def _unsafe_source_reason(root: Path, source: Path) -> str:
    if not source.exists():
        return "missing_path"
    resolved = source.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return "path_outside_repository"
    if source.is_symlink():
        return "symlink_source"
    return ""


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
        """
        insert into tombstones(
          id, manifest_id, path, digest, tombstoned_at, reason, payload_json
        )
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"tombstone:{_sha256_text(f'{manifest_id}:{rel}:{reason}')[:16]}",
            manifest_id,
            rel,
            digest,
            _now(),
            reason,
            json.dumps({"head": head}, sort_keys=True),
        ),
    )


def _index_source(
    connection: sqlite3.Connection,
    root: Path,
    manifest_id: str,
    source: Path,
    head: str,
) -> dict[str, int]:
    rel = source.relative_to(root).as_posix()
    unsafe_reason = _unsafe_source_reason(root, source)
    if unsafe_reason:
        _insert_tombstone(
            connection,
            manifest_id=manifest_id,
            rel=rel,
            digest=_sha256_text(f"{rel}:{unsafe_reason}"),
            reason=unsafe_reason,
            head=head,
        )
        return {"source_count": 1, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    payload = source.read_bytes()
    text = payload.decode("utf-8", errors="replace")
    stat = source.stat()
    file_id = f"file:{_sha256_text(rel)[:16]}"
    digest = _sha256_bytes(payload)
    language = _language_for(source)
    kind = _kind_for(rel, source)
    if _looks_secret_like(text):
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
        """
        insert into files(
          id, manifest_id, path, digest, size_bytes, mtime_ns, language, kind,
          indexed_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (file_id, manifest_id, rel, digest, len(payload), stat.st_mtime_ns, language, kind, _now()),
    )
    counts = {"source_count": 1, "span_count": 0, "chunk_count": 0, "symbol_count": 0}
    for ordinal, chunk in enumerate(_chunks_for(rel, text), start=1):
        span_id = _insert_span(connection, file_id, rel, chunk, {"head": head})
        chunk_key = f"{rel}:{ordinal}:{chunk['start_line']}"
        chunk_id = f"chunk:{_sha256_text(chunk_key)[:16]}"
        connection.execute(
            """
            insert into doc_chunks(
              id, manifest_id, file_id, span_id, chunk_ordinal, title, text,
              token_estimate, payload_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
        for symbol in _python_symbols(text):
            span_id = _insert_span(connection, file_id, rel, symbol, {"head": head})
            symbol_key = f"{rel}:{symbol['name']}:{symbol['start_line']}"
            symbol_id = f"symbol:{_sha256_text(symbol_key)[:16]}"
            connection.execute(
                """
                insert into code_symbols(
                  id, manifest_id, file_id, span_id, name, qualified_name,
                  symbol_kind, language, signature, payload_json
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
                """
                insert into code_symbols_fts(id, name, qualified_name, signature)
                values (?, ?, ?, ?)
                """,
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
    span_id = f"span:{_sha256_text(span_key)[:16]}"
    connection.execute(
        """
        insert or ignore into source_spans(
          id, file_id, path, start_line, end_line, start_byte, end_byte, digest,
          payload_json
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            span_id,
            file_id,
            rel,
            int(item["start_line"]),
            int(item["end_line"]),
            0,
            len(span_text.encode("utf-8")),
            _sha256_text(span_text),
            json.dumps(payload, sort_keys=True),
        ),
    )
    return span_id


def _chunks_for(rel: str, text: str) -> list[dict[str, Any]]:
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


def _python_symbols(text: str) -> list[dict[str, Any]]:
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
                    "signature": _signature_for(node),
                    "text": "\n".join(lines[start - 1 : end]),
                    "start_line": start,
                    "end_line": end,
                }
            )
    return symbols


def _signature_for(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ", ".join(arg.arg for arg in node.args.args)
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({args})"
    return ""


def _language_for(source: Path) -> str:
    return {
        ".py": "python",
        ".md": "markdown",
        ".json": "json",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }.get(source.suffix, "text")


def _kind_for(rel: str, source: Path) -> str:
    if rel.startswith("evidence/claims/"):
        return "claim"
    if rel.startswith("openspec/"):
        return "openspec"
    if rel.startswith("schemas/"):
        return "schema"
    if source.suffix == ".py":
        return "python_symbol"
    return "tracked_file"


def _latest_manifest_id(db_path: Path) -> str:
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(
            "select id from index_manifests order by created_at desc limit 1"
        ).fetchone()
    return str(row[0]) if row else "manifest:none"


def _latest_manifest_head(db_path: Path) -> str:
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(
            "select head from index_manifests order by created_at desc limit 1"
        ).fetchone()
    return str(row[0]) if row else "untracked"


def _query_candidates(db_path: Path, query: str, *, limit: int) -> list[dict[str, Any]]:
    fts_query = _fts_query(query)
    if not fts_query:
        return []
    candidates: list[dict[str, Any]] = []
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select dc.id, dc.title, dc.text, sp.id as span_id, sp.path, sp.start_line,
                   sp.end_line, sp.digest, f.digest as file_digest,
                   im.head
            from doc_chunks_fts fts
            join doc_chunks dc on dc.id = fts.id
            join source_spans sp on sp.id = dc.span_id
            join files f on f.id = dc.file_id
            join index_manifests im on im.id = dc.manifest_id
            where doc_chunks_fts match ?
            order by bm25(doc_chunks_fts), dc.id
            limit ?
            """,
            (fts_query, limit),
        ).fetchall()
        symbol_rows = connection.execute(
            """
            select cs.id, cs.qualified_name as title, cs.signature as text,
                   sp.id as span_id, sp.path, sp.start_line, sp.end_line, sp.digest,
                   f.digest as file_digest, im.head
            from code_symbols_fts fts
            join code_symbols cs on cs.id = fts.id
            join source_spans sp on sp.id = cs.span_id
            join files f on f.id = cs.file_id
            join index_manifests im on im.id = cs.manifest_id
            where code_symbols_fts match ?
            order by bm25(code_symbols_fts), cs.id
            limit ?
            """,
            (fts_query, limit),
        ).fetchall()
    for score, row in enumerate([*rows, *symbol_rows], start=1):
        candidates.append({**dict(row), "score": 1.0 / score})
    return candidates[:limit]


def _fts_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms:
        return ""
    return " OR ".join(terms)


def _verify_candidate(repo: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    reason = "digest_mismatch"
    status = "stale"
    rel = str(candidate["path"])
    path = (repo / rel).resolve()
    start_line = int(candidate["start_line"])
    end_line = int(candidate["end_line"])
    source_title = f"{rel}:{start_line}-{end_line}"
    source_key = f"{rel}:{start_line}:{end_line}:{candidate['digest']}"
    source_result_id = f"source:{_sha256_text(source_key)[:16]}"
    try:
        path.relative_to(repo)
    except ValueError:
        status = "unverified"
        reason = "path_outside_repository"
    else:
        tracked_paths = _tracked_source_paths(repo)
        current_head = _git_head(repo)
        allowed_paths = {source.relative_to(repo).as_posix() for source in _allowed_sources(repo)}
        if rel.startswith(".ethos/state/") or rel not in tracked_paths or rel not in allowed_paths:
            status = "unverified"
            reason = "path_not_allowed_source"
        elif current_head != candidate["head"]:
            status = "stale"
            reason = "head_mismatch"
        elif path.exists():
            reason = "digest_mismatch"
            current_file_digest = _sha256_bytes(path.read_bytes())
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            span = (
                "\n".join(lines[start_line - 1 : end_line])
                if 1 <= start_line <= end_line <= len(lines)
                else ""
            )
            if (
                current_file_digest == candidate["file_digest"]
                and _sha256_text(span) == candidate["digest"]
            ):
                status = "verified"
                reason = "verified"
        else:
            status = "stale"
            reason = "missing_path"
    return {
        "id": source_result_id,
        "kind": "source",
        "title": source_title,
        "authority_class": "retrieval_aid",
        "privacy_class": "repo_local",
        "score": float(candidate["score"]),
        "source_ref": {
            "path": candidate["path"],
            "start_line": start_line,
            "end_line": end_line,
            "sha256": candidate["digest"],
            "head": candidate["head"],
        },
        "verification": {
            "status": status,
            "method": "tracked-path+head+line-span+sha256",
            "reason": reason,
        },
    }


def _looks_secret_like(text: str) -> bool:
    return looks_secret_like(text)


def _redact_secret_like(text: str) -> str:
    return redact_secret_like(text)


def _redacted_query() -> str:
    return "<redacted-query>"


def _query_digest(query: str) -> str:
    return f"sha256:{_sha256_text(query)}"


def _empty_selection(
    query: str,
    *,
    query_digest: str,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "manifest_id": "manifest:none",
        "query": query,
        "query_digest": query_digest,
        "result_count": 0,
        "verified_count": 0,
        "untrusted_context_label": "UNTRUSTED CONTEXT",
        "diagnostics": diagnostics,
        "results": [],
    }

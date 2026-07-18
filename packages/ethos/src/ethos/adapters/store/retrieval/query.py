"""FTS/symbol search, candidate verification, and context eval report.

Provides the public :func:`search_context_index` and :func:`context_eval_report`
entry points plus private helpers for query building, candidate ranking, digest
verification, and secret redaction.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.retrieval.common import default_retrieval_db_path
from ethos.adapters.store.retrieval.common import git_head
from ethos.adapters.store.retrieval.common import latest_manifest_head
from ethos.adapters.store.retrieval.common import latest_manifest_id
from ethos.adapters.store.retrieval.common import sha256_bytes
from ethos.adapters.store.retrieval.common import sha256_text
from ethos.adapters.store.retrieval.sources import allowed_sources
from ethos.adapters.store.retrieval.sources import dirty_allowed_sources
from ethos.adapters.store.retrieval.sources import tracked_source_paths
from ethos_core.normalization.core import object_sequence
from ethos_core.normalization.core import string_mapping
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from pathlib import Path


def search_context_index(root: Path, query: str, *, limit: int = 10) -> dict[str, Any]:
    """Search the local context index and return source-verified results.

    Checks for a missing index, dirty sources, and stale HEAD before running
    the FTS query. All candidates are re-verified against the current filesystem
    state before inclusion in the response.
    """
    repo = root.resolve()
    db_path = default_retrieval_db_path(repo)
    safe_query = _redacted_query()
    query_digest = _query_digest(query)
    if not db_path.exists():
        return {
            "ok": False,
            "state": "gapped",
            "selection": empty_selection(
                safe_query,
                query_digest=query_digest,
                diagnostics=[{"kind": "context_index_missing"}],
            ),
            "required_gaps": ["context_index_missing"],
            "summary": {"result_count": 0, "verified_count": 0},
        }
    dirty_sources = dirty_allowed_sources(repo)
    if dirty_sources:
        return {
            "ok": False,
            "state": "blocked",
            "selection": empty_selection(
                safe_query,
                query_digest=query_digest,
                diagnostics=[{"kind": "context_index_dirty_sources"}],
            ),
            "required_gaps": ["context_index_dirty_sources"],
            "summary": {"result_count": 0, "verified_count": 0},
            "data": {"dirty_sources": dirty_sources},
        }
    manifest_id = latest_manifest_id(db_path)
    manifest_head = latest_manifest_head(db_path)
    current_head = git_head(repo)
    if manifest_head != current_head:
        return {
            "ok": False,
            "state": "stale",
            "selection": empty_selection(
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
    raw = query_candidates(db_path, query, limit=limit)
    verified: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for candidate in raw:
        result = verify_candidate(repo, candidate)
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
    """Run a named eval suite against the local context index and report results.

    Currently supports the ``"smoke"`` suite. Returns gap diagnostics for a
    missing index or an unknown suite name.
    """
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
    for raw_fixture in object_sequence(smoke_fixtures):
        fixture = string_mapping(raw_fixture)
        expected_paths = tuple(string_sequence(fixture.get("expected_paths")))
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


def query_candidates(db_path: Path, query: str, *, limit: int) -> list[dict[str, Any]]:
    """Run FTS queries against doc_chunks and code_symbols and return ranked candidates.

    Returns an empty list when the FTS query term list is empty (e.g., query is
    all punctuation).
    """
    fts_query = fts_query_str(query)
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


def fts_query_str(query: str) -> str:
    """Convert a natural-language query to an FTS5 OR-joined term expression.

    Returns ``""`` for queries that contain no alphanumeric terms.
    """
    terms = re.findall(r"[A-Za-z0-9_]+", query)
    if not terms:
        return ""
    return " OR ".join(terms)


def verify_candidate(repo: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    """Verify a query candidate against the current filesystem state.

    Checks path containment, git tracking, HEAD match, and file/span digest
    agreement. Returns a result dict with a ``verification`` sub-dict whose
    ``status`` is one of ``"verified"``, ``"stale"``, or ``"unverified"``.
    """
    reason = "digest_mismatch"
    status = "stale"
    rel = str(candidate["path"])
    path = (repo / rel).resolve()
    start_line = int(candidate["start_line"])
    end_line = int(candidate["end_line"])
    source_title = f"{rel}:{start_line}-{end_line}"
    source_key = f"{rel}:{start_line}:{end_line}:{candidate['digest']}"
    source_result_id = f"source:{sha256_text(source_key)[:16]}"
    try:
        path.relative_to(repo)
    except ValueError:
        status = "unverified"
        reason = "path_outside_repository"
    else:
        tracked_paths = tracked_source_paths(repo)
        current_head = git_head(repo)
        allowed_paths = {source.relative_to(repo).as_posix() for source in allowed_sources(repo)}
        if rel.startswith(".ethos/state/") or rel not in tracked_paths or rel not in allowed_paths:
            status = "unverified"
            reason = "path_not_allowed_source"
        elif current_head != candidate["head"]:
            status = "stale"
            reason = "head_mismatch"
        elif path.exists():
            reason = "digest_mismatch"
            current_file_digest = sha256_bytes(path.read_bytes())
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            span = (
                "\n".join(lines[start_line - 1 : end_line])
                if 1 <= start_line <= end_line <= len(lines)
                else ""
            )
            if (
                current_file_digest == candidate["file_digest"]
                and sha256_text(span) == candidate["digest"]
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


def empty_selection(
    query: str,
    *,
    query_digest: str,
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a standard empty selection dict for error/gap responses."""
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


def _redacted_query() -> str:
    return "<redacted-query>"


def _query_digest(query: str) -> str:
    return f"sha256:{sha256_text(query)}"

"""Lane Lease maintenance and revocation effects."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.lifecycle.core import expected_current_lease
from ethos.adapters.store.state.lease.lifecycle.core import initialize_lease_state
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path


def update_lease_payload(
    db_path: Path,
    *,
    subject: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    initialize_lease_state(db_path)
    matching = [lease for lease in active_leases(db_path) if lease["subject"] == subject]
    if len(matching) != 1:
        return {}
    lease = matching[0]
    merged_payload = dict(lease["payload"])
    merged_payload.update(payload)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute(
            """
            update leases
            set payload_json = ?
            where id = ?
            """,
            (json.dumps(merged_payload, sort_keys=True), lease["id"]),
        )
        connection.commit()
    updated = dict(lease)
    updated["payload"] = merged_payload
    return updated


def delete_lease(db_path: Path, *, subject: str) -> int:
    """Delete all leases for a subject (work-lane branch). Returns the count removed.

    Called on lane retirement so a lease cannot outlive its lane — a destroyed and
    later recreated same-named branch must not present a resolvable stale lease
    (a truth store that cannot be proved is not a trustworthy store).
    """
    if not db_path.exists():
        return 0
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        cursor = connection.execute(
            "delete from leases where subject = ?",
            (subject,),
        )
        connection.commit()
        return cursor.rowcount


def delete_exact_leases(db_path: Path, candidates: list[dict[str, Any]]) -> list[str]:
    """Delete exact maintenance candidates through a row-bound transaction."""
    if not candidates:
        return []
    if not db_path.exists():
        message = "lease_maintenance_database_missing"
        raise ValueError(message)
    deleted: list[str] = []
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        try:
            for candidate in candidates:
                lease_id = str(candidate.get("id") or "")
                _expect_lease_candidate(connection, candidate)
                connection.execute("delete from leases where id = ?", (lease_id,))
                deleted.append(lease_id)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return deleted


def _expect_lease_candidate(connection: sqlite3.Connection, candidate: dict[str, Any]) -> None:
    lease_id = str(candidate.get("id") or "")
    row = connection.execute(
        """
        select id, subject, owner, expires_at, payload_json
        from leases
        where id = ?
        """,
        (lease_id,),
    ).fetchone()
    if row is None or not _lease_candidate_matches(row, candidate):
        message = f"lease_maintenance_candidate_drift:{lease_id}"
        raise ValueError(message)


def _lease_candidate_matches(row: sqlite3.Row | tuple[Any, ...], candidate: dict[str, Any]) -> bool:
    payload_digest = hashlib.sha256(str(row[4]).encode("utf-8")).hexdigest()
    return (
        str(row[0]) == str(candidate.get("id") or "")
        and str(row[1]) == str(candidate.get("subject") or "")
        and str(row[2]) == str(candidate.get("owner") or "")
        and str(row[3]) == str(candidate.get("expires_at") or "")
        and payload_digest == str(candidate.get("payload_sha256") or "")
    )


def revoke_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
) -> dict[str, Any]:
    """Delete one exact local lease generation after a completed handoff saga."""
    HolderRef.parse(holder_ref)
    initialize_lease_state(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        row, payload = expected_current_lease(
            connection,
            subject=subject,
            holder_ref=holder_ref,
            expected_lease_id=expected_lease_id,
            expected_epoch=expected_epoch,
            expected_head=expected_head,
            require_expired=False,
        )
        connection.execute("delete from leases where id = ?", (str(row[0]),))
        connection.commit()
    return {
        "revoked": True,
        "subject": subject,
        "lease_id": str(row[0]),
        "holder_ref": holder_ref,
        "epoch": int(payload.get("epoch") or 0),
        "expected_head": str(payload.get("expected_head") or ""),
    }

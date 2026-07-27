"""Lane Lease revocation effects."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.coordination import LeaseOperationRequest


def revoke_lease(
    db_path: Path,
    *,
    request: LeaseOperationRequest,
) -> dict[str, Any]:
    """Delete one exact local lease generation after a completed handoff saga."""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        revoked = revoke_lease_from_connection(connection, request=request)
        connection.commit()
    return revoked


def revoke_lease_from_connection(
    connection: sqlite3.Connection,
    *,
    request: LeaseOperationRequest,
) -> dict[str, Any]:
    """Delete one request-bound Lease generation inside the active transaction."""
    row, lease = expected_current_lease(
        connection,
        request=request,
        require_expired=False,
    )
    cursor = connection.execute(
        "delete from leases where id = ? and subject = ? and owner = ? "
        "and expires_at = ? and payload_json = ?",
        (row.id, row.subject, row.owner, row.expires_at, row.payload_json),
    )
    if cursor.rowcount != 1:
        message = f"lease_maintenance_candidate_drift:{row.id}"
        raise ValueError(message)
    return {
        "revoked": True,
        "subject": request.branch,
        "lease_id": row.id,
        "holder_ref": request.holder_ref,
        "epoch": lease.epoch,
        "expected_head": lease.expected_head,
        "expires_at": row.expires_at,
        "payload_sha256": row.payload_sha256,
    }

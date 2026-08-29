"""Exact Lane Lease retirement effects."""

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
    """Delete one exact local Lease generation."""
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
    """Delete one request-bound Lease generation inside an active transaction."""
    row, _lease = expected_current_lease(
        connection,
        request=request,
        require_expired=None,
    )
    cursor = connection.execute(
        "delete from leases where lane_ref = ? and holder_ref = ? "
        "and generation = ? and expires_at = ?",
        (row.lane_ref, row.holder_ref, row.generation, row.expires_at),
    )
    if cursor.rowcount != 1:
        msg = f"lease_generation_stale:{row.lane_ref}"
        raise ValueError(msg)
    return {
        "revoked": True,
        "lane_ref": row.lane_ref,
        "holder_ref": row.holder_ref,
        "generation": row.generation,
        "expires_at": row.expires_at,
    }

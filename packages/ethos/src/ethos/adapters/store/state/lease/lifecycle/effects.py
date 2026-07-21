"""Lane Lease maintenance and revocation effects."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.lifecycle.core import expected_current_lease
from ethos.adapters.store.state.lease.projection import expect_exact_lease_candidate
from ethos.adapters.store.state.lease.projection import lease_record
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path


def update_lease_payload(
    db_path: Path,
    *,
    candidate: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not db_path.exists():
        return {}
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        row, merged_payload = expected_current_lease(
            connection,
            subject=str(candidate.get("subject") or ""),
            holder_ref=str(candidate.get("holder_ref") or ""),
            expected_lease_id=str(candidate.get("lease_id") or ""),
            expected_epoch=int(candidate.get("epoch") or 0),
            expected_head=str(candidate.get("expected_head") or ""),
            expected_expires_at=str(candidate.get("expires_at") or ""),
            expected_payload_sha256=str(candidate.get("payload_sha256") or ""),
            require_expired=False,
        )
        merged_payload.update(payload)
        raw_payload = json.dumps(merged_payload, sort_keys=True)
        connection.execute(
            "update leases set payload_json = ? where id = ?",
            (raw_payload, str(row[0])),
        )
        connection.commit()
    return lease_record(
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            raw_payload,
        )
    )


def delete_exact_leases_from_connection(
    connection: sqlite3.Connection,
    candidates: list[dict[str, Any]],
) -> list[str]:
    """Delete exact candidates inside the caller's active transaction."""
    initialize_state_connection(connection)
    deleted: list[str] = []
    for candidate in candidates:
        lease_id = str(candidate.get("id") or "")
        _expect_lease_candidate(connection, candidate)
        connection.execute("delete from leases where id = ?", (lease_id,))
        deleted.append(lease_id)
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
    if row is None:
        message = f"lease_maintenance_candidate_drift:{lease_id}"
        raise ValueError(message)
    expect_exact_lease_candidate(row, candidate)


def revoke_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    expected_expires_at: str,
    expected_payload_sha256: str,
) -> dict[str, Any]:
    """Delete one exact local lease generation after a completed handoff saga."""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        revoked = revoke_lease_from_connection(
            connection,
            subject=subject,
            holder_ref=holder_ref,
            expected_lease_id=expected_lease_id,
            expected_epoch=expected_epoch,
            expected_head=expected_head,
            expected_expires_at=expected_expires_at,
            expected_payload_sha256=expected_payload_sha256,
        )
        connection.commit()
    return revoked


def revoke_lease_from_connection(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    connection: sqlite3.Connection,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    expected_expires_at: str,
    expected_payload_sha256: str,
) -> dict[str, Any]:
    """Delete one exact lease generation inside the caller's active transaction."""
    HolderRef.parse(holder_ref)
    row, payload = expected_current_lease(
        connection,
        subject=subject,
        holder_ref=holder_ref,
        expected_lease_id=expected_lease_id,
        expected_epoch=expected_epoch,
        expected_head=expected_head,
        expected_expires_at=expected_expires_at,
        expected_payload_sha256=expected_payload_sha256,
        require_expired=False,
    )
    connection.execute("delete from leases where id = ?", (str(row[0]),))
    return {
        "revoked": True,
        "subject": subject,
        "lease_id": str(row[0]),
        "holder_ref": holder_ref,
        "epoch": int(payload.get("epoch") or 0),
        "expected_head": str(payload.get("expected_head") or ""),
        "expires_at": str(row[3]),
        "payload_sha256": expected_payload_sha256,
    }

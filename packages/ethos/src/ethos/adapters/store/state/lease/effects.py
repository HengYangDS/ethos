"""Lane Lease maintenance and revocation effects."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.events import initialize_state
from ethos.adapters.store.state.lease.core import expected_current_lease
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import table_columns
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from pathlib import Path


def update_lease_payload(
    db_path: Path,
    *,
    subject: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    initialize_state(db_path)
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
        columns = table_columns(connection, "leases")
        if "subject" not in columns:
            return 0
        cursor = connection.execute(
            "delete from leases where subject = ?",  # nosec B608 - fixed query, param bound
            (subject,),
        )
        connection.commit()
        return cursor.rowcount


def revoke_lease(
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
    initialize_state(db_path)
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

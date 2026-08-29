"""Exact four-coordinate SQLite Lane Lease transitions."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.store.state.lease.projection import LeaseRow
from ethos.adapters.store.state.lease.projection import lease_record
from ethos.adapters.store.state.lease.projection import observe_lease_from_connection
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest

if TYPE_CHECKING:
    from pathlib import Path


def acquire_lease(db_path: Path, *, lease: LaneLease) -> dict[str, object]:
    """Persist one minimal lane-to-holder relation."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma journal_mode = wal")
        connection.execute("begin immediate")
        result = acquire_lease_from_connection(connection, lease=lease)
        connection.commit()
    return result


def acquire_lease_from_connection(
    connection: sqlite3.Connection,
    *,
    lease: LaneLease,
) -> dict[str, object]:
    """Insert one minimal Lease inside the caller's active transaction."""
    initialize_state_connection(connection)
    holder = lease.holder_ref.serialize()
    expires_at = lease.expires_at.isoformat()
    try:
        connection.execute(
            "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
            (lease.lane_ref, holder, lease.generation, expires_at),
        )
    except sqlite3.IntegrityError as exc:
        msg = f"lane_lease_conflict:{lease.lane_ref}"
        raise ValueError(msg) from exc
    return lease_record((lease.lane_ref, holder, lease.generation, expires_at))


def apply_lease_operation(
    db_path: Path,
    *,
    request: LeaseOperationRequest,
) -> dict[str, object]:
    """Apply one exact renew, resume, or holder-transfer CAS."""
    if request.operation not in {"renew", "resume", "transfer"}:
        msg = f"lease_operation_unknown:{request.operation}"
        raise ValueError(msg)
    if not request.apply:
        msg = f"lease_apply_required:{request.operation}"
        raise ValueError(msg)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        row, current = expected_current_lease(
            connection,
            request=request,
            require_expired=request.operation == "resume",
        )
        holder = (
            HolderRef.parse(request.target_holder_ref)
            if request.operation == "transfer"
            else current.holder_ref
        )
        replacement = LaneLease(
            lane_ref=current.lane_ref,
            holder_ref=holder,
            generation=current.generation + 1,
            expires_at=datetime.now(UTC) + timedelta(seconds=request.ttl_seconds),
        )
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=replacement,
        )
        connection.commit()
    return result


def takeover_lease(
    db_path: Path,
    *,
    request: LeaseTakeoverRequest,
) -> dict[str, object]:
    """Apply one authorized holder replacement against the exact generation."""
    if not request.apply:
        msg = "lease_apply_required:takeover"
        raise ValueError(msg)
    operation = LeaseOperationRequest(
        operation="transfer",
        branch=request.branch,
        holder_ref=request.source_holder_ref,
        target_holder_ref=request.target_holder_ref,
        generation=request.generation,
        expires_at=request.expires_at,
        ttl_seconds=request.ttl_seconds,
        apply=True,
    )
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        row, current = expected_current_lease(
            connection,
            request=operation,
            require_expired=None,
        )
        replacement = LaneLease(
            lane_ref=current.lane_ref,
            holder_ref=HolderRef.parse(request.target_holder_ref),
            generation=current.generation + 1,
            expires_at=datetime.now(UTC) + timedelta(seconds=request.ttl_seconds),
        )
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=replacement,
        )
        connection.commit()
    return result


def expected_current_lease(
    connection: sqlite3.Connection,
    *,
    request: LeaseOperationRequest,
    require_expired: bool | None,
) -> tuple[LeaseRow, LaneLease]:
    """Admit one exact four-coordinate Lease before mutation."""
    HolderRef.parse(request.holder_ref)
    initialize_state_connection(connection)
    observation = observe_lease_from_connection(connection, request.branch)
    if observation.state == "missing":
        msg = f"work_lane_missing_lease:{request.branch}"
        raise ValueError(msg)
    if observation.state == "unknown" or observation.row is None or observation.lease is None:
        msg = f"lease_unknown:{request.branch}"
        raise ValueError(msg)
    row, lease = observation.row, observation.lease
    expected = (request.branch, request.holder_ref, request.generation, request.expires_at)
    actual = (row.lane_ref, row.holder_ref, row.generation, row.expires_at)
    if expected != actual:
        msg = f"lease_generation_stale:{request.branch}"
        raise ValueError(msg)
    if require_expired is True and observation.state != "expired":
        msg = f"lease_not_expired:{request.branch}"
        raise ValueError(msg)
    if require_expired is False and observation.state != "valid":
        msg = f"lease_expired:{request.branch}"
        raise ValueError(msg)
    return row, lease


def replace_exact_lease_from_connection(
    connection: sqlite3.Connection,
    *,
    current: LeaseRow,
    replacement: LaneLease,
) -> dict[str, object]:
    """Replace one row through exact four-coordinate compare-and-swap."""
    if replacement.lane_ref != current.lane_ref:
        msg = f"lease_reissue_identity_mismatch:{current.lane_ref}"
        raise ValueError(msg)
    holder = replacement.holder_ref.serialize()
    expires_at = replacement.expires_at.isoformat()
    cursor = connection.execute(
        "update leases set holder_ref = ?, generation = ?, expires_at = ? "
        "where lane_ref = ? and holder_ref = ? and generation = ? and expires_at = ?",
        (
            holder,
            replacement.generation,
            expires_at,
            current.lane_ref,
            current.holder_ref,
            current.generation,
            current.expires_at,
        ),
    )
    if cursor.rowcount != 1:
        msg = f"lease_generation_stale:{current.lane_ref}"
        raise ValueError(msg)
    return lease_record((current.lane_ref, holder, replacement.generation, expires_at))

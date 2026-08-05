"""Strict full-payload SQLite Lane Lease transitions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.store.state.lease.projection import LeaseRow
from ethos.adapters.store.state.lease.projection import exact_lease_candidate
from ethos.adapters.store.state.lease.projection import lease_record
from ethos.adapters.store.state.lease.projection import observe_lease_from_connection
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseHandoffOffer
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.coordination import lease_operation

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def acquire_lease(db_path: Path, *, lease: LaneLease) -> dict[str, object]:
    """Persist one complete strict Lease before any lane carrier effect."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload_json = _payload_json(lease)
    owner = lease.holder_ref.serialize()
    expires_at = lease.expires_at.isoformat()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma journal_mode = wal")
        connection.execute("begin immediate")
        try:
            initialize_state_connection(connection)
            connection.execute(
                "insert into leases(id, subject, owner, expires_at, payload_json) "
                "values (?, ?, ?, ?, ?)",
                (lease.lease_id, lease.lane_ref, owner, expires_at, payload_json),
            )
        except sqlite3.IntegrityError as exc:
            message = f"lane_lease_conflict:{lease.lane_ref}"
            raise ValueError(message) from exc
        connection.commit()
    return lease_record((lease.lease_id, lease.lane_ref, owner, expires_at, payload_json))


def apply_lease_operation(
    db_path: Path,
    *,
    request: LeaseOperationRequest,
) -> dict[str, object]:
    """Apply one exact full-payload Lease reissue."""
    operation = lease_operation(request.operation)
    if not request.apply:
        message = f"lease_apply_required:{request.operation}"
        raise ValueError(message)
    return _apply_lease_effect(
        db_path,
        kind=operation.kind,
        require_expired=operation.require_expired,
        request=request,
    )


def takeover_lease(
    db_path: Path,
    *,
    request: LeaseTakeoverRequest,
    observe_repository: Callable[[], tuple[str, str, str]],
) -> dict[str, object]:
    """Change one exact holder generation while repository observations stay fixed."""
    if not request.apply:
        message = "lease_apply_required:takeover"
        raise ValueError(message)
    lease_request = LeaseOperationRequest(
        operation="handoff_accept",
        branch=request.branch,
        holder_ref=request.source_holder_ref,
        lease_id=request.lease_id,
        expected_epoch=request.expected_epoch,
        expect_head=request.expect_head,
        expected_expires_at=request.expected_expires_at,
        expected_payload_sha256=request.expected_payload_sha256,
        apply=True,
    )
    expected_observation = (
        request.expect_head,
        request.expected_tree,
        request.expected_dirty_content_sha256,
    )
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        if observe_repository() != expected_observation:
            message = "lease_takeover_repository_drift"
            raise ValueError(message)
        row, current = expected_current_lease(
            connection,
            request=lease_request,
            require_expired=None,
        )
        if current.lane_incarnation_id != request.expected_lane_incarnation_id:
            message = "lease_takeover_incarnation_drift"
            raise ValueError(message)
        if current.expected_tree != request.expected_tree:
            message = "lease_takeover_tree_drift"
            raise ValueError(message)
        now = datetime.now(UTC)
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=_validated_reissue(
                current,
                holder_ref=HolderRef.parse(request.target_holder_ref),
                epoch=current.epoch + 1,
                renewed_at=now,
                expires_at=now + timedelta(seconds=request.ttl_seconds),
                handoff=None,
            ),
        )
        if observe_repository() != expected_observation:
            message = "lease_takeover_repository_drift"
            raise ValueError(message)
        connection.commit()
    return result


def _apply_lease_effect(
    db_path: Path,
    *,
    kind: str,
    require_expired: bool,
    request: LeaseOperationRequest,
) -> dict[str, object]:
    if kind not in {"refresh", "offer", "accept"}:
        message = f"lease_effect_unknown:{request.operation}"
        raise ValueError(message)
    _validate_lease_request(kind=kind, request=request)
    now = datetime.now(UTC)
    offer_id = f"handoff-offer:{uuid.uuid4()}" if kind == "offer" else ""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        row, current = expected_current_lease(
            connection,
            request=request,
            require_expired=require_expired,
        )
        replacement = _reissued_lease(
            current,
            kind=kind,
            request=request,
            now=now,
            offer_id=offer_id,
        )
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=replacement,
        )
        connection.commit()
    if kind == "offer":
        return {
            **result,
            "offer_id": offer_id,
            "target_holder_ref": request.target_holder_ref,
            "state": "offered",
        }
    return result


def _validate_lease_request(*, kind: str, request: LeaseOperationRequest) -> None:
    HolderRef.parse(request.holder_ref)
    if kind == "refresh":
        return
    HolderRef.parse(request.target_holder_ref)
    if kind == "accept" and not request.holder_quiesced:
        message = f"lease_handoff_holder_not_quiesced:{request.branch}"
        raise ValueError(message)


def _reissued_lease(
    current: LaneLease,
    *,
    kind: str,
    request: LeaseOperationRequest,
    now: datetime,
    offer_id: str,
) -> LaneLease:
    if kind == "refresh":
        return _validated_reissue(
            current,
            holder_ref=current.holder_ref,
            epoch=current.epoch,
            renewed_at=now,
            expires_at=now + timedelta(seconds=request.ttl_seconds),
            handoff=current.handoff,
        )
    if kind == "offer":
        return _validated_reissue(
            current,
            holder_ref=current.holder_ref,
            epoch=current.epoch,
            renewed_at=current.renewed_at,
            expires_at=current.expires_at,
            handoff=LeaseHandoffOffer(
                offer_id=offer_id,
                target_holder_ref=request.target_holder_ref,
                offered_at=now,
            ),
        )
    if current.handoff is None:
        message = f"lease_handoff_offer_missing:{request.branch}"
        raise ValueError(message)
    _expect_equal("handoff_offer", request.offer_id, current.handoff.offer_id)
    _expect_equal("handoff_target", request.target_holder_ref, current.handoff.target_holder_ref)
    return _validated_reissue(
        current,
        holder_ref=HolderRef.parse(request.target_holder_ref),
        epoch=current.epoch + 1,
        renewed_at=now,
        expires_at=now + timedelta(seconds=request.ttl_seconds),
        handoff=None,
    )


def _validated_reissue(
    current: LaneLease,
    *,
    holder_ref: HolderRef,
    epoch: int,
    renewed_at: datetime,
    expires_at: datetime,
    handoff: LeaseHandoffOffer | None,
    binding: dict[str, str] | None = None,
) -> LaneLease:
    """Validate one complete replacement before it reaches the SQL CAS boundary."""
    expected_head = binding["expected_head"] if binding is not None else current.expected_head
    expected_tree = binding["expected_tree"] if binding is not None else current.expected_tree
    path = binding["base_commitment_path"] if binding is not None else current.base_commitment_path
    bytes_sha256 = (
        binding["base_commitment_bytes_sha256"]
        if binding is not None
        else current.base_commitment_bytes_sha256
    )
    digest = (
        binding["base_commitment_digest"] if binding is not None else current.base_commitment_digest
    )
    return LaneLease(
        lane_incarnation_id=current.lane_incarnation_id,
        lease_id=current.lease_id,
        lane_ref=current.lane_ref,
        holder_ref=holder_ref,
        epoch=epoch,
        issued_at=current.issued_at,
        renewed_at=renewed_at,
        expires_at=expires_at,
        expected_head=expected_head,
        expected_tree=expected_tree,
        base_commitment_path=path,
        base_commitment_bytes_sha256=bytes_sha256,
        base_commitment_digest=digest,
        path_scope=current.path_scope,
        handoff=handoff,
    )


def advance_lease_ref(
    db_path: Path,
    *,
    request: LeaseOperationRequest,
    binding: dict[str, str],
) -> dict[str, object]:
    """Atomically rebind one strict Lease to one complete Git carrier binding."""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        row, current = expected_current_lease(
            connection,
            request=request,
            require_expired=False,
        )
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=_validated_reissue(
                current,
                holder_ref=current.holder_ref,
                epoch=current.epoch,
                renewed_at=current.renewed_at,
                expires_at=current.expires_at,
                handoff=current.handoff,
                binding=binding,
            ),
        )
        connection.commit()
    return result


def rebind_lease_commitment(
    db_path: Path,
    *,
    request: LeaseOperationRequest,
    binding: dict[str, str],
) -> dict[str, object]:
    """CAS one old Lease generation to a new Commitment and the next epoch."""
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        row, current = expected_current_lease(
            connection,
            request=request,
            require_expired=False,
        )
        if current.handoff is not None:
            message = f"lease_handoff_pending:{request.branch}"
            raise ValueError(message)
        result = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=_validated_reissue(
                current,
                holder_ref=current.holder_ref,
                epoch=current.epoch + 1,
                renewed_at=current.renewed_at,
                expires_at=current.expires_at,
                handoff=None,
                binding=binding,
            ),
        )
        connection.commit()
    return result


def expected_current_lease(
    connection: sqlite3.Connection,
    *,
    request: LeaseOperationRequest,
    require_expired: bool | None,
) -> tuple[LeaseRow, LaneLease]:
    """Admit one exact request-bound Lease before any mutation effect."""
    HolderRef.parse(request.holder_ref)
    initialize_state_connection(connection)
    observation = observe_lease_from_connection(connection, request.branch)
    if observation.state == "missing":
        message = f"work_lane_missing_lease:{request.branch}"
        raise ValueError(message)
    if observation.state == "unknown" or observation.row is None or observation.lease is None:
        message = f"lease_unknown:{request.branch}"
        raise ValueError(message)
    row, lease = observation.row, observation.lease
    _expect_equal("lease_id", request.lease_id, lease.lease_id)
    _expect_equal("holder", request.holder_ref, lease.holder_ref.serialize())
    _expect_equal("head", request.expect_head, lease.expected_head)
    if lease.epoch != request.expected_epoch:
        message = f"lease_epoch_stale:{request.expected_epoch}!={lease.epoch}"
        raise ValueError(message)
    expected = {
        "id": request.lease_id,
        "subject": request.branch,
        "owner": request.holder_ref,
        "expires_at": request.expected_expires_at,
        "payload_sha256": request.expected_payload_sha256,
    }
    actual = {
        "id": row.id,
        "subject": row.subject,
        "owner": row.owner,
        "expires_at": row.expires_at,
        "payload_sha256": row.payload_sha256,
    }
    if exact_lease_candidate(actual) != exact_lease_candidate(expected):
        message = f"lease_maintenance_candidate_drift:{request.lease_id}"
        raise ValueError(message)
    if require_expired is True and observation.state != "expired":
        message = f"lease_not_expired:{request.branch}"
        raise ValueError(message)
    if require_expired is False and observation.state != "valid":
        message = f"lease_expired:{request.branch}"
        raise ValueError(message)
    return row, lease


def replace_exact_lease_from_connection(
    connection: sqlite3.Connection,
    *,
    current: LeaseRow,
    replacement: LaneLease,
) -> dict[str, object]:
    """Replace one complete row through exact full-coordinate compare-and-swap."""
    if replacement.lease_id != current.id or replacement.lane_ref != current.subject:
        message = f"lease_reissue_identity_mismatch:{current.id}"
        raise ValueError(message)
    payload_json = _payload_json(replacement)
    owner = replacement.holder_ref.serialize()
    expires_at = replacement.expires_at.isoformat()
    cursor = connection.execute(
        "update leases set owner = ?, expires_at = ?, payload_json = ? "
        "where id = ? and subject = ? and owner = ? and expires_at = ? and payload_json = ?",
        (
            owner,
            expires_at,
            payload_json,
            current.id,
            current.subject,
            current.owner,
            current.expires_at,
            current.payload_json,
        ),
    )
    if cursor.rowcount != 1:
        message = f"lease_maintenance_candidate_drift:{current.id}"
        raise ValueError(message)
    return lease_record((current.id, current.subject, owner, expires_at, payload_json))


def _payload_json(lease: LaneLease) -> str:
    return json.dumps(lease.to_payload(), sort_keys=True)


def _expect_equal(kind: str, expected: str, actual: str) -> None:
    if expected == actual:
        return
    gap = {
        "holder": "lease_holder_mismatch",
        "lease_id": "lease_id_stale",
        "head": "lease_head_stale",
        "handoff_offer": "lease_handoff_offer_stale",
        "handoff_target": "lease_handoff_target_mismatch",
    }.get(kind, f"lease_{kind}_mismatch")
    message = f"{gap}:{expected}!={actual}"
    raise ValueError(message)

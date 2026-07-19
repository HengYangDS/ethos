"""Ignored SQLite Lane Lease lifecycle owner."""

# ruff: noqa: E501 - the source-budget closeout keeps bound state dimensions compact.

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.projection import json_object
from ethos.adapters.store.state.lease.projection import lease_contract_fields
from ethos.adapters.store.state.schema import initialize_state
from ethos.adapters.store.state.schema import now
from ethos_core.contracts.coordination import HolderRef
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

# fmt: off


def acquire_lease(
    db_path: Path, *, subject: str, holder_ref: str, ttl_seconds: int = 86_400,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one normalized local lease for a concrete execution instance.

    The physical ``leases.owner`` column remains only as a storage-compatibility
    carrier for legacy rows. New callers must provide a four-segment
    ``holder_ref``; accepting an unstructured owner here would manufacture new
    ambiguous state that readers are intentionally required to reject.
    """
    holder_ref = HolderRef.parse(holder_ref).serialize()
    initialize_state(db_path)
    lease_id = f"lease:{uuid.uuid4()}"
    current = datetime.now(UTC)
    expires_at = current + timedelta(seconds=ttl_seconds)
    supplied = dict(payload or {})
    normalized_payload = {
        **supplied, "lane_incarnation_id": str(supplied.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"),
        "lease_id": lease_id, "lane_ref": subject, "holder_ref": holder_ref,
        "epoch": int(supplied.get("epoch") or 1),
        "issued_at": str(supplied.get("issued_at") or current.isoformat()),
        "renewed_at": str(supplied.get("renewed_at") or current.isoformat()),
        "expected_head": str(supplied.get("expected_head") or ""),
        "claim_id": str(supplied.get("claim_id") or ""),
        "path_scope": string_sequence(supplied.get("path_scope"), drop_empty=True),
        "coordination_scope": "git_common_directory", "mints_authority": False,
        "filesystem_fence": False, "distributed_lock": False,
        "normalization_state": "normalized",
    }
    payload_json = json.dumps(normalized_payload, sort_keys=True)
    with closing(_transaction(db_path)) as connection:
        if _subject_rows(connection, subject):
            message = f"lane_lease_conflict:{subject}"
            raise ValueError(message)
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)",
            (lease_id, subject, holder_ref, expires_at.isoformat(), payload_json),
        )
        connection.commit()
    return _lease_record(lease_id=lease_id, subject=subject, expires_at=expires_at.isoformat(), payload=normalized_payload)


def normalize_lease(
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_head: str,
) -> dict[str, Any]:
    """Normalize one unambiguous legacy lease to a canonical holder ref.

    Legacy leases carry a free-form ``owner`` string (``codex``, ``agent:codex``,
    ``local-agent:codex:<lane>``, …) and no structured ``holder_ref``. Normalization
    rewrites both to a canonical four-segment ``HolderRef``. It deliberately does NOT
    require the new ``holder_ref`` to string-equal the legacy ``owner``: those are
    different schemas (a 4-segment ref can never equal a 1-to-3 segment legacy name), so
    such a check made migration impossible (the exact bug this closes). Anti-hijack
    safety comes from proof of OBSERVATION, established by the caller pipeline before we
    are reached: the request is admitted only from the lane's own worktree at its exact
    ``expect_head`` (``_lease_request_gaps``), and here the ``expected_lease_id`` must
    match the row's UUID. Knowing a lane's exact lease UUID and holding its checkout is
    the "same holder" evidence; a bystander cannot normalize another lane's lease.
    """
    HolderRef.parse(holder_ref)
    initialize_state(db_path)
    current = datetime.now(UTC)
    with closing(_transaction(db_path)) as connection:
        row = _sole_subject_row(connection, subject)
        payload = json_object(row[4])
        _expect_equal("lease_id", expected_lease_id, str(row[0]))
        normalized = _normalized_lease_payload(
            payload=payload, subject=subject, holder_ref=holder_ref,
            lease_id=str(row[0]), expected_head=expected_head, now=current,
        )
        return _write_lease(connection, row, normalized, owner=holder_ref)


def renew_lease(  # noqa: PLR0913, RUF100 - stable public lease lifecycle contract
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_epoch: int, expected_head: str, ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Renew one normalized, unexpired lease through generation-bound CAS."""
    return _refresh_lease(db_path, subject=subject, holder_ref=holder_ref,
        expected_lease_id=expected_lease_id, expected_epoch=expected_epoch,
        expected_head=expected_head, ttl_seconds=ttl_seconds, require_expired=False)


def resume_lease(  # noqa: PLR0913, RUF100 - stable public lease lifecycle contract
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_epoch: int, expected_head: str, ttl_seconds: int = 86_400,
    contrary_decision: bool = False,
) -> dict[str, Any]:
    """Resume an expired lease only for its prior holder and unchanged generation."""
    if contrary_decision:
        message = f"lease_resume_blocked_by_decision:{subject}"
        raise ValueError(message)
    return _refresh_lease(db_path, subject=subject, holder_ref=holder_ref,
        expected_lease_id=expected_lease_id, expected_epoch=expected_epoch,
        expected_head=expected_head, ttl_seconds=ttl_seconds, require_expired=True)


def offer_lease_handoff(  # noqa: PLR0913, RUF100 - stable public lease lifecycle contract
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_epoch: int, target_holder_ref: str, expected_head: str,
) -> dict[str, Any]:
    """Record a local handoff offer without changing the current holder."""
    HolderRef.parse(target_holder_ref)
    offer_id = f"handoff-offer:{uuid.uuid4()}"
    current = datetime.now(UTC)
    with closing(_transaction(db_path)) as connection:
        row, payload = expected_current_lease(
            connection, subject=subject, holder_ref=holder_ref,
            expected_lease_id=expected_lease_id, expected_epoch=expected_epoch,
            expected_head=expected_head, require_expired=False,
        )
        payload.update({"handoff_state": "offered", "handoff_offer_id": offer_id,
            "handoff_target_holder_ref": target_holder_ref,
            "handoff_offered_at": current.isoformat()})
        _write_lease(connection, row, payload)
    return {
        "offer_id": offer_id, "subject": subject, "holder_ref": holder_ref,
        "target_holder_ref": target_holder_ref, "lease_id": expected_lease_id,
        "epoch": expected_epoch, "expected_head": expected_head, "state": "offered",
    }


def accept_lease_handoff(  # noqa: PLR0913, RUF100 - stable public lease lifecycle contract
    db_path: Path, *, subject: str, target_holder_ref: str, offer_id: str,
    expected_lease_id: str, expected_epoch: int, expected_head: str,
    holder_quiesced: bool, ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Accept an offered handoff and atomically replace holder plus generation."""
    HolderRef.parse(target_holder_ref)
    if not holder_quiesced:
        message = f"lease_handoff_holder_not_quiesced:{subject}"
        raise ValueError(message)
    current = datetime.now(UTC)
    expires_at = current + timedelta(seconds=ttl_seconds)
    with closing(_transaction(db_path)) as connection:
        row = _sole_subject_row(connection, subject)
        payload = json_object(row[4])
        _expect_normalized(payload, subject)
        _expect_equal("lease_id", expected_lease_id, str(row[0]))
        _expect_epoch(payload, expected_epoch)
        _expect_equal("head", expected_head, str(payload.get("expected_head") or ""))
        _expect_equal("handoff_offer", offer_id, str(payload.get("handoff_offer_id") or ""))
        _expect_equal("handoff_target", target_holder_ref, str(payload.get("handoff_target_holder_ref") or ""))
        payload.update({"holder_ref": target_holder_ref, "epoch": expected_epoch + 1,
            "renewed_at": current.isoformat(), "handoff_state": "accepted",
            "handoff_accepted_at": current.isoformat()})
        return _write_lease(connection, row, payload, owner=target_holder_ref,
            expires_at=expires_at.isoformat())


def advance_lease_head(  # noqa: PLR0913, RUF100 - stable public lease lifecycle contract
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_epoch: int, old_head: str, new_head: str,
) -> dict[str, Any]:
    """Advance the lease's observed Git head through generation-bound CAS."""
    HolderRef.parse(holder_ref)
    initialize_state(db_path)
    with closing(_transaction(db_path)) as connection:
        row, payload = expected_current_lease(
            connection, subject=subject, holder_ref=holder_ref,
            expected_lease_id=expected_lease_id, expected_epoch=expected_epoch,
            expected_head=old_head, require_expired=False,
        )
        payload["expected_head"] = new_head
        payload["head_observed_at"] = now()
        return _write_lease(connection, row, payload, owner=holder_ref)


def _refresh_lease(  # noqa: PLR0913, RUF100 - stable internal lease refresh contract
    db_path: Path, *, subject: str, holder_ref: str, expected_lease_id: str,
    expected_epoch: int, expected_head: str, ttl_seconds: int, require_expired: bool,
) -> dict[str, Any]:
    HolderRef.parse(holder_ref)
    initialize_state(db_path)
    current = datetime.now(UTC)
    expires_at = current + timedelta(seconds=ttl_seconds)
    with closing(_transaction(db_path)) as connection:
        row, payload = expected_current_lease(
            connection, subject=subject, holder_ref=holder_ref,
            expected_lease_id=expected_lease_id, expected_epoch=expected_epoch,
            expected_head=expected_head, require_expired=require_expired,
        )
        payload["renewed_at"] = current.isoformat()
        return _write_lease(connection, row, payload, owner=holder_ref,
            expires_at=expires_at.isoformat())


def expected_current_lease(  # noqa: PLR0913, RUF100 - stable shared lease validation contract
    connection: sqlite3.Connection, *, subject: str, holder_ref: str,
    expected_lease_id: str, expected_epoch: int, expected_head: str,
    require_expired: bool,
) -> tuple[sqlite3.Row | tuple[Any, ...], dict[str, Any]]:
    row = _sole_subject_row(connection, subject)
    payload = json_object(row[4])
    _expect_normalized(payload, subject)
    _expect_equal("lease_id", expected_lease_id, str(row[0]))
    _expect_equal("holder", holder_ref, str(payload.get("holder_ref") or row[2]))
    _expect_epoch(payload, expected_epoch)
    _expect_equal("head", expected_head, str(payload.get("expected_head") or ""))
    expired = _is_expired(str(row[3]))
    if require_expired and not expired:
        message = f"lease_not_expired:{subject}"
        raise ValueError(message)
    if not require_expired and expired:
        message = f"lease_expired:{subject}"
        raise ValueError(message)
    return row, payload


def _normalized_lease_payload(  # noqa: PLR0913, RUF100 - stable normalized lease payload contract
    *, payload: dict[str, Any], subject: str, holder_ref: str, lease_id: str,
    expected_head: str, now: datetime,
) -> dict[str, Any]:
    return {
        **payload, "lane_incarnation_id": str(payload.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"),
        "lease_id": lease_id, "lane_ref": subject, "holder_ref": holder_ref,
        "epoch": int(payload.get("epoch") or 1),
        "issued_at": str(payload.get("issued_at") or now.isoformat()),
        "renewed_at": now.isoformat(), "expected_head": expected_head,
        "claim_id": str(payload.get("claim_id") or ""),
        "path_scope": string_sequence(payload.get("path_scope"), drop_empty=True),
        "coordination_scope": "git_common_directory", "mints_authority": False,
        "filesystem_fence": False, "distributed_lock": False,
        "normalization_state": "normalized",
    }


def _transaction(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("pragma foreign_keys = on")
    connection.execute("begin immediate")
    return connection


def _subject_rows(connection: sqlite3.Connection, subject: str) -> list[sqlite3.Row | tuple[Any, ...]]:
    return connection.execute(
        "select id, subject, owner, expires_at, payload_json from leases where subject = ? order by id", (subject,),
    ).fetchall()


def _sole_subject_row(connection: sqlite3.Connection, subject: str) -> sqlite3.Row | tuple[Any, ...]:
    rows = _subject_rows(connection, subject)
    if not rows:
        message = f"work_lane_missing_lease:{subject}"
        raise ValueError(message)
    if len(rows) != 1:
        message = f"lane_lease_ambiguous:{subject}"
        raise ValueError(message)
    return rows[0]


def _write_lease(
    connection: sqlite3.Connection, row: sqlite3.Row | tuple[Any, ...], payload: dict[str, Any],
    *, owner: str | None = None, expires_at: str | None = None,
) -> dict[str, Any]:
    owner, expires_at = owner or str(row[2]), expires_at or str(row[3])
    connection.execute(
        "update leases set owner = ?, expires_at = ?, payload_json = ? where id = ?",
        (owner, expires_at, json.dumps(payload, sort_keys=True), str(row[0])),
    )
    connection.commit()
    return _lease_record(lease_id=str(row[0]), subject=str(row[1]), expires_at=expires_at, payload=payload)


def _lease_record(
    *, lease_id: str, subject: str, expires_at: str, payload: dict[str, Any],
) -> dict[str, Any]:
    return {"id": lease_id, "subject": subject, "expires_at": expires_at,
        **lease_contract_fields(payload), "payload": payload}


def _expect_equal(kind: str, expected: str, actual: str) -> None:
    if expected == actual:
        return
    gap = {"holder": "lease_holder_mismatch", "lease_id": "lease_id_stale",
        "head": "lease_head_stale", "handoff_offer": "lease_handoff_offer_stale",
        "handoff_target": "lease_handoff_target_mismatch"}.get(kind, f"lease_{kind}_mismatch")
    message = f"{gap}:{expected}!={actual}"
    raise ValueError(message)


def _expect_epoch(payload: dict[str, Any], expected_epoch: int) -> None:
    actual = int(payload.get("epoch") or 0)
    if actual != expected_epoch:
        message = f"lease_epoch_stale:{expected_epoch}!={actual}"
        raise ValueError(message)


def _expect_normalized(payload: dict[str, Any], subject: str) -> None:
    if payload.get("normalization_state") != "normalized":
        message = f"lane_lease_legacy_ambiguous:{subject}"
        raise ValueError(message)


def _is_expired(value: str) -> bool:
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)

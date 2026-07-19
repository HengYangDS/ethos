"""Ignored SQLite Lane Lease lifecycle owner."""

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
from ethos_core.contracts.coordination import HolderRef
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from pathlib import Path


_SCHEMA = """
    create table if not exists leases (
      id text primary key,
      subject text not null,
      owner text not null,
      expires_at text not null,
      payload_json text not null
    )
    """


def initialize_lease_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma journal_mode = wal")
        connection.execute("pragma foreign_keys = on")
        connection.execute(_SCHEMA)
        connection.commit()


def acquire_lease(
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    ttl_seconds: int = 86_400,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one local lease for a concrete execution instance."""
    normalized_holder_ref = HolderRef.parse(holder_ref).serialize()
    initialize_lease_state(db_path)
    lease_id = f"lease:{uuid.uuid4()}"
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    supplied_payload = dict(payload or {})
    lane_incarnation_id = str(
        supplied_payload.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"
    )
    normalized_payload = {
        **supplied_payload,
        "lane_incarnation_id": lane_incarnation_id,
        "lease_id": lease_id,
        "lane_ref": subject,
        "holder_ref": normalized_holder_ref,
        "epoch": int(supplied_payload.get("epoch") or 1),
        "issued_at": str(supplied_payload.get("issued_at") or now.isoformat()),
        "renewed_at": str(supplied_payload.get("renewed_at") or now.isoformat()),
        "expected_head": str(supplied_payload.get("expected_head") or ""),
        "claim_id": str(supplied_payload.get("claim_id") or ""),
        "path_scope": string_sequence(supplied_payload.get("path_scope"), drop_empty=True),
        "coordination_scope": "git_common_directory",
        "mints_authority": False,
        "filesystem_fence": False,
        "distributed_lock": False,
    }
    payload_json = json.dumps(normalized_payload, sort_keys=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        if _subject_rows(connection, subject):
            raise ValueError(f"lane_lease_conflict:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, ?, ?, ?)
            """,
            (
                lease_id,
                subject,
                normalized_holder_ref,
                expires_at.isoformat(),
                payload_json,
            ),
        )
        connection.commit()
    return {
        "id": lease_id,
        "subject": subject,
        "expires_at": expires_at.isoformat(),
        **lease_contract_fields(normalized_payload),
        "payload": normalized_payload,
    }


def renew_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Renew one normalized, unexpired lease through generation-bound CAS."""
    return _refresh_lease(
        db_path,
        subject=subject,
        holder_ref=holder_ref,
        expected_lease_id=expected_lease_id,
        expected_epoch=expected_epoch,
        expected_head=expected_head,
        ttl_seconds=ttl_seconds,
        require_expired=False,
    )


def resume_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    ttl_seconds: int = 86_400,
    contrary_decision: bool = False,
) -> dict[str, Any]:
    """Resume an expired lease only for its prior holder and unchanged generation."""
    if contrary_decision:
        raise ValueError(f"lease_resume_blocked_by_decision:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    return _refresh_lease(
        db_path,
        subject=subject,
        holder_ref=holder_ref,
        expected_lease_id=expected_lease_id,
        expected_epoch=expected_epoch,
        expected_head=expected_head,
        ttl_seconds=ttl_seconds,
        require_expired=True,
    )


def offer_lease_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    target_holder_ref: str,
    expected_head: str,
) -> dict[str, Any]:
    """Record a local handoff offer without changing the current holder."""
    HolderRef.parse(target_holder_ref)
    offer_id = f"handoff-offer:{uuid.uuid4()}"
    now = datetime.now(UTC)
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
        payload.update(
            {
                "handoff_state": "offered",
                "handoff_offer_id": offer_id,
                "handoff_target_holder_ref": target_holder_ref,
                "handoff_offered_at": now.isoformat(),
            }
        )
        _update_lease_row(
            connection,
            lease_id=str(row[0]),
            owner=str(row[2]),
            expires_at=str(row[3]),
            payload=payload,
        )
        connection.commit()
    return {
        "offer_id": offer_id,
        "subject": subject,
        "holder_ref": holder_ref,
        "target_holder_ref": target_holder_ref,
        "lease_id": expected_lease_id,
        "epoch": expected_epoch,
        "expected_head": expected_head,
        "state": "offered",
    }


def accept_lease_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    target_holder_ref: str,
    offer_id: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    holder_quiesced: bool,
    ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Accept an offered handoff and atomically replace holder plus generation."""
    HolderRef.parse(target_holder_ref)
    if not holder_quiesced:
        raise ValueError(f"lease_handoff_holder_not_quiesced:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        row = _sole_subject_row(connection, subject)
        payload = json_object(row[4])
        _expect_equal("lease_id", expected_lease_id, str(row[0]))
        _expect_epoch(payload, expected_epoch)
        _expect_equal("head", expected_head, str(payload.get("expected_head") or ""))
        _expect_equal("handoff_offer", offer_id, str(payload.get("handoff_offer_id") or ""))
        _expect_equal(
            "handoff_target",
            target_holder_ref,
            str(payload.get("handoff_target_holder_ref") or ""),
        )
        payload.update(
            {
                "holder_ref": target_holder_ref,
                "epoch": expected_epoch + 1,
                "renewed_at": now.isoformat(),
                "handoff_state": "accepted",
                "handoff_accepted_at": now.isoformat(),
            }
        )
        _update_lease_row(
            connection,
            lease_id=str(row[0]),
            owner=target_holder_ref,
            expires_at=expires_at.isoformat(),
            payload=payload,
        )
        connection.commit()
    return _lease_record(
        lease_id=str(row[0]),
        subject=subject,
        owner=target_holder_ref,
        expires_at=expires_at.isoformat(),
        payload=payload,
    )


def advance_lease_head(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    old_head: str,
    new_head: str,
) -> dict[str, Any]:
    """Advance the lease's observed Git head through generation-bound CAS."""
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
            expected_head=old_head,
            require_expired=False,
        )
        payload["expected_head"] = new_head
        payload["head_observed_at"] = datetime.now(UTC).isoformat()
        _update_lease_row(
            connection,
            lease_id=str(row[0]),
            owner=holder_ref,
            expires_at=str(row[3]),
            payload=payload,
        )
        connection.commit()
    return _lease_record(
        lease_id=str(row[0]),
        subject=subject,
        owner=holder_ref,
        expires_at=str(row[3]),
        payload=payload,
    )


def _refresh_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    ttl_seconds: int,
    require_expired: bool,
) -> dict[str, Any]:
    HolderRef.parse(holder_ref)
    initialize_lease_state(db_path)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
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
            require_expired=require_expired,
        )
        payload["renewed_at"] = now.isoformat()
        _update_lease_row(
            connection,
            lease_id=str(row[0]),
            owner=holder_ref,
            expires_at=expires_at.isoformat(),
            payload=payload,
        )
        connection.commit()
    return _lease_record(
        lease_id=str(row[0]),
        subject=subject,
        owner=holder_ref,
        expires_at=expires_at.isoformat(),
        payload=payload,
    )


def expected_current_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    connection: sqlite3.Connection,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    require_expired: bool,
) -> tuple[sqlite3.Row | tuple[Any, ...], dict[str, Any]]:
    row = _sole_subject_row(connection, subject)
    payload = json_object(row[4])
    _expect_equal("lease_id", expected_lease_id, str(row[0]))
    _expect_equal("holder", holder_ref, str(payload.get("holder_ref") or ""))
    _expect_epoch(payload, expected_epoch)
    _expect_equal("head", expected_head, str(payload.get("expected_head") or ""))
    expired = _is_expired(str(row[3]))
    if require_expired and not expired:
        raise ValueError(f"lease_not_expired:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    if not require_expired and expired:
        raise ValueError(f"lease_expired:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    return row, payload


def _subject_rows(
    connection: sqlite3.Connection, subject: str
) -> list[sqlite3.Row | tuple[Any, ...]]:
    return connection.execute(
        """
        select id, subject, owner, expires_at, payload_json
        from leases
        where subject = ?
        order by id
        """,
        (subject,),
    ).fetchall()


def _sole_subject_row(
    connection: sqlite3.Connection, subject: str
) -> sqlite3.Row | tuple[Any, ...]:
    rows = _subject_rows(connection, subject)
    if not rows:
        raise ValueError(f"work_lane_missing_lease:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    if len(rows) != 1:
        raise ValueError(f"lane_lease_ambiguous:{subject}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    return rows[0]


def _update_lease_row(
    connection: sqlite3.Connection,
    *,
    lease_id: str,
    owner: str,
    expires_at: str,
    payload: dict[str, Any],
) -> None:
    connection.execute(
        """
        update leases
        set owner = ?, expires_at = ?, payload_json = ?
        where id = ?
        """,
        (owner, expires_at, json.dumps(payload, sort_keys=True), lease_id),
    )


def _lease_record(
    *,
    lease_id: str,
    subject: str,
    owner: str,
    expires_at: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": lease_id,
        "subject": subject,
        "expires_at": expires_at,
        **lease_contract_fields(payload),
        "payload": payload,
    }


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
    raise ValueError(f"{gap}:{expected}!={actual}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract


def _expect_epoch(payload: dict[str, Any], expected_epoch: int) -> None:
    actual = int(payload.get("epoch") or 0)
    if actual != expected_epoch:
        raise ValueError(f"lease_epoch_stale:{expected_epoch}!={actual}")  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract


def _is_expired(value: str) -> bool:
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)

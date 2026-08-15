"""Lane Lease read model and payload projection."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal

from ethos.adapters.store.state.schema import read_only_state_uri
from ethos.adapters.store.state.schema import validate_current_lease_schema
from ethos.contracts.coordination import LaneLease

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class LeaseRow:
    """One exact SQLite Lease row including its raw payload identity."""

    id: str
    subject: str
    owner: str
    expires_at: str
    payload_json: str
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class LeaseObservation:
    """One strict Lease observation with four terminal states."""

    state: Literal["valid", "expired", "unknown", "missing"]
    subject: str
    row: LeaseRow | None = None
    lease: LaneLease | None = None
    error: str = ""

    def record(self) -> dict[str, Any]:
        """Project safe row diagnostics and strict Lease fields for readers."""
        if self.row is None:
            return {"subject": self.subject, "lease_state": self.state}
        result: dict[str, Any] = {
            "id": self.row.id,
            "subject": self.row.subject,
            "owner": self.row.owner,
            "expires_at": self.row.expires_at,
            "payload_sha256": self.row.payload_sha256,
            "lease_state": self.state,
        }
        if self.error:
            result["error"] = self.error
        if self.lease is not None:
            result.update(self.lease.to_payload())
            result["payload"] = self.lease.to_payload()
        return result


def active_leases(db_path: Path) -> list[dict[str, Any]]:
    return [item.record() for item in lease_observations(db_path) if item.state == "valid"]


def lease_observations(
    db_path: Path, *, observed_at: datetime | None = None
) -> list[LeaseObservation]:
    """Observe every row without collapsing invalid rows to missing."""
    if not db_path.exists():
        return []
    observed = observed_at or datetime.now(UTC)
    return [observe_lease_row(row, observed_at=observed) for row in lease_rows(db_path)]


def observe_lease(
    db_path: Path, subject: str, *, observed_at: datetime | None = None
) -> LeaseObservation:
    """Observe one lane through the valid/expired/unknown/missing algebra."""
    if not db_path.exists():
        return LeaseObservation(state="missing", subject=subject)
    with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
        if not validate_current_lease_schema(connection):
            return LeaseObservation(state="missing", subject=subject)
        return observe_lease_from_connection(connection, subject, observed_at=observed_at)


def observe_lease_from_connection(
    connection: sqlite3.Connection,
    subject: str,
    *,
    observed_at: datetime | None = None,
) -> LeaseObservation:
    """Observe one lane inside the caller's transaction."""
    row = connection.execute(
        "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
        (subject,),
    ).fetchone()
    if row is None:
        return LeaseObservation(state="missing", subject=subject)
    return observe_lease_row(row, observed_at=observed_at)


def observe_lease_row(
    row: sqlite3.Row | tuple[Any, ...], *, observed_at: datetime | None = None
) -> LeaseObservation:
    """Strictly classify one raw row and retain safe diagnostics on failure."""
    exact = lease_row(row)
    try:
        lease = _strict_lease_from_row(exact)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return LeaseObservation(
            state="unknown",
            subject=exact.subject,
            row=exact,
            error=str(exc),
        )
    observed = observed_at or datetime.now(UTC)
    state: Literal["valid", "expired"] = (
        "expired" if lease.expires_at.astimezone(UTC) <= observed else "valid"
    )
    return LeaseObservation(state=state, subject=exact.subject, row=exact, lease=lease)


def _strict_lease_from_row(row: LeaseRow) -> LaneLease:
    payload = json.loads(row.payload_json)
    if not isinstance(payload, dict):
        message = "lane_lease_payload_not_object"
        raise TypeError(message)
    if payload.get("expires_at") != row.expires_at:
        message = "lease_row_payload_expiry_mismatch"
        raise ValueError(message)
    lease = LaneLease.from_payload(payload)
    if (
        row.id != lease.lease_id
        or row.subject != lease.lane_ref
        or row.owner != lease.holder_ref.serialize()
    ):
        message = "lease_row_payload_identity_mismatch"
        raise ValueError(message)
    return lease


def lease_rows(db_path: Path) -> list[sqlite3.Row | tuple[Any, ...]]:
    with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
        if not validate_current_lease_schema(connection):
            return []
        return _selectlease_rows(connection)


def lease_record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    """Project one strict valid or expired row; reject unknown payloads."""
    observation = observe_lease_row(row)
    if observation.state == "unknown":
        message = f"lease_unknown:{observation.subject}"
        raise ValueError(message)
    return observation.record()


def project_lease(lease: LaneLease) -> dict[str, Any]:
    """Project one in-memory Lease through the canonical storage shape."""
    payload_json = json.dumps(lease.to_payload(), sort_keys=True)
    return lease_record(
        (
            lease.lease_id,
            lease.lane_ref,
            lease.holder_ref.serialize(),
            lease.expires_at.isoformat(),
            payload_json,
        )
    )


def lease_row(row: sqlite3.Row | tuple[Any, ...]) -> LeaseRow:
    """Capture the complete exact row coordinates used by compare-and-swap."""
    payload_json = str(row[4])
    return LeaseRow(
        id=str(row[0]),
        subject=str(row[1]),
        owner=str(row[2]),
        expires_at=str(row[3]),
        payload_json=payload_json,
        payload_sha256=hashlib.sha256(payload_json.encode()).hexdigest(),
    )


def exact_lease_candidate(lease: dict[str, Any]) -> dict[str, str]:
    """Return the complete row identity required by lease compare-and-swap."""
    return {
        name: str(lease.get(name) or "")
        for name in ("id", "subject", "owner", "expires_at", "payload_sha256")
    }


def _selectlease_rows(connection: sqlite3.Connection) -> list[sqlite3.Row | tuple[Any, ...]]:
    return connection.execute(
        """
        select id, subject, owner, expires_at, payload_json
        from leases
        order by subject, id
        """
    ).fetchall()


def integer_value(value: object) -> int:
    """Normalize a lease integer field without trusting an untyped payload."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0

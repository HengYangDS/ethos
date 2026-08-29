"""Minimal Lane Lease read model."""

from __future__ import annotations

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
    """One exact persisted Lease relation."""

    lane_ref: str
    holder_ref: str
    generation: int
    expires_at: str


@dataclass(frozen=True, slots=True)
class LeaseObservation:
    """One strict Lease observation with four terminal states."""

    state: Literal["valid", "expired", "unknown", "missing"]
    subject: str
    row: LeaseRow | None = None
    lease: LaneLease | None = None
    error: str = ""

    def record(self) -> dict[str, Any]:
        """Project only the minimal relation and its observation state."""
        if self.row is None:
            return {"subject": self.subject, "lease_state": self.state}
        result: dict[str, Any] = {
            "subject": self.row.lane_ref,
            "lease_state": self.state,
            "lane_ref": self.row.lane_ref,
            "holder_ref": self.row.holder_ref,
            "generation": self.row.generation,
            "expires_at": self.row.expires_at,
        }
        if self.error:
            result["error"] = self.error
        return result


def active_leases(db_path: Path) -> list[dict[str, Any]]:
    return [item.record() for item in lease_observations(db_path) if item.state == "valid"]


def lease_observations(
    db_path: Path, *, observed_at: datetime | None = None
) -> list[LeaseObservation]:
    if not db_path.exists():
        return []
    observed = observed_at or datetime.now(UTC)
    return [observe_lease_row(row, observed_at=observed) for row in lease_rows(db_path)]


def observe_lease(
    db_path: Path, subject: str, *, observed_at: datetime | None = None
) -> LeaseObservation:
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
    row = connection.execute(
        "select lane_ref, holder_ref, generation, expires_at from leases where lane_ref = ?",
        (subject,),
    ).fetchone()
    return (
        LeaseObservation(state="missing", subject=subject)
        if row is None
        else observe_lease_row(row, observed_at=observed_at)
    )


def observe_lease_row(
    row: sqlite3.Row | tuple[Any, ...], *, observed_at: datetime | None = None
) -> LeaseObservation:
    exact = lease_row(row)
    try:
        lease = LaneLease(
            lane_ref=exact.lane_ref,
            holder_ref=exact.holder_ref,
            generation=exact.generation,
            expires_at=datetime.fromisoformat(exact.expires_at),
        )
    except (TypeError, ValueError) as error:
        return LeaseObservation("unknown", exact.lane_ref, exact, error=str(error))
    observed = observed_at or datetime.now(UTC)
    state: Literal["valid", "expired"] = (
        "expired" if lease.expires_at.astimezone(UTC) <= observed else "valid"
    )
    return LeaseObservation(state, exact.lane_ref, exact, lease)


def lease_rows(db_path: Path) -> list[sqlite3.Row | tuple[Any, ...]]:
    with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
        if not validate_current_lease_schema(connection):
            return []
        return _select_lease_rows(connection)


def lease_record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    observation = observe_lease_row(row)
    if observation.state == "unknown":
        msg = f"lease_unknown:{observation.subject}"
        raise ValueError(msg)
    return observation.record()


def project_lease(lease: LaneLease) -> dict[str, Any]:
    return lease_record(
        (
            lease.lane_ref,
            lease.holder_ref.serialize(),
            lease.generation,
            lease.expires_at.isoformat(),
        )
    )


def lease_row(row: sqlite3.Row | tuple[Any, ...]) -> LeaseRow:
    return LeaseRow(str(row[0]), str(row[1]), integer_value(row[2]), str(row[3]))


def _select_lease_rows(connection: sqlite3.Connection) -> list[sqlite3.Row | tuple[Any, ...]]:
    return connection.execute(
        "select lane_ref, holder_ref, generation, expires_at from leases order by lane_ref"
    ).fetchall()


def integer_value(value: object) -> int:
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

"""Shared state constructors for lifecycle contract matrices."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.contracts.coordination import LaneLease

if TYPE_CHECKING:
    from pathlib import Path


def assert_public_decision(
    report: dict[str, object],
    *,
    verdict: str,
    state: str | None = None,
    gaps: list[str] | None = None,
) -> None:
    """Assert the stable public decision envelope without duplicating projections."""
    assert report["verdict"] == verdict
    assert "ok" not in report
    mutation = report.get("mutation")
    if isinstance(mutation, dict):
        decision = mutation.get("decision")
        if isinstance(decision, dict):
            assert decision["verdict"] == verdict
    if state is not None:
        assert report["state"] == state
    if gaps is not None:
        assert report["required_gaps"] == gaps


def strict_lease(
    *,
    branch: str = "work/example",
    holder: str = "agent:test:case:holder",
    **updates: object,
) -> LaneLease:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "lane_ref": branch,
        "holder_ref": holder,
        "generation": 1,
        "expires_at": now + timedelta(days=1),
    }
    values.update(updates)
    return LaneLease.model_validate(values)


def insert_lease_row(
    database: Path,
    lease: LaneLease,
    *,
    row_expires_at: str | None = None,
) -> None:
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
            (
                lease.lane_ref,
                lease.holder_ref.serialize(),
                lease.generation,
                row_expires_at or lease.expires_at.isoformat(),
            ),
        )

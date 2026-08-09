"""Fail-closed Lease projection behavior at the SQLite boundary."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import LeaseObservation
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.lease.projection import lease_record
from ethos.adapters.store.state.lease.projection import lease_rows
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.lease.projection import observe_lease_row
from ethos.adapters.store.state.schema import initialize_state_connection
from tests.support.lifecycle_cases import strict_lease


def test_missing_or_uninitialized_state_projects_no_active_authority(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    uninitialized = tmp_path / "uninitialized.sqlite"
    sqlite3.connect(uninitialized).close()

    assert LeaseObservation(state="missing", subject="work/example").record() == {
        "subject": "work/example",
        "lease_state": "missing",
    }
    assert lease_observations(missing) == []
    assert active_leases(missing) == []
    assert observe_lease(uninitialized, "work/example").state == "missing"
    assert lease_rows(uninitialized) == []


def test_projection_retains_expired_and_unknown_rows_but_filters_active_authority(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    expired = strict_lease(
        branch="work/expired",
        lease_id="lease:expired",
        lane_incarnation_id="lane-incarnation:expired",
        issued_at=datetime.now(UTC) - timedelta(days=2),
        renewed_at=datetime.now(UTC) - timedelta(days=2),
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    valid = strict_lease(
        branch="work/valid",
        lease_id="lease:valid",
        lane_incarnation_id="lane-incarnation:valid",
    )
    acquire_lease(database, lease=expired)
    acquire_lease(database, lease=valid)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            (
                "lease:unknown",
                "work/unknown",
                valid.holder_ref.serialize(),
                valid.expires_at.isoformat(),
                "[]",
            ),
        )

    observations = {item.subject: item for item in lease_observations(database)}

    assert set(observations) == {"work/expired", "work/unknown", "work/valid"}
    assert observations["work/expired"].state == "expired"
    assert observations["work/unknown"].state == "unknown"
    assert observations["work/unknown"].record()["error"] == "lane_lease_payload_not_object"
    assert [item["subject"] for item in active_leases(database)] == ["work/valid"]
    with pytest.raises(ValueError, match="lease_unknown:work/unknown"):
        lease_record(
            (
                "lease:unknown",
                "work/unknown",
                valid.holder_ref.serialize(),
                valid.expires_at.isoformat(),
                "[]",
            )
        )


def test_projection_rejects_row_payload_identity_mismatch() -> None:
    lease = strict_lease()
    row = (
        "lease:other",
        lease.lane_ref,
        lease.holder_ref.serialize(),
        lease.expires_at.isoformat(),
        json.dumps(lease.to_payload(), sort_keys=True),
    )

    observation = observe_lease_row(row)

    assert observation.state == "unknown"
    assert observation.error == "lease_row_payload_identity_mismatch"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, 0), (7, 7), ("8", 8), ("not-an-integer", 0), (None, 0)],
)
def test_integer_projection_never_trusts_untyped_values(value: object, expected: int) -> None:
    assert integer_value(value) == expected

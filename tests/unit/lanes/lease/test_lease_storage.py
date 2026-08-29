"""Minimal exact-CAS coverage for the four-field Lane Lease relation."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import takeover_lease
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from tests.support.lifecycle_cases import strict_lease
from tests.support.semantic import attestation_fixture

SOURCE = "agent:test:case:source"
TARGET = "agent:test:case:target"


def _operation(
    lease: dict[str, object], operation: str = "renew", **updates: object
) -> LeaseOperationRequest:
    return LeaseOperationRequest.model_validate(
        {
            "operation": operation,
            "branch": lease["lane_ref"],
            "holder_ref": lease["holder_ref"],
            "generation": lease["generation"],
            "expires_at": lease["expires_at"],
            "apply": True,
            **updates,
        }
    )


def _takeover(
    lease: dict[str, object], *, apply: bool = True, **updates: object
) -> LeaseTakeoverRequest:
    now = datetime.now(UTC)
    branch = str(lease["lane_ref"])
    expected = {
        "branch": branch,
        "holder_ref": SOURCE,
        "generation": int(lease["generation"]),
        "expires_at": str(lease["expires_at"]),
        "target_holder_ref": TARGET,
        "source_state": "source_lost",
    }
    return LeaseTakeoverRequest.model_validate(
        {
            "branch": branch,
            "source_holder_ref": SOURCE,
            "target_holder_ref": TARGET,
            "generation": lease["generation"],
            "expires_at": lease["expires_at"],
            "source_state": "source_lost",
            "authorization": attestation_fixture(
                predicate="lane-resolution:takeover",
                verifier="maintainer:test:case:reviewer",
                subject=f"git:branch:{branch}",
                issued_at=now,
                valid_from=now,
                payload_kind="authorization:lane-takeover",
                payload_body={"authorization": expected},
                evidence_refs=("evidence:test:takeover",),
            ),
            "apply": apply,
            **updates,
        }
    )


def test_acquire_conflict_preserves_the_original_generation(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    lease = strict_lease(holder=SOURCE)
    acquired = acquire_lease(database, lease=lease)

    with pytest.raises(ValueError, match="lane_lease_conflict:work/example"):
        acquire_lease(database, lease=lease)

    assert observe_lease(database, "work/example").record() == acquired


@pytest.mark.parametrize("operation", ["renew", "transfer"])
def test_unexpired_operation_replaces_one_exact_generation(tmp_path, operation: str) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))

    replacement = apply_lease_operation(
        database,
        request=_operation(
            acquired,
            operation,
            **({"target_holder_ref": TARGET} if operation == "transfer" else {}),
        ),
    )

    assert replacement["generation"] == 2
    assert replacement["holder_ref"] == (TARGET if operation == "transfer" else SOURCE)
    assert set(replacement) == {
        "subject",
        "lease_state",
        "lane_ref",
        "holder_ref",
        "generation",
        "expires_at",
    }


def test_resume_requires_expiry_and_replaces_the_same_holder(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    with pytest.raises(ValueError, match="lease_not_expired:work/example"):
        apply_lease_operation(database, request=_operation(acquired, "resume"))

    expired = strict_lease(
        holder=SOURCE,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    other = tmp_path / "expired.sqlite"
    stored = acquire_lease(other, lease=expired)
    resumed = apply_lease_operation(other, request=_operation(stored, "resume"))

    assert (resumed["generation"], resumed["holder_ref"]) == (2, SOURCE)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("holder_ref", TARGET),
        ("generation", 2),
        ("expires_at", "2026-08-29T00:00:00+00:00"),
    ],
)
def test_stale_coordinate_rejects_without_mutation(tmp_path, field: str, value: object) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))

    with pytest.raises(ValueError, match="lease_generation_stale:work/example"):
        apply_lease_operation(
            database,
            request=_operation(acquired).model_copy(update={field: value}),
        )

    assert observe_lease(database, "work/example").record() == acquired


def test_missing_and_unknown_are_distinct_and_non_authoritative(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    assert observe_lease(missing, "work/missing").state == "missing"

    unknown = tmp_path / "unknown.sqlite"
    with closing(sqlite3.connect(unknown)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
            ("work/unknown", SOURCE, 1, "not-a-time"),
        )
    observed = observe_lease(unknown, "work/unknown")

    assert observed.state == "unknown"
    assert active_leases(unknown) == []


def test_takeover_and_revoke_use_the_same_four_coordinate_cas(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))

    taken = takeover_lease(database, request=_takeover(acquired))
    assert (taken["generation"], taken["holder_ref"]) == (2, TARGET)

    revoked = revoke_lease(database, request=_operation(taken, "revoke"))
    assert revoked == {
        "revoked": True,
        "lane_ref": "work/example",
        "holder_ref": TARGET,
        "generation": 2,
        "expires_at": taken["expires_at"],
    }
    assert observe_lease(database, "work/example").state == "missing"


def test_failed_revoke_cas_leaves_the_row_unchanged(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))

    with pytest.raises(ValueError, match="lease_generation_stale:work/example"):
        revoke_lease(
            database,
            request=_operation(acquired, "revoke").model_copy(update={"generation": 2}),
        )

    assert observe_lease(database, "work/example").record() == acquired

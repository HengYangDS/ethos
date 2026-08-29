"""Minimal exact-CAS coverage for the four-field Lane Lease relation."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.mutation.lane_lifecycle.lease as lease_lifecycle
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import (
    replace_exact_lease_from_connection,
)
from ethos.adapters.store.state.lease.lifecycle.transitions import takeover_lease
from ethos.adapters.store.state.lease.projection import LeaseRow
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


def test_storage_rejects_nonapplying_or_unknown_operations(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))

    for request, gap in (
        (_operation(acquired, "unknown"), "lease_operation_unknown:unknown"),
        (_operation(acquired).model_copy(update={"apply": False}), "lease_apply_required:renew"),
    ):
        with pytest.raises(ValueError, match=gap):
            apply_lease_operation(database, request=request)
    with pytest.raises(ValueError, match="lease_apply_required:takeover"):
        takeover_lease(database, request=_takeover(acquired, apply=False))


def test_storage_observation_and_exact_cas_fail_closed(tmp_path) -> None:
    lease = strict_lease(holder=SOURCE)
    request = _operation(lease.to_payload())
    with pytest.raises(ValueError, match="work_lane_missing_lease:work/example"):
        apply_lease_operation(tmp_path / "missing.sqlite", request=request)

    unknown = tmp_path / "unknown.sqlite"
    with closing(sqlite3.connect(unknown)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
            ("work/example", SOURCE, 1, "not-a-time"),
        )
    with pytest.raises(ValueError, match="lease_unknown:work/example"):
        apply_lease_operation(
            unknown,
            request=request.model_copy(update={"expires_at": "not-a-time"}),
        )

    expired = tmp_path / "expired.sqlite"
    expired_record = acquire_lease(
        expired,
        lease=strict_lease(holder=SOURCE, expires_at=datetime.now(UTC) - timedelta(seconds=1)),
    )
    with pytest.raises(ValueError, match="lease_expired:work/example"):
        apply_lease_operation(expired, request=_operation(expired_record))

    database = tmp_path / "cas.sqlite"
    acquired = acquire_lease(database, lease=lease)
    current = LeaseRow(
        "work/example",
        SOURCE,
        1,
        str(acquired["expires_at"]),
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        with pytest.raises(ValueError, match="lease_reissue_identity_mismatch:work/example"):
            replace_exact_lease_from_connection(
                connection,
                current=current,
                replacement=strict_lease(branch="work/other", holder=SOURCE),
            )
        connection.execute("delete from leases where lane_ref = ?", ("work/example",))
        with pytest.raises(ValueError, match="lease_generation_stale:work/example"):
            replace_exact_lease_from_connection(
                connection,
                current=current,
                replacement=strict_lease(holder=SOURCE, generation=2),
            )


def test_public_lease_operation_projects_and_applies_exact_four_coordinate_cas(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    monkeypatch.setattr(lease_lifecycle, "repository_root", lambda _root: root)
    monkeypatch.setattr(
        lease_lifecycle,
        "workspace_status",
        lambda _root: {"role": "work_lane", "branch": "work/example"},
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "leases_by_branch",
        lambda _root: {"work/example": observe_lease(database, "work/example").record()},
    )
    monkeypatch.setattr(lease_lifecycle, "state_database", lambda _root: database)
    monkeypatch.setattr(lease_lifecycle, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(lease_lifecycle, "current_tree", lambda _root: "b" * 40)

    planned = lease_lifecycle.execute_lease_operation(
        root=root,
        request=_operation(acquired).model_copy(update={"apply": False}),
    )
    applied = lease_lifecycle.execute_lease_operation(
        root=root,
        request=_operation(acquired),
    )

    assert (planned["verdict"], planned["state"], planned["lease"]) == (
        "pass",
        "planned",
        {},
    )
    assert (applied["verdict"], applied["state"]) == ("pass", "renewed")
    assert applied["lease"]["generation"] == 2
    assert applied["mutation"]["decision"]["decision_basis"]["enforcement_boundary"] == (
        "local_sqlite_compare_and_swap"
    )


@pytest.mark.parametrize(
    ("operation", "updates", "status", "lease", "actor", "gap", "verdict"),
    [
        ("unknown", {}, {}, {}, SOURCE, "lease_operation_unknown:unknown", "block"),
        ("renew", {}, {"role": "accepted_root"}, {}, SOURCE, "work_lane_required", "block"),
        (
            "renew",
            {},
            {"role": "work_lane", "branch": "work/other"},
            {},
            SOURCE,
            "lane_branch_mismatch",
            "block",
        ),
        (
            "renew",
            {},
            {"role": "work_lane", "branch": "work/example"},
            {"lease_state": "missing"},
            SOURCE,
            "work_lane_missing_lease:work/example",
            "block",
        ),
        (
            "renew",
            {},
            {"role": "work_lane", "branch": "work/example"},
            {"lease_state": "unknown"},
            SOURCE,
            "work_lane_lease_unknown:work/example",
            "unknown",
        ),
        (
            "resume",
            {},
            {"role": "work_lane", "branch": "work/example"},
            {},
            SOURCE,
            "lease_not_expired:work/example",
            "block",
        ),
        (
            "renew",
            {"generation": 2},
            {"role": "work_lane", "branch": "work/example"},
            {},
            SOURCE,
            "lease_generation_stale:work/example",
            "block",
        ),
        (
            "renew",
            {},
            {"role": "work_lane", "branch": "work/example"},
            {},
            TARGET,
            "lease_actor_mismatch",
            "block",
        ),
        (
            "transfer",
            {},
            {"role": "work_lane", "branch": "work/example"},
            {},
            SOURCE,
            "target_holder_ref_required",
            "block",
        ),
        (
            "resume",
            {"contrary_decision": True},
            {"role": "work_lane", "branch": "work/example"},
            {},
            SOURCE,
            "lease_resume_blocked_by_decision",
            "block",
        ),
    ],
)
def test_public_lease_operation_fails_closed_with_one_precise_reason(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    updates: dict[str, object],
    status: dict[str, object],
    lease: dict[str, object],
    actor: str,
    gap: str,
    verdict: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    acquired = acquire_lease(tmp_path / "state.sqlite", lease=strict_lease(holder=SOURCE))
    observed = {**acquired, **lease}
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.setattr(lease_lifecycle, "repository_root", lambda _root: root)
    monkeypatch.setattr(
        lease_lifecycle,
        "workspace_status",
        lambda _root: {
            "role": "work_lane",
            "branch": "work/example",
            **status,
        },
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "leases_by_branch",
        lambda _root: {"work/example": observed},
    )
    monkeypatch.setattr(lease_lifecycle, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(lease_lifecycle, "current_tree", lambda _root: "b" * 40)
    request = _operation(acquired, operation).model_copy(update=updates)

    report = lease_lifecycle.execute_lease_operation(root=root, request=request)

    assert report["verdict"] == verdict
    assert gap in report["required_gaps"]
    assert report["lease"] == {}


def test_public_lease_takeover_requires_accepted_authorization_and_is_idempotent(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    request = _takeover(acquired)
    recorded = []
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    monkeypatch.setattr(lease_lifecycle, "repository_root", lambda _root: root)
    monkeypatch.setattr(
        lease_lifecycle,
        "leases_by_branch",
        lambda _root: {"work/example": observe_lease(database, "work/example").record()},
    )
    monkeypatch.setattr(lease_lifecycle, "state_database", lambda _root: database)
    monkeypatch.setattr(
        lease_lifecycle,
        "read_attestation_set",
        lambda _root: ("repository", (request.authorization,)),
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "record_attestations",
        lambda _root, values: recorded.extend(values),
    )
    monkeypatch.setattr(lease_lifecycle, "repository_identity", lambda _root: "repository")
    monkeypatch.setattr(lease_lifecycle, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(lease_lifecycle, "current_tree", lambda _root: "b" * 40)
    monkeypatch.setattr(lease_lifecycle, "dirty_content_sha256", lambda _root: "c" * 64)

    applied = lease_lifecycle.execute_lease_takeover(root=root, request=request)
    recovered = lease_lifecycle.execute_lease_takeover(root=root, request=request)

    assert (applied["verdict"], applied["state"], applied["lease"]["holder_ref"]) == (
        "pass",
        "taken_over",
        TARGET,
    )
    assert (recovered["verdict"], recovered["state"], recovered["lease"]["generation"]) == (
        "pass",
        "taken_over",
        2,
    )
    assert [item.predicate for item in recorded] == [
        "lane-resolution:takeover",
        "lane-resolution:takeover",
    ]


@pytest.mark.parametrize(
    ("accepted_count", "actor", "request_updates", "gap"),
    [
        (0, TARGET, {}, "lease_takeover_authorization_unaccepted"),
        (1, SOURCE, {}, "lease_takeover_actor_mismatch"),
        (1, TARGET, {"generation": 2}, "lease_takeover_generation_drift"),
        (1, TARGET, {"source_holder_ref": TARGET}, "lease_takeover_generation_drift"),
    ],
)
def test_public_lease_takeover_rejects_unaccepted_or_drifted_coordinates(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    accepted_count: int,
    actor: str,
    request_updates: dict[str, object],
    gap: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    request = _takeover(acquired).model_copy(update=request_updates)
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.setattr(lease_lifecycle, "repository_root", lambda _root: root)
    monkeypatch.setattr(
        lease_lifecycle,
        "leases_by_branch",
        lambda _root: {"work/example": observe_lease(database, "work/example").record()},
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "read_attestation_set",
        lambda _root: ("repository", (request.authorization,) * accepted_count),
    )

    report = lease_lifecycle.execute_lease_takeover(root=root, request=request)

    assert report["verdict"] == "block"
    assert gap in report["required_gaps"]
    assert observe_lease(database, "work/example").record() == acquired

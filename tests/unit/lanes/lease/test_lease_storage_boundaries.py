"""Public Lease transition failures preserve the exact stored generation."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.mutation.lane_lifecycle.lease as lease_lifecycle
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_takeover
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.lifecycle.transitions import takeover_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.lifecycle_cases import strict_lease

SOURCE = "agent:test:case:source"
TARGET = "agent:test:case:target"


def _operation(lease: dict[str, object], operation: str = "renew", **updates: object):
    values = {
        "operation": operation,
        "branch": lease["lane_ref"],
        "holder_ref": lease["holder_ref"],
        "lease_id": lease["lease_id"],
        "expected_epoch": lease["epoch"],
        "expect_head": lease["expected_head"],
        "expected_expires_at": lease["expires_at"],
        "expected_payload_sha256": lease["payload_sha256"],
        "apply": True,
        **updates,
    }
    return LeaseOperationRequest.model_validate(values)


def _authorization(branch: str, digest: str, *, verdict: str = "pass") -> Attestation:
    now = datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "lane-resolution:takeover",
            "verifier": "maintainer:test:case:reviewer",
            "subject": f"git:branch:{branch}",
            "issued_at": now,
            "valid_from": now,
            "valid_until": None,
            "verdict": verdict,
            "payload": {
                "kind": "authorization:lane-takeover",
                "body": {"authorization": {"test": "storage-boundary"}},
            },
            "relations": (),
            "advisories": (),
            "commitment_digest": digest,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "evidence_refs": ("evidence:test:takeover",),
            "mints_authority": False,
        }
    )


def _takeover_request(lease: dict[str, object], *, apply: bool = True, **updates: object):
    values = {
        "branch": lease["lane_ref"],
        "source_holder_ref": lease["holder_ref"],
        "target_holder_ref": TARGET,
        "lease_id": lease["lease_id"],
        "expected_lane_incarnation_id": lease["lane_incarnation_id"],
        "expected_epoch": lease["epoch"],
        "expect_head": lease["expected_head"],
        "expected_tree": lease["expected_tree"],
        "expected_expires_at": lease["expires_at"],
        "expected_payload_sha256": lease["payload_sha256"],
        "expected_dirty_content_sha256": "e" * 64,
        "source_state": "source_lost",
        "authorization": _authorization(
            str(lease["lane_ref"]), str(lease["base_commitment_digest"])
        ),
        "apply": apply,
        **updates,
    }
    return LeaseTakeoverRequest.model_validate(values)


def test_acquire_and_transition_conflicts_leave_the_original_generation(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    current = strict_lease(holder=SOURCE)
    acquired = acquire_lease(database, lease=current)

    with pytest.raises(ValueError, match="lane_lease_conflict:work/example"):
        acquire_lease(database, lease=current)
    with pytest.raises(ValueError, match="lease_apply_required:takeover"):
        takeover_lease(
            database,
            request=_takeover_request(acquired, apply=False),
            observe_repository=lambda: ("a" * 40, "b" * 40, "e" * 64),
        )
    with pytest.raises(ValueError, match="lease_handoff_holder_not_quiesced"):
        apply_lease_operation(
            database,
            request=_operation(
                acquired,
                "handoff_accept",
                target_holder_ref=TARGET,
                offer_id="handoff-offer:absent",
            ),
        )
    assert observe_lease(database, "work/example").record() == acquired


@pytest.mark.parametrize("state", ["missing", "unknown"])
def test_storage_transition_rejects_missing_or_unknown_current_row(tmp_path, state: str) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    with closing(sqlite3.connect(database)) as connection, connection:
        if state == "missing":
            connection.execute("delete from leases where subject = ?", ("work/example",))
        else:
            connection.execute(
                "update leases set payload_json = ? where subject = ?",
                (json.dumps({}), "work/example"),
            )

    expected = "work_lane_missing_lease" if state == "missing" else "lease_unknown"
    with pytest.raises(ValueError, match=expected):
        apply_lease_operation(database, request=_operation(acquired))


@pytest.mark.parametrize(
    ("updates", "gap"),
    [
        ({"expected_lane_incarnation_id": "lane-incarnation:other"}, "incarnation_drift"),
        ({"expected_tree": "f" * 40}, "tree_drift"),
    ],
)
def test_takeover_storage_rechecks_generation_binding(tmp_path, updates, gap: str) -> None:
    database = tmp_path / "state.sqlite"
    acquired = acquire_lease(database, lease=strict_lease(holder=SOURCE))
    request = _takeover_request(acquired, **updates)

    with pytest.raises(ValueError, match=f"lease_takeover_{gap}"):
        takeover_lease(
            database,
            request=request,
            observe_repository=lambda: (
                request.expect_head,
                request.expected_tree,
                request.expected_dirty_content_sha256,
            ),
        )
    assert observe_lease(database, "work/example").record() == acquired


def test_public_operations_project_state_migration_and_storage_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(tmp_path, name="lease-boundary", holder_ref=SOURCE)
    database = state_database(fixture.worktree)
    current = observe_lease(database, "work/lease-boundary").record()
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    request = _operation(current)
    monkeypatch.setattr(
        lease_lifecycle,
        "local_state_mutation_guard",
        lambda _repo: {
            "required_gaps": ["local_state_migration_required"],
            "next_action": "migrate",
        },
    )

    blocked = execute_lease_operation(root=fixture.worktree, request=request)

    assert blocked["required_gaps"] == ["local_state_migration_required"]
    assert blocked["next_action"] == "migrate"

    monkeypatch.setattr(
        lease_lifecycle,
        "local_state_mutation_guard",
        lambda _repo: {"required_gaps": []},
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "apply_lease_operation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("locked")),
    )
    failed = execute_lease_operation(root=fixture.worktree, request=request)

    assert failed["verdict"] == "block"
    assert failed["required_gaps"] == ["locked"]


def test_public_operation_rejects_invalid_operation_and_holder_values(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(tmp_path, name="invalid-lease", holder_ref=SOURCE)
    current = observe_lease(state_database(fixture.worktree), "work/invalid-lease").record()
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)

    unknown = execute_lease_operation(
        root=fixture.worktree,
        request=_operation(current, "unsupported"),
    )
    invalid_holder = execute_lease_operation(
        root=fixture.worktree,
        request=_operation(current, holder_ref="invalid"),
    )

    assert unknown["required_gaps"] == ["lease_operation_unknown:unsupported"]
    assert any(gap == "holder_ref_invalid" for gap in invalid_holder["required_gaps"])


def test_resume_public_boundary_distinguishes_valid_and_expired_rows(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(tmp_path, name="resume-boundary", holder_ref=SOURCE)
    database = state_database(fixture.worktree)
    current = observe_lease(database, "work/resume-boundary").record()
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)

    not_expired = execute_lease_operation(
        root=fixture.worktree,
        request=_operation(current, "resume", contrary_decision=True),
    )
    assert {
        "lease_not_expired:work/resume-boundary",
        "lease_resume_blocked_by_decision",
    } <= set(not_expired["required_gaps"])

    expires_at = datetime.now(UTC) - timedelta(seconds=1)
    payload = dict(current["payload"])
    payload.update(expires_at=expires_at.isoformat())
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expires_at.isoformat(), json.dumps(payload, sort_keys=True), "work/resume-boundary"),
        )
    expired = observe_lease(database, "work/resume-boundary").record()
    renewed = execute_lease_operation(
        root=fixture.worktree,
        request=_operation(expired),
    )

    assert renewed["required_gaps"] == ["work_lane_lease_expired:work/resume-boundary"]


def test_public_takeover_projects_migration_and_transition_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(tmp_path, name="takeover-boundary", holder_ref=SOURCE)
    current = observe_lease(state_database(fixture.worktree), "work/takeover-boundary").record()
    request = _takeover_request(
        current,
        expected_dirty_content_sha256=lease_lifecycle.dirty_content_sha256(fixture.worktree),
    )
    authorization_payload = request.authorization.model_dump(mode="python", exclude={"id"})
    authorization_payload["payload"] = {
        "kind": "authorization:lane-takeover",
        "body": {
            "authorization": {
                "branch": request.branch,
                "head": request.expect_head,
                "tree": request.expected_tree,
                "dirty_content_sha256": request.expected_dirty_content_sha256,
                "lane_incarnation_id": request.expected_lane_incarnation_id,
                "lease_id": request.lease_id,
                "lease_epoch": request.expected_epoch,
                "lease_payload_sha256": request.expected_payload_sha256,
                "source_holder_ref": request.source_holder_ref,
                "target_holder_ref": request.target_holder_ref,
                "source_state": request.source_state,
            },
        },
    }
    authorization = Attestation.issue(authorization_payload)
    request = request.model_copy(update={"authorization": authorization})
    record_attestations(fixture.worktree, (authorization,))
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    monkeypatch.setattr(
        lease_lifecycle,
        "local_state_mutation_guard",
        lambda _repo: {
            "required_gaps": ["local_state_migration_required"],
            "next_action": "migrate",
        },
    )

    blocked = execute_lease_takeover(root=fixture.worktree, request=request)

    assert blocked["required_gaps"] == ["local_state_migration_required"]
    monkeypatch.setattr(
        lease_lifecycle,
        "local_state_mutation_guard",
        lambda _repo: {"required_gaps": []},
    )
    monkeypatch.setattr(
        lease_lifecycle,
        "takeover_lease",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("takeover rejected")),
    )
    failed = execute_lease_takeover(root=fixture.worktree, request=request)

    assert failed["verdict"] == "block"
    assert failed["required_gaps"] == ["takeover rejected"]

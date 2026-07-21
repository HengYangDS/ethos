from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
from tests.unit.lanes.retirement.test_unbound_and_helpers import _exceptional_fixture
from tests.unit.lanes.retirement.test_unbound_and_helpers import _owner_unavailable_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _rejects(pattern: str, call) -> None:
    with pytest.raises((TypeError, ValueError), match=pattern):
        call()


def test_observation_and_record_fail_closed_matrix(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    before = observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    assert before["chronicle"][observation.HAS_ACCEPTED_CHRONICLE] is True
    assert observation.chronicle_fields(b"\xff") == {}
    operation = records.operation_id(
        branch=branch,
        expect_head=head,
        accepted_head=str(before["accepted_head"]),
        protected_refs=before["protected_refs"],
        claim_id=str(before["claim_id"]),
        chronicle=observation.chronicle_binding(before),
        reason="record",
        observation_sha256=str(before["observation_sha256"]),
    )
    payload = records.attempt_payload(
        operation_id=operation,
        branch=branch,
        expect_head=head,
        reason="record",
        observation=before,
    )
    assert payload["lease_relinquish_binding"] == {
        "active": False,
        "lease_id": "",
        "holder_ref": "",
        "epoch": 0,
        "expected_head": "",
        "expires_at": "",
        "payload_sha256": "",
    }
    path = tmp_path / "record.json"
    assert records.write_record(path, payload, kind=records.ATTEMPT_KIND) == path.as_posix()
    assert records.write_record(path, payload, kind=records.ATTEMPT_KIND) == path.as_posix()
    path.write_text(json.dumps({**payload, "reason": "different"}), encoding="utf-8")
    _rejects(
        "unbound_retire_record_collision",
        lambda: records.write_record(path, payload, kind=records.ATTEMPT_KIND),
    )
    for invalid in (
        {},
        {**payload, "operation_id": "wrong"},
        {**payload, "branch": "topic"},
        {
            **payload,
            "lease_relinquish_binding": {
                **payload["lease_relinquish_binding"],
                "active": True,
                "lease_id": "",
            },
        },
    ):
        _rejects(
            "unbound_retire_record_invalid",
            lambda invalid=invalid: records.validate_record(invalid, kind=records.ATTEMPT_KIND),
        )

    assert (
        policy.lease_relinquish_gap(
            {
                observation.HAS_ACTIVE_LEASE: True,
                "active_lease": {
                    "holder_ref": "agent:test",
                    "lease_id": "",
                    "expected_head": head,
                },
                "head": head,
            },
            holder_ref="agent:test",
        )
        == "unbound_retire_active_lease"
    )
    assert not records.valid_lease_relinquish_binding([])
    assert not records.valid_lease_relinquish_binding(
        {
            "active": "bad",
            "lease_id": "lease:test",
            "holder_ref": "agent:test",
            "epoch": 1,
            "expected_head": head,
            "expires_at": "2099-01-01T00:00:00+00:00",
            "payload_sha256": "a" * 64,
        }
    )
    assert records.valid_lease_relinquishment(
        payload["lease_relinquish_binding"], {}, subject=branch
    )


def test_owner_unavailable_policy_requires_source_path_digest(tmp_path: Path) -> None:
    repo, branch, _head, chronicle, _lease, source_path = _owner_unavailable_fixture(tmp_path)
    observed = observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    observed["chronicle"]["source_worktree_path_sha256"] = hashlib.sha256(
        (source_path.as_posix() + "-mismatch").encode()
    ).hexdigest()

    assert policy.owner_unavailable_recovery_gaps(
        observed, recovery_actor="agent:test:recovery"
    ) == ["unbound_retire_owner_unavailable_source_path_mismatch"]


@pytest.mark.parametrize(
    ("recovery_actor", "expected_gap"),
    [
        ("", "unbound_retire_recovery_actor_required"),
        (
            "agent:test:session:missing-source-owner",
            "unbound_retire_owner_unavailable_holder_not_foreign",
        ),
    ],
)
def test_owner_unavailable_policy_requires_distinct_recovery_actor(
    tmp_path: Path, recovery_actor: str, expected_gap: str
) -> None:
    repo, branch, _head, chronicle, _lease, _source_path = _owner_unavailable_fixture(tmp_path)
    observed = observation.observe(repo, branch=branch, chronicle_ref=chronicle)

    assert policy.owner_unavailable_recovery_gaps(observed, recovery_actor=recovery_actor) == [
        expected_gap
    ]


def test_owner_unavailable_policy_rejects_invalid_source_path_contract(tmp_path: Path) -> None:
    repo, branch, _head, chronicle, _lease, _source_path = _owner_unavailable_fixture(tmp_path)
    observed = observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    observed["active_lease"]["recorded_path"] = "relative-source-worktree"

    assert policy.owner_unavailable_recovery_gaps(
        observed, recovery_actor="agent:test:recovery"
    ) == ["unbound_retire_owner_unavailable_source_path_invalid"]


def test_owner_unavailable_policy_requires_absent_source_path_declaration(tmp_path: Path) -> None:
    repo, branch, _head, chronicle, _lease, _source_path = _owner_unavailable_fixture(tmp_path)
    observed = observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    observed["chronicle"]["source_worktree_absent"] = "false"

    assert policy.owner_unavailable_recovery_gaps(
        observed, recovery_actor="agent:test:recovery"
    ) == ["unbound_retire_owner_unavailable_chronicle_missing"]


def test_owner_unavailable_policy_rejects_nonexact_lease_binding(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    observed = observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    observed[observation.HAS_ACTIVE_LEASE] = True
    observed["active_lease"] = {
        "lease_id": "lease:foreign",
        "holder_ref": "agent:test:foreign",
        "epoch": 1,
        "expected_head": head,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "payload_sha256": "a" * 64,
        "recorded_path": (tmp_path / "missing-worktree").as_posix(),
    }

    assert policy.owner_unavailable_recovery_gaps(
        observed, recovery_actor="agent:test:recovery"
    ) == ["unbound_retire_owner_unavailable_chronicle_missing"]

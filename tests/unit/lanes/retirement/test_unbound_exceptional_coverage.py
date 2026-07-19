from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
from tests.unit.lanes.retirement.test_unbound_and_helpers import _exceptional_fixture

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
    ):
        _rejects(
            "unbound_retire_record_invalid",
            lambda invalid=invalid: records.validate_record(invalid, kind=records.ATTEMPT_KIND),
        )

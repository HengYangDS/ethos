from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from ethos.adapters.repo.coordination import collaboration_competition_projection
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import RepositoryRelativePath
from tests.support.literal_cases import literal_case


def test_holder_ref_is_provider_neutral_and_carries_no_privilege() -> None:
    holder = HolderRef.parse("agent:codex:thread:019f46b5")

    assert holder.kind == "agent"
    assert holder.namespace == "codex"
    assert holder.instance_kind == "thread"
    assert holder.opaque_id == "019f46b5"
    assert holder.serialize() == "agent:codex:thread:019f46b5"
    assert holder.mints_authority is False


@pytest.mark.parametrize(
    "value",
    ["codex", "agent:codex", "agent:codex:thread", "agent::thread:id", " agent:x:y:z"],
)
def test_holder_ref_rejects_provider_only_or_ambiguous_values(value: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        HolderRef.parse(value)


@pytest.mark.parametrize(
    "value",
    TypeAdapter(list[str]).validate_python(
        literal_case(
            "kernel.test_coordination_contract:parametrize:test_repository_relative_path_accepts_canonical_posix_values:0"
        )
    ),
)
def test_repository_relative_path_accepts_canonical_posix_values(value: str) -> None:
    assert TypeAdapter(RepositoryRelativePath).validate_python(value) == value


@pytest.mark.parametrize(
    "value",
    ["", "/absolute", "1:a", "a//b", "a/./b", "a/../b", r"a\b", "a/", ".", ".."],
)
def test_repository_relative_path_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(RepositoryRelativePath).validate_python(value)


def test_lane_lease_binds_only_lane_holder_generation_and_expiry() -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC)
    lease = LaneLease(
        lane_ref="work/example",
        holder_ref=HolderRef.parse("agent:claude:session:abc"),
        generation=3,
        expires_at=now,
    )

    payload = lease.to_payload()

    assert payload == {
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "generation": 3,
        "expires_at": now.isoformat(),
    }
    assert LaneLease.from_payload(payload) == lease


def _lease_payload(**updates: object) -> dict[str, object]:
    now = datetime(2026, 7, 10, tzinfo=UTC).isoformat()
    return {
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "generation": 1,
        "expires_at": now,
    } | updates


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing-fields"),
        pytest.param({"generation": 0}, id="bad-generation"),
        pytest.param(
            {"generation": 1, "parallel_authority": "forbidden"},
            id="extra-authority-field",
        ),
    ],
)
def test_lane_lease_rejects_missing_malformed_or_legacy_wire_fields(
    payload: dict[str, object],
) -> None:
    candidate = _lease_payload(**payload)
    if not payload:
        candidate.pop("generation")

    with pytest.raises((ValueError, ValidationError)):
        LaneLease.from_payload(candidate)


def test_lane_lease_rejects_non_json_python_wire_values() -> None:
    with pytest.raises(TypeError, match="lane_lease_payload_type_invalid"):
        LaneLease.from_payload(_lease_payload(expires_at=datetime(2026, 7, 10, tzinfo=UTC)))


@pytest.mark.parametrize(
    ("scopes", "state", "reason"),
    [
        ([], "independent", "no_peer_work_lanes"),
        (["unknown", "overlap"], "await_facts", "peer_scope_unknown"),
        (["deferred"], "await_facts", "peer_scope_unknown"),
        (["overlap", "disjoint"], "collaborate", "overlapping_intents_require_coordination"),
        (["disjoint"], "independent", "peer_scopes_disjoint"),
    ],
)
@pytest.mark.parametrize(
    ("candidate", "backpressure"),
    [
        (None, "open"),
        ({"behind_accepted": 1}, "candidate_behind_accepted"),
        ({"latest_advance_age_seconds": 20, "latest_interval_seconds": 10}, "candidate_stalled"),
        ({"latest_advance_age_seconds": 10, "latest_interval_seconds": 10}, "open"),
        ({"latest_advance_age_seconds": 20, "latest_interval_seconds": 0}, "open"),
        ({"latest_advance_age_seconds": "unknown", "latest_interval_seconds": 10}, "open"),
        ({"latest_interval_seconds": 10}, "open"),
        (
            {"behind_accepted": 1, "latest_advance_age_seconds": 20, "latest_interval_seconds": 10},
            "candidate_behind_accepted",
        ),
    ],
)
def test_collaboration_competition_public_state_matrix(
    scopes, candidate, state, reason, backpressure
):
    branches = [f"work/peer-{index}" for index in range(len(scopes))]
    lanes = [
        {
            "branch": branch,
            "coordination_state": scope,
            "lease": LaneLease.from_payload(_lease_payload(lane_ref=branch)).to_payload(),
        }
        for branch, scope in zip(branches, scopes, strict=True)
    ]
    result = collaboration_competition_projection(lanes, candidate=candidate)
    assert result == {
        "state": state,
        "reason": reason,
        "peer_count": len(lanes),
        "overlap_count": scopes.count("overlap"),
        "unknown_count": scopes.count("unknown") + scopes.count("deferred"),
        "branches": branches,
        "backpressure": backpressure,
        "candidate_progress": candidate or {},
    }

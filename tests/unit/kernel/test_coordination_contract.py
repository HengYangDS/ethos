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
    literal_case(
        "kernel.test_coordination_contract:parametrize:test_repository_relative_path_accepts_canonical_posix_values:0"
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


def test_lane_lease_binds_local_incarnation_holder_generation_and_head() -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC)
    lease = LaneLease(
        lane_incarnation_id="lane-incarnation:01",
        lease_id="lease:01",
        lane_ref="work/example",
        holder_ref=HolderRef.parse("agent:claude:session:abc"),
        epoch=3,
        issued_at=now,
        renewed_at=now,
        expires_at=now,
        expected_head="a" * 40,
        expected_tree="c" * 40,
        base_commitment_path="openspec/changes/example/commitment.toml",
        base_commitment_bytes_sha256="d" * 64,
        base_commitment_digest="b" * 64,
        path_scope=("packages/example.py",),
    )

    payload = lease.to_payload()

    assert payload == {
        "lane_incarnation_id": "lane-incarnation:01",
        "lease_id": "lease:01",
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "epoch": 3,
        "issued_at": now.isoformat(),
        "renewed_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "expected_head": "a" * 40,
        "expected_tree": "c" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "d" * 64,
        "base_commitment_digest": "b" * 64,
        "path_scope": ["packages/example.py"],
        "handoff": None,
    }
    assert LaneLease.from_payload(payload) == lease


def _lease_payload(**updates: object) -> dict[str, object]:
    now = datetime(2026, 7, 10, tzinfo=UTC).isoformat()
    return {
        "lane_incarnation_id": "lane-incarnation:01",
        "lease_id": "lease:01",
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "epoch": 1,
        "issued_at": now,
        "renewed_at": now,
        "expires_at": now,
        "expected_head": "a" * 40,
        "expected_tree": "c" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "d" * 64,
        "base_commitment_digest": "b" * 64,
        "path_scope": [],
        "handoff": None,
    } | updates


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing-base-digest"),
        pytest.param({"base_commitment_digest": "not-a-digest"}, id="bad-base-digest"),
        pytest.param(
            {"base_commitment_digest": "b" * 64, "claim_id": "retired"},
            id="retired-claim-field",
        ),
        pytest.param(
            {"base_commitment_digest": "b" * 64, "path": "/tmp/worktree"},
            id="redundant-worktree-path",
        ),
    ],
)
def test_lane_lease_rejects_missing_malformed_or_legacy_wire_fields(
    payload: dict[str, object],
) -> None:
    candidate = _lease_payload(**payload)
    if not payload:
        candidate.pop("base_commitment_digest")

    with pytest.raises((ValueError, ValidationError)):
        LaneLease.from_payload(candidate)


def test_lane_lease_rejects_non_json_python_wire_values() -> None:
    with pytest.raises(TypeError, match="lane_lease_payload_type_invalid"):
        LaneLease.from_payload(_lease_payload(path_scope=("src/**",)))


@pytest.mark.parametrize(
    ("lanes", "risks", "capacity", "candidate", "state", "reason"),
    [
        ([], (), 3, {}, "independent", "no_peer_work_lanes"),
        (
            [{"branch": "work/unknown", "coordination_state": "unknown"}],
            (),
            3,
            {},
            "await_facts",
            "peer_scope_unknown",
        ),
        (
            [{"branch": "work/conflict", "coordination_state": "overlap"}],
            (),
            3,
            {},
            "collaborate",
            "overlapping_intents_require_coordination",
        ),
        (
            [{"branch": "work/disjoint", "coordination_state": "disjoint"}],
            (),
            3,
            {},
            "independent",
            "peer_scopes_disjoint",
        ),
        (
            [
                {
                    "branch": "work/same",
                    "coordination_state": "overlap",
                    "base_commitment_digest": "digest",
                    "proof_cost": 1,
                }
            ],
            (),
            3,
            {},
            "collaborate",
            "competition_has_no_declared_risk_basis",
        ),
        (
            [
                {
                    "branch": "work/same",
                    "coordination_state": "overlap",
                    "base_commitment_digest": "digest",
                }
            ],
            ("collision",),
            None,
            {},
            "await_facts",
            "proof_capacity_or_cost_missing",
        ),
        (
            [
                {
                    "branch": "work/same",
                    "coordination_state": "overlap",
                    "base_commitment_digest": "digest",
                    "proof_cost": 3,
                }
            ],
            ("collision",),
            3,
            {"behind_accepted": 1},
            "collaborate",
            "proof_capacity_below_alternative_cost",
        ),
        (
            [
                {
                    "branch": "work/same",
                    "coordination_state": "overlap",
                    "base_commitment_digest": "digest",
                    "proof_cost": 1,
                    "lease": {"issued_at": "2026-07-09T00:00:00+00:00"},
                }
            ],
            ("collision",),
            3,
            {"latest_advance_age_seconds": 20, "latest_interval_seconds": 10},
            "compete",
            "alternative_realizations_admitted",
        ),
    ],
)
def test_collaboration_competition_public_state_matrix(
    lanes: list[dict[str, object]],
    risks: tuple[str, ...],
    capacity: int | None,
    candidate: dict[str, object],
    state: str,
    reason: str,
) -> None:
    result = collaboration_competition_projection(
        lanes,
        commitment_digest="digest",
        risks=risks,
        proof_cost=1,
        proof_capacity=capacity,
        observed_at=datetime(2026, 7, 10, tzinfo=UTC),
        candidate=candidate,
    )

    assert (result["state"], result["reason"]) == (state, reason)
    if candidate.get("behind_accepted"):
        assert result["backpressure"] == "candidate_behind_accepted"
    elif candidate:
        assert result["backpressure"] == "candidate_stalled"

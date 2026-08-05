from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from itertools import product
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from pydantic import ValidationError

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import RepositoryRelativePath


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
    [
        "openspec/changes/example/commitment.toml",
        "src/main.py",
        ".github/workflows/check.yml",
        "a/.hidden/file",
        "a/b:c",
    ],
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


def test_repository_relative_path_pattern_is_the_schema_ssot() -> None:
    pattern = TypeAdapter(RepositoryRelativePath).json_schema()["pattern"]
    schemas = Path("system/schemas/kernel")
    lane = json.loads((schemas / "lane-lease.schema.json").read_text(encoding="utf-8"))
    package = json.loads((schemas / "handoff-package.schema.json").read_text(encoding="utf-8"))
    acknowledgement = json.loads(
        (schemas / "handoff-acknowledgement.schema.json").read_text(encoding="utf-8")
    )
    workspace = json.loads((schemas / "workspace-status.schema.json").read_text(encoding="utf-8"))
    projected = [
        lane["properties"]["base_commitment_path"]["pattern"],
        package["properties"]["base_commitment_path"]["pattern"],
        package["properties"]["artifacts"]["items"]["properties"]["path"]["pattern"],
        acknowledgement["properties"]["destination_lease_base_commitment_path"]["pattern"],
        workspace["$defs"]["closeoutSupport"]["properties"]["lease_base_commitment_path"][
            "pattern"
        ],
        workspace["$defs"]["leaseSummary"]["properties"]["base_commitment_path"]["pattern"],
        workspace["$defs"]["unboundWorkLaneRef"]["properties"]["base_commitment_path"]["pattern"],
    ]
    assert projected == [pattern] * len(projected)
    source_binding = package["properties"]["source_lease_binding"]
    assert "lane_incarnation_id" in source_binding["required"]
    for projection in (
        workspace["$defs"]["leaseSummary"],
        workspace["$defs"]["unboundWorkLaneRef"],
    ):
        assert {"issued_at", "renewed_at", "path_scope"} <= set(projection["required"])


def test_lane_lease_binds_local_incarnation_holder_generation_and_head(tmp_path: Path) -> None:
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
    assert set(payload) == {
        "lane_incarnation_id",
        "lease_id",
        "lane_ref",
        "holder_ref",
        "epoch",
        "issued_at",
        "renewed_at",
        "expires_at",
        "expected_head",
        "expected_tree",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
        "base_commitment_digest",
        "path_scope",
        "handoff",
    }
    assert payload["holder_ref"] == "agent:claude:session:abc"
    assert payload["epoch"] == 3
    assert payload["expected_head"] == "a" * 40
    assert payload["expected_tree"] == "c" * 40
    assert payload["base_commitment_path"] == "openspec/changes/example/commitment.toml"
    assert payload["base_commitment_bytes_sha256"] == "d" * 64
    assert payload["base_commitment_digest"] == "b" * 64
    assert payload["handoff"] is None
    assert LaneLease.from_payload(payload) == lease
    database = tmp_path / "state.sqlite"
    acquire_lease(database, lease=lease)
    with closing(sqlite3.connect(database)) as connection:
        persisted = connection.execute("select payload_json from leases").fetchone()[0]
    assert persisted == json.dumps(payload, sort_keys=True)


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
    now = datetime(2026, 7, 10, tzinfo=UTC)
    candidate = {
        "lane_incarnation_id": "lane-incarnation:01",
        "lease_id": "lease:01",
        "lane_ref": "work/example",
        "holder_ref": "agent:claude:session:abc",
        "epoch": 1,
        "issued_at": now.isoformat(),
        "renewed_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "expected_head": "a" * 40,
        "expected_tree": "c" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "d" * 64,
        "path_scope": [],
        "handoff": None,
        **payload,
    }

    with pytest.raises((ValueError, ValidationError)):
        LaneLease.from_payload(candidate)


def test_lane_lease_rejects_non_json_python_wire_values() -> None:
    now = datetime(2026, 7, 10, tzinfo=UTC).isoformat()
    payload = {
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
        "path_scope": ("src/**",),
        "handoff": None,
    }

    with pytest.raises(TypeError, match="lane_lease_payload_type_invalid"):
        LaneLease.from_payload(payload)


def test_takeover_bounded_model_requires_every_exact_authorization_coordinate() -> None:
    """Exhaust the abstract takeover guard; task 4.4 owns its concrete effect."""

    def transition(
        state: tuple[str, int, str, str],
        *,
        exact: tuple[bool, ...],
        source_state: str,
    ) -> tuple[str, int, str, str]:
        holder, epoch, head, dirty_digest = state
        admitted = all(exact) and source_state in {"quiesced", "source_lost"}
        return (
            ("agent:test:case:target", epoch + 1, head, dirty_digest)
            if admitted
            else (holder, epoch, head, dirty_digest)
        )

    initial = ("agent:test:case:source", 7, "a" * 40, "b" * 64)
    for exact, source_state in product(
        product((False, True), repeat=6),
        ("active", "quiesced", "source_lost"),
    ):
        observed = transition(initial, exact=exact, source_state=source_state)
        admitted = all(exact) and source_state in {"quiesced", "source_lost"}
        if admitted:
            assert observed == ("agent:test:case:target", 8, "a" * 40, "b" * 64)
        else:
            assert observed == initial


def test_shared_inbox_deduplicates_rebuilds_and_preserves_conflicts() -> None:
    from ethos.adapters.repo.coordination import shared_inbox_projection

    item = {
        "kind": "gap",
        "subject": "work/example",
        "claim": "lease_holder_unknown",
        "source_refs": ["lease:example"],
        "next_action": "obtain accepted takeover authorization",
    }
    duplicate = {**item, "source_refs": ["lease:example", "lease:example"]}

    rebuilt = shared_inbox_projection([item, duplicate], attestations=())
    repeated = shared_inbox_projection([duplicate, item], attestations=())

    assert rebuilt == repeated
    assert rebuilt["state"] == "open"
    assert rebuilt["item_count"] == 1
    assert rebuilt["items"][0]["acknowledged_by"] == []
    assert rebuilt["items"][0]["consumed_by"] == []

    conflict = shared_inbox_projection(
        [item, {**item, "next_action": "preserve lane"}], attestations=()
    )
    assert conflict["state"] == "conflict"
    assert conflict["item_count"] == 1
    assert conflict["items"][0]["conflict"] is True


def test_shared_inbox_acknowledgement_does_not_consume_and_effect_does() -> None:
    from datetime import UTC
    from datetime import datetime

    from ethos.adapters.repo.coordination import shared_inbox_projection
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import canonical_json_digest

    item = {
        "kind": "handoff",
        "subject": "work/example",
        "claim": "successor_ready",
        "source_refs": ["handoff:example"],
        "next_action": "accept exact result",
    }
    digest = canonical_json_digest({key: item[key] for key in ("kind", "subject", "claim")})
    issued = datetime.now(UTC)
    acknowledgement = Attestation.issue(
        {
            "predicate": "inbox:acknowledged",
            "verifier": "agent:test:case:reader",
            "subject": f"inbox:item:{digest}",
            "issued_at": issued,
            "verdict": "pass",
            "evidence_refs": (f"inbox:item:{digest}",),
            "statement": {"actor": "agent:test:case:reader", "item_digest": digest},
        }
    )
    consumed = Attestation.issue(
        {
            "predicate": "inbox:consumed",
            "verifier": "agent:test:case:owner",
            "subject": f"inbox:item:{digest}",
            "issued_at": issued,
            "verdict": "pass",
            "effect_digest": "e" * 64,
            "statement": {
                "actor": "agent:test:case:owner",
                "item_digest": digest,
                "accepted_result": "git:commit:" + "a" * 40,
            },
        }
    )

    acknowledged = shared_inbox_projection([item], attestations=(acknowledgement,))
    assert acknowledged["items"][0]["acknowledged_by"] == ["agent:test:case:reader"]
    assert acknowledged["items"][0]["consumed_by"] == []

    completed = shared_inbox_projection([item], attestations=(acknowledgement, consumed))
    assert completed["state"] == "consumed"
    assert completed["items"][0]["consumed_by"] == ["agent:test:case:owner"]

    uneffected = consumed.model_copy(update={"effect_digest": ""})
    unbound = shared_inbox_projection([item], attestations=(uneffected,))
    assert unbound["state"] == "open"
    assert unbound["items"][0]["consumed_by"] == []


def test_python_reference_parser_never_emits_invalid_escape_warnings() -> None:
    import warnings

    from ethos.repository.policy.references.python_syntax import python_trees

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        python_trees('pattern = "[^\\s]+"')

    assert captured == []

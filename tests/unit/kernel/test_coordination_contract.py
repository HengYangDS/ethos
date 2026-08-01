from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
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

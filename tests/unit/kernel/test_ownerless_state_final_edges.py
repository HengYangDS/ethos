from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.store.state import closeout
from ethos.adapters.store.state import schema

if TYPE_CHECKING:
    from pathlib import Path


def _fence_kwargs() -> dict[str, str]:
    return {
        "subject": "work/20260722-state-final",
        "expected_head": "a" * 40,
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000302",
        "executor_ref": "agent:codex:thread:state-final",
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "target_path": "/tmp/20260722-state-final",
        "lane_incarnation_id": "lane-incarnation:20260722-state-final",
        "observation_digest": "c" * 64,
        "decision_sha256": "d" * 64,
        "chronicle_digest": "e" * 64,
    }


def _replace_fence_payload(
    db_path: Path,
    *,
    fence: dict[str, object],
    payload: dict[str, object],
) -> None:
    binding = {
        field: fence[field]
        for field in (
            "subject",
            "expected_head",
            "decision_id",
            "executor_ref",
            "accepted_branch",
            "accepted_head",
        )
    }
    binding["payload"] = payload
    canonical_binding = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    target_binding_digest = hashlib.sha256(canonical_binding.encode()).hexdigest()
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(
            """update closeout_fences
            set target_binding_digest = ?, payload_json = ? where subject = ?""",
            (
                target_binding_digest,
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False),
                _fence_kwargs()["subject"],
            ),
        )


def test_closeout_fence_rejects_same_decision_with_changed_binding(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    changed = _fence_kwargs()
    changed["accepted_head"] = "1" * 40

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_mismatch"):
        closeout.acquire_closeout_fence(db_path, **changed)


def test_closeout_fence_probe_rejects_a_database_without_current_schema(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "plain.sqlite"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("create table unrelated(value text)")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_probe_maps_corrupt_database_to_unverifiable(tmp_path: Path) -> None:
    db_path = tmp_path / "corrupt.sqlite"
    db_path.write_bytes(b"not-a-sqlite-database")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_probe_maps_malformed_schema_to_unverifiable(tmp_path: Path) -> None:
    db_path = tmp_path / "malformed.sqlite"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("create table closeout_fences(subject text not null)")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_rejects_provider_field_with_rebound_digest(tmp_path: Path) -> None:
    db_path = tmp_path / "provider-field.sqlite"
    fence = closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    payload = dict(fence["payload"])
    payload["provider_binding_digest"] = "f" * 64
    _replace_fence_payload(db_path, fence=fence, payload=payload)

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid"):
        closeout.acquire_closeout_fence(db_path, **_fence_kwargs())


@pytest.mark.parametrize("provider_field", ["wcp_binding_digest", "provider_binding_digest"])
def test_closeout_fence_probe_maps_provider_prefixed_payload_to_unverifiable(
    tmp_path: Path,
    provider_field: str,
) -> None:
    db_path = tmp_path / f"{provider_field}.sqlite"
    fence = closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    payload = dict(fence["payload"])
    payload[provider_field] = "f" * 64
    _replace_fence_payload(db_path, fence=fence, payload=payload)

    assert closeout.probe_closeout_fence(db_path, subject=_fence_kwargs()["subject"]) == (
        "unverifiable",
        None,
    )


@pytest.mark.parametrize(
    ("case", "expected_gap"),
    [
        ("table", "state_schema_closeout_fence_table_definition_mismatch"),
        ("index", "state_schema_closeout_fence_subject_unique_missing"),
        ("trigger", "state_schema_closeout_fence_trigger_present"),
    ],
)
def test_closeout_fence_schema_rejects_noncanonical_objects(
    case: str,
    expected_gap: str,
) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        if case == "table":
            connection.execute("create table closeout_fences(subject text not null)")
        else:
            connection.execute(schema.CLOSEOUT_FENCE_SCHEMA[0])
            if case == "trigger":
                connection.execute(schema.CLOSEOUT_FENCE_SCHEMA[1])
                connection.execute(
                    "create trigger closeout_fences_extra after insert on closeout_fences "
                    "begin select 1; end"
                )

        with pytest.raises(RuntimeError, match=expected_gap):
            schema.validate_current_closeout_fence_schema(connection)


def test_closeout_fence_schema_initialization_requires_a_writer_transaction() -> None:
    with (
        closing(sqlite3.connect(":memory:")) as connection,
        pytest.raises(RuntimeError, match="state_schema_transaction_required"),
    ):
        schema.initialize_closeout_fence_connection(connection)

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.lease as lease_lifecycle
import ethos.adapters.store.state.lease.lifecycle.transitions as transitions
import ethos.adapters.store.state.lease.projection as projection
import ethos.surface.cli.lane.lease as lease_cli
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.lifecycle_cases import strict_lease

if TYPE_CHECKING:
    from pathlib import Path

HOLDER = "agent:test:case:owner"
TARGET = "agent:test:case:target"


def _request(
    lease: dict[str, object],
    operation: str,
    *,
    apply: bool = True,
    **updates: object,
) -> LeaseOperationRequest:
    values: dict[str, object] = {
        "operation": operation,
        "branch": lease["lane_ref"],
        "holder_ref": lease["holder_ref"],
        "lease_id": lease["lease_id"],
        "expected_epoch": lease["epoch"],
        "expect_head": lease["expected_head"],
        "expected_expires_at": lease["expires_at"],
        "expected_payload_sha256": lease["payload_sha256"],
        "apply": apply,
        **updates,
    }
    return LeaseOperationRequest.model_validate(values)


def _expire_lease(database: Path, branch: str) -> dict[str, object]:
    observed = projection.observe_lease(database, branch).record()
    payload = dict(observed["payload"])
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    payload.update(
        issued_at=(expired_at - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired_at - timedelta(seconds=1)).isoformat(),
        expires_at=expired_at.isoformat(),
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired_at.isoformat(), json.dumps(payload, sort_keys=True), branch),
        )
    return projection.observe_lease(database, branch).record()


def test_resume_public_command_requires_expired_generation_and_preserves_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(tmp_path / "resume-cli", name="resume-cli", holder_ref=HOLDER)
    database = state_database(fixture.worktree)
    branch = "work/resume-cli"
    expired = _expire_lease(database, branch)
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)

    payload = run_ethos(
        "lane",
        "lease",
        "resume",
        "--root",
        fixture.worktree.as_posix(),
        "--branch",
        branch,
        "--holder-ref",
        HOLDER,
        "--lease-id",
        str(expired["lease_id"]),
        "--epoch",
        str(expired["epoch"]),
        "--expect-head",
        str(expired["expected_head"]),
        "--expires-at",
        str(expired["expires_at"]),
        "--payload-sha256",
        str(expired["payload_sha256"]),
        "--ttl-seconds",
        "120",
        "--apply",
        "--json",
        cwd=fixture.worktree,
    )

    resumed = payload["data"]["lease"]
    assert (payload["verdict"], payload["state"]) == ("pass", "resumed")
    assert payload["summary"] == {
        "branch": branch,
        "lease_id": expired["lease_id"],
        "epoch": expired["epoch"],
        "holder_ref": HOLDER,
    }
    assert resumed["payload_sha256"] != expired["payload_sha256"]
    assert resumed["lane_incarnation_id"] == expired["lane_incarnation_id"]


def test_resume_public_command_blocks_contrary_decision_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = start_adopted_work_lane(
        tmp_path / "resume-block", name="resume-block", holder_ref=HOLDER
    )
    database = state_database(fixture.worktree)
    branch = "work/resume-block"
    expired = _expire_lease(database, branch)
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)

    payload = run_ethos_blocked(
        "lane",
        "lease",
        "resume",
        "--root",
        fixture.worktree.as_posix(),
        "--branch",
        branch,
        "--holder-ref",
        HOLDER,
        "--lease-id",
        str(expired["lease_id"]),
        "--epoch",
        str(expired["epoch"]),
        "--expect-head",
        str(expired["expected_head"]),
        "--expires-at",
        str(expired["expires_at"]),
        "--payload-sha256",
        str(expired["payload_sha256"]),
        "--contrary-decision-present",
        "--apply",
        "--json",
        cwd=fixture.worktree,
    )

    assert payload["required_gaps"] == ["lease_resume_blocked_by_decision"]
    assert projection.observe_lease(database, branch).record() == expired


def test_takeover_storage_rechecks_incarnation_tree_and_repository_after_cas(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    stored = transitions.acquire_lease(
        database,
        lease=strict_lease(branch="work/takeover", holder=HOLDER),
    )
    expected_repository = (
        str(stored["expected_head"]),
        str(stored["expected_tree"]),
        "e" * 64,
    )
    request = lease_lifecycle.LeaseTakeoverRequest.model_validate(
        {
            "branch": stored["lane_ref"],
            "source_holder_ref": HOLDER,
            "target_holder_ref": TARGET,
            "lease_id": stored["lease_id"],
            "expected_lane_incarnation_id": stored["lane_incarnation_id"],
            "expected_epoch": stored["epoch"],
            "expect_head": stored["expected_head"],
            "expected_tree": stored["expected_tree"],
            "expected_expires_at": stored["expires_at"],
            "expected_payload_sha256": stored["payload_sha256"],
            "expected_dirty_content_sha256": expected_repository[2],
            "source_state": "source_lost",
            "authorization": Attestation.issue(
                {
                    "subject": "git:branch:work/takeover",
                    "predicate": "lane-resolution:takeover",
                    "verdict": "pass",
                    "statement": {"authorization": {}},
                    "issued_at": datetime.now(UTC),
                    "valid_from": datetime.now(UTC),
                    "verifier": "maintainer:test:case:reviewer",
                    "evidence_refs": ("evidence:test:takeover",),
                    "commitment_digest": "d" * 64,
                }
            ),
            "apply": True,
        }
    )
    snapshots = iter((expected_repository, ("0" * 40, *expected_repository[1:])))

    with pytest.raises(ValueError, match="lease_takeover_repository_drift"):
        transitions.takeover_lease(
            database, request=request, observe_repository=lambda: next(snapshots)
        )
    assert projection.observe_lease(database, "work/takeover").record() == stored

    for field, value, gap in (
        (
            "expected_lane_incarnation_id",
            "lane-incarnation:stale",
            "lease_takeover_incarnation_drift",
        ),
        ("expected_tree", "0" * 40, "lease_takeover_tree_drift"),
    ):
        stale = request.model_copy(update={field: value})
        observed = (
            stale.expect_head,
            stale.expected_tree,
            stale.expected_dirty_content_sha256,
        )
        with pytest.raises(ValueError, match=gap):
            transitions.takeover_lease(
                database,
                request=stale,
                observe_repository=lambda observed=observed: observed,
            )
        assert projection.observe_lease(database, "work/takeover").record() == stored


def test_projection_retains_unknown_row_diagnostics_and_filters_active_leases(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    now = datetime.now(UTC)
    valid = strict_lease(branch="work/valid", expires_at=now + timedelta(hours=1))
    expired = strict_lease(
        branch="work/expired",
        lease_id="lease:expired",
        lane_incarnation_id="lane-incarnation:expired",
        expires_at=now - timedelta(seconds=1),
        renewed_at=now - timedelta(seconds=2),
        issued_at=now - timedelta(seconds=3),
    )
    transitions.acquire_lease(database, lease=valid)
    transitions.acquire_lease(database, lease=expired)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            ("lease:unknown", "work/unknown", HOLDER, now.isoformat(), "[]"),
        )

    observations = projection.lease_observations(database, observed_at=now)
    records = {item.subject: item.record() for item in observations}

    assert [item["subject"] for item in projection.active_leases(database)] == ["work/valid"]
    assert records["work/expired"]["lease_state"] == "expired"
    assert records["work/unknown"]["lease_state"] == "unknown"
    assert records["work/unknown"]["error"] == "lane_lease_payload_not_object"
    with pytest.raises(ValueError, match="lease_unknown:work/unknown"):
        projection.lease_record(
            (
                "lease:unknown",
                "work/unknown",
                HOLDER,
                now.isoformat(),
                "[]",
            )
        )


def test_projection_missing_and_invalid_schema_are_observable_as_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sqlite"
    assert projection.lease_observations(missing) == []
    assert projection.observe_lease(missing, "work/missing").record() == {
        "subject": "work/missing",
        "lease_state": "missing",
    }

    invalid = tmp_path / "invalid.sqlite"
    with closing(sqlite3.connect(invalid)) as connection, connection:
        connection.execute("create table unrelated(value text)")
    assert projection.lease_rows(invalid) == []
    assert projection.observe_lease(invalid, "work/missing").state == "missing"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, 0), (3, 3), ("4", 4), ("bad", 0), (None, 0)],
)
def test_projection_integer_value_fails_closed(value: object, expected: int) -> None:
    assert projection.integer_value(value) == expected


def test_cli_result_projection_prefers_lease_then_offer_and_preserves_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[tuple[object, bool]] = []
    monkeypatch.setattr(
        lease_cli, "emit", lambda result, json_output: emitted.append((result, json_output))
    )

    lease_cli.emit_lease_result(
        "lane lease resume",
        {
            "verdict": "pass",
            "state": "resumed",
            "branch": "work/example",
            "lease": {"lease_id": "lease:one", "epoch": 2, "holder_ref": HOLDER},
            "handoff_offer": {"lease_id": "lease:offer", "epoch": 1, "holder_ref": HOLDER},
            "diagnostics": [{"code": "observed"}, "discard"],
            "required_gaps": [],
        },
        json_output=True,
    )
    result, json_output = emitted.pop()
    assert json_output is True
    assert result.summary == {
        "branch": "work/example",
        "lease_id": "lease:one",
        "epoch": 2,
        "holder_ref": HOLDER,
    }
    assert result.diagnostics == ({"code": "observed"},)
    assert result.next_action == "ethos lane status --json"

    lease_cli.emit_lease_result(
        "lane lease handoff",
        {
            "verdict": "block",
            "state": "blocked",
            "branch": "work/example",
            "lease": {},
            "handoff_offer": {"lease_id": "lease:offer", "epoch": 1, "holder_ref": HOLDER},
            "required_gaps": ["lease_unknown"],
        },
        json_output=False,
    )
    result, _json_output = emitted.pop()
    assert result.summary["lease_id"] == "lease:offer"
    assert result.required_gaps == ("lease_unknown",)
    assert result.next_action == ""

"""Minimal exact-CAS coverage for the four-field Lane Lease relation."""

from __future__ import annotations

import shlex
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.mutation.lane_lifecycle.lease.acquisition as lease_acquisition
import ethos.adapters.mutation.lane_lifecycle.lease.operation as lease_operation
import ethos.adapters.mutation.lane_lifecycle.lease.takeover as lease_takeover
import ethos.adapters.store.state.lease.lifecycle.transitions as lease_storage
import ethos.adapters.store.state.lease.projection as lease_projection
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.lifecycle_cases import strict_lease
from tests.support.semantic import attestation_fixture

SOURCE = "agent:test:case:source"
TARGET = "agent:test:case:target"


def _unleased_dirty_lane(tmp_path):
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "retained-work"
    git(repo, "worktree", "add", "-b", "work/retained", str(target), "dev")
    (target / "README.md").write_text("staged\n")
    git(target, "add", "README.md")
    (target / "README.md").write_text("unstaged\n")
    (target / "untracked.txt").write_bytes(b"retained\x00bytes")
    return repo, target


def _reacquire(root, target, **options):
    return lease_acquisition.reacquire_lease(root=root, path=target, holder_ref=TARGET, **options)


def _reacquire_arguments(planned):
    return {
        "expect_head": planned["head"],
        "expect_snapshot": planned["snapshot"],
        "expires_at": planned["expires_at"],
        "authorize": True,
        "apply": True,
    }


@pytest.mark.parametrize("stale_policy", [False, True])
def test_reacquire_missing_lease_preserves_index_and_dirty_content(
    tmp_path, monkeypatch, stale_policy
):
    repo, target = _unleased_dirty_lane(tmp_path)
    if stale_policy:
        (target / ".ethos/workspace.toml").write_text('[branch_roles]\naccepted_branch="lost"\n')
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    before = (git(target, "rev-parse", "HEAD"), git(target, "diff", "--cached"))

    planned = run_ethos(
        "lane",
        "lease",
        "reacquire",
        "--path",
        str(target),
        "--holder-ref",
        TARGET,
        "--root",
        str(target),
        "--json",
        cwd=repo,
    )
    assert planned["verdict"] == "pass"
    assert lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
    arguments = shlex.split(planned["next_action"])
    assert arguments[:4] == ["ethos", "lane", "lease", "reacquire"]
    assert "--expect-snapshot" in arguments
    applied = run_ethos(*arguments[1:], cwd=repo)["data"]
    repeated = run_ethos(*arguments[1:], cwd=repo)["data"]
    assert applied["verdict"] == repeated["verdict"] == "pass"
    assert applied["state"] == "acquired"
    assert repeated["state"] == "recognized"
    assert applied["lease"] == repeated["lease"]
    assert applied["attestation"] == repeated["attestation"]
    assert applied["lease"]["holder_ref"] == TARGET
    assert applied["lease"]["generation"] == 1
    assert applied["attestation"]["commitment_digest"] is None
    assert (git(target, "rev-parse", "HEAD"), git(target, "diff", "--cached")) == before
    assert git(target, "show", ":README.md") == "staged"
    assert (target / "README.md").read_text() == "unstaged\n"
    assert (target / "untracked.txt").read_bytes() == b"retained\x00bytes"


@pytest.mark.parametrize(
    "drift",
    [
        "head",
        "index",
        "working",
        "untracked",
        "lease",
        "same-holder",
        "renewed",
        "lock",
        "actor",
        "expired",
        "protected",
        "foreign",
    ],
)
def test_reacquire_rejects_exact_snapshot_or_ownership_drift(tmp_path, monkeypatch, drift):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    arguments = _reacquire_arguments(_reacquire(repo, target))
    if drift == "head":
        git(target, "commit", "-m", "advance retained source")
    elif drift == "index":
        git(target, "reset", "HEAD", "README.md")
    elif drift in {"working", "untracked"}:
        (target / ("README.md" if drift == "working" else "untracked.txt")).write_text("changed\n")
    elif drift in {"lease", "expired", "same-holder", "renewed"}:
        lease_storage.acquire_lease(
            state_database(repo),
            lease=strict_lease(
                branch="work/retained",
                holder=TARGET if drift in {"same-holder", "renewed"} else SOURCE,
                generation=2 if drift == "renewed" else 1,
                expires_at=(
                    datetime.fromisoformat(arguments["expires_at"])
                    if drift == "renewed"
                    else datetime.now(UTC) + timedelta(days=-1 if drift == "expired" else 1)
                ),
            ),
        )
    elif drift == "lock":
        git(repo, "worktree", "lock", str(target))
    elif drift == "actor":
        monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    elif drift == "protected":
        target = repo
    else:
        target, _candidate = init_repo_with_candidate(tmp_path / "foreign")
    result = _reacquire(repo, target, **arguments)
    assert result["verdict"] == "block", result
    observed = lease_projection.observe_lease(state_database(repo), "work/retained")
    assert observed.state == {
        "lease": "valid",
        "same-holder": "valid",
        "renewed": "valid",
        "expired": "expired",
    }.get(drift, "missing")
    if drift in {"lease", "expired"}:
        assert observed.record()["holder_ref"] == SOURCE


def test_reacquire_rejects_invalid_request_and_unreadable_state(tmp_path, monkeypatch):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    arguments = _reacquire_arguments(_reacquire(repo, target))
    for invalid in (
        {"authorize": False},
        {"expires_at": ""},
        {"expires_at": "2020-01-01T00:00:00Z"},
    ):
        assert _reacquire(repo, target, **(arguments | invalid))["verdict"] == "block"
        assert (
            lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
        )
    state_database(repo).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(state_database(repo))) as connection, connection:
        connection.execute("create table leases (old_id text)")
    result = _reacquire(repo, target, **arguments)
    assert result["verdict"] == "unknown"
    assert result["required_gaps"] == ["state_schema_lease_table_definition_mismatch"]


def test_reacquire_rolls_back_lease_when_content_changes_during_insertion(tmp_path, monkeypatch):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    planned = _reacquire(repo, target)
    insert = lease_storage.acquire_lease_from_connection

    def drift(connection, *, lease):
        result = insert(connection, lease=lease)
        (target / "README.md").write_text("concurrent edit\n")
        return result

    monkeypatch.setattr(lease_storage, "acquire_lease_from_connection", drift)
    result = _reacquire(repo, target, **_reacquire_arguments(planned))

    assert result["verdict"] == "block"
    assert "lease_reacquire_snapshot_drift" in result["required_gaps"]
    assert lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
    assert (target / "README.md").read_text() == "concurrent edit\n"


def test_reacquire_recovers_evidence_failure_without_replacing_committed_lease(
    tmp_path, monkeypatch
):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    planned = _reacquire(repo, target)
    record = lease_acquisition.record_attestations

    def unavailable(*_args):
        message = "evidence unavailable"
        raise ValueError(message)

    monkeypatch.setattr(lease_acquisition, "record_attestations", unavailable)
    partial = _reacquire(repo, target, **_reacquire_arguments(planned))
    assert partial["state"] == "partial_transition"
    lease = lease_projection.observe_lease(state_database(repo), "work/retained").record()
    assert lease["holder_ref"] == TARGET
    monkeypatch.setattr(lease_acquisition, "record_attestations", record)
    recovered = _reacquire(repo, target, **_reacquire_arguments(planned))
    assert recovered["verdict"] == "pass"
    assert recovered["lease"] == lease


def _operation(
    lease: dict[str, object], operation: str = "renew", **updates: object
) -> LeaseOperationRequest:
    return LeaseOperationRequest.model_validate(
        {
            "operation": operation,
            "branch": lease["lane_ref"],
            **{key: lease[key] for key in ("holder_ref", "generation", "expires_at")},
            "apply": True,
            **updates,
        }
    )


def _takeover(
    lease: dict[str, object], *, apply: bool = True, **updates: object
) -> LeaseTakeoverRequest:
    expected = {
        **{key: lease[key] for key in ("holder_ref", "generation", "expires_at")},
        "branch": lease["lane_ref"],
        "target_holder_ref": TARGET,
        "source_state": "source_lost",
    }
    authorization = attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="maintainer:test:case:reviewer",
        subject=f"git:branch:{lease['lane_ref']}",
        issued_at=datetime.now(UTC),
        payload_kind="authorization:lane-takeover",
        payload_body={"authorization": expected},
        evidence_refs=("evidence:test:takeover",),
    )
    request = {key: value for key, value in expected.items() if key != "holder_ref"}
    return LeaseTakeoverRequest.model_validate(
        {
            **request,
            "source_holder_ref": SOURCE,
            "authorization": authorization,
            "apply": apply,
            **updates,
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("holder_ref", TARGET),
        ("generation", 2),
        ("expires_at", "2026-08-29T00:00:00+00:00"),
    ],
)
@pytest.mark.parametrize("effect", [lease_storage.apply_lease_operation, revoke_lease])
def test_stale_coordinate_rejects_without_mutation(
    tmp_path, field: str, value: object, effect
) -> None:
    database = tmp_path / "state.sqlite"
    acquired = lease_storage.acquire_lease(database, lease=strict_lease(holder=SOURCE))

    with pytest.raises(ValueError, match="lease_generation_stale:work/example"):
        effect(
            database,
            request=_operation(acquired).model_copy(update={field: value}),
        )

    assert lease_projection.observe_lease(database, "work/example").record() == acquired


def test_storage_rejects_conflicting_nonapplying_or_unknown_operations(tmp_path) -> None:
    database = tmp_path / "state.sqlite"
    lease = strict_lease(holder=SOURCE)
    acquired = lease_storage.acquire_lease(database, lease=lease)
    with pytest.raises(ValueError, match="lane_lease_conflict:work/example"):
        lease_storage.acquire_lease(database, lease=lease)

    for request, gap in (
        (_operation(acquired, "unknown"), "lease_operation_unknown:unknown"),
        (_operation(acquired, "resume"), "lease_not_expired:work/example"),
        (_operation(acquired).model_copy(update={"apply": False}), "lease_apply_required:renew"),
    ):
        with pytest.raises(ValueError, match=gap):
            lease_storage.apply_lease_operation(database, request=request)
    with pytest.raises(ValueError, match="lease_apply_required:takeover"):
        lease_storage.takeover_lease(database, request=_takeover(acquired, apply=False))
    assert lease_projection.observe_lease(database, "work/example").record() == acquired


def test_storage_observation_and_exact_cas_fail_closed(tmp_path) -> None:
    lease = strict_lease(holder=SOURCE)
    request = _operation(lease.to_payload())
    assert (
        lease_projection.observe_lease(tmp_path / "missing.sqlite", "work/missing").state
        == "missing"
    )
    assert lease_projection.lease_observations(tmp_path / "missing.sqlite") == []
    with pytest.raises(ValueError, match="work_lane_missing_lease:work/example"):
        lease_storage.apply_lease_operation(tmp_path / "missing.sqlite", request=request)

    unknown = tmp_path / "unknown.sqlite"
    with closing(sqlite3.connect(unknown)) as connection, connection:
        assert lease_projection.observe_lease(unknown, "work/example").record() == {
            "subject": "work/example",
            "lease_state": "missing",
        }
        assert lease_projection.lease_rows(unknown) == []
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(lane_ref, holder_ref, generation, expires_at) values (?, ?, ?, ?)",
            ("work/example", SOURCE, 1, "not-a-time"),
        )
    assert lease_projection.observe_lease(unknown, "work/example").state == "unknown"
    assert lease_projection.active_leases(unknown) == []
    assert lease_projection.observe_lease(unknown, "work/example").record()["error"]
    with pytest.raises(ValueError, match="lease_unknown:work/example"):
        lease_projection.lease_record(("work/example", SOURCE, 1, "not-a-time"))
    with pytest.raises(ValueError, match="lease_unknown:work/example"):
        lease_storage.apply_lease_operation(
            unknown,
            request=request.model_copy(update={"expires_at": "not-a-time"}),
        )

    expired = tmp_path / "expired.sqlite"
    expired_record = lease_storage.acquire_lease(
        expired,
        lease=strict_lease(holder=SOURCE, expires_at=datetime.now(UTC) - timedelta(seconds=1)),
    )
    with pytest.raises(ValueError, match="lease_expired:work/example"):
        lease_storage.apply_lease_operation(expired, request=_operation(expired_record))
    resumed = lease_storage.apply_lease_operation(
        expired, request=_operation(expired_record, "resume")
    )
    assert (resumed["generation"], resumed["holder_ref"]) == (2, SOURCE)

    now = datetime.now(UTC)
    for branch, expires in (("valid", now + timedelta(days=1)), ("expired", now)):
        lease_storage.acquire_lease(
            unknown, lease=strict_lease(branch=f"work/{branch}", expires_at=expires)
        )
    observations = lease_projection.lease_observations(unknown, observed_at=now)
    assert [(item.subject, item.state) for item in observations] == [
        ("work/example", "unknown"),
        ("work/expired", "expired"),
        ("work/valid", "valid"),
    ]
    assert [item["subject"] for item in lease_projection.active_leases(unknown)] == ["work/valid"]

    database = tmp_path / "cas.sqlite"
    lease_storage.acquire_lease(database, lease=lease)
    current = lease_projection.observe_lease(database, "work/example").row
    assert current is not None
    with closing(sqlite3.connect(database)) as connection, connection:
        with pytest.raises(ValueError, match="lease_reissue_identity_mismatch:work/example"):
            lease_storage.replace_exact_lease_from_connection(
                connection,
                current=current,
                replacement=strict_lease(branch="work/other", holder=SOURCE),
            )
        connection.execute("delete from leases where lane_ref = ?", ("work/example",))
        with pytest.raises(ValueError, match="lease_generation_stale:work/example"):
            lease_storage.replace_exact_lease_from_connection(
                connection,
                current=current,
                replacement=strict_lease(holder=SOURCE, generation=2),
            )


@pytest.mark.parametrize(
    ("value", "expected"), [(True, 0), (7, 7), ("8", 8), ("bad", 0), (None, 0)]
)
def test_generation_projection_preserves_integer_or_rejects_unknown(value, expected):
    assert lease_projection.integer_value(value) == expected


@pytest.fixture
def lease_context(tmp_path, monkeypatch):
    """Exercise repository observations and Lease mutations against one real linked lane."""
    repo, _candidate = init_repo_with_candidate(tmp_path)
    root = tmp_path / "owned"
    git(repo, "worktree", "add", "-b", "work/example", str(root), "dev")
    database = state_database(root)
    acquired = lease_storage.acquire_lease(database, lease=strict_lease(holder=SOURCE))
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    return root, database, acquired


@pytest.mark.parametrize("takeover", [False, True], ids=["renew", "takeover"])
@pytest.mark.parametrize("error", [sqlite3.OperationalError("locked"), ValueError("stale")])
def test_public_lease_storage_failure_preserves_generation(
    lease_context, monkeypatch, takeover, error
):
    root, database, acquired = lease_context
    request = _takeover(acquired) if takeover else _operation(acquired)
    module = lease_takeover if takeover else lease_operation
    if isinstance(request, LeaseTakeoverRequest):
        monkeypatch.setenv("ETHOS_ACTOR", TARGET)
        record_attestations(root, (request.authorization,))
    before = read_attestation_set(root)

    def reject(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(module, "takeover_lease" if takeover else "apply_lease_operation", reject)
    report = (
        lease_takeover.execute_lease_takeover(root=root, request=request)
        if isinstance(request, LeaseTakeoverRequest)
        else lease_operation.execute_lease_operation(root=root, request=request)
    )
    assert (report["verdict"], report["required_gaps"], report["lease"]) == (
        "block",
        [str(error)],
        {},
    )
    assert lease_projection.observe_lease(database, "work/example").record() == acquired
    assert read_attestation_set(root) == before


@pytest.mark.parametrize("operation", ["renew", "transfer"])
def test_public_lease_operation_projects_and_applies_exact_four_coordinate_cas(
    lease_context, operation
):
    root, _database, acquired = lease_context
    request = _operation(
        acquired, operation, target_holder_ref=TARGET if operation == "transfer" else ""
    )
    planned = lease_operation.execute_lease_operation(
        root=root,
        request=request.model_copy(update={"apply": False}),
    )
    applied = lease_operation.execute_lease_operation(root=root, request=request)
    lease, mutation = applied["lease"], applied["mutation"]
    assert isinstance(lease, dict)
    assert isinstance(mutation, dict)
    assert (planned["verdict"], planned["state"], planned["lease"]) == ("pass", "planned", {})
    assert (applied["verdict"], applied["state"]) == (
        "pass",
        "transferred" if operation == "transfer" else "renewed",
    )
    assert lease["generation"] == 2
    assert lease["holder_ref"] == (TARGET if operation == "transfer" else SOURCE)
    assert set(lease) == {
        "subject",
        "lease_state",
        "lane_ref",
        "holder_ref",
        "generation",
        "expires_at",
    }
    assert mutation["decision"]["decision_basis"]["enforcement_boundary"] == (
        "local_sqlite_compare_and_swap"
    )


@pytest.mark.parametrize(
    ("operation", "changes", "gap"),
    [
        ("unknown", {}, "lease_operation_unknown:unknown"),
        ("renew", {"status": {"role": "accepted_root"}}, "work_lane_required"),
        ("renew", {"status": {"branch": "work/other"}}, "lane_branch_mismatch"),
        ("renew", {"lease": "missing"}, "work_lane_missing_lease:work/example"),
        ("renew", {"lease": "unknown"}, "work_lane_lease_unknown:work/example"),
        ("resume", {}, "lease_not_expired:work/example"),
        ("renew", {"request": {"generation": 2}}, "lease_generation_stale:work/example"),
        ("renew", {"actor": TARGET}, "lease_actor_mismatch"),
        ("transfer", {}, "target_holder_ref_required"),
        ("resume", {"request": {"contrary_decision": True}}, "lease_resume_blocked_by_decision"),
    ],
)
def test_public_lease_operation_fails_closed_with_one_precise_reason(
    lease_context,
    monkeypatch,
    operation,
    changes,
    gap,
):
    root, _database, acquired = lease_context
    if status := changes.get("status"):
        monkeypatch.setattr(
            lease_operation,
            "workspace_status",
            lambda _root: {
                "role": "work_lane",
                "branch": "work/example",
                **status,
            },
        )
    if lease := changes.get("lease"):
        monkeypatch.setattr(
            lease_operation,
            "leases_by_branch",
            lambda _root: {
                "work/example": {**acquired, "lease_state": lease},
            },
        )
    monkeypatch.setenv("ETHOS_ACTOR", changes.get("actor", SOURCE))
    request = _operation(acquired, operation).model_copy(update=changes.get("request", {}))
    report = lease_operation.execute_lease_operation(root=root, request=request)
    assert report["verdict"] == ("unknown" if changes.get("lease") == "unknown" else "block")
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert gap in gaps
    assert report["lease"] == {}


@pytest.mark.parametrize("recovery_actor", [SOURCE, ""])
def test_public_lease_takeover_requires_accepted_authorization_and_is_idempotent(
    lease_context, monkeypatch: pytest.MonkeyPatch, recovery_actor: str
) -> None:
    root, database, acquired = lease_context
    request = _takeover(acquired)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    record_attestations(root, (request.authorization,))
    applied = lease_takeover.execute_lease_takeover(root=root, request=request)
    recovered = lease_takeover.execute_lease_takeover(root=root, request=request)
    lease, recovered_lease = applied["lease"], recovered["lease"]
    assert isinstance(lease, dict)
    assert isinstance(recovered_lease, dict)

    assert (applied["verdict"], applied["state"], lease["holder_ref"]) == (
        "pass",
        "taken_over",
        TARGET,
    )
    assert (recovered["verdict"], recovered["state"], recovered_lease["generation"]) == (
        "pass",
        "taken_over",
        2,
    )
    monkeypatch.setenv("ETHOS_ACTOR", recovery_actor)
    denied = lease_takeover.execute_lease_takeover(root=root, request=request)
    assert denied["verdict"] == "block", "recovery readmission bypassed the current actor"
    assert denied["required_gaps"] == ["lease_takeover_actor_mismatch"]
    _selected, records = read_attestation_set(root)
    assert len([item for item in records if item.payload.kind == "effect:native"]) == 2
    revoked = revoke_lease(database, request=_operation(lease, "revoke"))
    assert revoked == {
        "revoked": True,
        "lane_ref": "work/example",
        "holder_ref": TARGET,
        "generation": 2,
        "expires_at": lease["expires_at"],
    }
    assert lease_projection.observe_lease(database, "work/example").state == "missing"


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
    lease_context,
    monkeypatch,
    accepted_count,
    actor,
    request_updates,
    gap,
) -> None:
    root, database, acquired = lease_context
    request = _takeover(acquired).model_copy(update=request_updates)
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    if accepted_count:
        record_attestations(root, (request.authorization,))

    report = lease_takeover.execute_lease_takeover(root=root, request=request)

    assert report["verdict"] == "block"
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert gap in gaps
    assert lease_projection.observe_lease(database, "work/example").record() == acquired

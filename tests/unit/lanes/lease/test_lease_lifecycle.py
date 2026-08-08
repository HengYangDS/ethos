from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import cast

import pytest
from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine
from hypothesis.stateful import invariant
from hypothesis.stateful import precondition
from hypothesis.stateful import rule

import ethos.adapters.mutation.lane_retirement.effects as retirement_effects
import ethos.adapters.repo.git_effects as git_effects
import ethos.adapters.store.state.lease.lifecycle.transitions as lease_transitions
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_takeover
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.mutation.proof import persist_attestation
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.lane_scenarios import superseded_work_lane


def _successor_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, str, Path, str, Path, LinkedRetirementRequest]:
    holder_ref = "agent:test:case:campaign"
    repo, source, source_head, _, database = superseded_work_lane(
        tmp_path,
        holder_ref=holder_ref,
    )
    source_lease = LaneLease.from_payload(
        dict(leases_by_branch(source)["work/superseded"]["payload"])
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", ("work/superseded",))
    successor_branch = "work/campaign"
    successor = tmp_path.parent / f"{tmp_path.name}-campaign"
    git(repo, "worktree", "add", "-b", successor_branch, successor.as_posix(), source_head)
    acquire_lease(
        database,
        lease=source_lease.model_copy(
            update={
                "lane_incarnation_id": "lane-incarnation:campaign",
                "lease_id": "lease:campaign",
                "lane_ref": successor_branch,
                "holder_ref": HolderRef.parse(holder_ref),
            }
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    successor_head = commit_fixture_file(
        successor,
        "campaign.txt",
        "campaign\n",
        "continue campaign",
    )
    return (
        repo,
        source,
        source_head,
        successor,
        successor_branch,
        database,
        LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=successor_head,
            reason="campaign contains the exact source history",
            authorize=True,
        ),
    )


def test_linked_leased_archive_equivalent_carrier_retires_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:archive-equivalent"
    repo, lane, _source_head, _accepted, database = superseded_work_lane(
        tmp_path / "archive-equivalent",
        holder_ref=holder,
        absorbed=False,
    )
    active_root = lane / "openspec/changes/fixture-change"
    archive_root = repo / "openspec/changes/archive/2026-08-08-fixture-change"
    archive_root.parent.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir()
    for name in ("proposal.md", "commitment.toml"):
        (archive_root / name).write_bytes((active_root / name).read_bytes())
    git(repo, "rm", "-r", "openspec/changes/fixture-change")
    git(repo, "add", archive_root.relative_to(repo).as_posix())
    git(repo, "commit", "-m", "archive fixture carrier")
    accepted = git(repo, "rev-parse", "HEAD")
    git(lane, "reset", "--hard", accepted)
    active_root.mkdir(parents=True)
    for name in ("proposal.md", "commitment.toml"):
        (active_root / name).write_bytes((archive_root / name).read_bytes())
    git(lane, "add", active_root.relative_to(lane).as_posix())
    git(lane, "commit", "-m", "reconstruct active carrier")
    source_head = git(lane, "rev-parse", "HEAD")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", ("work/superseded",))
    acquire_lease(
        database,
        lease=exact_lease(
            repo=lane,
            branch="work/superseded",
            holder_ref=holder,
            expected_head=source_head,
            carrier="openspec/changes/fixture-change/commitment.toml",
            change_id="fixture-change",
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    request = LinkedRetirementRequest(
        branch="work/superseded",
        expect_head=source_head,
        absorbed_by=accepted,
        reason="accepted archive contains the exact active carrier",
        authorize=True,
    )

    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)
    mapping = planned["lane"]["archive_absorption"]
    commitment_blob = git(
        repo,
        "rev-parse",
        f"{source_head}:openspec/changes/fixture-change/commitment.toml",
    )
    proposal_blob = git(
        repo,
        "rev-parse",
        f"{source_head}:openspec/changes/fixture-change/proposal.md",
    )
    applied = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert (planned["verdict"], planned["state"], planned["required_gaps"]) == (
        "pass",
        "ready_to_retire_superseded",
        [],
    )
    assert mapping == {
        "change": "fixture-change",
        "archive_root": "openspec/changes/archive/2026-08-08-fixture-change",
        "paths": {
            "openspec/changes/fixture-change/commitment.toml": {
                "target": "openspec/changes/archive/2026-08-08-fixture-change/commitment.toml",
                "blob": commitment_blob,
            },
            "openspec/changes/fixture-change/proposal.md": {
                "target": "openspec/changes/archive/2026-08-08-fixture-change/proposal.md",
                "blob": proposal_blob,
            },
        },
    }
    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "retired_superseded",
        [],
    )
    assert not lane.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert observe_lease(database, "work/superseded").state == "missing"


def test_archive_equivalent_retirement_rejects_extra_source_delta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:archive-extra"
    repo, lane, source_head, accepted, database = superseded_work_lane(
        tmp_path / "archive-extra",
        holder_ref=holder,
        absorbed=False,
    )
    archive_root = repo / "openspec/changes/archive/2026-08-08-fixture-change"
    archive_root.parent.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir()
    active_root = lane / "openspec/changes/fixture-change"
    for name in ("proposal.md", "commitment.toml"):
        (archive_root / name).write_bytes((active_root / name).read_bytes())
    git(repo, "add", archive_root.relative_to(repo).as_posix())
    git(repo, "commit", "-m", "archive fixture carrier")
    accepted = git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", holder)

    planned = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="archive omits the extra obsolete delta",
            authorize=True,
        ),
    )

    assert planned["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert lane.exists()
    assert git(repo, "rev-parse", "work/superseded") == source_head
    assert observe_lease(database, "work/superseded").state == "valid"


def _lease_request(
    *,
    operation: str,
    branch: str,
    holder_ref: str,
    lease: dict[str, object],
    apply: bool,
    **values: object,
) -> LeaseOperationRequest:
    """Build a generation-bound public lease request from its current projection."""
    payload: dict[str, object] = {
        "operation": operation,
        "branch": branch,
        "holder_ref": holder_ref,
        "lease_id": str(lease["lease_id"]),
        "expected_epoch": int(lease["epoch"]),
        "expect_head": str(lease["expected_head"]),
        "expected_expires_at": str(lease["expires_at"]),
        "expected_payload_sha256": str(lease["payload_sha256"]),
        "apply": apply,
    }
    payload.update(values)
    return LeaseOperationRequest.model_validate(payload)


def _lease_snapshot(worktree: Path, branch: str) -> dict[str, object]:
    return leases_by_branch(worktree)[branch]


def _assert_reissue_changes(
    before: dict[str, object],
    after: dict[str, object],
    *declared_fields: str,
) -> None:
    before_payload = dict(before["payload"])
    after_payload = dict(after["payload"])
    assert set(before_payload) == set(after_payload) == set(LaneLease.model_fields)
    assert {
        field for field in LaneLease.model_fields if before_payload[field] != after_payload[field]
    } == set(declared_fields)


def _install_reference_transaction_hook(
    repo: Path,
    invocation_root: Path,
    _monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hook_launchers(repo)
    if invocation_root != repo:
        install_hook_launchers(invocation_root)
    exclude = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("tools/\n", encoding="utf-8")


def _apply_lease(database: Path, request: LeaseOperationRequest) -> dict[str, object]:
    return apply_lease_operation(database, request=request)


@dataclass
class LeaseCase:
    worktree: Path
    database: Path
    branch: str
    holder: str

    @classmethod
    def start(cls, tmp_path: Path, name: str, holder: str) -> LeaseCase:
        fixture = start_adopted_work_lane(tmp_path / name, name=name, holder_ref=holder)
        return cls(fixture.worktree, state_database(fixture.worktree), f"work/{name}", holder)

    def snapshot(self) -> dict[str, object]:
        return _lease_snapshot(self.worktree, self.branch)

    def request(
        self,
        operation: str,
        lease: dict[str, object],
        *,
        apply: bool = True,
        holder: str | None = None,
        **values: object,
    ) -> LeaseOperationRequest:
        return _lease_request(
            operation=operation,
            branch=self.branch,
            holder_ref=holder or self.holder,
            lease=lease,
            apply=apply,
            **values,
        )

    def apply(
        self, operation: str, lease: dict[str, object], **values: object
    ) -> dict[str, object]:
        return _apply_lease(self.database, self.request(operation, lease, **values))

    def execute(
        self,
        operation: str,
        lease: dict[str, object],
        *,
        apply: bool = True,
        **values: object,
    ) -> dict[str, object]:
        return execute_lease_operation(
            root=self.worktree,
            request=self.request(operation, lease, apply=apply, **values),
        )


def _insert_lease_row(
    database: Path,
    lease: LaneLease,
    *,
    payload: dict[str, object] | None = None,
    row_expires_at: str | None = None,
) -> None:
    raw_payload = json.dumps(payload or lease.to_payload(), sort_keys=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            (
                lease.lease_id,
                lease.lane_ref,
                lease.holder_ref.serialize(),
                row_expires_at or lease.expires_at.isoformat(),
                raw_payload,
            ),
        )


class LeaseTransitionMachine(RuleBasedStateMachine):
    """Bounded model of exact Lease refresh, offer, accept, and stale-CAS behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "state.sqlite"
        now = datetime.now(UTC)
        self.binding = {
            "expected_head": "a" * 40,
            "expected_tree": "b" * 40,
            "base_commitment_path": "openspec/changes/example/commitment.toml",
            "base_commitment_bytes_sha256": "c" * 64,
            "base_commitment_digest": "d" * 64,
        }
        acquire_lease(
            self.database,
            lease=LaneLease(
                lane_incarnation_id="lane-incarnation:model",
                lease_id="lease:model",
                lane_ref="work/model",
                holder_ref=HolderRef.parse("agent:test:case:first"),
                epoch=1,
                issued_at=now,
                renewed_at=now,
                expires_at=now + timedelta(hours=1),
                path_scope=(),
                handoff=None,
                **self.binding,
            ),
        )

    def teardown(self) -> None:
        self.temporary_directory.cleanup()

    def snapshot(self) -> dict[str, Any]:
        return observe_lease(self.database, "work/model").record()

    def request(self, operation: str, **values: object) -> LeaseOperationRequest:
        lease = self.snapshot()
        return _lease_request(
            operation=operation,
            branch="work/model",
            holder_ref=str(lease["holder_ref"]),
            lease=lease,
            apply=True,
            **values,
        )

    @rule()
    def renew(self) -> None:
        before = self.snapshot()
        after = _apply_lease(self.database, self.request("renew", ttl_seconds=3600))
        assert (after["holder_ref"], after["epoch"]) == (
            before["holder_ref"],
            before["epoch"],
        )

    @rule()
    def offer(self) -> None:
        before = self.snapshot()
        target = (
            "agent:test:case:second"
            if before["holder_ref"] == "agent:test:case:first"
            else "agent:test:case:first"
        )
        after = _apply_lease(
            self.database,
            self.request("handoff_offer", target_holder_ref=target),
        )
        assert (after["holder_ref"], after["epoch"]) == (
            before["holder_ref"],
            before["epoch"],
        )

    @precondition(lambda self: bool(self.snapshot()["payload"]["handoff"]))
    @rule()
    def accept(self) -> None:
        before = self.snapshot()
        handoff = before["payload"]["handoff"]
        assert isinstance(handoff, dict)
        after = _apply_lease(
            self.database,
            self.request(
                "handoff_accept",
                target_holder_ref=str(handoff["target_holder_ref"]),
                offer_id=str(handoff["offer_id"]),
                holder_quiesced=True,
                ttl_seconds=3600,
            ),
        )
        payload = cast("dict[str, object]", after["payload"])
        assert (after["holder_ref"], after["epoch"], payload["handoff"]) == (
            handoff["target_holder_ref"],
            int(before["epoch"]) + 1,
            None,
        )

    @rule()
    def stale_epoch_has_zero_effect(self) -> None:
        before = self.snapshot()
        request = self.request("renew").model_copy(
            update={"expected_epoch": int(before["epoch"]) + 1}
        )
        with pytest.raises(ValueError, match=r"^lease_epoch_stale:"):
            _apply_lease(self.database, request)
        assert self.snapshot() == before

    @invariant()
    def identity_and_binding_are_preserved(self) -> None:
        lease = self.snapshot()
        assert (lease["lease_id"], lease["lane_ref"]) == ("lease:model", "work/model")
        assert all(lease[field] == value for field, value in self.binding.items())


TestLeaseTransitionMachine = LeaseTransitionMachine.TestCase
TestLeaseTransitionMachine.settings = settings(
    deadline=None,
    max_examples=20,
    stateful_step_count=12,
)


def test_lease_observation_keeps_valid_expired_unknown_and_missing_distinct(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite"
    missing = observe_lease(database, "work/missing")
    assert (missing.state, missing.lease, missing.row) == ("missing", None, None)

    now = datetime.now(UTC)
    valid = LaneLease(
        lane_incarnation_id="lane-incarnation:valid",
        lease_id="lease:valid",
        lane_ref="work/valid",
        holder_ref=HolderRef.parse("agent:test:case:valid"),
        epoch=1,
        issued_at=now,
        renewed_at=now,
        expires_at=now + timedelta(hours=1),
        expected_head="a" * 40,
        expected_tree="c" * 40,
        base_commitment_path="openspec/changes/terminal-convergence/commitment.toml",
        base_commitment_bytes_sha256="d" * 64,
        base_commitment_digest="b" * 64,
        path_scope=(),
        handoff=None,
    )
    _insert_lease_row(database, valid)
    observed_valid = observe_lease(database, valid.lane_ref)
    assert observed_valid.state == "valid"
    assert observed_valid.lease == valid

    expired = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:expired",
            "lease_id": "lease:expired",
            "lane_ref": "work/expired",
            "issued_at": now - timedelta(hours=2),
            "renewed_at": now - timedelta(hours=2),
            "expires_at": now - timedelta(hours=1),
        }
    )
    _insert_lease_row(database, expired)
    assert observe_lease(database, expired.lane_ref).state == "expired"

    legacy_payload = valid.to_payload() | {"claim_id": "retired"}
    legacy_payload.pop("base_commitment_digest")
    legacy = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:legacy",
            "lease_id": "lease:legacy",
            "lane_ref": "work/legacy",
        }
    )
    _insert_lease_row(
        database,
        legacy,
        payload=legacy_payload
        | {
            "lane_incarnation_id": legacy.lane_incarnation_id,
            "lease_id": legacy.lease_id,
            "lane_ref": legacy.lane_ref,
        },
    )
    observed_unknown = observe_lease(database, legacy.lane_ref)
    assert observed_unknown.state == "unknown"
    assert observed_unknown.lease is None
    assert observed_unknown.row is not None
    assert observed_unknown.row.id == legacy.lease_id
    assert len(observed_unknown.row.payload_sha256) == 64
    assert observed_unknown.record()["error"] == "lane_lease_payload_fields_invalid"

    mismatch = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:mismatch",
            "lease_id": "lease:mismatch",
            "lane_ref": "work/mismatch",
        }
    )
    _insert_lease_row(
        database,
        mismatch,
        row_expires_at=(mismatch.expires_at + timedelta(minutes=1)).isoformat(),
    )
    assert observe_lease(database, mismatch.lane_ref).state == "unknown"


def test_unknown_lease_is_observe_only_for_public_mutation_and_retirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    fixture = start_adopted_work_lane(
        tmp_path / "unknown-mutation", name="unknown-mutation", holder_ref=holder_ref
    )
    branch = "work/unknown-mutation"
    database = state_database(fixture.worktree)
    initial = _lease_snapshot(fixture.worktree, branch)
    unknown_payload = dict(initial["payload"])
    unknown_payload["claim_id"] = "retired"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(unknown_payload, sort_keys=True), branch),
        )

    mutation = execute_lease_operation(
        root=fixture.worktree,
        request=_lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=initial,
            apply=False,
        ),
    )
    assert mutation["verdict"] == "unknown"
    assert "ok" not in mutation
    assert mutation["mutation"]["decision"]["verdict"] == mutation["verdict"]
    assert mutation["required_gaps"] == [f"work_lane_lease_unknown:{branch}"]
    assert observe_lease(database, branch).state == "unknown"

    repo, lane, head, accepted, retirement_database = superseded_work_lane(
        tmp_path / "unknown-retirement", holder_ref=holder_ref
    )
    retired = leases_by_branch(lane)["work/superseded"]
    retired_payload = dict(retired["payload"])
    retired_payload["claim_id"] = "retired"
    with closing(sqlite3.connect(retirement_database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(retired_payload, sort_keys=True), "work/superseded"),
        )
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    retirement = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=head,
            absorbed_by=accepted,
            reason="superseded fixture",
            authorize=True,
            apply=False,
        ),
    )
    assert retirement["verdict"] == "unknown", retirement
    assert "ok" not in retirement
    assert retirement["mutation"]["decision"]["verdict"] == retirement["verdict"]
    assert "work_lane_lease_unknown:work/superseded" in retirement["required_gaps"]
    assert observe_lease(retirement_database, "work/superseded").state == "unknown"


def test_missing_lease_source_retires_through_exact_leased_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:campaign"
    repo, source, source_head, accepted, database = superseded_work_lane(
        tmp_path / "successor-retirement",
        holder_ref=holder_ref,
    )
    source_lease = LaneLease.from_payload(
        dict(leases_by_branch(source)["work/superseded"]["payload"])
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", ("work/superseded",))
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    blocked = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="accepted tree contains the obsolete delta",
            authorize=True,
        ),
    )
    assert blocked["required_gaps"] == [
        "foreign_work_lane_retire_authority_required",
        "work_lane_missing_lease:work/superseded",
    ]

    successor_branch = "work/campaign"
    successor = tmp_path / "successor-retirement-campaign"
    git(
        repo,
        "worktree",
        "add",
        "-b",
        successor_branch,
        successor.as_posix(),
        source_head,
    )
    acquire_lease(
        database,
        lease=source_lease.model_copy(
            update={
                "lane_incarnation_id": "lane-incarnation:campaign",
                "lease_id": "lease:campaign",
                "lane_ref": successor_branch,
                "holder_ref": HolderRef.parse(holder_ref),
            }
        ),
    )
    successor_head = commit_fixture_file(
        successor,
        "campaign.txt",
        "campaign\n",
        "continue campaign",
    )
    request = LinkedRetirementRequest(
        branch="work/superseded",
        expect_head=source_head,
        absorbed_by=successor_head,
        reason="campaign contains the exact source history",
        authorize=True,
    )
    ready = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request,
    )
    assert (ready["verdict"], ready["state"], ready["required_gaps"]) == (
        "pass",
        "ready_to_retire_superseded",
        [],
    )
    assert "ok" not in ready
    assert ready["mutation"]["decision"]["verdict"] == ready["verdict"]

    retired = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )
    assert (retired["verdict"], retired["state"], retired["required_gaps"]) == (
        "pass",
        "retired_superseded",
        [],
    )
    assert "ok" not in retired
    assert retired["mutation"]["decision"]["verdict"] == retired["verdict"]
    assert not source.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert (
        git(repo, "show-ref", "--verify", "--hash", f"refs/heads/{successor_branch}")
        == successor_head
    )
    assert observe_lease(database, successor_branch).state == "valid"
    assert observe_lease(database, "work/superseded").state == "missing"


def test_successor_retirement_rechecks_the_invoking_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source, _, successor, _, _, request = _successor_retirement(
        tmp_path / "checkout-race",
        monkeypatch,
    )
    original = retirement_effects.apply_retirement

    def switch_branch(*args: Any, **kwargs: Any) -> dict[str, object]:
        git(successor, "branch", "work/not-campaign", request.absorbed_by)
        git(successor, "symbolic-ref", "HEAD", "refs/heads/work/not-campaign")
        return original(*args, **kwargs)

    monkeypatch.setattr(retirement_effects, "apply_retirement", switch_branch)
    report = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert report["required_gaps"] == ["retirement_authority_checkout_stale"]
    assert source.exists()
    assert git(repo, "rev-parse", "work/superseded") == request.expect_head


def test_successor_retirement_restores_binding_after_ref_cas_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source, source_head, successor, _, _, request = _successor_retirement(
        tmp_path / "ref-failure",
        monkeypatch,
    )
    original = git_effects.run_git

    def fail_ref_cas(
        root: Path,
        *args: str,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("update-ref", "--stdin"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "forced ref failure")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(git_effects, "run_git", fail_ref_cas)
    report = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["mutation"]["decision"]["verdict"] == report["verdict"]
    assert source.exists()
    assert git(source, "branch", "--show-current") == "work/superseded"
    assert git(repo, "rev-parse", "work/superseded") == source_head


def test_direct_retirement_ref_cas_failure_restores_exact_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    repo, source, source_head, accepted, database = superseded_work_lane(
        tmp_path / "direct-ref-failure", holder_ref=holder_ref
    )
    before = _lease_snapshot(source, "work/superseded")
    original = git_effects.run_git

    def fail_ref_cas(root: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("update-ref", "--stdin"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "forced ref failure")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(git_effects, "run_git", fail_ref_cas)
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="accepted tree contains the obsolete delta",
            authorize=True,
            apply=True,
        ),
    )

    assert report["verdict"] == "block"
    assert source.exists()
    assert git(source, "branch", "--show-current") == "work/superseded"
    assert git(repo, "rev-parse", "work/superseded") == source_head
    assert _lease_snapshot(source, "work/superseded") == before
    assert observe_lease(database, "work/superseded").state == "valid"


def test_retirement_reobservation_blocks_target_branch_rebind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    repo, source, source_head, accepted, database = superseded_work_lane(
        tmp_path / "target-branch-rebind", holder_ref=holder_ref
    )
    original = retirement_effects.apply_retirement

    def switch_target_branch(*args: Any, **kwargs: Any) -> dict[str, object]:
        git(source, "branch", "work/other", source_head)
        git(source, "symbolic-ref", "HEAD", "refs/heads/work/other")
        return original(*args, **kwargs)

    monkeypatch.setattr(retirement_effects, "apply_retirement", switch_target_branch)
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="accepted tree contains the obsolete delta",
            authorize=True,
            apply=True,
        ),
    )

    assert report["required_gaps"] == ["retirement_worktree_branch_stale"]
    assert source.exists()
    assert git(repo, "rev-parse", "work/superseded") == source_head
    assert observe_lease(database, "work/superseded").state == "valid"


@pytest.mark.parametrize("commit_outcome", ["before", "after"])
def test_retirement_commit_error_reports_observed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    commit_outcome: str,
) -> None:
    commit_applied = commit_outcome == "after"
    holder_ref = "agent:test:case:source"
    repo, source, source_head, accepted, database = superseded_work_lane(
        tmp_path / f"commit-error-{commit_outcome}", holder_ref=holder_ref
    )
    real_closing = retirement_effects.closing

    class CommitProxy:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self.connection = connection

        def __getattr__(self, name: str) -> Any:
            return getattr(self.connection, name)

        def commit(self) -> None:
            if commit_applied:
                self.connection.commit()
            message = "forced uncertain commit"
            raise sqlite3.OperationalError(message)

        def close(self) -> None:
            self.connection.close()

    monkeypatch.setattr(
        retirement_effects,
        "closing",
        lambda connection: real_closing(CommitProxy(connection)),
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="accepted tree contains the obsolete delta",
            authorize=True,
            apply=True,
        ),
    )

    observed = report["retired"] if commit_applied else report["observed"]
    if commit_applied:
        assert (report["verdict"], report["state"]) == ("pass", "retired_superseded")
        assert observed["lease_state"] == "missing"
        assert observed["ref_state"] == "absent"
        assert observed["worktree_state"] == "absent"
        assert not source.exists()
    else:
        assert report["verdict"] == "block"
        assert observed["lease_state"] == "valid"
        assert observed["ref_state"] == "absent"
        assert observed["worktree_state"] == "absent"
        assert not source.exists()
        assert observe_lease(database, "work/superseded").state == "valid"


def test_successor_retirement_uses_the_installed_reference_transaction_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, source, _, successor, successor_branch, database, request = _successor_retirement(
        tmp_path / "installed-hook",
        monkeypatch,
    )
    _install_reference_transaction_hook(repo, successor, monkeypatch)
    raw_delete = subprocess.run(
        ["git", "update-ref", "-d", "refs/heads/work/superseded", request.expect_head],
        cwd=successor,
        check=False,
        capture_output=True,
        text=True,
    )
    assert raw_delete.returncode != 0
    assert git(repo, "rev-parse", "work/superseded") == request.expect_head

    report = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "retired_superseded",
        [],
    )
    assert "ok" not in report
    assert report["mutation"]["decision"]["verdict"] == report["verdict"]
    assert not source.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert observe_lease(database, successor_branch).state == "valid"


def test_raw_delete_of_valid_leased_work_lane_requires_ref_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    repo, source, source_head, accepted, database = superseded_work_lane(
        tmp_path / "leased-delete",
        holder_ref=holder_ref,
    )
    _install_reference_transaction_hook(repo, repo, monkeypatch)
    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)

    raw_delete = subprocess.run(
        ["git", "update-ref", "-d", "refs/heads/work/superseded", source_head],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert raw_delete.returncode != 0
    assert git(repo, "rev-parse", "work/superseded") == source_head
    assert observe_lease(database, "work/superseded").state == "valid"

    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=LinkedRetirementRequest(
            branch="work/superseded",
            expect_head=source_head,
            absorbed_by=accepted,
            reason="accepted tree contains the obsolete delta",
            authorize=True,
            apply=True,
        ),
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "retired_superseded",
        [],
    )
    assert not source.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert observe_lease(database, "work/superseded").state == "missing"


def test_full_lease_reissues_preserve_every_undeclared_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, "reissue", holder_ref)
    initial = case.snapshot()
    initial_payload = dict(initial["payload"])
    initial_payload["path_scope"] = ["src/**", "tests/**"]
    with closing(sqlite3.connect(case.database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(initial_payload, sort_keys=True), case.branch),
        )
    initial = observe_lease(case.database, case.branch).record()

    renewed = case.apply("renew", initial)
    _assert_reissue_changes(initial, renewed, "renewed_at", "expires_at")

    offered = case.apply("handoff_offer", renewed, target_holder_ref=target_holder_ref)
    _assert_reissue_changes(renewed, offered, "handoff")

    accepted = case.apply(
        "handoff_accept",
        offered,
        target_holder_ref=target_holder_ref,
        offer_id=str(offered["offer_id"]),
        holder_quiesced=True,
    )
    _assert_reissue_changes(
        offered,
        accepted,
        "holder_ref",
        "epoch",
        "renewed_at",
        "expires_at",
        "handoff",
    )

    advanced = advance_lease_ref(
        case.database,
        request=case.request("advance", accepted, holder=target_holder_ref),
        binding={
            "expected_head": "c" * 40,
            "expected_tree": "d" * 40,
            "base_commitment_path": "records/change/commitment.toml",
            "base_commitment_bytes_sha256": "e" * 64,
            "base_commitment_digest": "f" * 64,
        },
    )
    _assert_reissue_changes(
        accepted,
        advanced,
        "expected_head",
        "expected_tree",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
        "base_commitment_digest",
    )

    def unexpected_replace(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError

    with monkeypatch.context() as invalid_reissue:
        invalid_reissue.setattr(
            lease_transitions,
            "replace_exact_lease_from_connection",
            unexpected_replace,
        )
        with pytest.raises(ValueError, match="expected_head"):
            advance_lease_ref(
                case.database,
                request=case.request("advance", advanced, holder=target_holder_ref),
                binding={
                    "expected_head": "invalid-head",
                    "expected_tree": "d" * 40,
                    "base_commitment_path": advanced["base_commitment_path"],
                    "base_commitment_bytes_sha256": advanced["base_commitment_bytes_sha256"],
                    "base_commitment_digest": advanced["base_commitment_digest"],
                },
            )
    assert observe_lease(case.database, case.branch).record() == advanced

    resume = LeaseCase.start(tmp_path, "resume-reissue", holder_ref)
    expired = resume.snapshot()
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    expired_payload = dict(expired["payload"])
    expired_payload.update(
        issued_at=(expired_at - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired_at - timedelta(seconds=1)).isoformat(),
        expires_at=expired_at.isoformat(),
        path_scope=["src/**", "tests/**"],
    )
    with closing(sqlite3.connect(resume.database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired_at.isoformat(), json.dumps(expired_payload, sort_keys=True), resume.branch),
        )
    expired = observe_lease(resume.database, resume.branch).record()
    resumed = resume.apply("resume", expired)
    _assert_reissue_changes(expired, resumed, "renewed_at", "expires_at")


def test_full_lease_reissue_rejects_legacy_payload(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    now = datetime.now(UTC)
    initial = acquire_lease(
        database,
        lease=LaneLease(
            lane_incarnation_id="lane-incarnation:example",
            lease_id="lease:example",
            lane_ref="work/example",
            holder_ref="agent:test:case:holder",
            epoch=1,
            issued_at=now,
            renewed_at=now,
            expires_at=now + timedelta(days=1),
            expected_head="a" * 40,
            expected_tree="c" * 40,
            base_commitment_path="openspec/changes/terminal-convergence/commitment.toml",
            base_commitment_bytes_sha256="d" * 64,
            base_commitment_digest="b" * 64,
            path_scope=(),
        ),
    )
    renewed = apply_lease_operation(
        database,
        request=_lease_request(
            operation="renew",
            branch="work/example",
            holder_ref="agent:test:case:holder",
            lease=initial,
            apply=True,
        ),
    )

    assert renewed["base_commitment_digest"] == initial["base_commitment_digest"]
    assert set(renewed["payload"]) == set(LaneLease.model_fields)
    assert renewed["payload"]["handoff"] is None

    with closing(sqlite3.connect(database)) as connection, connection:
        raw = connection.execute(
            "select payload_json from leases where subject = ?", ("work/example",)
        ).fetchone()[0]
        payload = json.loads(raw)
        payload["claim_id"] = "retired"
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True), "work/example"),
        )
    with pytest.raises(ValueError, match="lease_unknown:work/example"):
        apply_lease_operation(
            database,
            request=_lease_request(
                operation="renew",
                branch="work/example",
                holder_ref="agent:test:case:holder",
                lease=renewed,
                apply=True,
            ),
        )


def test_lease_public_transition_matrix_enforces_actor_cas_and_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    target_holder = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, "lease", source_holder)
    initial = case.snapshot()

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    wrong_actor = case.execute("renew", initial)
    assert wrong_actor["verdict"] == "block"
    assert "ok" not in wrong_actor
    assert wrong_actor["mutation"]["decision"]["verdict"] == wrong_actor["verdict"]
    assert "lease_actor_mismatch" in wrong_actor["required_gaps"]

    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    renewed = case.execute("renew", initial)
    assert renewed["verdict"] == "pass"
    assert "ok" not in renewed
    assert renewed["mutation"]["decision"]["verdict"] == renewed["verdict"]
    renewed_lease = renewed["lease"]
    assert isinstance(renewed_lease, dict)
    offered = case.execute("handoff_offer", renewed_lease, target_holder_ref=target_holder)
    assert offered["verdict"] == "pass"
    assert "ok" not in offered
    assert offered["mutation"]["decision"]["verdict"] == offered["verdict"]
    offer = offered["handoff_offer"]
    assert isinstance(offer, dict)

    monkeypatch.setenv("ETHOS_ACTOR", target_holder)
    accept = {
        "target_holder_ref": target_holder,
        "offer_id": str(offer["offer_id"]),
    }
    not_quiesced = case.execute(
        "handoff_accept",
        offer,
        **accept,
        holder_quiesced=False,
    )
    assert not_quiesced["verdict"] == "block"
    assert "ok" not in not_quiesced
    assert not_quiesced["mutation"]["decision"]["verdict"] == not_quiesced["verdict"]
    assert "holder_quiescence_confirmation_required" in not_quiesced["required_gaps"]
    accepted = case.execute("handoff_accept", offer, **accept, holder_quiesced=True)
    assert accepted["verdict"] == "pass"
    assert "ok" not in accepted
    assert accepted["mutation"]["decision"]["verdict"] == accepted["verdict"]
    accepted_lease = accepted["lease"]
    assert isinstance(accepted_lease, dict)
    assert (accepted_lease["holder_ref"], accepted_lease["epoch"]) == (
        target_holder,
        int(offer["epoch"]) + 1,
    )
    repeated = case.execute("handoff_accept", offer, **accept, holder_quiesced=True)
    assert repeated["verdict"] == "block"
    assert "ok" not in repeated
    assert repeated["mutation"]["decision"]["verdict"] == repeated["verdict"]
    assert any("lease_holder_mismatch" in gap for gap in repeated["required_gaps"])


def _takeover_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    *,
    source_state: str,
    persist: bool = True,
) -> tuple[LeaseCase, dict[str, object], Attestation, LeaseTakeoverRequest]:
    source = "agent:test:case:source"
    target = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, name, source)
    before = case.snapshot()
    authorization = _takeover_authorization(
        before,
        branch=case.branch,
        source=source,
        target=target,
        dirty_digest=dirty_content_sha256(case.worktree),
        source_state=source_state,
    )
    if persist:
        persist_attestation(case.worktree, authorization)
    monkeypatch.setenv("ETHOS_ACTOR", target)
    return (
        case,
        before,
        authorization,
        _takeover_request(
            before,
            branch=case.branch,
            source_state=source_state,
            authorization=authorization,
            apply=True,
        ),
    )


def test_exact_takeover_changes_only_holder_generation_and_emits_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, before, _authorization, request = _takeover_case(
        tmp_path, monkeypatch, "takeover", source_state="source_lost"
    )

    report = execute_lease_takeover(root=case.worktree, request=request)

    assert report["verdict"] == "pass"
    assert report["state"] == "taken_over"
    assert report["source_state"] == "source_lost"
    after = cast("dict[str, object]", report["lease"])
    assert after["holder_ref"] == "agent:test:case:target"
    assert after["epoch"] == int(before["epoch"]) + 1
    assert after["expected_head"] == before["expected_head"]
    assert after["expected_tree"] == before["expected_tree"]
    attestation = Attestation.model_validate_json(json.dumps(report["attestation"]))
    assert attestation.predicate == "lane-resolution:takeover"
    assert attestation.effect_digest
    assert attestation.statement["output"]["source_state"] == "source_lost"


def test_exact_takeover_drift_has_zero_lease_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, before, _authorization, request = _takeover_case(
        tmp_path, monkeypatch, "takeover-drift", source_state="quiesced"
    )

    for changed in (
        {"expect_head": "f" * 40},
        {"expected_tree": "f" * 40},
        {"expected_epoch": int(before["epoch"]) + 1},
        {"expected_dirty_content_sha256": "f" * 64},
        {"target_holder_ref": "agent:test:case:other"},
        {"source_state": "source_lost"},
    ):
        report = execute_lease_takeover(
            root=case.worktree,
            request=request.model_copy(update=changed),
        )
        assert report["verdict"] in {"block", "unknown"}
        assert case.snapshot() == before


def test_exact_takeover_recovers_receipt_after_post_cas_persistence_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, before, _authorization, request = _takeover_case(
        tmp_path, monkeypatch, "takeover-recovery", source_state="source_lost"
    )
    original_persist = persist_attestation
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.lease.persist_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("simulated crash")),
    )

    with pytest.raises(OSError, match="simulated crash"):
        execute_lease_takeover(root=case.worktree, request=request)

    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.lease.persist_attestation",
        original_persist,
    )
    recovered = execute_lease_takeover(root=case.worktree, request=request)

    assert recovered["verdict"] == "pass", recovered["required_gaps"]
    assert recovered["state"] == "taken_over"
    assert recovered["lease"]["holder_ref"] == "agent:test:case:target"
    assert recovered["lease"]["epoch"] == int(before["epoch"]) + 1
    assert recovered["attestation"]


def test_exact_takeover_rejects_authorization_store_content_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, before, authorization, request = _takeover_case(
        tmp_path,
        monkeypatch,
        "takeover-authorization",
        source_state="quiesced",
        persist=False,
    )
    path = persist_attestation(case.worktree, authorization)
    path.write_text("{}", encoding="utf-8")

    report = execute_lease_takeover(root=case.worktree, request=request)

    assert report["verdict"] == "block"
    assert "lease_takeover_authorization_unaccepted" in report["required_gaps"]
    assert case.snapshot() == before


@pytest.mark.parametrize(
    "authorization_update",
    [
        {"subject": "git:branch:work/other"},
        {"commitment_digest": "f" * 64},
        {"valid_from": datetime.max.replace(tzinfo=UTC)},
        {"verdict": "block"},
    ],
)
def test_exact_takeover_rejects_wrong_or_stale_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authorization_update: dict[str, object],
) -> None:
    case, before, original, _request = _takeover_case(
        tmp_path,
        monkeypatch,
        "takeover-wrong-authorization",
        source_state="source_lost",
        persist=False,
    )
    payload = original.model_dump(
        exclude={"id", "statement_digest", "schema_version", *authorization_update}
    )
    payload.update(authorization_update)
    authorization = Attestation.issue(payload)
    persist_attestation(case.worktree, authorization)

    report = execute_lease_takeover(
        root=case.worktree,
        request=_takeover_request(
            before,
            branch=case.branch,
            source_state="source_lost",
            authorization=authorization,
            apply=True,
        ),
    )

    assert report["verdict"] == "block"
    assert case.snapshot() == before


def _takeover_authorization(
    lease: dict[str, object],
    *,
    branch: str,
    source: str,
    target: str,
    dirty_digest: str,
    source_state: str,
) -> Attestation:
    issued = datetime.now(UTC)
    authorization = {
        "branch": branch,
        "head": lease["expected_head"],
        "tree": lease["expected_tree"],
        "dirty_content_sha256": dirty_digest,
        "lane_incarnation_id": lease["lane_incarnation_id"],
        "lease_id": lease["lease_id"],
        "lease_epoch": lease["epoch"],
        "lease_payload_sha256": lease["payload_sha256"],
        "source_holder_ref": source,
        "target_holder_ref": target,
        "source_state": source_state,
    }
    return Attestation.issue(
        {
            "predicate": "lane-resolution:takeover",
            "verifier": "maintainer:test:case:reviewer",
            "subject": f"git:branch:{branch}",
            "issued_at": issued,
            "valid_from": issued,
            "verdict": "pass",
            "commitment_digest": str(lease["base_commitment_digest"]),
            "evidence_refs": ("evidence:test:takeover",),
            "statement": {"authorization": authorization},
        }
    )


def _takeover_request(
    lease: dict[str, object],
    *,
    branch: str,
    source_state: str,
    authorization: Attestation,
    apply: bool,
) -> LeaseTakeoverRequest:
    bound = cast("dict[str, object]", authorization.statement["authorization"])
    return LeaseTakeoverRequest(
        branch=branch,
        source_holder_ref=str(bound["source_holder_ref"]),
        target_holder_ref=str(bound["target_holder_ref"]),
        lease_id=str(lease["lease_id"]),
        expected_lane_incarnation_id=str(lease["lane_incarnation_id"]),
        expected_epoch=int(lease["epoch"]),
        expect_head=str(lease["expected_head"]),
        expected_tree=str(lease["expected_tree"]),
        expected_expires_at=str(lease["expires_at"]),
        expected_payload_sha256=str(lease["payload_sha256"]),
        expected_dirty_content_sha256=str(bound["dirty_content_sha256"]),
        source_state=source_state,
        authorization=authorization,
        apply=apply,
    )


def test_lease_effect_rejects_unknown_and_non_applying_requests_without_mutation(
    tmp_path: Path,
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    branch = "work/effect-boundary"
    fixture = start_adopted_work_lane(
        tmp_path / "effect-boundary", name="effect-boundary", holder_ref=holder_ref
    )
    initial = _lease_snapshot(fixture.worktree, branch)
    database = state_database(fixture.worktree)

    non_applying = _lease_request(
        operation="renew",
        branch=branch,
        holder_ref=holder_ref,
        lease=initial,
        apply=False,
    )
    with pytest.raises(ValueError, match=r"^lease_apply_required:renew$"):
        _apply_lease(database, non_applying)
    assert _lease_snapshot(fixture.worktree, branch) == initial

    unknown = _lease_request(
        operation="typo_accept",
        branch=branch,
        holder_ref=holder_ref,
        lease=initial,
        apply=True,
        target_holder_ref=target_holder_ref,
    )
    with pytest.raises(ValueError, match=r"^lease_operation_unknown:typo_accept$"):
        apply_lease_operation(
            database,
            request=unknown,
        )
    assert _lease_snapshot(fixture.worktree, branch) == initial


def test_lease_effect_enforces_expiry_cas_handoff_tokens_and_transient_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holder_ref = "agent:test:case:source"
    target_holder_ref = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, "effect-cas", holder_ref)
    initial = case.snapshot()

    with pytest.raises(ValueError, match=f"^lease_not_expired:{case.branch}$"):
        case.apply("resume", initial)

    expired = datetime.now(UTC) - timedelta(seconds=1)
    expired_payload = dict(initial["payload"])
    expired_payload.update(
        issued_at=(expired - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired - timedelta(seconds=1)).isoformat(),
        expires_at=expired.isoformat(),
    )
    with closing(sqlite3.connect(case.database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired.isoformat(), json.dumps(expired_payload, sort_keys=True), case.branch),
        )
    expired_lease = observe_lease(case.database, case.branch).record()
    with pytest.raises(ValueError, match=f"^lease_expired:{case.branch}$"):
        case.apply("renew", expired_lease)
    resumed = case.apply("resume", expired_lease)
    assert resumed["expires_at"] > expired.isoformat()

    _assert_stale_lease_dimensions(case.database, case.branch, holder_ref, resumed)

    with pytest.raises(ValueError, match=r"^holder_ref must have four non-empty segments$"):
        _apply_lease(case.database, case.request("renew", resumed, holder="invalid-holder"))

    offer = case.apply("handoff_offer", resumed, target_holder_ref=target_holder_ref)
    unquiesced = case.request(
        "handoff_accept",
        offer,
        target_holder_ref=target_holder_ref,
        offer_id=str(offer["offer_id"]),
    )
    with pytest.raises(ValueError, match=f"^lease_handoff_holder_not_quiesced:{case.branch}$"):
        _apply_lease(case.database, unquiesced)

    _assert_stale_handoff_tokens(
        case.database,
        case.branch,
        holder_ref,
        target_holder_ref,
        offer,
    )

    monkeypatch.setenv("ETHOS_ACTOR", holder_ref)
    public = case.execute("renew", offer)
    assert "receipt" not in public
    assert (public["verdict"], public["state"], public["branch"]) == (
        "pass",
        "renewed",
        case.branch,
    )
    assert "ok" not in public
    assert public["mutation"]["decision"]["verdict"] == public["verdict"]
    assert public["handoff_offer"] == {}
    assert set(public["lease"]) >= {
        "lease_id",
        "holder_ref",
        "epoch",
        "lane_ref",
        "expected_head",
        "expires_at",
        "payload_sha256",
    }


def _assert_stale_lease_dimensions(
    database: Path,
    branch: str,
    holder_ref: str,
    lease: dict[str, Any],
) -> None:
    for field, value, token in (
        ("lease_id", "lease:stale", "lease_id_stale"),
        ("expected_epoch", int(lease["epoch"]) + 1, "lease_epoch_stale"),
        ("expect_head", "f" * 40, "lease_head_stale"),
        ("expected_expires_at", "1970-01-01T00:00:00+00:00", "lease_maintenance_candidate_drift"),
        ("expected_payload_sha256", "0" * 64, "lease_maintenance_candidate_drift"),
    ):
        request = _lease_request(
            operation="renew",
            branch=branch,
            holder_ref=holder_ref,
            lease=lease,
            apply=True,
            **{field: value},
        )
        with pytest.raises(ValueError, match=f"^{token}"):
            _apply_lease(database, request)


def _assert_stale_handoff_tokens(
    database: Path,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    offer: dict[str, Any],
) -> None:
    for field, value, token in (
        ("offer_id", "handoff-offer:stale", "lease_handoff_offer_stale"),
        ("target_holder_ref", "agent:test:case:other", "lease_handoff_target_mismatch"),
    ):
        values: dict[str, object] = {
            "target_holder_ref": target_holder_ref,
            "offer_id": str(offer["offer_id"]),
            "holder_quiesced": True,
        }
        values[field] = value
        request = _lease_request(
            operation="handoff_accept",
            branch=branch,
            holder_ref=holder_ref,
            lease=offer,
            apply=True,
            **values,
        )
        with pytest.raises(ValueError, match=f"^{token}"):
            _apply_lease(database, request)

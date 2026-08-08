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
from tests.support.lifecycle_cases import assert_public_decision
from tests.support.lifecycle_cases import insert_lease_row
from tests.support.lifecycle_cases import strict_lease


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

    assert_public_decision(planned, verdict="pass", state="ready_to_retire_superseded", gaps=[])
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
    assert_public_decision(applied, verdict="pass", state="retired_superseded", gaps=[])
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
    valid = strict_lease(
        branch="work/valid",
        holder="agent:test:case:valid",
        lane_incarnation_id="lane-incarnation:valid",
        lease_id="lease:valid",
        expected_tree="c" * 40,
        base_commitment_path="openspec/changes/terminal-convergence/commitment.toml",
        base_commitment_bytes_sha256="d" * 64,
        base_commitment_digest="b" * 64,
        expires_at=now + timedelta(hours=1),
    )
    insert_lease_row(database, valid)
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
    insert_lease_row(database, expired)
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
    insert_lease_row(
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
    insert_lease_row(
        database,
        mismatch,
        row_expires_at=(mismatch.expires_at + timedelta(minutes=1)).isoformat(),
    )
    assert observe_lease(database, mismatch.lane_ref).state == "unknown"


def test_lease_transition_matrix_preserves_binding_and_rejects_invalid_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "agent:test:case:source"
    target = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, "transition-matrix", source)
    initial = case.snapshot()
    payload = dict(initial["payload"])
    payload["path_scope"] = ["src/**", "tests/**"]
    with closing(sqlite3.connect(case.database)) as connection, connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True), case.branch),
        )
    initial = case.snapshot()

    renewed = case.apply("renew", initial)
    _assert_reissue_changes(initial, renewed, "renewed_at", "expires_at")
    offered = case.apply("handoff_offer", renewed, target_holder_ref=target)
    _assert_reissue_changes(renewed, offered, "handoff")
    accepted = case.apply(
        "handoff_accept",
        offered,
        target_holder_ref=target,
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
        request=case.request("advance", accepted, holder=target),
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

    monkeypatch.setattr(
        lease_transitions,
        "replace_exact_lease_from_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError),
    )
    with pytest.raises(ValueError, match="expected_head"):
        advance_lease_ref(
            case.database,
            request=case.request("advance", advanced, holder=target),
            binding={
                "expected_head": "invalid-head",
                "expected_tree": advanced["expected_tree"],
                "base_commitment_path": advanced["base_commitment_path"],
                "base_commitment_bytes_sha256": advanced[
                    "base_commitment_bytes_sha256"
                ],
                "base_commitment_digest": advanced["base_commitment_digest"],
            },
        )
    stable = case.snapshot()
    assert {key: stable[key] for key in advanced} == advanced

    for request, error in (
        (case.request("renew", advanced, apply=False, holder=target), "lease_apply_required"),
        (case.request("typo_accept", advanced, holder=target), "lease_operation_unknown"),
    ):
        with pytest.raises(ValueError, match=error):
            _apply_lease(case.database, request)
        assert case.snapshot() == stable


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
    assert_public_decision(ready, verdict="pass", state="ready_to_retire_superseded", gaps=[])

    retired = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )
    assert_public_decision(retired, verdict="pass", state="retired_superseded", gaps=[])
    assert not source.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert (
        git(repo, "show-ref", "--verify", "--hash", f"refs/heads/{successor_branch}")
        == successor_head
    )
    assert observe_lease(database, successor_branch).state == "valid"
    assert observe_lease(database, "work/superseded").state == "missing"


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

    assert_public_decision(report, verdict="pass", state="retired_superseded", gaps=[])
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

    assert_public_decision(report, verdict="pass", state="retired_superseded", gaps=[])
    assert not source.exists()
    assert git(repo, "branch", "--list", "work/superseded") == ""
    assert observe_lease(database, "work/superseded").state == "missing"


def test_lease_public_transition_matrix_enforces_actor_cas_and_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_holder = "agent:test:case:source"
    target_holder = "agent:test:case:target"
    case = LeaseCase.start(tmp_path, "lease", source_holder)
    initial = case.snapshot()

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    wrong_actor = case.execute("renew", initial)
    assert_public_decision(wrong_actor, verdict="block")
    assert "lease_actor_mismatch" in wrong_actor["required_gaps"]

    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    renewed = case.execute("renew", initial)
    assert_public_decision(renewed, verdict="pass")
    renewed_lease = renewed["lease"]
    assert isinstance(renewed_lease, dict)
    offered = case.execute("handoff_offer", renewed_lease, target_holder_ref=target_holder)
    assert_public_decision(offered, verdict="pass")
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
    assert_public_decision(not_quiesced, verdict="block")
    assert "holder_quiescence_confirmation_required" in not_quiesced["required_gaps"]
    accepted = case.execute("handoff_accept", offer, **accept, holder_quiesced=True)
    assert_public_decision(accepted, verdict="pass")
    accepted_lease = accepted["lease"]
    assert isinstance(accepted_lease, dict)
    assert (accepted_lease["holder_ref"], accepted_lease["epoch"]) == (
        target_holder,
        int(offer["epoch"]) + 1,
    )
    repeated = case.execute("handoff_accept", offer, **accept, holder_quiesced=True)
    assert_public_decision(repeated, verdict="block")
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

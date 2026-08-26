from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
from contextlib import closing
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

import ethos.adapters.mutation.lane_lifecycle.lease as lease_lifecycle
import ethos.adapters.mutation.lane_retirement.effects as retirement_effects
import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
import ethos.adapters.repo.git_effects as git_effects
import ethos.adapters.store.state.lease.lifecycle.transitions as lease_transitions
import tests.support.governed_repository as governed_repository
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_takeover
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.hook.activation import install_hook_launchers
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
from tests.support.literal_cases import literal_case
from tests.support.semantic import attestation_fixture

SOURCE = "agent:test:case:source"
TARGET = "agent:test:case:target"
BRANCH = "work/superseded"


class LeaseCase:
    def __init__(self, worktree: Path, branch: str, holder: str) -> None:
        self.worktree, self.branch, self.holder = (worktree, branch, holder)
        self.database = state_database(worktree)

    @classmethod
    def start(cls, tmp_path: Path, name: str, holder: str = SOURCE) -> LeaseCase:
        fixture = start_adopted_work_lane(tmp_path / name, name=name, holder_ref=holder)
        return cls(fixture.worktree, f"work/{name}", holder)

    def snapshot(self) -> dict[str, object]:
        return leases_by_branch(self.worktree)[self.branch]

    def request(
        self, operation: str, lease: dict[str, object], *, apply: bool = True, **values: object
    ) -> LeaseOperationRequest:
        payload: dict[str, object] = {
            "operation": operation,
            "branch": self.branch,
            "holder_ref": values.pop("holder_ref", self.holder),
            "lease_id": lease["lease_id"],
            "expected_epoch": lease["epoch"],
            "expect_head": lease["expected_head"],
            "expected_expires_at": lease["expires_at"],
            "expected_payload_sha256": lease["payload_sha256"],
            "apply": apply,
            **values,
        }
        return LeaseOperationRequest.model_validate(payload)

    def apply(
        self, operation: str, lease: dict[str, object], **values: object
    ) -> dict[str, object]:
        return apply_lease_operation(
            self.database, request=self.request(operation, lease, **values)
        )

    def execute(
        self, operation: str, lease: dict[str, object], **values: object
    ) -> dict[str, object]:
        return execute_lease_operation(
            root=self.worktree, request=self.request(operation, lease, **values)
        )


class LeaseTransitionMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "state.sqlite"
        self.binding = {
            "expected_head": "a" * 40,
            "expected_tree": "b" * 40,
            "base_commitment_path": "openspec/changes/example/commitment.toml",
            "base_commitment_bytes_sha256": "c" * 64,
            "base_commitment_digest": "d" * 64,
        }
        acquire_lease(
            self.database,
            lease=strict_lease(
                branch="work/model",
                holder="agent:test:case:first",
                lane_incarnation_id="lane-incarnation:model",
                lease_id="lease:model",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                **self.binding,
            ),
        )

    def teardown(self) -> None:
        self.temporary_directory.cleanup()

    def snapshot(self) -> dict[str, Any]:
        return observe_lease(self.database, "work/model").record()

    def request(self, operation: str, **values: object) -> LeaseOperationRequest:
        lease = self.snapshot()
        return LeaseOperationRequest.model_validate(
            {
                "operation": operation,
                "branch": "work/model",
                "holder_ref": lease["holder_ref"],
                "lease_id": lease["lease_id"],
                "expected_epoch": lease["epoch"],
                "expect_head": lease["expected_head"],
                "expected_expires_at": lease["expires_at"],
                "expected_payload_sha256": lease["payload_sha256"],
                "apply": True,
                **values,
            }
        )

    @rule()
    def renew(self) -> None:
        before = self.snapshot()
        after = apply_lease_operation(
            self.database, request=self.request("renew", ttl_seconds=3600)
        )
        assert (after["holder_ref"], after["epoch"]) == (before["holder_ref"], before["epoch"])

    @rule()
    def offer(self) -> None:
        before = self.snapshot()
        target = (
            "agent:test:case:second"
            if before["holder_ref"] == "agent:test:case:first"
            else "agent:test:case:first"
        )
        after = apply_lease_operation(
            self.database, request=self.request("handoff_offer", target_holder_ref=target)
        )
        assert (after["holder_ref"], after["epoch"]) == (before["holder_ref"], before["epoch"])

    @precondition(lambda self: bool(self.snapshot()["payload"]["handoff"]))
    @rule()
    def accept(self) -> None:
        before = self.snapshot()
        handoff = cast("dict[str, object]", before["payload"]["handoff"])
        after = apply_lease_operation(
            self.database,
            request=self.request(
                "handoff_accept",
                target_holder_ref=handoff["target_holder_ref"],
                offer_id=handoff["offer_id"],
                holder_quiesced=True,
                ttl_seconds=3600,
            ),
        )
        assert (after["holder_ref"], after["epoch"], after["payload"]["handoff"]) == (
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
            apply_lease_operation(self.database, request=request)
        assert self.snapshot() == before

    @invariant()
    def identity_and_binding_are_preserved(self) -> None:
        lease = self.snapshot()
        assert (lease["lease_id"], lease["lane_ref"]) == ("lease:model", "work/model")
        assert all(lease[field] == value for field, value in self.binding.items())


TestLeaseTransitionMachine = LeaseTransitionMachine.TestCase
TestLeaseTransitionMachine.settings = settings(
    deadline=None, max_examples=20, stateful_step_count=12
)


def _retirement_request(
    head: str, absorbed_by: str, *, apply: bool = False
) -> LinkedRetirementRequest:
    return LinkedRetirementRequest(
        branch=BRANCH,
        expect_head=head,
        absorbed_by=absorbed_by,
        reason="accepted tree contains the obsolete delta",
        authorize=True,
        apply=apply,
    )


def _assert_retired(repo: Path, source: Path, database: Path) -> None:
    assert (
        source.exists(),
        git(repo, "branch", "--list", BRANCH),
        observe_lease(database, BRANCH).state,
    ) == (False, "", "missing")


def test_landed_retirement_readiness_and_apply_share_exact_ref_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(governed_repository, "install_hook_launchers", lambda _root: {})
    monkeypatch.setattr(lane_start_carrier, "install_hook_launchers", lambda _root: {})
    fixture = start_adopted_work_lane(tmp_path, name="landed", holder_ref=SOURCE)
    branch = "work/landed"
    head = git(fixture.worktree, "rev-parse", "HEAD")
    git(fixture.repository, "merge", "--ff-only", branch)
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    request = LinkedRetirementRequest(
        branch=branch,
        expect_head=head,
        authorize=True,
    )

    planned = retire_linked_work_lane(
        root=fixture.repository,
        mode="landed",
        request=request,
    )
    assert_public_decision(planned, verdict="pass", state="planned", gaps=[])

    applied = retire_linked_work_lane(
        root=fixture.worktree,
        mode="landed",
        request=request.model_copy(update={"apply": True}),
    )
    assert_public_decision(applied, verdict="pass", state="retired", gaps=[])
    assert not fixture.worktree.exists()
    assert git(fixture.repository, "branch", "--list", branch) == ""
    assert observe_lease(state_database(fixture.repository), branch).state == "missing"


def _assert_reissue(before: dict[str, object], after: dict[str, object], *changed: str) -> None:
    old, new = (dict(before["payload"]), dict(after["payload"]))
    assert set(old) == set(new) == set(LaneLease.model_fields)
    assert {field for field in old if old[field] != new[field]} == set(changed)


def _successor(
    tmp_path: Path, repo: Path, source: Path, database: Path, head: str
) -> tuple[Path, str, str]:
    source_lease = LaneLease.from_payload(dict(leases_by_branch(source)[BRANCH]["payload"]))
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", (BRANCH,))
    branch, successor = ("work/campaign", tmp_path / "campaign")
    git(repo, "worktree", "add", "-b", branch, successor.as_posix(), head)
    acquire_lease(
        database,
        lease=source_lease.model_copy(
            update={
                "lane_incarnation_id": "lane-incarnation:campaign",
                "lease_id": "lease:campaign",
                "lane_ref": branch,
                "holder_ref": HolderRef.parse(SOURCE),
            }
        ),
    )
    return (
        successor,
        branch,
        commit_fixture_file(successor, "campaign.txt", "campaign\n", "continue campaign"),
    )


def _retire_through_successor(
    tmp_path: Path,
    repo: Path,
    source: Path,
    head: str,
    accepted: str,
    database: Path,
) -> None:
    successor, branch, absorbed = _successor(tmp_path, repo, source, database, head)
    blocked = retire_linked_work_lane(
        root=repo, mode="superseded", request=_retirement_request(head, accepted)
    )
    assert blocked["required_gaps"] == [
        "foreign_work_lane_retire_authority_required",
        "work_lane_missing_lease:work/superseded",
    ]
    request = _retirement_request(head, absorbed)
    ready = retire_linked_work_lane(root=successor, mode="superseded", request=request)
    assert_public_decision(ready, verdict="pass", state="ready_to_retire_superseded", gaps=[])
    applied = retire_linked_work_lane(
        root=successor,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )
    assert_public_decision(applied, verdict="pass", state="retired_superseded", gaps=[])
    assert git(repo, "show-ref", "--verify", "--hash", f"refs/heads/{branch}") == absorbed
    assert observe_lease(database, branch).state == "valid"
    _assert_retired(repo, source, database)


def _reject_failed_ref_cas(
    repo: Path,
    source: Path,
    head: str,
    accepted: str,
    database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before, original = leases_by_branch(source)[BRANCH], git_effects.run_git

    def fail_ref(root: Path, *args: str, **kwargs: Any):
        if args[:2] == ("update-ref", "--stdin"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "forced ref failure")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(git_effects, "run_git", fail_ref)
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=_retirement_request(head, accepted, apply=True),
    )
    assert report["verdict"] == "block"
    assert git(source, "branch", "--show-current") == BRANCH
    assert git(repo, "rev-parse", BRANCH) == head
    assert leases_by_branch(source)[BRANCH] == before
    assert observe_lease(database, BRANCH).state == "valid"


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("control-root", "retirement_control_root_stale"),
        ("dirty-reobservation", "work_lane_dirty"),
        ("worktree-remove", "worktree_remove_failed"),
    ],
)
def test_retirement_public_failure_matrix_preserves_lane_and_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    gap: str,
) -> None:
    repo, source, head, accepted, database = superseded_work_lane(
        tmp_path / failure, holder_ref=SOURCE
    )
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    before = leases_by_branch(source)[BRANCH]
    if failure == "control-root":
        observed = retirement_effects.output

        def stale_control(root: Path, *args: str) -> str | None:
            if root == repo and args == ("symbolic-ref", "--short", "HEAD"):
                return "candidate/dev"
            return observed(root, *args)

        monkeypatch.setattr(retirement_effects, "output", stale_control)
    elif failure == "dirty-reobservation":
        run_git = retirement_effects.run_git

        def dirty_lane(root: Path, *args: str, **kwargs: object) -> object:
            if root == source and args == ("status", "--porcelain", "--untracked-files=all"):
                return subprocess.CompletedProcess(args, 0, " M drift\n", "")
            return run_git(root, *args, **kwargs)

        monkeypatch.setattr(retirement_effects, "run_git", dirty_lane)
    else:
        monkeypatch.setattr(
            retirement_effects,
            "remove_worktree",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("remove rejected")),
        )

    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=_retirement_request(head, accepted, apply=True),
    )

    assert report["verdict"] == "block"
    assert gap in report["required_gaps"]
    assert (source.is_dir(), git(repo, "rev-parse", BRANCH)) == (True, head)
    assert leases_by_branch(source)[BRANCH] == before
    assert observe_lease(database, BRANCH).state == "valid"


@pytest.mark.parametrize(
    ("scenario", "accepted_state", "source_state", "gaps"),
    [
        (
            "accepted-moved",
            "moved",
            "expected",
            {"accepted_ref_changed_after_worktree_removed"},
        ),
        (
            "states-unavailable",
            "unavailable",
            "unavailable",
            {
                "accepted_ref_state_unavailable_after_worktree_removed",
                "retirement_ref_state_unavailable_after_worktree_removed",
            },
        ),
        (
            "restore-fails",
            "expected",
            "expected",
            {
                "branch_delete_failed_after_worktree_removed",
                "worktree_restore_failed_after_ref_transition",
            },
        ),
    ],
)
def test_retirement_ref_failure_reports_observation_and_compensation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    accepted_state: str,
    source_state: str,
    gaps: set[str],
) -> None:
    repo, source, head, accepted, database = superseded_work_lane(
        tmp_path / accepted_state, holder_ref=SOURCE
    )
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    before = leases_by_branch(source)[BRANCH]
    run_git = git_effects.run_git

    def fail_ref(root: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("update-ref", "--stdin"):
            return subprocess.CompletedProcess(["git", *args], 1, "", "forced ref failure")
        return run_git(root, *args, **kwargs)

    def ref_state(_root: Path, branch: str, _head: str) -> str:
        return accepted_state if branch == "dev" else source_state

    monkeypatch.setattr(git_effects, "run_git", fail_ref)
    monkeypatch.setattr(retirement_effects, "ref_outcome", ref_state)
    if scenario == "restore-fails":
        monkeypatch.setattr(
            retirement_effects,
            "add_worktree",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("restore rejected")),
        )

    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=_retirement_request(head, accepted, apply=True),
    )

    assert report["verdict"] == "block"
    assert gaps <= set(report["required_gaps"])
    assert report["worktree_restored"] is (
        source_state == "expected" and scenario != "restore-fails"
    )
    if scenario == "restore-fails":
        assert report["worktree_restoration"] == {
            "state": "blocked",
            "error": "restore rejected",
        }
    elif source_state == "expected":
        assert report["worktree_restoration"]["state"] in {"applied", "recognized"}
    assert git(repo, "rev-parse", BRANCH) == head
    assert leases_by_branch(repo)[BRANCH] == before
    assert observe_lease(database, BRANCH).state == "valid"


def _observe_uncertain_commit(
    repo: Path,
    source: Path,
    head: str,
    accepted: str,
    database: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    commit_applied: bool,
) -> None:
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
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=_retirement_request(head, accepted, apply=True),
    )
    observed = report["retired"] if commit_applied else report["observed"]
    assert observed["ref_state"] == observed["worktree_state"] == "absent"
    assert not source.exists()
    expected = ("pass", "missing") if commit_applied else ("block", "valid")
    assert (report["verdict"], observed["lease_state"]) == expected
    if commit_applied:
        assert report["state"] == "retired_superseded"
    else:
        assert observe_lease(database, BRANCH).state == "valid"


def _retire_through_installed_hook(
    tmp_path: Path,
    repo: Path,
    source: Path,
    head: str,
    accepted: str,
    database: Path,
    *,
    through_successor: bool,
) -> None:
    invocation, successor_branch = repo, None
    if through_successor:
        invocation, successor_branch, accepted = _successor(tmp_path, repo, source, database, head)
    install_hook_launchers(repo)
    if invocation != repo:
        install_hook_launchers(invocation)
    exclude = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("tools/\n", encoding="utf-8")
    raw = subprocess.run(
        ["git", "update-ref", "-d", f"refs/heads/{BRANCH}", head],
        cwd=invocation,
        check=False,
        capture_output=True,
        text=True,
    )
    assert raw.returncode != 0
    assert git(repo, "rev-parse", BRANCH) == head
    report = retire_linked_work_lane(
        root=invocation,
        mode="superseded",
        request=_retirement_request(head, accepted, apply=True),
    )
    assert_public_decision(report, verdict="pass", state="retired_superseded", gaps=[])
    assert not source.exists()
    assert git(repo, "branch", "--list", BRANCH) == ""
    assert observe_lease(database, successor_branch or BRANCH).state == (
        "valid" if successor_branch else "missing"
    )


@pytest.mark.parametrize(
    "mode",
    ["exact", "extra", "stale"],
    ids=[
        "test_linked_leased_archive_equivalent_carrier_retires_atomically",
        "test_archive_equivalent_retirement_rejects_extra_source_delta",
        "test_archive_equivalent_retirement_rechecks_absorption_before_effect",
    ],
)
def test_archive_retirement_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    holder = "agent:test:case:archive"
    repo, lane, source_head, _, database = superseded_work_lane(
        tmp_path, holder_ref=holder, absorbed=False
    )
    active = lane / "openspec/changes/fixture-change"
    archive = repo / "openspec/changes/archive/2026-08-08-fixture-change"
    archive.mkdir(parents=True)
    for name in ("proposal.md", "commitment.toml"):
        (archive / name).write_bytes((active / name).read_bytes())
    git(repo, "add", archive.relative_to(repo).as_posix())
    git(repo, "commit", "-m", "archive fixture carrier")
    accepted = git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    if mode == "extra":
        report = retire_linked_work_lane(
            root=repo, mode="superseded", request=_retirement_request(source_head, accepted)
        )
        assert report["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
        assert lane.exists()
        assert git(repo, "rev-parse", BRANCH) == source_head
        assert observe_lease(database, BRANCH).state == "valid"
        return
    git(repo, "rm", "-r", "openspec/changes/fixture-change")
    git(repo, "commit", "-m", "retire active carrier")
    accepted = git(repo, "rev-parse", "HEAD")
    git(lane, "reset", "--hard", accepted)
    active.mkdir(parents=True)
    for name in ("proposal.md", "commitment.toml"):
        (active / name).write_bytes((archive / name).read_bytes())
    git(lane, "add", active.relative_to(lane).as_posix())
    git(lane, "commit", "-m", "reconstruct active carrier")
    source_head = git(lane, "rev-parse", "HEAD")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", (BRANCH,))
    acquire_lease(
        database,
        lease=exact_lease(
            repo=lane,
            branch=BRANCH,
            holder_ref=holder,
            expected_head=source_head,
            carrier="openspec/changes/fixture-change/commitment.toml",
            change_id="fixture-change",
        ),
    )
    request = _retirement_request(source_head, accepted)
    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)
    paths = planned["lane"]["archive_absorption"]["paths"]
    assert_public_decision(planned, verdict="pass", state="ready_to_retire_superseded", gaps=[])
    for name in ("commitment.toml", "proposal.md"):
        source = f"openspec/changes/fixture-change/{name}"
        assert paths[source] == {
            "target": f"openspec/changes/archive/2026-08-08-fixture-change/{name}",
            "blob": git(repo, "rev-parse", f"{source_head}:{source}"),
        }
    if mode == "stale":
        observed, calls = retirement_effects.archived_carrier_absorption, [0]

        def stale_after_planning(*args: object, **kwargs: object) -> dict[str, object]:
            calls[0] += 1
            return observed(*args, **kwargs) if calls[0] == 1 else {}

        monkeypatch.setattr(retirement_effects, "archived_carrier_absorption", stale_after_planning)
        applied = retire_linked_work_lane(
            root=repo, mode="superseded", request=request.model_copy(update={"apply": True})
        )
        assert applied["required_gaps"] == ["retirement_archive_absorption_stale"]
        assert (lane.is_dir(), git(repo, "rev-parse", BRANCH)) == (True, source_head)
        assert observe_lease(database, BRANCH).state == "valid"
        return
    applied = retire_linked_work_lane(
        root=repo, mode="superseded", request=request.model_copy(update={"apply": True})
    )
    assert_public_decision(applied, verdict="pass", state="retired_superseded", gaps=[])
    _assert_retired(repo, lane, database)


def test_lease_observation_keeps_valid_expired_unknown_and_missing_distinct(tmp_path: Path) -> None:
    database, now = (tmp_path / "state.sqlite", datetime.now(UTC))
    missing = observe_lease(database, "work/missing")
    assert (missing.state, missing.lease, missing.row) == ("missing", None, None)
    valid = strict_lease(
        branch="work/valid",
        holder="agent:test:case:valid",
        lane_incarnation_id="lane-incarnation:valid",
        lease_id="lease:valid",
        expected_tree="c" * 40,
        base_commitment_path="openspec/changes/example/commitment.toml",
        base_commitment_bytes_sha256="d" * 64,
        base_commitment_digest="b" * 64,
        expires_at=now + timedelta(hours=1),
    )
    insert_lease_row(database, valid)
    observed = observe_lease(database, valid.lane_ref)
    assert (observed.state, observed.lease) == ("valid", valid)
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
    legacy = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:legacy",
            "lease_id": "lease:legacy",
            "lane_ref": "work/legacy",
        }
    )
    payload = valid.to_payload() | {"claim_id": "retired"}
    payload.pop("base_commitment_digest")
    insert_lease_row(
        database,
        legacy,
        payload=payload
        | {
            "lane_incarnation_id": legacy.lane_incarnation_id,
            "lease_id": legacy.lease_id,
            "lane_ref": legacy.lane_ref,
        },
    )
    unknown = observe_lease(database, legacy.lane_ref)
    assert (unknown.state, unknown.lease, unknown.row.id) == ("unknown", None, legacy.lease_id)
    assert len(unknown.row.payload_sha256) == 64
    assert unknown.record()["error"] == "lane_lease_payload_fields_invalid"
    mismatch = valid.model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:mismatch",
            "lease_id": "lease:mismatch",
            "lane_ref": "work/mismatch",
        }
    )
    insert_lease_row(
        database, mismatch, row_expires_at=(mismatch.expires_at + timedelta(minutes=1)).isoformat()
    )
    assert observe_lease(database, mismatch.lane_ref).state == "unknown"


def test_lease_transition_matrix_preserves_binding_and_rejects_invalid_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = LeaseCase.start(tmp_path, "transition")
    initial = case.snapshot()
    renewed = case.apply("renew", initial)
    _assert_reissue(initial, renewed, "renewed_at", "expires_at")
    offered = case.apply("handoff_offer", renewed, target_holder_ref=TARGET)
    _assert_reissue(renewed, offered, "handoff")
    accepted = case.apply(
        "handoff_accept",
        offered,
        target_holder_ref=TARGET,
        offer_id=offered["offer_id"],
        holder_quiesced=True,
    )
    _assert_reissue(offered, accepted, "holder_ref", "epoch", "renewed_at", "expires_at", "handoff")
    binding = {
        "expected_head": "c" * 40,
        "expected_tree": "d" * 40,
        "base_commitment_path": "records/change/commitment.toml",
        "base_commitment_bytes_sha256": "e" * 64,
        "base_commitment_digest": "f" * 64,
    }
    advanced = advance_lease_ref(
        case.database, request=case.request("advance", accepted, holder_ref=TARGET), binding=binding
    )
    _assert_reissue(accepted, advanced, *binding)
    monkeypatch.setattr(
        lease_transitions,
        "replace_exact_lease_from_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError),
    )
    with pytest.raises(ValueError, match="expected_head"):
        advance_lease_ref(
            case.database,
            request=case.request("advance", advanced, holder_ref=TARGET),
            binding=binding | {"expected_head": "invalid-head"},
        )
    stable = case.snapshot()
    assert {key: stable[key] for key in advanced} == advanced
    stale = case.request("renew", advanced, holder_ref=TARGET).model_copy(
        update={"expected_epoch": int(advanced["epoch"]) + 1}
    )
    for request, error in (
        (stale, "^lease_epoch_stale:"),
        (case.request("renew", advanced, apply=False, holder_ref=TARGET), "lease_apply_required"),
        (case.request("typo_accept", advanced, holder_ref=TARGET), "lease_operation_unknown"),
    ):
        with pytest.raises(ValueError, match=error):
            apply_lease_operation(case.database, request=request)
        assert case.snapshot() == stable


def test_lease_transition_failure_matrix_preserves_exact_generation(tmp_path: Path) -> None:
    case = LeaseCase.start(tmp_path, "transition-failures")
    initial = case.snapshot()
    requests = (
        (case.request("resume", initial), f"lease_not_expired:{case.branch}"),
        (
            case.request("renew", initial).model_copy(
                update={"expected_expires_at": "1970-01-01T00:00:00+00:00"}
            ),
            "lease_maintenance_candidate_drift",
        ),
        (
            case.request("renew", initial).model_copy(update={"expected_payload_sha256": "0" * 64}),
            "lease_maintenance_candidate_drift",
        ),
    )
    for request, gap in requests:
        with pytest.raises(ValueError, match=gap):
            apply_lease_operation(case.database, request=request)
        assert case.snapshot() == initial

    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    payload = dict(initial["payload"])
    payload.update(
        issued_at=(expired_at - timedelta(seconds=2)).isoformat(),
        renewed_at=(expired_at - timedelta(seconds=1)).isoformat(),
        expires_at=expired_at.isoformat(),
    )
    with closing(sqlite3.connect(case.database)) as connection, connection:
        connection.execute(
            "update leases set expires_at = ?, payload_json = ? where subject = ?",
            (expired_at.isoformat(), json.dumps(payload, sort_keys=True), case.branch),
        )
    expired = case.snapshot()
    with pytest.raises(ValueError, match=f"lease_expired:{case.branch}"):
        case.apply("renew", expired)
    resumed = case.apply("resume", expired)
    assert resumed["expires_at"] > expired_at.isoformat()

    with pytest.raises(ValueError, match="lease_handoff_offer_missing"):
        case.apply(
            "handoff_accept",
            resumed,
            target_holder_ref=TARGET,
            offer_id="handoff-offer:missing",
            holder_quiesced=True,
        )
    offered = case.apply("handoff_offer", resumed, target_holder_ref=TARGET)
    offered_snapshot = case.snapshot()
    for update, gap in (
        ({"offer_id": "handoff-offer:stale"}, "lease_handoff_offer_stale"),
        ({"target_holder_ref": "agent:test:case:other"}, "lease_handoff_target_mismatch"),
    ):
        values = {
            "target_holder_ref": TARGET,
            "offer_id": offered["offer_id"],
            "holder_quiesced": True,
            **update,
        }
        with pytest.raises(ValueError, match=gap):
            case.apply("handoff_accept", offered, **values)
        assert case.snapshot() == offered_snapshot


@pytest.mark.parametrize(
    ("state", "gap"),
    [
        ("missing", "work_lane_missing_lease"),
        ("unknown", "lease_unknown"),
    ],
)
def test_lease_public_missing_and_unknown_rows_fail_closed(
    tmp_path: Path, state: str, gap: str
) -> None:
    case = LeaseCase.start(tmp_path, f"lease-{state}")
    current = case.snapshot()
    with closing(sqlite3.connect(case.database)) as connection, connection:
        if state == "missing":
            connection.execute("delete from leases where subject = ?", (case.branch,))
        else:
            connection.execute(
                "update leases set payload_json = ? where subject = ?",
                ("{}", case.branch),
            )

    report = execute_lease_operation(root=case.worktree, request=case.request("renew", current))

    assert report["verdict"] == ("unknown" if state == "unknown" else "block")
    assert any(gap in item for item in report["required_gaps"])


def test_lease_storage_cas_rejects_identity_and_row_drift(tmp_path: Path) -> None:
    case = LeaseCase.start(tmp_path, "storage-cas")
    current = case.snapshot()
    offered = case.apply("handoff_offer", current, target_holder_ref=TARGET)
    binding = {
        "expected_head": current["expected_head"],
        "expected_tree": current["expected_tree"],
        "base_commitment_path": current["base_commitment_path"],
        "base_commitment_bytes_sha256": current["base_commitment_bytes_sha256"],
        "base_commitment_digest": current["base_commitment_digest"],
    }
    with pytest.raises(ValueError, match=f"lease_handoff_pending:{case.branch}"):
        lease_transitions.rebind_lease_commitment(
            case.database,
            request=case.request("advance", offered),
            binding=binding,
        )

    with closing(sqlite3.connect(case.database)) as connection:
        connection.execute("begin immediate")
        row, current_lease = lease_transitions.expected_current_lease(
            connection,
            request=case.request("renew", offered),
            require_expired=False,
        )
        replacement = strict_lease(
            branch="work/other",
            lane_incarnation_id=offered["lane_incarnation_id"],
            lease_id=offered["lease_id"],
        )
        with pytest.raises(ValueError, match="lease_reissue_identity_mismatch"):
            lease_transitions.replace_exact_lease_from_connection(
                connection, current=row, replacement=replacement
            )
        connection.execute("delete from leases where subject = ?", (case.branch,))
        with pytest.raises(ValueError, match="lease_maintenance_candidate_drift"):
            lease_transitions.replace_exact_lease_from_connection(
                connection,
                current=row,
                replacement=current_lease,
            )


@pytest.mark.parametrize(
    "claim",
    literal_case(
        "lanes.lease.test_lease_lifecycle:parametrize:test_retirement_authority_transaction_matrix:0"
    ),
)
def test_retirement_authority_transaction_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claim: str
) -> None:
    repo, source, head, accepted, database = superseded_work_lane(
        tmp_path / claim, holder_ref=SOURCE
    )
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    if claim.startswith("test_missing"):
        _retire_through_successor(tmp_path, repo, source, head, accepted, database)
        return
    if claim.startswith("test_direct"):
        _reject_failed_ref_cas(repo, source, head, accepted, database, monkeypatch)
        return
    if "commit_error" in claim:
        _observe_uncertain_commit(
            repo,
            source,
            head,
            accepted,
            database,
            monkeypatch,
            commit_applied=claim.endswith("[after]"),
        )
        return
    _retire_through_installed_hook(
        tmp_path,
        repo,
        source,
        head,
        accepted,
        database,
        through_successor=claim.startswith("test_successor"),
    )


def test_lease_public_transition_matrix_enforces_actor_cas_and_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = LeaseCase.start(tmp_path, "lease")
    initial = case.snapshot()
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong")
    assert_public_decision(wrong := case.execute("renew", initial), verdict="block")
    assert "lease_actor_mismatch" in wrong["required_gaps"]
    monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    renewed_report = case.execute("renew", initial)
    assert_public_decision(renewed_report, verdict="pass")
    renewed = cast("dict[str, object]", renewed_report["lease"])
    offered = case.execute("handoff_offer", renewed, target_holder_ref=TARGET)
    assert_public_decision(offered, verdict="pass")
    offer = cast("dict[str, object]", offered["handoff_offer"])
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    values = {"target_holder_ref": TARGET, "offer_id": offer["offer_id"]}
    blocked = case.execute("handoff_accept", offer, **values, holder_quiesced=False)
    assert_public_decision(blocked, verdict="block")
    assert "holder_quiescence_confirmation_required" in blocked["required_gaps"]
    accepted = case.execute("handoff_accept", offer, **values, holder_quiesced=True)
    assert_public_decision(accepted, verdict="pass")
    lease = cast("dict[str, object]", accepted["lease"])
    assert (lease["holder_ref"], lease["epoch"]) == (TARGET, int(offer["epoch"]) + 1)
    repeated = case.execute("handoff_accept", offer, **values, holder_quiesced=True)
    assert any("lease_holder_mismatch" in gap for gap in repeated["required_gaps"])
    assert_public_decision(repeated, verdict="block")


def _takeover_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claim: str):
    state = "quiesced" if "drift" in claim or "content_mismatch" in claim else "source_lost"
    case, issued = (LeaseCase.start(tmp_path, claim), datetime.now(UTC))
    before = case.snapshot()
    bound = {
        "branch": case.branch,
        "head": before["expected_head"],
        "tree": before["expected_tree"],
        "dirty_content_sha256": dirty_content_sha256(case.worktree),
        "lane_incarnation_id": before["lane_incarnation_id"],
        "lease_id": before["lease_id"],
        "lease_epoch": before["epoch"],
        "lease_payload_sha256": before["payload_sha256"],
        "source_holder_ref": SOURCE,
        "target_holder_ref": TARGET,
        "source_state": state,
    }
    auth = attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="maintainer:test:case:reviewer",
        subject=f"git:branch:{case.branch}",
        issued_at=issued,
        valid_from=issued,
        payload_kind="authorization:lane-takeover",
        payload_body={"authorization": bound},
        commitment_digest=str(before["base_commitment_digest"]),
        evidence_refs=("evidence:test:takeover",),
    )
    if "content_mismatch" not in claim and "wrong_or_stale" not in claim:
        record_attestations(case.worktree, (auth,))
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    request = LeaseTakeoverRequest(
        branch=case.branch,
        source_holder_ref=SOURCE,
        target_holder_ref=TARGET,
        lease_id=str(before["lease_id"]),
        expected_lane_incarnation_id=str(before["lane_incarnation_id"]),
        expected_epoch=int(before["epoch"]),
        expect_head=str(before["expected_head"]),
        expected_tree=str(before["expected_tree"]),
        expected_expires_at=str(before["expires_at"]),
        expected_payload_sha256=str(before["payload_sha256"]),
        expected_dirty_content_sha256=str(bound["dirty_content_sha256"]),
        source_state=state,
        authorization=auth,
        apply=True,
    )
    return (case, before, auth, request)


def test_lease_takeover_ignores_unrelated_attestation_with_same_effect_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case, _before, _authorization, request = _takeover_case(tmp_path, monkeypatch, "changes_only")
    original_issue = lease_lifecycle.issue_native_effect
    unrelated: Attestation | None = None

    def issue_with_unrelated(*args, **kwargs):
        nonlocal unrelated
        candidate = original_issue(*args, **kwargs)
        payload = candidate.model_dump(mode="python", exclude={"id", "subject"})
        payload["subject"] = "git:branch:work/unrelated"
        unrelated = Attestation.issue(payload)
        record_attestations(case.worktree, (unrelated,))
        return candidate

    monkeypatch.setattr(lease_lifecycle, "issue_native_effect", issue_with_unrelated)

    report = execute_lease_takeover(root=case.worktree, request=request)

    assert unrelated is not None
    assert report["attestation"]["id"] != unrelated.id
    assert report["attestation"]["subject"] != unrelated.subject


@pytest.mark.parametrize(
    "claim",
    literal_case("lanes.lease.test_lease_lifecycle:parametrize:test_exact_takeover_claim_matrix:1"),
)
def test_exact_takeover_claim_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claim: str
) -> None:
    case, before, auth, request = _takeover_case(tmp_path, monkeypatch, claim)
    if "changes_only" in claim:
        report = execute_lease_takeover(root=case.worktree, request=request)
        after = cast("dict[str, object]", report["lease"])
        assert (report["verdict"], report["state"], report["source_state"]) == (
            "pass",
            "taken_over",
            "source_lost",
        )
        assert (after["holder_ref"], after["epoch"]) == (TARGET, int(before["epoch"]) + 1)
        assert (after["expected_head"], after["expected_tree"]) == (
            before["expected_head"],
            before["expected_tree"],
        )
        _root, selected = read_attestation_set(case.worktree)
        attestation = next(item for item in selected if item.id == report["attestation"]["id"])
        assert attestation.predicate == "lane-resolution:takeover"
        assert attestation.effect_digest
        assert attestation.payload.body["output"]["source_state"] == "source_lost"
    elif "drift" in claim:
        updates = (
            {"expect_head": "f" * 40},
            {"expected_tree": "f" * 40},
            {"expected_epoch": int(before["epoch"]) + 1},
            {"expected_dirty_content_sha256": "f" * 64},
            {"target_holder_ref": "agent:test:case:other"},
            {"source_state": "source_lost"},
        )
        for update in updates:
            report = execute_lease_takeover(
                root=case.worktree, request=request.model_copy(update=update)
            )
            assert report["verdict"] in {"block", "unknown"}
            assert case.snapshot() == before
    elif "persistence_failure" in claim:
        interrupted_id = ""

        def interrupt(_root: Path, attestations: tuple[Attestation, ...]) -> None:
            nonlocal interrupted_id
            interrupted_id = attestations[0].id
            message = "simulated crash"
            raise OSError(message)

        with monkeypatch.context() as context:
            context.setattr(lease_lifecycle, "record_attestations", interrupt)
            with pytest.raises(OSError, match="simulated crash"):
                execute_lease_takeover(root=case.worktree, request=request)
        recovered = execute_lease_takeover(root=case.worktree, request=request)
        assert (recovered["verdict"], recovered["state"]) == ("pass", "taken_over")
        assert (recovered["lease"]["holder_ref"], recovered["lease"]["epoch"]) == (
            TARGET,
            int(before["epoch"]) + 1,
        )
        assert recovered["attestation"]["id"] == interrupted_id
    elif "content_mismatch" in claim:
        record_attestations(case.worktree, (auth,))
        report = execute_lease_takeover(root=case.worktree, request=request)
        assert (report["verdict"], report["state"]) == ("pass", "taken_over")
        assert report["lease"]["holder_ref"] == TARGET
    else:
        report = execute_lease_takeover(root=case.worktree, request=request)
        assert "lease_takeover_authorization_unaccepted" in report["required_gaps"]
        assert case.snapshot() == before
        updates: tuple[dict[str, object], ...] = (
            {"subject": "git:branch:work/other"},
            {"commitment_digest": "f" * 64},
            {"valid_from": datetime.max.replace(tzinfo=UTC)},
            {"verdict": "block"},
        )
        for update in updates:
            payload = auth.model_dump(mode="python", exclude={"id", *update})
            payload.update(update)
            if update.get("verdict") == "block":
                payload["payload"] = {
                    "kind": auth.payload.kind,
                    "body": {
                        **dict(auth.payload.body),
                        "required_gaps": ("test_authorization_blocked",),
                    },
                }
            wrong = Attestation.issue(payload)
            record_attestations(case.worktree, (wrong,))
            report = execute_lease_takeover(
                root=case.worktree, request=request.model_copy(update={"authorization": wrong})
            )
            assert (report["verdict"], case.snapshot()) == ("block", before)


@pytest.mark.parametrize("drift_at", ["before-cas", "after-cas"])
def test_public_takeover_repository_drift_rolls_back_exact_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift_at: str,
) -> None:
    case, before, _auth, request = _takeover_case(
        tmp_path, monkeypatch, f"repository-drift-{drift_at}"
    )
    observed = dirty_content_sha256
    calls = 0

    def drift(root: Path) -> str:
        nonlocal calls
        calls += 1
        digest = observed(root)
        if calls == (2 if drift_at == "before-cas" else 3):
            return "f" * 64
        return digest

    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.lease.dirty_content_sha256",
        drift,
    )

    report = execute_lease_takeover(root=case.worktree, request=request)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_takeover_repository_drift"]
    assert case.snapshot() == before

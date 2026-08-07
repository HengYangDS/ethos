"""Accepted-ref move admission — the reference-transaction boundary.

`ref_move_admission_report` is the reducer bound to git's reference-transaction hook:
it decides whether a LOCAL ref update (merge/reset/branch -f/commit) to a protected
role may proceed. The candidate train's load-bearing invariant is that the accepted
branch only ever advances to the LIVE candidate head, by a fast-forward, carrying a
complete executed proof. These tests hold that boundary — the raw-git escapes it must
block and the sanctioned closeout path it must still admit — split out of
test_hook_admission.py so each file stays a cohesive, bounded contract suite.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.transitions as transitions
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_FIXTURE_COMMITMENT_CARRIER = "openspec/changes/fixture-change/commitment.toml"
_HOLDER = "agent:codex:thread:first"


def _acquire_fixture_lease(repo: Path, branch: str, head: str, holder: str):
    return acquire_lease(
        state_database(repo),
        lease=exact_lease(
            repo=repo,
            branch=branch,
            holder_ref=holder,
            expected_head=head,
            carrier=_FIXTURE_COMMITMENT_CARRIER,
        ),
    )


def _leased_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    candidate = tmp_path / "repo-candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    lane = tmp_path / "repo-work-current"
    git(repo, "worktree", "add", "-b", "work/current", lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    lease = _acquire_fixture_lease(repo, "work/current", head, _HOLDER)
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    return repo, candidate, lane, head, lease


def _poison_lease(database: Path, branch: str, lease: dict[str, object]) -> str:
    payload = dict(lease["payload"])
    payload["retired_field"] = "retired"
    raw = json.dumps(payload, sort_keys=True)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("update leases set payload_json = ? where subject = ?", (raw, branch))
        connection.commit()
    return raw


def _advance_candidate(repo: Path, name: str) -> str:
    """Commit one fixture path on the currently checked-out candidate."""
    (repo / name).write_text(name, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("old_value", "new_value"),
    [
        ("a" * 40, "0" * 40),
        ("a" * 64, "0" * 64),
        ("0" * 40, "a" * 40),
        ("0" * 64, "a" * 64),
    ],
)
def test_work_lane_ref_transition_rejects_zero_oid_without_lease(
    tmp_path: Path, old_value: str, new_value: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/doomed",
        old_value=old_value,
        new_value=new_value,
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["work_lane_missing_lease:work/doomed"]


def test_lane_start_uses_the_work_lane_creation_intent_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/zero-bound"
    head = git(repo, "rev-parse", "HEAD")
    _acquire_fixture_lease(repo, branch, head, "agent:test:case:zero-bound")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:zero-bound")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40,
        new_value=head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_create_no_ref_intent"]
    update = GitRefUpdate(expected="0" * 40, desired=head)
    intent = write_ref_intent(
        root=repo,
        ref_name=f"refs/heads/{branch}",
        update=update,
        operation="lane.start",
        plan_digest=canonical_json_digest({"operation": "lane.start"}),
    )
    admitted = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value=update.expected,
        new_value=update.desired,
    )

    assert admitted["verdict"] == "pass"
    assert admitted["decision"] == {"action": "allow", "reason": "lane_creation_saga_started"}
    assert intent["nonce"]


def test_work_lane_ref_deletion_requires_ref_intent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/zero-bound"
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", branch, head)
    database = state_database(repo)
    _acquire_fixture_lease(repo, branch, head, "agent:test:case:zero-bound")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:zero-bound")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name=f"refs/heads/{branch}",
        old_value=head,
        new_value="0" * 40,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_delete_no_ref_intent"]
    assert git(repo, "rev-parse", branch) == head
    assert observe_lease(database, branch).state == "valid"


@pytest.mark.parametrize("case", ["create", "delete"])
def test_work_lane_ref_transition_committed_accepts_observed_zero_oid_terminal_state(
    tmp_path: Path,
    case: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    branch = "work/terminal"
    if case == "create":
        git(repo, "branch", branch, head)
    report = work_lane_ref_transition_report(
        root=repo,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40 if case == "create" else head,
        new_value=head if case == "create" else "0" * 40,
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "admitted"
    assert report["decision"] == {
        "action": "allow",
        "reason": "lane_ref_terminal_state_observed",
    }


def test_work_lane_zero_oid_unknown_lease_is_observe_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch = "work/unknown-create"
    head = git(repo, "rev-parse", "HEAD")
    database = state_database(repo)
    lease = _acquire_fixture_lease(repo, branch, head, "agent:test:case:unknown-create")
    raw_payload = _poison_lease(database, branch, lease)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:unknown-create")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value="0" * 40,
        new_value=head,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == [f"work_lane_lease_unknown:{branch}"]
    with closing(sqlite3.connect(database)) as connection:
        stored = connection.execute(
            "select payload_json from leases where subject = ?", (branch,)
        ).fetchone()[0]
    assert stored == raw_payload


@pytest.mark.parametrize("width", [0, 1, 39, 41, 63, 65])
def test_work_lane_ref_transition_rejects_invalid_oid(tmp_path: Path, width: int) -> None:
    repo = init_git_repo(tmp_path / "repo")
    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/doomed",
        old_value="a" * (width or 40),
        new_value="0" * width,
    )
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["work_lane_ref_oid_invalid"]


def test_work_lane_ref_transition_admits_noop_without_lease(tmp_path: Path) -> None:
    """A worktree setup can reassert a just-created lane ref at its existing HEAD before
    the lane lease is recorded.  This is no state transition and must not be blocked by
    the lease guard."""
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "branch", "work/starting", "dev")
    head = git(repo, "rev-parse", "work/starting")

    report = work_lane_ref_transition_report(
        root=repo,
        phase="prepared",
        ref_name="refs/heads/work/starting",
        old_value=head,
        new_value=head,
    )

    assert report["verdict"] == "pass"
    assert report["decision"] == {"action": "allow", "reason": "lane_ref_noop"}


def test_work_lane_ref_transition_prepared_checks_holder_generation_and_old_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    target = _advance_candidate(candidate, "target")

    def unexpected_workspace_status(_root: Path) -> dict[str, object]:
        message = "work-lane ref transition must not build full workspace status"
        raise AssertionError(message)

    monkeypatch.setattr(transitions, "workspace_status", unexpected_workspace_status, raising=False)

    report = transitions.work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )
    assert report["verdict"] == "pass"
    assert report["decision"]["action"] == "allow"
    assert report["lease"]["epoch"] == 1

    stale = transitions.work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value="c" * 40,
        new_value=target,
    )
    assert stale["verdict"] == "block"
    assert stale["required_gaps"] == [f"lane_ref_observation_stale:{'c' * 40}!={head}"]


def test_work_lane_ref_transition_committed_advances_local_lease_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    new_head = _advance_candidate(candidate, "target")
    git(repo, "update-ref", "refs/heads/work/current", new_head, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=new_head,
    )
    assert report["verdict"] == "pass"
    assert report["state"] == "lease_ref_advanced"
    assert report["lease"]["expected_head"] == new_head
    assert report["lease"]["expected_tree"] == git(repo, "rev-parse", f"{new_head}^{{tree}}")


def test_work_lane_ref_transition_rebinds_one_exact_carrier_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, initial = _leased_lane(tmp_path, monkeypatch)
    relocated = "records/fixture-change/commitment.toml"
    (candidate / relocated).parent.mkdir(parents=True)
    git(candidate, "mv", _FIXTURE_COMMITMENT_CARRIER, relocated)
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "relocate commitment carrier",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "pass", report
    assert report["state"] == "lease_ref_advanced"
    rebound = report["lease"]
    assert rebound["expected_head"] == target
    assert rebound["expected_tree"] == git(repo, "rev-parse", f"{target}^{{tree}}")
    assert rebound["base_commitment_path"] == relocated
    assert rebound["base_commitment_bytes_sha256"] == initial["base_commitment_bytes_sha256"]
    assert rebound["base_commitment_digest"] == initial["base_commitment_digest"]
    assert rebound["payload_sha256"] != initial["payload_sha256"]
    assert {
        name for name in initial["payload"] if initial["payload"][name] != rebound["payload"][name]
    } == {"expected_head", "expected_tree", "base_commitment_path"}


@pytest.mark.parametrize("case", ["content_change", "non_unique"])
def test_work_lane_ref_transition_rejects_inexact_carrier_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    repo, candidate, lane, head, initial = _leased_lane(tmp_path, monkeypatch)
    relocated = candidate / "records/fixture-change/commitment.toml"
    relocated.parent.mkdir(parents=True)
    git(candidate, "mv", _FIXTURE_COMMITMENT_CARRIER, relocated.relative_to(candidate).as_posix())
    if case == "non_unique":
        duplicate_path = candidate / "records/fixture-change-copy/commitment.toml"
        duplicate_path.parent.mkdir(parents=True)
        shutil.copyfile(relocated, duplicate_path)
        git(candidate, "add", duplicate_path.relative_to(candidate).as_posix())
    else:
        relocated.write_text(
            relocated.read_text(encoding="utf-8").replace(
                "Exercise the governed fixture lifecycle.",
                "Rewrite the governed fixture lifecycle.",
            ),
            encoding="utf-8",
        )
        git(candidate, "add", relocated.relative_to(candidate).as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "relocate commitment carrier inexactly",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_base_commitment_path_mismatch"]
    stored = leases_by_branch(lane)["work/current"]
    assert (stored["expected_head"], stored["expected_tree"], stored["base_commitment_path"]) == (
        initial["expected_head"],
        initial["expected_tree"],
        initial["base_commitment_path"],
    )
    assert stored["payload_sha256"] == initial["payload_sha256"]


def test_work_lane_ref_transition_committed_rejects_unmoved_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    new_head = _advance_candidate(candidate, "target")

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=new_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [f"lane_ref_observation_stale:{new_head}!={head}"]
    lease = leases_by_branch(lane)["work/current"]
    assert (lease["expected_head"], lease["expected_tree"]) == (
        head,
        git(repo, "rev-parse", f"{head}^{{tree}}"),
    )


def test_work_lane_ref_transition_blocks_target_with_rewritten_base_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, lane, head, _lease = _leased_lane(tmp_path, monkeypatch)
    commitment = candidate / "openspec" / "changes" / "fixture-change" / "commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Rewrite the governed fixture lifecycle.",
        ),
        encoding="utf-8",
    )
    git(candidate, "add", commitment.relative_to(candidate).as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "rewrite base commitment",
    )
    target = git(candidate, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/heads/work/current", target, head)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="committed",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value=target,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lease_base_commitment_bytes_mismatch"]
    assert leases_by_branch(lane)["work/current"]["expected_head"] == head


def test_work_lane_ref_transition_rejects_unknown_lease_without_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _candidate, lane, head, lease = _leased_lane(tmp_path, monkeypatch)
    database = state_database(repo)
    _poison_lease(database, "work/current", lease)

    report = work_lane_ref_transition_report(
        root=lane,
        phase="prepared",
        ref_name="refs/heads/work/current",
        old_value=head,
        new_value="b" * 40,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["work_lane_lease_unknown:work/current"]

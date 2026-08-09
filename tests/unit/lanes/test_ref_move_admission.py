"""Claim-preserving matrix for Work Lane ref intent, lease, and policy."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.transitions as transitions
from ethos.adapters.admission.ref_intent import write_ref_intent
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

_CARRIER = "openspec/changes/fixture-change/commitment.toml"
_HOLDER = "agent:codex:thread:first"


def _lease(repo: Path, branch: str, head: str, holder: str = _HOLDER):
    item = exact_lease(
        repo=repo, branch=branch, holder_ref=holder, expected_head=head, carrier=_CARRIER
    )
    return acquire_lease(state_database(repo), lease=item)


def _lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    candidate, lane = tmp_path / "candidate", tmp_path / "lane"
    git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), "dev")
    git(repo, "worktree", "add", "-b", "work/current", str(lane), "dev")
    head = git(lane, "rev-parse", "HEAD")
    lease = _lease(repo, "work/current", head)
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    return repo, candidate, lane, head, lease


def _commit(repo: Path, name: str = "target") -> str:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "-m", name)
    return git(repo, "rev-parse", "HEAD")


def _report(root: Path, phase: str, old: str, new: str, branch: str):
    return transitions.work_lane_ref_transition_report(
        root=root, phase=phase, ref_name=f"refs/heads/{branch}", old_value=old, new_value=new
    )


def _expect(report: dict[str, object], verdict: str, gap: str | None = None) -> None:
    assert report["verdict"] == verdict
    if gap:
        assert report["required_gaps"] == [gap]


def _assert_lease_unchanged(stored: dict[str, object], initial: dict[str, object]) -> None:
    assert stored["expected_head"] == initial["expected_head"]
    assert stored["expected_tree"] == initial["expected_tree"]
    assert stored["base_commitment_path"] == initial["base_commitment_path"]
    assert stored["base_commitment_bytes_sha256"] == initial["base_commitment_bytes_sha256"]
    assert stored["base_commitment_digest"] == initial["base_commitment_digest"]
    assert stored["payload_sha256"] == initial["payload_sha256"]


@pytest.mark.parametrize(
    ("old", "new", "verdict", "gap", "reason"),
    [
        ("a" * 40, "0" * 40, "block", "work_lane_missing_lease:work/doomed", None),
        ("a" * 64, "0" * 64, "block", "work_lane_missing_lease:work/doomed", None),
        ("0" * 40, "a" * 40, "block", "work_lane_missing_lease:work/doomed", None),
        ("0" * 64, "a" * 64, "block", "work_lane_missing_lease:work/doomed", None),
        *(
            ("a" * (n or 40), "0" * n, "block", "work_lane_ref_oid_invalid", None)
            for n in (0, 1, 39, 41, 63, 65)
        ),
        ("HEAD", "HEAD", "pass", None, "lane_ref_noop"),
    ],
)
def test_prepared_ref_shape_matrix(
    tmp_path: Path, old: str, new: str, verdict: str, gap: str | None, reason: str | None
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    report = _report(
        repo,
        "prepared",
        head if old == "HEAD" else old,
        head if new == "HEAD" else new,
        "work/starting" if reason else "work/doomed",
    )
    _expect(report, verdict, gap)
    if reason:
        assert report["decision"]["reason"] == reason
    else:
        assert "ok" not in report


@pytest.mark.parametrize("case", ["create", "delete", "unknown"])
def test_committed_zero_oid_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head, zero, branch = git(repo, "rev-parse", "HEAD"), "0" * 40, "work/terminal"
    if case == "unknown":
        commit_active_commitment(repo)
        head = git(repo, "rev-parse", "HEAD")
        holder = "agent:test:case:unknown-create"
        initial = _lease(repo, branch, head, holder)
        payload = dict(initial["payload"])
        payload["retired_field"] = "retired"
        raw = json.dumps(payload, sort_keys=True)
        database = state_database(repo)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute(
                "update leases set payload_json = ? where subject = ?", (raw, branch)
            )
            connection.commit()
        monkeypatch.setenv("ETHOS_ACTOR", holder)
        _expect(
            _report(repo, "committed", zero, head, branch),
            "unknown",
            f"work_lane_lease_unknown:{branch}",
        )
        with closing(sqlite3.connect(database)) as connection:
            stored = connection.execute(
                "select payload_json from leases where subject = ?", (branch,)
            ).fetchone()[0]
        assert stored == raw
        return
    if case == "create":
        git(repo, "branch", branch, head)
    old, new = (zero, head) if case == "create" else (head, zero)
    report = _report(repo, "committed", old, new, branch)
    _expect(report, "pass")
    assert report["state"] == "admitted"
    assert report["decision"]["reason"] == "lane_ref_terminal_state_observed"


@pytest.mark.parametrize("case", ["create", "delete"])
def test_ref_intent_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    branch, holder = "work/zero-bound", "agent:test:case:zero-bound"
    head, zero = git(repo, "rev-parse", "HEAD"), "0" * 40
    _lease(repo, branch, head, holder)
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    if case == "delete":
        git(repo, "branch", branch, head)
        _expect(
            _report(repo, "prepared", head, zero, branch),
            "block",
            "work_lane_ref_delete_no_ref_intent",
        )
        assert git(repo, "rev-parse", branch) == head
        assert observe_lease(state_database(repo), branch).state == "valid"
        return
    _expect(
        _report(repo, "prepared", zero, head, branch), "block", "work_lane_ref_create_no_ref_intent"
    )
    update = GitRefUpdate(expected=zero, desired=head)
    intent = write_ref_intent(
        root=repo,
        ref_name=f"refs/heads/{branch}",
        update=update,
        operation="lane.start",
        plan_digest=canonical_json_digest({"operation": "lane.start"}),
    )
    report = _report(repo, "prepared", zero, head, branch)
    _expect(report, "pass")
    assert report["decision"]["reason"] == "lane_creation_saga_started"
    assert intent["nonce"]


@pytest.mark.parametrize("case", ["prepared", "moved", "unmoved", "unknown"])
def test_lease_transition_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    repo, candidate, lane, head, initial = _lane(tmp_path, monkeypatch)
    target = _commit(candidate)
    if case == "unknown":
        payload = dict(initial["payload"])
        payload["retired_field"] = "retired"
        raw = json.dumps(payload, sort_keys=True)
        with closing(sqlite3.connect(state_database(repo))) as connection:
            connection.execute(
                "update leases set payload_json = ? where subject = ?", (raw, "work/current")
            )
            connection.commit()
        _expect(
            _report(lane, "prepared", head, target, "work/current"),
            "unknown",
            "work_lane_lease_unknown:work/current",
        )
        return
    if case == "prepared":
        monkeypatch.setattr(
            transitions, "workspace_status", lambda _root: pytest.fail("status"), raising=False
        )
        report = _report(lane, "prepared", head, target, "work/current")
        _expect(report, "pass")
        assert report["decision"]["action"] == "allow"
        assert report["lease"]["epoch"] == 1
        stale = "c" * 40
        _expect(
            _report(lane, "prepared", stale, target, "work/current"),
            "block",
            f"lane_ref_observation_stale:{stale}!={head}",
        )
        return
    if case == "moved":
        git(repo, "update-ref", "refs/heads/work/current", target, head)
    report = _report(lane, "committed", head, target, "work/current")
    stored = leases_by_branch(lane)["work/current"]
    if case == "unmoved":
        _expect(report, "block", f"lane_ref_observation_stale:{target}!={head}")
        _assert_lease_unchanged(stored, initial)
    else:
        _expect(report, "pass")
        assert report["state"] == "lease_ref_advanced"
        assert stored["expected_head"] == target
        assert stored["expected_tree"] == git(repo, "rev-parse", f"{target}^{{tree}}")


@pytest.mark.parametrize("case", ["exact", "content", "duplicate", "rewrite"])
def test_commitment_policy_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    repo, candidate, lane, head, initial = _lane(tmp_path, monkeypatch)
    relocated = candidate / "records/fixture-change/commitment.toml"
    if case == "rewrite":
        relocated = candidate / _CARRIER
    else:
        relocated.parent.mkdir(parents=True)
        git(candidate, "mv", _CARRIER, str(relocated.relative_to(candidate)))
    if case in {"content", "rewrite"}:
        relocated.write_text(relocated.read_text().replace("Exercise", "Rewrite"))
        git(candidate, "add", str(relocated.relative_to(candidate)))
    if case == "duplicate":
        duplicate = candidate / "records/fixture-change-copy/commitment.toml"
        duplicate.parent.mkdir(parents=True)
        shutil.copyfile(relocated, duplicate)
        git(candidate, "add", str(duplicate.relative_to(candidate)))
    target = _commit(candidate, "marker")
    git(repo, "update-ref", "refs/heads/work/current", target, head)
    report = _report(lane, "committed", head, target, "work/current")
    stored = leases_by_branch(lane)["work/current"]
    if case in {"content", "duplicate"}:
        _expect(report, "block", "lease_base_commitment_path_mismatch")
        _assert_lease_unchanged(stored, initial)
    elif case == "rewrite":
        _expect(report, "block", "lease_base_commitment_bytes_mismatch")
        _assert_lease_unchanged(stored, initial)
    else:
        _expect(report, "pass")
        assert report["state"] == "lease_ref_advanced"
        assert stored["expected_head"] == target
        assert stored["expected_tree"] == git(repo, "rev-parse", f"{target}^{{tree}}")
        assert stored["base_commitment_path"] == str(relocated.relative_to(candidate))
        assert stored["base_commitment_bytes_sha256"] == initial["base_commitment_bytes_sha256"]
        assert stored["base_commitment_digest"] == initial["base_commitment_digest"]
        assert stored["payload_sha256"] != initial["payload_sha256"]
        assert {
            name
            for name in initial["payload"]
            if initial["payload"][name] != stored["payload"][name]
        } == {"expected_head", "expected_tree", "base_commitment_path"}

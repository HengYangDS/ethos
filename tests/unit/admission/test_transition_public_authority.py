from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.transitions as transitions
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import commit_active_commitment
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_BRANCH = "work/current"
_CARRIER = "openspec/changes/fixture-change/commitment.toml"
_HOLDER = "agent:test:case:transition-authority"


def _lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_commitment(repo)
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", "-b", _BRANCH, lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repo),
        lease=exact_lease(
            repo=repo,
            branch=_BRANCH,
            holder_ref=_HOLDER,
            expected_head=head,
            carrier=_CARRIER,
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    return repo, lane, head


def _target_commit(lane: Path, head: str, *, parent: str | None = None) -> str:
    carrier = lane / _CARRIER
    carrier.write_text(carrier.read_text().replace("Exercise", "Refine"), encoding="utf-8")
    git(lane, "add", _CARRIER)
    tree = git(lane, "write-tree")
    return git(
        lane,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        tree,
        "-p",
        parent or head,
        "-m",
        "refine commitment",
    )


def _intent(lane: Path, old: str, new: str) -> None:
    write_ref_intent(
        root=lane,
        ref_name=f"refs/heads/{_BRANCH}",
        update=GitRefUpdate(expected=old, desired=new),
        operation="commitment.rebind",
        plan_digest=canonical_json_digest({"operation": "commitment.rebind"}),
    )


def _report(lane: Path, phase: str, old: str, new: str) -> dict[str, object]:
    return transitions.work_lane_ref_transition_report(
        root=lane,
        phase=phase,
        ref_name=f"refs/heads/{_BRANCH}",
        old_value=old,
        new_value=new,
    )


@pytest.mark.parametrize(
    ("phase", "reason", "state"),
    [
        ("prepared", "commitment_rebind_admitted", "admitted"),
        ("committed", "commitment_rebind_pending", "commitment_rebind_pending"),
        ("aborted", "commitment_rebind_aborted", "admitted"),
    ],
)
def test_commitment_rebind_transition_requires_exact_intent_and_cas_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    reason: str,
    state: str,
) -> None:
    repo, lane, head = _lane(tmp_path, monkeypatch)
    target = _target_commit(lane, head)
    _intent(lane, head, target)
    if phase == "committed":
        assert _report(lane, "prepared", head, target)["verdict"] == "pass"
        git(repo, "update-ref", f"refs/heads/{_BRANCH}", target, head)

    report = _report(lane, phase, head, target)

    assert report["verdict"] == "pass"
    assert report["state"] == state
    assert report["decision"] == {"action": "allow", "reason": reason}


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("parent", "commitment_rebind_target_parent_mismatch"),
        ("index", "commitment_rebind_index_tree_mismatch"),
    ],
)
def test_commitment_rebind_transition_blocks_stale_target_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected: str,
) -> None:
    _repo, lane, head = _lane(tmp_path, monkeypatch)
    parent = git(lane, "rev-parse", f"{head}^") if case == "parent" else head
    target = _target_commit(lane, head, parent=parent)
    _intent(lane, head, target)
    if case == "index":
        (lane / "unexpected.txt").write_text("drift\n", encoding="utf-8")
        git(lane, "add", "unexpected.txt")

    report = _report(lane, "prepared", head, target)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [expected]
    assert report["decision"]["action"] == "block"


def test_committed_ref_transition_reports_lease_cas_failure_without_false_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane, head = _lane(tmp_path, monkeypatch)
    (lane / "change.txt").write_text("change\n", encoding="utf-8")
    git(lane, "add", "change.txt")
    tree = git(lane, "write-tree")
    target = git(
        lane,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        tree,
        "-p",
        head,
        "-m",
        "advance lane",
    )
    git(repo, "update-ref", f"refs/heads/{_BRANCH}", target, head)
    initial = leases_by_branch(lane)[_BRANCH]

    def stale_lease(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = "lease_epoch_mismatch"
        raise ValueError(message)

    monkeypatch.setattr(transitions, "advance_lease_ref", stale_lease)
    report = _report(lane, "committed", head, target)

    assert report["verdict"] == "block"
    assert report["state"] == "repair_required"
    assert report["decision"] == {"action": "block", "reason": "lease_ref_update_failed"}
    assert report["required_gaps"] == ["lease_epoch_mismatch"]
    assert leases_by_branch(lane)[_BRANCH]["payload_sha256"] == initial["payload_sha256"]

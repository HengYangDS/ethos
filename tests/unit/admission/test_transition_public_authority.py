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
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_BRANCH = "work/current"
_TASKS = "openspec/changes/fixture-change/tasks.md"
_HOLDER = "agent:test:case:transition-authority"


def _lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo)
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", "-b", _BRANCH, lane.as_posix(), "dev")
    head = git(lane, "rev-parse", "HEAD")
    acquire_lease(
        state_database(repo),
        lease=exact_lease(
            branch=_BRANCH,
            holder_ref=_HOLDER,
        ),
    )
    monkeypatch.setenv("ETHOS_ACTOR", _HOLDER)
    return repo, lane, head


def _target_commit(lane: Path, head: str, *, parent: str | None = None) -> str:
    tasks = lane / _TASKS
    tasks.write_text(tasks.read_text().replace("Exercise", "Refine"), encoding="utf-8")
    git(lane, "add", _TASKS)
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
        "refine change",
    )


def _intent(lane: Path, old: str, new: str) -> None:
    write_ref_intent(
        root=lane,
        ref_name=f"refs/heads/{_BRANCH}",
        update=GitRefUpdate(expected=old, desired=new),
        operation="repository.effect",
        plan_digest=canonical_json_digest({"operation": "repository.effect"}),
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
        ("prepared", "executor_ref_intent_admitted", "admitted"),
    ],
)
def test_executor_ref_transition_requires_exact_intent_and_cas_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    reason: str,
    state: str,
) -> None:
    _repo, lane, head = _lane(tmp_path, monkeypatch)
    target = _target_commit(lane, head)
    _intent(lane, head, target)
    report = _report(lane, phase, head, target)

    assert report["verdict"] == "pass"
    assert report["state"] == state
    assert report["decision"] == {"action": "allow", "reason": reason}


def test_owned_ref_change_without_executor_intent_uses_general_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, lane, head = _lane(tmp_path, monkeypatch)
    target = _target_commit(lane, head)

    report = _report(lane, "prepared", head, target)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["decision"] == {
        "action": "allow",
        "reason": "work_lane_ref_transition_admitted",
    }


@pytest.mark.parametrize("case", ["parent", "index"])
def test_executor_intent_owns_target_coordinates_without_lease_payload_duplication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    _repo, lane, head = _lane(tmp_path, monkeypatch)
    parent = git(lane, "rev-parse", f"{head}^") if case == "parent" else head
    target = _target_commit(lane, head, parent=parent)
    _intent(lane, head, target)
    if case == "index":
        (lane / "unexpected.txt").write_text("drift\n", encoding="utf-8")
        git(lane, "add", "unexpected.txt")

    report = _report(lane, "prepared", head, target)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["decision"] == {
        "action": "allow",
        "reason": "executor_ref_intent_admitted",
    }


@pytest.mark.parametrize("phase", ["committed", "aborted"])
def test_terminal_ref_transition_only_observes_git_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    repo, lane, head = _lane(tmp_path, monkeypatch)
    lease_before = leases_by_branch(lane)[_BRANCH]
    target = _target_commit(lane, head)
    _intent(lane, head, target)
    if phase == "committed":
        assert _report(lane, "prepared", head, target)["verdict"] == "pass"
        git(repo, "update-ref", f"refs/heads/{_BRANCH}", target, head)

    report = _report(lane, phase, head, target)

    assert report["verdict"] == "pass"
    assert report["state"] == "admitted"
    assert report["decision"] == {"action": "allow", "reason": f"{phase}_observed"}
    assert report["lease"] == {}
    assert leases_by_branch(lane)[_BRANCH] == lease_before

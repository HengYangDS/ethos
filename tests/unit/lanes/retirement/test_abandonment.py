from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.abandonment as abandonment
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.fixture
def divergent_lane(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    lane = tmp_path / "repo-work-abandon"
    git(repo, "worktree", "add", "-b", "work/abandon", str(lane), "dev")
    for root, name in ((repo, "accepted"), (lane, "abandoned")):
        (root / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        commit_fixture(root, f"advance {name} independently")
    actor = "agent:test:case:abandonment-recovery"
    acquire_lease(state_database(repo), lease=exact_lease(branch="work/abandon", holder_ref=actor))
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    return repo, lane


def _derive(repo: Path, **updates: str):
    return abandonment.derive_lane_abandonment(
        root=repo,
        branch=updates.get("branch", "work/abandon"),
        reason_code=updates.get("reason_code", "superseded-experiment"),
        reason=updates.get("reason", "discard divergent experiment"),
    )


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("branch", "lane_abandonment_branch_invalid"),
        ("missing", "lane_abandonment_coordinates_unavailable"),
        ("control", "retirement_control_root_unavailable"),
        ("absorbed", "lane_abandonment_divergence_required"),
        ("descendant", "lane_abandonment_divergence_required"),
        ("ambiguous", "lane_abandonment_worktree_ambiguous"),
        ("dirty", "lane_abandonment_worktree_not_clean"),
        ("lease", "work_lane_lease_missing"),
        ("actor", "invocation_actor_missing"),
        ("foreign", "foreign_work_lane_retire_authority_required"),
        ("code", "lane_abandonment_reason_invalid"),
        ("reason", "lane_abandonment_reason_invalid"),
        ("mode", "lane_retirement_receipt_mode_invalid"),
    ],
)
def test_abandonment_rejects_invalid_current_facts_without_effects(
    divergent_lane, monkeypatch, fault, gap
):
    repo, lane = divergent_lane
    valid = _derive(repo)
    assert valid["state"] == "derived", valid
    receipt = valid["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    arguments = {}
    if fault in {"branch", "missing"}:
        arguments["branch"] = "dev" if fault == "branch" else "work/missing"
    elif fault == "control":
        git(repo, "switch", "-c", "other")
    elif fault in {"absorbed", "descendant"}:
        target = (
            request.head if fault == "absorbed" else git(repo, "merge-base", "dev", request.head)
        )
        git(repo, "reset", "--hard", target)
    elif fault == "ambiguous":
        status = abandonment.workspace_status(repo)
        worktrees = status["worktrees"]
        assert isinstance(worktrees, list)
        row = next(row for row in worktrees if row["branch"] == "work/abandon")
        worktrees.append(dict(row))
        monkeypatch.setattr(abandonment, "workspace_status", lambda _root: status)
    elif fault == "dirty":
        (lane / "abandoned.txt").write_text("preserve uncommitted work\n", encoding="utf-8")
    elif fault == "lease":
        operation.revoke_operation_lease(repo, request)
    elif fault in {"actor", "foreign"}:
        monkeypatch.setenv("ETHOS_ACTOR", "" if fault == "actor" else "agent:test:case:foreign")
    elif fault in {"code", "reason"}:
        arguments["reason_code" if fault == "code" else "reason"] = (
            "INVALID" if fault == "code" else " "
        )
    else:
        receipt = operation.persist_operation(repo, request.model_copy(update={"mode": "landed"}))

    def state():
        return (
            git(repo, "show-ref"),
            git(repo, "worktree", "list", "--porcelain"),
            (lane / "abandoned.txt").read_bytes(),
            observe_lease(state_database(repo), "work/abandon"),
            tuple(sorted(operation.operation_store(repo).iterdir())),
        )

    before = state()
    receipt_path, receipt_sha256 = receipt["path"], receipt["sha256"]
    assert isinstance(receipt_path, str)
    assert isinstance(receipt_sha256, str)
    report = (
        abandonment.execute_lane_abandonment(
            root=repo,
            receipt_path=receipt_path,
            receipt_sha256=receipt_sha256,
            apply=True,
            authorized=True,
        )
        if fault == "mode"
        else _derive(repo, **arguments)
    )
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]
    assert state() == before


def test_abandonment_apply_requires_authorization_before_loading_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        abandonment,
        "load_operation",
        lambda *_args: pytest.fail("unauthorized abandonment must not load or execute"),
    )

    report = abandonment.execute_lane_abandonment(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=False,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required"]


def test_real_abandonment_recovers_after_worktree_removal_and_git_spawn_failure(
    divergent_lane, monkeypatch
):
    repo, lane = divergent_lane
    head = git(lane, "rev-parse", "HEAD")
    derived = _derive(repo)
    assert derived["state"] == "derived", derived
    assert "ethos lane retire abandon" in derived["next_action"]
    receipt = derived["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    assert request.mode == "abandon"
    assert request.effects == ("remove_worktree", "delete_ref", "revoke_lease")
    assert request.head == head
    assert request.tree == git(lane, "rev-parse", "HEAD^{tree}")
    assert operation.persist_operation(repo, request) == receipt
    written = []
    persist = operation.persist_progress

    def record(root, request, progress):
        written.append(progress.completed_effects)
        return persist(root, request, progress)

    monkeypatch.setattr(operation, "persist_progress", record)
    original = operation.delete_operation_ref
    monkeypatch.setattr(
        operation,
        "delete_operation_ref",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_process_spawn_failed")),
    )

    partial = abandonment.execute_lane_abandonment(
        root=repo,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert written == [(), ("remove_worktree",), ("remove_worktree",)]
    assert partial["required_gaps"] == ["git_process_spawn_failed"]
    assert "ethos lane retire recover" in str(partial["next_action"])
    assert partial["state"] == "partial_transition"
    assert partial["completed_effects"] == ["remove_worktree"]
    assert partial["remaining_effects"] == ["delete_ref", "revoke_lease"]
    assert not lane.exists()
    assert git(repo, "rev-parse", "work/abandon") == head
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"

    monkeypatch.setattr(operation, "delete_operation_ref", original)
    monkeypatch.setattr(
        operation,
        "remove_operation_worktree",
        lambda *_a: pytest.fail("recovery replays worktree removal"),
    )
    for _ in range(2):
        recovered = operation.recover_retirement_operation(
            root=repo,
            receipt_path=receipt["path"],
            receipt_sha256=receipt["sha256"],
            apply=True,
            authorized=True,
        )
        assert recovered["state"] == "retired", recovered
        monkeypatch.setattr(
            operation,
            "delete_operation_ref",
            lambda *_a: pytest.fail("terminal recovery replays deletion"),
        )
        terminal = recovered["terminal_receipt"]
        assert isinstance(terminal, dict)
        payload = json.loads(Path(terminal["path"]).read_text())
        assert payload["kind"] == "lane-retirement-receipt"
        assert payload["request"] == request.model_dump(mode="json")
        assert payload["progress"]["completed_effects"] == [
            "remove_worktree",
            "delete_ref",
            "revoke_lease",
        ]
        assert payload["progress"]["remaining_effects"] == []
    operation.revoke_operation_lease(repo, request)
    assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == "missing"

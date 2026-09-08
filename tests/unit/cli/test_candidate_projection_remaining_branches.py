"""Candidate failure classification and exact recovery boundaries."""

from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as projection
from ethos.contracts.branch.roles import BranchRolePolicy


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    status = {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "head": "head",
            "worktree_path": str(tmp_path / "candidate"),
        },
    }
    monkeypatch.setattr(projection, "repository_root", lambda _root: tmp_path)
    monkeypatch.setattr(projection, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(projection, "workspace_status", lambda *_a, **_k: status)
    monkeypatch.setattr(
        projection, "run_git", lambda *_a, **_k: SimpleNamespace(stdout="head", returncode=0)
    )
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: None)
    monkeypatch.setattr(projection, "worktree_sync_gap", lambda *_a: "")
    return status["candidate"]


@pytest.mark.parametrize(
    ("existing", "boundary", "error", "gap"),
    [
        (True, "execute_git_effect", "git_effect_recovery_stale", "git_effect_recovery_stale"),
        (False, "_add_candidate_worktree", "projection failed", "candidate_worktree_add_failed"),
        (False, "execute_git_effect", "effect failed", "candidate_ref_creation_failed"),
        (
            False,
            "execute_git_effect",
            "git_effect_recovery_unproven",
            "git_effect_recovery_unproven",
        ),
    ],
)
def test_bootstrap_failure_preserves_the_failed_boundary(
    tmp_path, monkeypatch, candidate, existing, boundary, error, gap
):
    candidate.update(exists=existing, worktree_exists=existing)
    monkeypatch.setattr(projection, "_candidate_plan", lambda **_k: object())
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: object())
    monkeypatch.setattr(projection, "execute_git_effect", lambda *_a, **_k: None)

    def fail(*_args, **_kwargs):
        raise ValueError(error)

    def run_git(_root, *args, **_kwargs):
        absent = boundary == "execute_git_effect" and args[-1] == "candidate/dev"
        return SimpleNamespace(stdout="" if absent else "head", returncode=int(absent))

    monkeypatch.setattr(projection, boundary, fail)
    monkeypatch.setattr(projection, "run_git", run_git)
    report = projection.bootstrap_candidate(
        root=tmp_path, path=tmp_path / "candidate", expect_head="head", apply=True
    )
    assert (report["state"], report["required_gaps"]) == ("blocked", [gap])
    if not existing:
        assert report["stderr"] == error


@pytest.mark.parametrize(
    ("current_gap", "apply", "previous", "recovery_error", "state", "gaps"),
    [
        ("worktree_index_mismatch", True, "head", "", "blocked", ["git_effect_recovery_unproven"]),
        ("worktree_dirty", False, "head", "", "blocked", ["candidate_worktree_dirty"]),
        ("", False, "head", "", "base_current", []),
        ("", False, "previous", "", "ready_to_refresh_from_accepted", []),
        (
            "",
            True,
            "head",
            "git_effect_recovery_ambiguous",
            "blocked",
            ["git_effect_recovery_ambiguous"],
        ),
    ],
)
def test_refresh_readiness_does_not_execute(
    tmp_path, monkeypatch, candidate, current_gap, apply, previous, recovery_error, state, gaps
):
    candidate["head"] = previous
    monkeypatch.setattr(projection, "worktree_sync_gap", lambda *_a: current_gap)

    def recovery(*_args):
        if recovery_error:
            raise ValueError(recovery_error)

    monkeypatch.setattr(projection, "_recovery_plan", recovery)
    monkeypatch.setattr(
        projection, "execute_git_effect", lambda *_a, **_k: pytest.fail("readiness cannot mutate")
    )
    report = projection.refresh_candidate_from_accepted(
        root=tmp_path, apply=apply, authorized=apply, expect_head="head" if apply else None
    )
    assert (report["state"], report["required_gaps"]) == (state, gaps)
    action = report["next_action"]
    assert isinstance(action, str)
    assert action
    if state == "ready_to_refresh_from_accepted":
        assert "--expect-head head" in action


@pytest.mark.parametrize(
    ("previous", "error", "gap"),
    [
        ("previous", "", ""),
        ("previous", "projection failed", "candidate_refresh_from_accepted_failed"),
        ("head", "projection failed", "candidate_worktree_dirty"),
        ("head", "candidate_worktree_sync_failed", "candidate_worktree_sync_failed"),
        ("head", "git_effect_recovery_stale", "git_effect_recovery_stale"),
    ],
)
def test_refresh_recovers_exact_plan_and_reports_projection_failure(
    tmp_path, monkeypatch, candidate, previous, error, gap
):
    assert candidate["head"] == "head"
    plan = SimpleNamespace(digest="plan")
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: plan)
    monkeypatch.setattr(
        projection,
        "git_effect_from_plan",
        lambda _p: SimpleNamespace(
            updates={"refs/heads/candidate/dev": SimpleNamespace(expected=previous)}
        ),
    )
    monkeypatch.setattr(projection, "worktree_sync_gap", lambda *_a: "worktree_index_mismatch")
    effects, syncs = [], []
    monkeypatch.setattr(
        projection, "execute_git_effect", lambda _r, value, **_k: effects.append(value)
    )

    def sync(_root, _path, branch, ref, old, desired):
        syncs.append((branch, ref, old, desired))
        if error:
            raise ValueError(error)

    monkeypatch.setattr(projection, "_sync_candidate_worktree", sync)
    report = projection.refresh_candidate_from_accepted(
        root=tmp_path, apply=True, authorized=True, expect_head="head"
    )
    assert report["state"] == ("blocked" if gap else "refreshed_from_accepted")
    assert report["required_gaps"] == ([gap] if gap else [])
    assert report.get("stderr", "") == error
    assert effects == [plan]
    assert syncs == [("candidate/dev", "head", previous, "head")]

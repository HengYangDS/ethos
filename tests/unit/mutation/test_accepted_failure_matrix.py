from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.accepted.promotion as accepted
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path

CURRENT = "a" * 40
CANDIDATE = "b" * 40


def _attestation(predicate):
    return SimpleNamespace(model_dump=lambda **_kwargs: {"predicate": predicate, "verdict": "pass"})


def _promote(root: Path, *, path="/tmp/candidate", mirror="independent") -> dict[str, object]:
    return accepted.promote_candidate(
        root=root,
        policy=BranchRolePolicy(release_mirror=mirror),
        current_head=CURRENT,
        candidate_head=CANDIDATE,
        status={"candidate": {"worktree_path": path}, "worktrees": []},
    )


def _prime(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    boundaries = {}
    for name, result in {
        "is_ancestor": True,
        "proof_for_repository_transition": (_attestation("proof:execution"), []),
        "sweep_stale_ref_intents": [],
        "worktree_sync_gap": "",
        "ref_worktree_paths": (),
        "execute_git_effect": _attestation("effect:git-ref"),
        "sync_ref_worktrees": {"worktrees": [{"state": "synced"}]},
        "sync_linked_ref_worktree": {"mode": "accepted_ff", "worktree_sync": "synced"},
        "compile_observed_git_effect": object(),
        "run_git": SimpleNamespace(stdout=CURRENT),
    }.items():
        boundaries[name] = Mock(return_value=result)
        monkeypatch.setattr(accepted, name, boundaries[name])
    return boundaries


def test_candidate_promotion_uses_proof_without_repository_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _prime(monkeypatch)["compile_observed_git_effect"]

    report = _promote(tmp_path)

    assert report["verdict"] == "pass"
    assert captured.call_args.args[1] is None
    assert captured.call_args.kwargs["prior_attestations"] == {
        "proof": {"predicate": "proof:execution", "verdict": "pass"}
    }


@pytest.mark.parametrize("ancestor", [False, True])
def test_candidate_promotion_checks_ancestry_before_exact_proof(
    tmp_path, monkeypatch: pytest.MonkeyPatch, ancestor
) -> None:
    boundaries = _prime(monkeypatch)
    boundaries["is_ancestor"].return_value = ancestor
    proof = boundaries["proof_for_repository_transition"]
    proof.return_value = None, ["proof_head_stale"]
    report = _promote(tmp_path)
    assert report["required_gaps"] == [
        "proof_head_stale" if ancestor else "candidate_diverged_from_accepted"
    ]
    assert proof.call_count == int(ancestor)


@pytest.mark.parametrize("gap", ["missing-path", "dirty", "failed"])
def test_candidate_promotion_preflights_accepted_worktree_before_effect(
    tmp_path, monkeypatch: pytest.MonkeyPatch, gap: str
) -> None:
    boundaries = _prime(monkeypatch)
    effect = boundaries["execute_git_effect"]
    boundaries["worktree_sync_gap"].return_value = gap
    report = _promote(tmp_path, path="" if gap == "missing-path" else "/tmp/candidate")
    assert report["required_gaps"] == [
        "candidate_worktree_binding_stale" if gap == "missing-path" else f"accepted_{gap}"
    ]
    effect.assert_not_called()


@pytest.mark.parametrize("outcome", ["transition", "unchanged", "unknown"])
def test_candidate_promotion_reports_transition_and_git_effect_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch, outcome
) -> None:
    boundaries = _prime(monkeypatch)
    failure = (
        ValueError("profile invalid")
        if outcome == "transition"
        else ProcessExecutionError(
            "git_effect_cas_rejected",
            reason="native_exit_nonzero",
            observation={"outcome": outcome, "stderr": "hook refused"},
        )
    )
    name = "compile_observed_git_effect" if outcome == "transition" else "execute_git_effect"
    boundaries[name].side_effect = failure
    effect = _promote(tmp_path)
    assert effect["required_gaps"] == [
        "accepted_transition_invalid"
        if outcome == "transition"
        else "accepted_atomic_update_rejected"
    ]
    assert effect["stderr"] == str(failure)
    if isinstance(failure, ProcessExecutionError):
        assert effect["process_failure"] == failure.evidence()
    assert effect["verdict"] == ("unknown" if outcome == "unknown" else "block")


@pytest.mark.parametrize(
    ("owner", "state", "expected"),
    [
        ("release", "failed", "release_mirror_worktree_sync_failed"),
        ("release", "dirty", "release_mirror_worktree_dirty_after_sync"),
        ("accepted", "failed", "accepted_worktree_sync_failed"),
        ("accepted", "dirty", "accepted_worktree_dirty_after_sync"),
    ],
)
def test_candidate_promotion_reports_post_effect_worktree_compensation_state(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    owner: str,
    state: str,
    expected: str,
) -> None:
    boundaries = _prime(monkeypatch)
    name = "sync_linked_ref_worktree" if owner == "release" else "sync_ref_worktrees"
    boundaries[name].return_value = (
        {"mode": "accepted_ff", "worktree_sync": state}
        if owner == "release"
        else {"worktrees": [{"state": state}]}
    )

    report = _promote(tmp_path, mirror="accepted_ff")

    assert report["required_gaps"] == [expected]
    assert report["accepted_advanced"] is True
    assert report["attestation"]["predicate"] == "effect:git-ref"


@pytest.mark.parametrize(
    ("release_head", "ancestor", "error"),
    [
        ("", True, "release_mirror_release_branch_missing"),
        ("c" * 40, False, "release_mirror_diverged"),
    ],
)
def test_candidate_promotion_rejects_invalid_release_mirror_before_effect(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    release_head: str,
    ancestor: object,
    error: str,
) -> None:
    boundaries = _prime(monkeypatch)
    boundaries["run_git"].return_value = SimpleNamespace(stdout=release_head)
    boundaries["is_ancestor"].side_effect = lambda _root, old, _new: old == CURRENT or ancestor
    report = _promote(tmp_path, mirror="accepted_ff")

    assert report["required_gaps"] == ["accepted_transition_invalid"]
    assert report["stderr"] == error

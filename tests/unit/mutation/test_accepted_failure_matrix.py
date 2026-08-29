from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.accepted as accepted
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path

CURRENT = "a" * 40
CANDIDATE = "b" * 40


class _Proof:
    def model_dump(self, **_kwargs):
        return {"predicate": "proof:execution", "verdict": "pass"}


class _EffectAttestation:
    def model_dump(self, **_kwargs):
        return {"predicate": "effect:git-ref", "verdict": "pass"}


def _status(path: str = "/tmp/candidate", worktrees: tuple[object, ...] = ()) -> dict[str, object]:
    return {"candidate": {"worktree_path": path}, "worktrees": list(worktrees)}


def _promote(root: Path, *, status: dict[str, object] | None = None) -> dict[str, object]:
    return accepted.promote_candidate(
        root=root,
        policy=BranchRolePolicy(),
        current_head=CURRENT,
        candidate_head=CANDIDATE,
        status=_status() if status is None else status,
    )


def _prime(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured = {}
    monkeypatch.setattr(accepted, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(accepted, "proof_for_repository_transition", lambda *_a: (_Proof(), []))
    monkeypatch.setattr(accepted, "sweep_stale_ref_intents", lambda *_args: [])
    monkeypatch.setattr(accepted, "worktree_sync_gap", lambda *_args: "")
    monkeypatch.setattr(accepted, "ref_worktree_paths", lambda *_args: ())

    def compile_plan(_root, authority, effect, **kwargs):
        captured.update(commitment=authority, effect=effect, kwargs=kwargs)
        return SimpleNamespace(effect=effect)

    monkeypatch.setattr(accepted, "compile_observed_git_effect", compile_plan)
    monkeypatch.setattr(
        accepted, "execute_git_effect", lambda *_args, **_kwargs: _EffectAttestation()
    )
    monkeypatch.setattr(
        accepted,
        "sync_ref_worktrees",
        lambda *_args, **_kwargs: {"worktrees": [{"state": "synced"}]},
    )
    monkeypatch.setattr(
        accepted,
        "sync_linked_ref_worktree",
        lambda *_args, **_kwargs: {"mode": "accepted_ff", "worktree_sync": "synced"},
    )
    return captured


def test_candidate_promotion_uses_proof_without_repository_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _prime(monkeypatch)

    report = _promote(tmp_path)

    assert report["verdict"] == "pass"
    assert captured["commitment"] is None
    assert captured["kwargs"]["prior_attestations"] == {
        "proof": {"predicate": "proof:execution", "verdict": "pass"}
    }


def test_candidate_promotion_rejects_divergence_before_proof_lookup(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proof_calls = []
    monkeypatch.setattr(accepted, "is_ancestor", lambda *_args: False)
    monkeypatch.setattr(
        accepted, "proof_for_repository_transition", lambda *_a: proof_calls.append(True)
    )

    report = _promote(tmp_path)

    assert report["required_gaps"] == ["candidate_diverged_from_accepted"]
    assert proof_calls == []


def test_candidate_promotion_preserves_exact_proof_gaps(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(accepted, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(
        accepted, "proof_for_repository_transition", lambda *_a: (None, ["proof_head_stale"])
    )

    report = _promote(tmp_path)

    assert report["required_gaps"] == ["proof_head_stale"]


def test_candidate_promotion_requires_candidate_worktree_binding(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prime(monkeypatch)
    report = _promote(tmp_path, status=_status(path=""))
    assert report["required_gaps"] == ["candidate_worktree_binding_stale"]


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        ("dirty", "accepted_dirty"),
        ("failed", "accepted_failed"),
    ],
)
def test_candidate_promotion_preflights_accepted_worktree_before_effect(
    tmp_path, monkeypatch: pytest.MonkeyPatch, gap: str, expected: str
) -> None:
    _prime(monkeypatch)
    effects = []
    monkeypatch.setattr(accepted, "worktree_sync_gap", lambda *_args: gap)
    monkeypatch.setattr(
        accepted, "execute_git_effect", lambda *_args, **_kwargs: effects.append(True)
    )

    report = _promote(tmp_path)

    assert report["required_gaps"] == [expected]
    assert effects == []


def test_candidate_promotion_reports_transition_and_git_effect_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prime(monkeypatch)
    monkeypatch.setattr(
        accepted,
        "compile_observed_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("profile invalid")),
    )
    transition = _promote(tmp_path)
    assert transition["required_gaps"] == ["accepted_transition_invalid"]
    assert transition["stderr"] == "profile invalid"

    _prime(monkeypatch)
    monkeypatch.setattr(
        accepted,
        "execute_git_effect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("git_effect_cas_rejected")),
    )
    effect = _promote(tmp_path)
    assert effect["required_gaps"] == ["accepted_atomic_update_rejected"]
    assert effect["stderr"] == "git_effect_cas_rejected"


@pytest.mark.parametrize(
    ("release_state", "accepted_state", "expected"),
    [
        ("failed", "synced", ["release_mirror_worktree_sync_failed"]),
        ("dirty", "synced", ["release_mirror_worktree_dirty_after_sync"]),
        ("synced", "failed", ["accepted_worktree_sync_failed"]),
        ("synced", "dirty", ["accepted_worktree_dirty_after_sync"]),
    ],
)
def test_candidate_promotion_reports_post_effect_worktree_compensation_state(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    release_state: str,
    accepted_state: str,
    expected: list[str],
) -> None:
    _prime(monkeypatch)
    policy = BranchRolePolicy(release_mirror="accepted_ff")
    monkeypatch.setattr(
        accepted, "run_git", lambda *_args, **_kwargs: SimpleNamespace(stdout=CURRENT)
    )
    monkeypatch.setattr(accepted, "is_ancestor", lambda *_args: True)
    monkeypatch.setattr(
        accepted,
        "sync_linked_ref_worktree",
        lambda *_args, **_kwargs: {
            "mode": "accepted_ff",
            "worktree_sync": release_state,
        },
    )
    monkeypatch.setattr(
        accepted,
        "sync_ref_worktrees",
        lambda *_args, **_kwargs: {"worktrees": [{"state": accepted_state}]},
    )

    report = accepted.promote_candidate(
        root=tmp_path,
        policy=policy,
        current_head=CURRENT,
        candidate_head=CANDIDATE,
        status=_status(),
    )

    assert report["required_gaps"] == expected
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
    _prime(monkeypatch)
    monkeypatch.setattr(
        accepted, "run_git", lambda *_args, **_kwargs: SimpleNamespace(stdout=release_head)
    )

    def is_ancestor(_root, old, _new):
        return True if old == CURRENT else ancestor

    monkeypatch.setattr(accepted, "is_ancestor", is_ancestor)
    report = accepted.promote_candidate(
        root=tmp_path,
        policy=BranchRolePolicy(release_mirror="accepted_ff"),
        current_head=CURRENT,
        candidate_head=CANDIDATE,
        status=_status(),
    )

    assert report["required_gaps"] == ["accepted_transition_invalid"]
    assert report["stderr"] == error

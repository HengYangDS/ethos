from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as projection
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


def _git(stdout: str = "head", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode)


def _status(path: Path, *, exists: bool = True, worktree_exists: bool = True) -> dict[str, object]:
    return {
        "role": "accepted_root",
        "dirty": False,
        "candidate": {
            "exists": exists,
            "worktree_exists": worktree_exists,
            "head": "head",
            "worktree_path": path.as_posix(),
        },
    }


def _common(monkeypatch: pytest.MonkeyPatch, root: Path, status: dict[str, object]) -> None:
    monkeypatch.setattr(projection, "repository_root", lambda _root: root)
    monkeypatch.setattr(projection, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(projection, "workspace_status", lambda *_a, **_k: status)
    monkeypatch.setattr(projection, "run_git", lambda *_a, **_k: _git())


def test_candidate_bootstrap_existing_projection_reports_recovery_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    _common(monkeypatch, tmp_path, _status(candidate))
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: object())
    monkeypatch.setattr(
        projection,
        "execute_git_effect",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("git_effect_recovery_stale")),
    )

    report = projection.bootstrap_candidate(root=tmp_path, apply=True)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["git_effect_recovery_stale"]


@pytest.mark.parametrize(
    ("ref_exists", "error", "gap"),
    [
        (True, "projection failed", "candidate_worktree_add_failed"),
        (False, "effect failed", "candidate_ref_creation_failed"),
        (False, "git_effect_recovery_unproven", "git_effect_recovery_unproven"),
    ],
)
def test_candidate_bootstrap_effect_failure_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ref_exists: object,
    error: str,
    gap: str,
) -> None:
    target = tmp_path / "candidate"
    _common(monkeypatch, tmp_path, _status(target, exists=False, worktree_exists=False))
    monkeypatch.setattr(projection, "_candidate_plan", lambda **_k: object())
    if error == "projection failed":
        monkeypatch.setattr(projection, "execute_git_effect", lambda *_a, **_k: None)
        monkeypatch.setattr(
            projection,
            "_add_candidate_worktree",
            lambda *_a, **_k: (_ for _ in ()).throw(ValueError(error)),
        )
    else:
        monkeypatch.setattr(
            projection,
            "execute_git_effect",
            lambda *_a, **_k: (_ for _ in ()).throw(ValueError(error)),
        )

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if args[-1] == "candidate/dev":
            return _git("head" if ref_exists else "", 0 if ref_exists else 1)
        return _git()

    monkeypatch.setattr(projection, "run_git", run_git)

    report = projection.bootstrap_candidate(
        root=tmp_path, path=target, expect_head="head", apply=True
    )

    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("current_gap", "should_apply", "expected"),
    [
        ("worktree_index_mismatch", True, "git_effect_recovery_unproven"),
        ("worktree_dirty", False, "candidate_worktree_dirty"),
    ],
)
def test_candidate_refresh_exact_equal_worktree_failure_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_gap: str,
    should_apply: object,
    expected: str,
) -> None:
    candidate = tmp_path / "candidate"
    _common(monkeypatch, tmp_path, _status(candidate))
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: None)
    monkeypatch.setattr(projection, "worktree_sync_gap", lambda *_a, **_k: current_gap)

    report = projection.refresh_candidate_from_accepted(
        root=tmp_path,
        apply=should_apply,
        authorized=should_apply,
        expect_head="head" if should_apply else None,
    )

    assert report["required_gaps"] == [expected]


def test_candidate_refresh_reports_base_current_without_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    _common(monkeypatch, tmp_path, _status(candidate))
    monkeypatch.setattr(projection, "worktree_sync_gap", lambda *_a, **_k: "")

    report = projection.refresh_candidate_from_accepted(root=tmp_path)

    assert report["state"] == "base_current"
    assert report["required_gaps"] == []


def test_candidate_refresh_retries_only_the_missing_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    _common(monkeypatch, tmp_path, _status(candidate))
    plan = SimpleNamespace(digest="plan")
    update = SimpleNamespace(expected="previous")
    monkeypatch.setattr(projection, "_recovery_plan", lambda *_a: plan)
    monkeypatch.setattr(
        projection,
        "git_effect_from_plan",
        lambda _plan: SimpleNamespace(updates={"refs/heads/candidate/dev": update}),
    )
    monkeypatch.setattr(
        projection,
        "worktree_sync_gap",
        lambda *_a, **_k: "worktree_index_mismatch",
    )
    effects: list[object] = []
    syncs: list[tuple[str, str]] = []
    monkeypatch.setattr(
        projection, "execute_git_effect", lambda _root, value, **_kwargs: effects.append(value)
    )
    monkeypatch.setattr(
        projection,
        "_sync_candidate_worktree",
        lambda _root, _path, _branch, _ref, previous, desired: syncs.append((previous, desired)),
    )

    report = projection.refresh_candidate_from_accepted(
        root=tmp_path,
        apply=True,
        authorized=True,
        expect_head="head",
    )

    assert report["state"] == "refreshed_from_accepted"
    assert effects == [plan]
    assert syncs == [("previous", "head")]

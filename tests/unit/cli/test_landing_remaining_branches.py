from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.landing as landing
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


def _git(stdout: str = "head", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, returncode=returncode)


def test_land_apply_stops_at_public_mutation_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(landing, "run_git", lambda *_a, **_k: _git())
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_k: SimpleNamespace(verdict="block", required_gaps=("authorization_required",)),
    )
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=False, expect_head=None)

    assert report["required_gaps"] == ["authorization_required"]


def test_land_apply_normalizes_unexpected_candidate_plan_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(landing, "run_git", lambda *_a, **_k: _git())
    monkeypatch.setattr(
        landing,
        "evaluate_mutation",
        lambda **_k: SimpleNamespace(verdict="pass", required_gaps=()),
    )
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(
        landing,
        "_candidate_plan",
        lambda *_a, **_k: (_ for _ in ()).throw(TypeError("broken plan")),
    )

    report = landing.apply_land_to_candidate(root=tmp_path, authorized=True, expect_head="head")

    assert report["required_gaps"] == ["candidate_update_failed"]
    assert report["stderr"] == "broken plan"


def test_candidate_readiness_reports_exact_equal_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = {"verdict": "pass", "head": "head", "required_gaps": []}
    monkeypatch.setattr(
        landing,
        "_candidate_plan",
        lambda *_a, **_k: (None, (BranchRolePolicy(), base, tmp_path, "head", None)),
    )

    report = landing.candidate_transition_readiness(root=tmp_path)

    assert report["state"] == "candidate_current"
    assert report["effect"] == {}


@pytest.mark.parametrize(
    ("candidate", "gap"),
    [
        ({"exists": False, "worktree_exists": False}, "candidate_branch_missing"),
        ({"exists": True, "worktree_exists": False}, "candidate_worktree_missing"),
    ],
)
def test_candidate_base_report_exposes_missing_projection_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate: dict[str, object],
    gap: str,
) -> None:
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(landing, "run_git", lambda *_a, **_k: _git())

    report = landing.candidate_base_report(root=tmp_path, status={"candidate": candidate})

    assert report["required_gaps"] == [gap]


def test_candidate_base_report_blocks_dirty_and_non_ancestor_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_path = tmp_path / "candidate"
    status = {
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": candidate_path.as_posix(),
        }
    }
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: BranchRolePolicy())
    monkeypatch.setattr(landing, "run_git", lambda *_a, **_k: _git("candidate"))
    monkeypatch.setattr(landing, "dirty_provenance", lambda _root: {"dirty": True})

    assert landing.candidate_base_report(root=tmp_path, status=status)["required_gaps"] == [
        "candidate_worktree_dirty"
    ]

    monkeypatch.setattr(landing, "dirty_provenance", lambda _root: {"dirty": False})
    monkeypatch.setattr(landing, "is_ancestor", lambda *_a: False)
    assert landing.candidate_base_report(root=tmp_path, status=status)["required_gaps"] == [
        "candidate_base_stale"
    ]

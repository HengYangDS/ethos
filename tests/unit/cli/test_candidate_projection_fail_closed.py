from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as projection
from ethos.adapters.repo.attestation_set import read_attestation_set
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path


def _repo_without_candidate(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    return repo, git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("should_apply", [False, True])
def test_candidate_bootstrap_distinguishes_plan_from_path_collision(
    tmp_path: Path, *, should_apply: bool
) -> None:
    repo, head = _repo_without_candidate(tmp_path)
    target = tmp_path / "candidate"
    target.mkdir()

    report = projection.bootstrap_candidate(
        root=repo,
        path=target,
        expect_head=head,
        apply=should_apply,
    )

    assert report["state"] == ("planned" if not should_apply else "blocked")
    assert report["required_gaps"] == (
        [] if not should_apply else ["candidate_worktree_path_exists"]
    )
    assert git(repo, "branch", "--list", "candidate/dev") == ""


def test_candidate_bootstrap_reports_unproven_recovery_before_any_ref_effect(
    tmp_path: Path,
) -> None:
    repo, head = _repo_without_candidate(tmp_path)
    candidate = tmp_path / "candidate"
    git(repo, "branch", "candidate/dev", head)

    report = projection.bootstrap_candidate(
        root=repo,
        path=candidate,
        expect_head=head,
        apply=True,
    )

    assert report["required_gaps"] == ["git_effect_recovery_unproven"]
    assert not candidate.exists()
    assert git(repo, "rev-parse", "candidate/dev") == head


@pytest.mark.parametrize(
    ("condition", "apply", "authorized", "expected", "gap"),
    [
        ("role", False, False, None, "accepted_root_required"),
        ("dirty", False, False, None, "accepted_root_dirty"),
        ("clean", True, False, "head", "authorization_required"),
        ("clean", True, True, None, "expect_head_required"),
        ("clean", True, True, "other", "expect_head_mismatch"),
        ("no-ref", False, False, None, "candidate_branch_missing"),
        ("no-tree", False, False, None, "candidate_worktree_missing"),
    ],
)
def test_candidate_preconditions_preserve_real_repository(
    tmp_path, condition, apply, authorized, expected, gap
):
    repo, head = _repo_without_candidate(tmp_path)
    candidate = tmp_path / "candidate"
    if condition != "no-ref":
        git(repo, "branch", "candidate/dev", head)
        if condition != "no-tree":
            git(repo, "worktree", "add", str(candidate), "candidate/dev")
    if condition == "role":
        git(repo, "switch", "-c", "work/topic")
    if condition == "dirty":
        (repo / "README.md").write_text("local overlay\n")
    before = git(repo, "show-ref"), git(repo, "status", "--porcelain")
    report = projection.refresh_candidate_from_accepted(
        root=repo,
        apply=apply,
        authorized=authorized,
        expect_head=head if expected == "head" else expected,
    )
    assert report["required_gaps"] == [gap]
    if condition in {"role", "dirty"} or expected == "other":
        blocked = projection.bootstrap_candidate(root=repo, expect_head=expected, apply=True)
        assert blocked["required_gaps"] == [
            "expect_head_mismatch"
            if expected == "other"
            else "candidate_bootstrap_requires_clean_accepted_root"
        ]
    assert (git(repo, "show-ref"), git(repo, "status", "--porcelain")) == before


@pytest.mark.parametrize("interruption", ["", "projection denied", "empty diagnostic"])
def test_candidate_exact_cas_projection_and_recovery(tmp_path, monkeypatch, interruption):
    repo, previous = _repo_without_candidate(tmp_path)
    candidate = tmp_path / "candidate"
    monkeypatch.setattr(projection, "install_hook_launchers", install_fixture_hook_runtime)
    created = projection.bootstrap_candidate(
        root=repo, path=candidate, expect_head=previous, apply=True
    )
    assert created["state"] == "bootstrapped", created
    assert git(candidate, "rev-parse", "HEAD") == previous
    assert git(candidate, "status", "--porcelain") == ""
    assert (
        projection.bootstrap_candidate(root=repo, path=candidate, apply=True)["state"] == "present"
    )
    head = commit_fixture_file(repo, "payload.txt", "accepted\n", "advance accepted")
    ready = projection.refresh_candidate_from_accepted(root=repo)
    assert ready["state"] == "ready_to_refresh_from_accepted", ready
    assert git(candidate, "rev-parse", "HEAD") == previous
    with monkeypatch.context() as failure:
        if interruption:
            failure.setattr(
                projection,
                "sync_ref_worktrees",
                lambda *_a: {
                    "worktrees": [
                        {
                            "state": "failed",
                            "stderr": "" if interruption == "empty diagnostic" else interruption,
                        }
                    ]
                },
            )
        report = projection.refresh_candidate_from_accepted(
            root=repo, apply=True, authorized=True, expect_head=head
        )
    assert report["state"] == ("blocked" if interruption else "refreshed_from_accepted"), report
    assert git(repo, "rev-parse", "candidate/dev") == head
    if interruption:
        assert report["required_gaps"] == ["candidate_refresh_from_accepted_failed"]
        assert report["stderr"] == (
            "candidate_worktree_sync_failed" if interruption == "empty diagnostic" else interruption
        )
        assert not (candidate / "payload.txt").exists()
        recovered = projection.refresh_candidate_from_accepted(
            root=repo, apply=True, authorized=True, expect_head=head
        )
        assert recovered["state"] == "refreshed_from_accepted", recovered
    assert (candidate / "payload.txt").read_text() == "accepted\n"
    assert git(candidate, "write-tree") == git(repo, "rev-parse", "HEAD^{tree}")
    assert git(candidate, "status", "--porcelain") == ""
    before = {item.id for item in read_attestation_set(repo)[1]}
    assert (
        projection.refresh_candidate_from_accepted(
            root=repo, apply=True, authorized=True, expect_head=head
        )["verdict"]
        == "pass"
    )
    assert {item.id for item in read_attestation_set(repo)[1]} == before
    (candidate / "payload.txt").write_text("user overlay\n")
    blocked = projection.refresh_candidate_from_accepted(
        root=repo, apply=True, authorized=True, expect_head=head
    )
    assert blocked["verdict"] == "block"
    assert blocked["stderr"] == "worktree_index_mismatch"
    assert (candidate / "payload.txt").read_text() == "user overlay\n"
    assert git(repo, "rev-parse", "candidate/dev") == head

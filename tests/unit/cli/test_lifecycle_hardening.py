from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as work_lane_refresh
import ethos.adapters.openspec.profile as openspec_profile
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def test_work_lane_commitment_never_falls_back_from_an_invalid_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid_lease(*_args: object, **_kwargs: object) -> None:
        message = "lease_expected_tree_mismatch"
        raise ValueError(message)

    monkeypatch.setattr(openspec_profile, "load_lease_bound_commitment", invalid_lease)
    monkeypatch.setattr(
        openspec_profile,
        "load_profile_commitment",
        lambda *_args, **_kwargs: pytest.fail("invalid Lease must stop carrier selection"),
    )

    with pytest.raises(ValueError, match="lease_expected_tree_mismatch"):
        openspec_profile.load_work_lane_commitment(tmp_path, lease={})


def _diverged_candidate_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    old_candidate_head = commit_fixture_file(
        candidate, "CANDIDATE.md", "# CANDIDATE.md\n", "advance candidate"
    )
    accepted_head = commit_fixture_file(repo, "ACCEPTED.md", "# ACCEPTED.md\n", "advance accepted")
    return repo, candidate, accepted_head, old_candidate_head


def _refresh_arguments(head: str) -> tuple[str, ...]:
    return (
        "lane",
        "candidate",
        "--refresh-from-accepted",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
    )


def _fail_once(monkeypatch, target, name: str, message: str):
    original = getattr(target, name)
    failed = False

    def injected(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(target, name, injected)


@pytest.mark.parametrize(
    ("target", "name", "message", "effect_persisted"),
    [
        (candidate_projection, "sync_ref_worktrees", "injected post-CAS failure", False),
        (git_effects, "_clear_claimed_intents", "injected post-projection failure", True),
    ],
)
def test_lane_candidate_refresh_recovers_after_interrupted_projection(
    tmp_path: Path, monkeypatch, target, name: str, message: str, effect_persisted
) -> None:
    repo, candidate, accepted_head, old_candidate_head = _diverged_candidate_repo(tmp_path)
    _fail_once(monkeypatch, target, name, message)
    arguments = _refresh_arguments(accepted_head)
    failed_report = run_ethos_blocked(*arguments, cwd=repo)
    assert bool(list(ref_intent_dir(repo).glob("*.json"))) is effect_persisted
    assert git(repo, "rev-parse", "candidate/dev") == (
        accepted_head if effect_persisted else old_candidate_head
    )
    recovered = run_ethos(*arguments, cwd=repo)
    assert failed_report["required_gaps"] == ["candidate_refresh_from_accepted_failed"]
    assert failed_report["data"]["previous_head"] == old_candidate_head
    assert recovered["state"] == "refreshed_from_accepted"
    assert git(candidate, "rev-parse", "HEAD") == accepted_head
    assert git(candidate, "status", "--short") == ""
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_lane_candidate_bootstrap_recovers_after_worktree_creation_precedes_intent_clear(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    candidate = tmp_path / "repo-candidate-dev"
    arguments = (
        "lane",
        "candidate",
        "--apply",
        "--path",
        candidate.as_posix(),
        "--expect-head",
        head,
        "--json",
    )
    _fail_once(monkeypatch, git_effects, "_clear_claimed_intents", "injected intent clear failure")

    assert run_ethos_blocked(*arguments, cwd=repo)["required_gaps"] == [
        "candidate_worktree_add_failed"
    ]
    recovered = run_ethos(*arguments, cwd=repo)

    assert recovered["state"] == "present"
    assert hook_runtime_binding(candidate)["required_gaps"] == []
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_lane_refresh_recovers_after_ref_cas_precedes_branch_attachment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    previous = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    failed = False
    branch_was_advanced = False

    original = work_lane_refresh.attach_worktree

    def fail_first_attachment(root, path, *, branch, head):
        nonlocal branch_was_advanced, failed
        if branch == "work/feature" and not failed:
            failed = True
            branch_was_advanced = git(root, "rev-parse", "work/feature") == git(
                root, "rev-parse", "HEAD"
            )
            msg = "injected post-CAS attachment failure"
            raise OSError(msg)
        return original(root, path, branch=branch, head=head)

    monkeypatch.setattr(work_lane_refresh, "attach_worktree", fail_first_attachment)
    arguments = (
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
    )

    blocked = run_ethos_blocked(*arguments, cwd=worktree)
    recovered = run_ethos(*arguments, cwd=worktree)
    assert branch_was_advanced
    assert blocked["required_gaps"] == ["refresh_base_worktree_attach_failed"]
    assert recovered["state"] == "base_refreshed"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert not list(ref_intent_dir(worktree).glob("*.json"))


def test_lane_refresh_restores_original_branch_when_ref_cas_is_rejected_after_rebase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    previous = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    def reject_effect(*_args: object, **_kwargs: object) -> None:
        message = "git_effect_lease_generation_stale"
        raise ValueError(message)

    monkeypatch.setattr(work_lane_refresh, "execute_git_effect", reject_effect)

    payload = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
        cwd=worktree,
    )

    assert payload["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]
    assert payload["data"]["stderr"] == "git_effect_lease_generation_stale"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert git(worktree, "rev-parse", "HEAD") == previous
    assert git(worktree, "rev-parse", "work/feature") == previous
    assert git(worktree, "status", "--short") == ""


def test_land_closeout_reports_actionable_candidate_divergence(tmp_path: Path) -> None:
    repo, _candidate, accepted_head, _old_candidate_head = _diverged_candidate_repo(tmp_path)
    seed_executed_proof(repo, accepted_head)

    payload = run_ethos_blocked(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["required_gaps"] == ["candidate_diverged_from_accepted"]
    assert payload["next_action"] == (
        "ethos lane candidate --refresh-from-accepted --apply --authorize "
        f"--expect-head {accepted_head} --json"
    )
    assert payload["continuation"] == "await-user"
    assert payload["user_decision_required"] is True

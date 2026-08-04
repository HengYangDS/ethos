from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as work_lane_refresh
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.ref_intent import ref_intent_dir
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked

if TYPE_CHECKING:
    from pathlib import Path


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
    ("target", "name", "message", "reject_recompile"),
    [
        (candidate_projection, "sync_ref_worktrees", "injected post-CAS failure", True),
        (git_effects, "_clear_claimed_intents", "injected post-projection failure", False),
    ],
)
def test_lane_candidate_refresh_recovers_after_interrupted_projection(
    tmp_path: Path, monkeypatch, target, name: str, message: str, reject_recompile
) -> None:
    repo, candidate, accepted_head, old_candidate_head = _diverged_candidate_repo(tmp_path)
    _fail_once(monkeypatch, target, name, message)
    arguments = _refresh_arguments(accepted_head)
    failed_report = run_ethos_blocked(*arguments, cwd=repo)
    assert list(ref_intent_dir(repo).glob("*.json"))
    if reject_recompile:
        monkeypatch.setattr(
            candidate_projection,
            "_candidate_plan",
            lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("recovery must consume the attested original plan")
            ),
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
    assert not list(ref_intent_dir(repo).glob("*.json"))


def test_lane_refresh_recovers_after_ref_cas_precedes_branch_attachment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    previous = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    original = work_lane_refresh.run_git
    failed = False
    branch_was_advanced = False

    def fail_first_attachment(root, *args, **kwargs):
        nonlocal branch_was_advanced, failed
        if args == ("switch", "work/feature") and not failed:
            failed = True
            branch_was_advanced = git(root, "rev-parse", "work/feature") == git(
                root, "rev-parse", "HEAD"
            )
            msg = "injected post-CAS attachment failure"
            raise OSError(msg)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(work_lane_refresh, "run_git", fail_first_attachment)
    arguments = (
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
    )

    failed_report = run_ethos_blocked(*arguments, cwd=worktree)
    assert branch_was_advanced
    assert list(ref_intent_dir(worktree).glob("*.json"))
    recovered = run_ethos(*arguments, cwd=worktree)

    assert failed_report["required_gaps"] == ["refresh_base_worktree_attach_failed"]
    assert recovered["state"] == "base_refreshed"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert not list(ref_intent_dir(worktree).glob("*.json"))


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

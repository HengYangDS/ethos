from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.mutation.lane_lifecycle.identity_repair as identity_repair
import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as work_lane_refresh
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.repo.commit_identity import verify_commit_trust
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

    failed_report = run_ethos_blocked(*arguments, cwd=worktree)
    assert branch_was_advanced
    assert list(ref_intent_dir(worktree).glob("*.json"))
    recovered = run_ethos(*arguments, cwd=worktree)

    assert failed_report["required_gaps"] == ["refresh_base_worktree_attach_failed"]
    assert recovered["state"] == "base_refreshed"
    assert git(worktree, "branch", "--show-current") == "work/feature"
    assert not list(ref_intent_dir(worktree).glob("*.json"))


def test_refresh_base_blocks_same_tree_identity_repair_instead_of_rebasing_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old_head)
    repaired_head = _replace_signature(worktree, old_head)
    _advance_lane_lease(worktree, old_head, repaired_head)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, repaired_head)

    payload = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        repaired_head,
        "--json",
        cwd=worktree,
    )

    assert payload["required_gaps"] == ["commit_identity_replacement_required"]
    assert git(worktree, "rev-parse", "HEAD") == repaired_head
    assert git(candidate, "rev-parse", "HEAD") == old_head


def test_repair_identity_requires_protected_trust_and_exact_new_head_proof(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old_head)
    repaired_head = _replace_signature(worktree, old_head)
    _advance_lane_lease(worktree, old_head, repaired_head)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, repaired_head)
    assert proof_attestation(worktree, repaired_head) is not None

    payload = run_ethos_blocked(
        "lane",
        "repair-identity",
        "--old-commit",
        old_head,
        "--new-commit",
        repaired_head,
        "--expect-head",
        repaired_head,
        "--apply",
        "--authorize",
        "--json",
        cwd=worktree,
    )

    assert "commit_trust_anchor_missing" in payload["required_gaps"]
    assert git(candidate, "rev-parse", "HEAD") == old_head


def test_repair_identity_rejects_repository_owned_trust_anchor(tmp_path: Path, monkeypatch) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    repaired_head = _replace_signature(worktree, old_head)
    anchor = worktree / ".ethos" / "state" / "allowed-signers"
    anchor.write_text("agent:test ssh-ed25519 synthetic\n", encoding="utf-8")
    git(worktree, "config", "gpg.ssh.allowedSignersFile", anchor.as_posix())
    monkeypatch.setattr(
        "ethos.adapters.repo.commit_identity.os.geteuid",
        lambda: anchor.stat().st_uid + 1,
    )

    report = verify_commit_trust(worktree, repaired_head)

    assert report["required_gaps"] == ["commit_trust_anchor_inside_repository"]


def test_repair_identity_advances_candidate_and_accepted_through_exact_cas(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old_head)
    git(repo, "reset", "--hard", old_head)
    repaired_head = _replace_signature(worktree, old_head)
    _advance_lane_lease(worktree, old_head, repaired_head)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, repaired_head)
    monkeypatch.setattr(
        identity_repair,
        "verify_commit_trust",
        lambda _root, revision: {
            "verdict": "pass",
            "revision": revision,
            "anchor": "/protected/allowed-signers",
            "required_gaps": [],
        },
    )

    payload = run_ethos(
        "lane",
        "repair-identity",
        "--old-commit",
        old_head,
        "--new-commit",
        repaired_head,
        "--expect-head",
        repaired_head,
        "--apply",
        "--authorize",
        "--json",
        cwd=worktree,
    )

    assert payload["state"] == "identity_repaired"
    assert git(candidate, "rev-parse", "HEAD") == repaired_head
    assert git(repo, "rev-parse", "HEAD") == repaired_head


def test_repair_identity_resumes_after_candidate_cas_before_worktree_sync(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old_head)
    git(repo, "reset", "--hard", old_head)
    repaired_head = _replace_signature(worktree, old_head)
    _advance_lane_lease(worktree, old_head, repaired_head)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, repaired_head)
    monkeypatch.setattr(
        identity_repair,
        "verify_commit_trust",
        lambda _root, revision: {
            "verdict": "pass",
            "revision": revision,
            "anchor": "/protected/allowed-signers",
            "required_gaps": [],
        },
    )
    original = identity_repair.sync_ref_worktrees
    interrupted = False

    def interrupt_candidate_once(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            return {"worktree_sync": "failed", "worktrees": []}
        return original(*args, **kwargs)

    monkeypatch.setattr(identity_repair, "sync_ref_worktrees", interrupt_candidate_once)
    arguments = (
        "lane",
        "repair-identity",
        "--old-commit",
        old_head,
        "--new-commit",
        repaired_head,
        "--expect-head",
        repaired_head,
        "--apply",
        "--authorize",
        "--json",
    )

    failed = run_ethos_blocked(*arguments, cwd=worktree)
    recovered = run_ethos(*arguments, cwd=worktree)

    assert failed["required_gaps"] == ["identity_repair_cas_rejected"]
    assert recovered["state"] == "identity_repaired"
    assert git(candidate, "rev-parse", "HEAD") == repaired_head
    assert git(candidate, "status", "--short") == ""
    assert git(repo, "rev-parse", "HEAD") == repaired_head
    assert git(repo, "status", "--short") == ""


def test_repair_identity_resumes_after_accepted_cas_before_worktree_sync(
    tmp_path: Path, monkeypatch
) -> None:
    repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    old_head = commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    git(candidate, "reset", "--hard", old_head)
    git(repo, "reset", "--hard", old_head)
    repaired_head = _replace_signature(worktree, old_head)
    _advance_lane_lease(worktree, old_head, repaired_head)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, repaired_head)
    monkeypatch.setattr(
        identity_repair,
        "verify_commit_trust",
        lambda _root, revision: {
            "verdict": "pass",
            "revision": revision,
            "anchor": "/protected/allowed-signers",
            "required_gaps": [],
        },
    )
    original = identity_repair.sync_ref_worktrees
    calls = 0

    def interrupt_accepted_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return {"worktree_sync": "failed", "worktrees": []}
        return original(*args, **kwargs)

    monkeypatch.setattr(identity_repair, "sync_ref_worktrees", interrupt_accepted_once)
    arguments = (
        "lane",
        "repair-identity",
        "--old-commit",
        old_head,
        "--new-commit",
        repaired_head,
        "--expect-head",
        repaired_head,
        "--apply",
        "--authorize",
        "--json",
    )

    failed = run_ethos_blocked(*arguments, cwd=worktree)
    recovered = run_ethos(*arguments, cwd=worktree)

    assert failed["required_gaps"] == ["identity_repair_cas_rejected"]
    assert recovered["state"] == "identity_repaired"
    assert git(candidate, "rev-parse", "HEAD") == repaired_head
    assert git(repo, "rev-parse", "HEAD") == repaired_head
    assert git(repo, "status", "--short") == ""


def _replace_signature(worktree: Path, head: str) -> str:
    raw = git(worktree, "cat-file", "commit", head)
    repaired = raw.replace(
        "\n\nfeature work",
        "\ngpgsig -----BEGIN SSH SIGNATURE-----\n synthetic\n -----END SSH SIGNATURE-----\n\nfeature work",
    )
    completed = subprocess.run(
        ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
        cwd=worktree,
        input=repaired + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    repaired_head = completed.stdout.strip()
    git(worktree, "update-ref", "refs/heads/work/feature", repaired_head, head)
    git(worktree, "reset", "--hard", repaired_head)
    return repaired_head


def _advance_lane_lease(worktree: Path, previous: str, head: str) -> None:
    prior = os.environ.get("ETHOS_ACTOR")
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    report = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name="refs/heads/work/feature",
        old_value=previous,
        new_value=head,
    )
    if prior is None:
        os.environ.pop("ETHOS_ACTOR", None)
    else:
        os.environ["ETHOS_ACTOR"] = prior
    assert report["state"] == "lease_ref_advanced", report


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

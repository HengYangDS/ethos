from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.mutation import core as mutation
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.core import evaluate_mutation
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.mutation.proof import record_executed_proof


def seed_proof(root: Path, head: str) -> None:
    """Seed a HEAD-keyed executed-proof record, as `ethos prove --execute` would.

    evaluate_mutation now requires executed proof at the current HEAD before a
    merge; tests exercising the OTHER admission gates seed the proof so the proof
    gate is satisfied and the intended gap is isolated. The record is
    self-authenticating (digest recomputed on read), so this seeds a REAL evidence
    body — proof cannot be faked, in tests or production.
    """
    from ethos.repository.evidence.core import EvidenceSet
    from ethos.repository.evidence.core import ProofRun

    run = ProofRun.from_adapter_result(
        action_id="python-tests",
        command=("pytest",),
        exit_code=0,
        stdout="",
        stderr="",
        adapter_state="proven",
        evidence_class="test",
        trust_bearing=True,
        diagnostics=(),
    )
    evidence = EvidenceSet.from_runs(id="proof", head=head, runs=(run,)).to_dict()
    record_executed_proof(root, evidence)


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    # Generated state (incl. HEAD-keyed proof records) is ignored, as in a real
    # adopted repo — so a proof record never dirties the work lane.
    (path / ".gitignore").write_text(".ethos/state/\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def add_candidate_worktree(repo: Path, path: Path) -> Path:
    git(repo, "worktree", "add", "-b", "candidate/dev", path.as_posix(), "dev")
    return path


def add_owned_work_lane(repo: Path, name: str, path: Path) -> Path:
    report = start_work_lane(root=repo, name=name, path=path, owner="agent:test", apply=True)
    assert report["ok"] is True
    return path


def test_mutation_requires_authorization_and_expected_head() -> None:
    request = MutationRequest(command="land", apply=True, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is False
    assert "authorization_required" in result.gaps
    assert "expect_head_required" in result.gaps


def test_mutation_allows_dry_run_without_authorization() -> None:
    request = MutationRequest(command="land", apply=False, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is True
    assert result.state == "dry_run"


def test_mutation_apply_requires_matching_expected_head(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = add_owned_work_lane(repo, "apply", tmp_path / "repo-work-apply")
    request = MutationRequest(
        command="publish",
        apply=True,
        authorized=True,
        expect_head="abc123",
    )

    seed_proof(worktree, "abc123")

    result = evaluate_mutation(request, root=worktree, current_head="abc123")

    assert result.ok is True
    assert result.state == "publish_ready"


def test_mutation_apply_rejects_protected_root_even_with_authorization(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    request = MutationRequest(
        command="land",
        apply=True,
        authorized=True,
        expect_head=git(repo, "rev-parse", "HEAD"),
    )

    result = evaluate_mutation(request, root=repo, current_head=request.expect_head or "")

    assert result.ok is False
    assert result.state == "blocked"
    assert "protected_root_mutation" in result.gaps


def test_mutation_apply_rejects_dirty_work_lane(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = add_owned_work_lane(repo, "apply", tmp_path / "repo-work-apply")
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")
    request = MutationRequest(
        command="land",
        apply=True,
        authorized=True,
        expect_head=git(worktree, "rev-parse", "HEAD"),
    )

    result = evaluate_mutation(request, root=worktree, current_head=request.expect_head or "")

    assert result.ok is False
    assert result.state == "blocked"
    assert "work_lane_dirty" in result.gaps



def test_mutation_apply_rejects_overlapping_foreign_work_lane_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    first = tmp_path / "repo-work-first"
    second = tmp_path / "repo-work-second"
    git(repo, "worktree", "add", "-b", "work/first", first.as_posix(), "candidate/dev")
    git(repo, "worktree", "add", "-b", "work/second", second.as_posix(), "candidate/dev")

    (first / "README.md").write_text("# first\n", encoding="utf-8")
    git(first, "add", "README.md")
    git(
        first,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "first change",
    )
    (second / "README.md").write_text("# second\n", encoding="utf-8")
    git(second, "add", "README.md")
    git(
        second,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "second change",
    )
    head = git(second, "rev-parse", "HEAD")
    seed_proof(second, head)
    request = MutationRequest(
        command="land",
        apply=True,
        authorized=True,
        expect_head=head,
    )

    result = evaluate_mutation(request, root=second, current_head=head)

    assert result.ok is False
    assert result.state == "blocked"
    assert "coordination_gap:scope_overlap:work/first" in result.gaps


def test_mutation_apply_rejects_raw_work_lane_without_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-raw"
    git(repo, "worktree", "add", "-b", "work/raw", worktree.as_posix(), "candidate/dev")
    head = git(worktree, "rev-parse", "HEAD")
    seed_proof(worktree, head)
    request = MutationRequest(
        command="land",
        apply=True,
        authorized=True,
        expect_head=head,
    )

    result = evaluate_mutation(request, root=worktree, current_head=head)

    assert result.ok is False
    assert result.state == "blocked"
    assert "work_lane_missing_lease:work/raw" in result.gaps

def test_apply_land_to_candidate_advances_candidate_without_advancing_dev(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = add_owned_work_lane(repo, "apply", tmp_path / "repo-work-apply")
    (worktree / "README.md").write_text("# work lane change\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "work lane change",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    dev_head = git(repo, "rev-parse", "dev")
    seed_proof(worktree, work_head)

    report = apply_land_to_candidate(
        root=worktree,
        authorized=True,
        expect_head=work_head,
    )

    assert report["ok"] is True
    assert report["state"] == "candidate_validated"
    assert git(repo, "rev-parse", "candidate/dev") == work_head
    assert git(candidate, "rev-parse", "HEAD") == work_head
    assert git(repo, "rev-parse", "dev") == dev_head


def test_apply_land_to_candidate_reports_stale_candidate_base(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = add_owned_work_lane(repo, "apply", tmp_path / "repo-work-apply")
    (candidate / "README.md").write_text("# candidate change\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "candidate change",
    )
    (worktree / "README.md").write_text("# work lane change\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "work lane change",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_proof(worktree, work_head)

    report = apply_land_to_candidate(
        root=worktree,
        authorized=True,
        expect_head=work_head,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["head"] == work_head
    assert report["candidate_head"] == candidate_head
    assert report["required_gaps"] == ["candidate_base_stale"]


def test_accepted_root_closeout_fast_forwards_configured_candidate_branch(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir()
    (repo / ".ethos" / "workspace.toml").write_text(
        "[branch_roles]\n"
        'release_branch = "release"\n'
        'accepted_branch = "integration"\n'
        'candidate_branch = "stage/integration"\n'
        'work_branch_prefix = "lane/"\n'
        'submit_branch_prefix = "review/"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )
    git(repo, "branch", "-m", "integration")
    candidate = tmp_path / "repo-stage-integration"
    git(repo, "worktree", "add", "-b", "stage/integration", candidate.as_posix(), "integration")
    (candidate / "README.md").write_text("# candidate change\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "candidate change",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_proof(repo, accepted_head)

    report = mutation.apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=accepted_head,
    )

    assert report["ok"] is True
    assert report["state"] == "accepted_validated"
    assert report["branch"] == "integration"
    assert report["source_branch"] == "stage/integration"
    assert report["head"] == candidate_head
    assert report["previous_head"] == accepted_head
    assert git(repo, "rev-parse", "integration") == candidate_head
    assert git(repo, "rev-parse", "HEAD") == candidate_head


def test_apply_land_reuses_admitted_decision_after_runtime_proof_cleanup(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = add_owned_work_lane(repo, "apply", tmp_path / "repo-work-apply")
    (worktree / "README.md").write_text("# work lane change\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "work lane change",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    seed_proof(worktree, work_head)
    admitted = evaluate_mutation(
        MutationRequest(command="land", apply=True, authorized=True, expect_head=work_head),
        root=worktree,
        current_head=work_head,
    )
    assert admitted.ok is True
    proof_dir = worktree / ".ethos" / "state" / "proof"
    for path in proof_dir.glob("*.json"):
        path.unlink()

    report = apply_land_to_candidate(
        root=worktree,
        authorized=True,
        expect_head=work_head,
        admitted_decision=admitted,
    )

    assert report["ok"] is True
    assert report["state"] == "candidate_validated"
    assert git(candidate, "rev-parse", "HEAD") == work_head

from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.repository.adoption.planner import adoption_plan
from ethos_core.contracts.branch_roles import load_branch_role_policy
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import write_role_policy


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
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


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, profile="generic", apply=True)
    assert plan["applied"] is True
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )


def seed_executed_proof(repo: Path, head: str) -> None:
    """Record an executed-proof at HEAD, as `ethos prove --execute` would.

    Land/publish now require a HEAD-keyed proof record before the merge, so tests
    exercising land mechanics seed the proof the same way the prove command does. The
    record is self-authenticating (digest recomputed on read), so this seeds a REAL
    evidence body — a proof cannot be faked, in tests or production.
    """
    from ethos.adapters.mutation.proof import record_executed_proof
    from ethos.repository.evidence.core import EvidenceSet
    from ethos.repository.evidence.core import ProofRun

    run = ProofRun(
        action_id="python-tests",
        command=("pytest",),
        exit_code=0,
        stdout="",
        stderr="",
        state="proven",
        evidence_class="test",
        verdict="passed",
        trust_bearing=True,
        diagnostics=(),
    )
    record_executed_proof(repo, EvidenceSet.from_runs(id="proof", head=head, runs=(run,)).to_dict())


def test_land_dry_run_reports_dirty_work_lane_gap(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "candidate/dev",
        (tmp_path / "repo-candidate-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-work-feature"
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")

    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "work_lane_dirty" in payload["required_gaps"]


def test_land_blocks_completed_active_openspec_change_before_candidate_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ethos import cli

    repo = init_git_repo(tmp_path / "repo")
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "candidate/dev",
        (tmp_path / "repo-candidate-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-work-feature"
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        return {"ok": True, "required_gaps": [], "root": root.as_posix()}

    def fake_openspec_lifecycle(root: Path) -> dict[str, object]:
        return {
            "ok": False,
            "state": "blocked",
            "root": root.as_posix(),
            "completed_changes": ["sample-change"],
            "required_gaps": ["openspec_completed_change_unarchived:sample-change"],
        }

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    monkeypatch.setattr(
        cli,
        "openspec_completed_active_changes_report",
        fake_openspec_lifecycle,
        raising=False,
    )

    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["sample-change"]


def test_land_dry_run_reports_stale_candidate_base_with_refresh_action(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    worktree = tmp_path / "repo-work-feature"
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", "FEATURE.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "feature work",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["candidate_base_stale"]
    assert payload["next_actions"] == [
        f"ethos lane refresh-base --apply --authorize --expect-head {work_head} --json"
    ]
    assert payload["data"]["candidate_update"] == {
        "ok": False,
        "state": "blocked",
        "branch": "candidate/dev",
        "head": work_head,
        "candidate_head": candidate_head,
        "path": candidate.as_posix(),
        "required_gaps": ["candidate_base_stale"],
        "remediation": [
            {
                "gap": "candidate_base_stale",
                "kind": "stale_base",
                "next_actions": [
                    "ethos lane refresh-base --apply --authorize --expect-head <head> --json",
                    "rerun proof after the lane is replayed onto candidate/dev",
                ],
            }
        ],
    }


def test_lane_refresh_base_apply_rebases_stale_work_lane(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    worktree = tmp_path / "repo-work-feature"
    run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )
    (candidate / "CANDIDATE.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "CANDIDATE.md")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance candidate",
    )
    (worktree / "FEATURE.md").write_text("# feature\n", encoding="utf-8")
    git(worktree, "add", "FEATURE.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "feature work",
    )
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")

    payload = run_ethos(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous_head,
        "--json",
        cwd=worktree,
    )

    refreshed_head = git(worktree, "rev-parse", "HEAD")
    assert payload["ok"] is True
    assert payload["state"] == "base_refreshed"
    assert payload["required_gaps"] == []
    assert payload["next_actions"] == ["ethos land --json"]
    assert payload["data"]["branch"] == "work/feature"
    assert payload["data"]["previous_head"] == previous_head
    assert payload["data"]["head"] == refreshed_head
    assert payload["data"]["candidate_head"] == candidate_head
    assert refreshed_head != previous_head


def test_land_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos_blocked("land", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_land_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "protected_root_mutation" in payload["required_gaps"]


def test_land_closeout_apply_fast_forwards_accepted_root_from_candidate(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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
    seed_executed_proof(candidate, candidate_head)

    payload = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "accepted_validated"
    assert payload["required_gaps"] == []
    assert payload["next_actions"] == ["ethos lane retire-landed --branch <work-branch>"]
    accepted_update = payload["data"]["accepted_update"]
    assert accepted_update["ok"] is True
    assert accepted_update["state"] == "accepted_validated"
    assert accepted_update["branch"] == "dev"
    assert accepted_update["source_branch"] == "candidate/dev"
    assert accepted_update["head"] == candidate_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["required_gaps"] == []
    assert accepted_update["proof_carry"]["state"] == "carried"
    assert accepted_update["proof_carry"]["source_verified"] is True
    assert accepted_update["proof_carry"]["target_verified"] is True
    assert accepted_update["proof_carry"]["mints_proof"] is False
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert git(repo, "rev-parse", "HEAD") == candidate_head


def test_land_closeout_audits_candidate_content_before_fast_forward(
    tmp_path: Path,
    monkeypatch,
) -> None:

    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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
    seed_executed_proof(candidate, candidate_head)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        if root.resolve() == candidate.resolve():
            return {"ok": True, "required_gaps": [], "root": root.as_posix()}
        return {
            "ok": False,
            "required_gaps": ["accepted_root_precloseout_audit"],
            "root": root.as_posix(),
        }

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)

    payload = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["repository_audit"]["root"] == candidate.as_posix()


def test_publish_dry_run_remains_available_on_accepted_root_after_land_boundary(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["ok"] is True
    assert payload["state"] == "ready_to_publish"
    assert payload["required_gaps"] == []


def test_publish_dry_run_blocks_release_root_active_openspec_residue(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    git(repo, "checkout", "-b", "main")
    leak = repo / "openspec" / "changes" / "release-leak"
    leak.mkdir(parents=True)
    (leak / "proposal.md").write_text("# release leak\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "leak active openspec carrier on release root",
    )
    git(repo, "checkout", "dev")

    payload = run_ethos("publish", "--json", cwd=repo)

    gap = "openspec_protected_branch_active_change_unarchived:main:release_root:release-leak"
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert gap in payload["required_gaps"]
    assert payload["data"]["release_root_open_spec"] == {
        "required_gaps": [gap],
        "blocking": True,
    }


def test_land_dry_run_blocks_accepted_root_without_closeout(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")

    payload = run_ethos("land", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "protected_root_mutation" in payload["required_gaps"]
    assert payload["next_actions"] == ["ethos land --closeout --json"]


def test_land_dry_run_blocks_candidate_root_without_closeout(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")

    payload = run_ethos("land", "--root", candidate.as_posix(), "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "protected_root_mutation" in payload["required_gaps"]
    assert payload["next_actions"] == ["ethos land --closeout --json"]


def test_land_closeout_dry_run_reports_expect_head_mismatch(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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
    candidate_head = git(candidate, "rev-parse", "HEAD")

    payload = run_ethos(
        "land",
        "--closeout",
        "--expect-head",
        candidate_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["expect_head_mismatch"]
    assert payload["data"]["mutation"]["decision"] == "blocked"
    assert payload["data"]["closeout_bootstrap"]["required_gaps"] == ["expect_head_mismatch"]


def test_land_closeout_dry_run_reports_accepted_root_required(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    accepted_head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
        "land",
        "--closeout",
        "--root",
        candidate.as_posix(),
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["accepted_root_required"]
    assert payload["data"]["mutation"]["decision"] == "blocked"
    assert payload["data"]["closeout_bootstrap"]["required_gaps"] == ["accepted_root_required"]


def test_land_closeout_exposes_bootstrap_package_for_current_runner(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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

    payload = run_ethos("land", "--closeout", "--json", cwd=repo)

    bootstrap = payload["data"]["closeout_bootstrap"]
    assert payload["ok"] is True
    runner_binding = bootstrap["runner_binding"]
    assert runner_binding["kind"] == "closeout_runner_binding"
    assert runner_binding["accepted_root"] == repo.resolve().as_posix()
    assert runner_binding["audit_root"] == candidate.resolve().as_posix()
    assert runner_binding["runner_module_path"] == bootstrap["runner_module_path"]
    assert runner_binding["runner_package_root"] == bootstrap["runner_package_root"]
    assert runner_binding["runner_source_root"] == bootstrap["runner_source_root"]
    assert (
        runner_binding["runner_matches_accepted_root"] == bootstrap["runner_matches_accepted_root"]
    )
    assert runner_binding["runner_matches_audit_root"] == bootstrap["runner_matches_audit_root"]
    assert runner_binding["advisory_gaps"] == bootstrap["runner_advisories"]
    assert bootstrap == {
        "kind": "closeout_bootstrap",
        "mode": "maintainer_break_glass_local",
        "runner_mode": "current_runner_with_explicit_accepted_root",
        "remote_state": "deferred",
        "remote_push": "not_performed",
        "uses_current_runner": True,
        "runner_binding": runner_binding,
        "runner_module_path": runner_binding["runner_module_path"],
        "runner_package_root": runner_binding["runner_package_root"],
        "runner_source_root": runner_binding["runner_source_root"],
        "runner_matches_accepted_root": runner_binding["runner_matches_accepted_root"],
        "runner_matches_audit_root": runner_binding["runner_matches_audit_root"],
        "runner_advisories": runner_binding["advisory_gaps"],
        "state": "ready",
        "accepted_root": repo.resolve().as_posix(),
        "audit_root": candidate.resolve().as_posix(),
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "proof_target": {
            "kind": "closeout_proof_target",
            "role": "candidate",
            "root": candidate.resolve().as_posix(),
            "head": candidate_head,
            "reason": "accepted-root closeout promotes the candidate head",
        },
        "blocking": False,
        "required_gaps": [],
        "command": (
            "ethos land --closeout --apply --authorize "
            f"--expect-head {accepted_head} --root {repo.resolve().as_posix()} --json"
        ),
        "required_order": [
            "run closeout command with a current ETHOS runner",
            "bind --root to the clean accepted_root checkout",
            "audit the configured candidate worktree before accepted-root movement",
            "prove the configured candidate head before accepted-root movement",
            "fast-forward accepted_root from candidate only after proof and lifecycle gates pass",
            "defer remote push until remote publication is available",
        ],
        "next_action": "run closeout with a current ETHOS runner against accepted_root",
    }


def test_land_closeout_bootstrap_proof_target_stays_candidate_when_blocked(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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

    bootstrap = payload["data"]["closeout_bootstrap"]
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["proof_not_proven"]
    assert bootstrap["audit_root"] == repo.resolve().as_posix()
    assert bootstrap["proof_target"] == {
        "kind": "closeout_proof_target",
        "role": "candidate",
        "root": candidate.resolve().as_posix(),
        "head": candidate_head,
        "reason": "accepted-root closeout promotes the candidate head",
    }


def test_land_closeout_blocks_candidate_with_completed_active_openspec_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from ethos import cli

    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
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

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        return {"ok": True, "required_gaps": [], "root": root.as_posix()}

    def fake_openspec_lifecycle(root: Path) -> dict[str, object]:
        if root.resolve() == candidate.resolve():
            return {
                "ok": False,
                "state": "blocked",
                "root": root.as_posix(),
                "completed_changes": ["sample-change"],
                "required_gaps": ["openspec_completed_change_unarchived:sample-change"],
            }
        return {
            "ok": True,
            "state": "clean",
            "root": root.as_posix(),
            "completed_changes": [],
            "required_gaps": [],
        }

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    monkeypatch.setattr(
        cli,
        "openspec_completed_active_changes_report",
        fake_openspec_lifecycle,
        raising=False,
    )

    payload = run_ethos("land", "--closeout", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["root"] == candidate.as_posix()


def test_configured_branch_roles_drive_local_lifecycle_commands(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    git(repo, "branch", "integration", "dev")
    git(repo, "checkout", "integration")
    write_role_policy(
        repo,
        release_branch="release",
        accepted_branch="integration",
        candidate_branch="stage/integration",
        work_branch_prefix="lane/",
        submit_branch_prefix="review/",
    )
    git(repo, "branch", "release", "integration")
    accepted_head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, accepted_head)
    candidate_path = tmp_path / "repo-stage-integration"

    candidate_payload = run_ethos(
        "lane",
        "candidate",
        "--root",
        repo.as_posix(),
        "--path",
        candidate_path.as_posix(),
        "--expect-head",
        accepted_head,
        "--apply",
        "--json",
        cwd=repo,
    )

    assert candidate_payload["ok"] is True
    assert candidate_payload["data"]["branch"] == "stage/integration"
    assert candidate_payload["data"]["path"] == candidate_path.as_posix()

    worktree = tmp_path / "repo-lane-configured"
    start_payload = run_ethos(
        "lane",
        "start",
        "configured",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--apply",
        "--json",
        cwd=repo,
    )

    assert start_payload["ok"] is True
    assert start_payload["data"]["branch"] == "lane/configured"
    assert start_payload["data"]["base"] == "stage/integration"
    assert start_payload["summary"] == {
        "branch": "lane/configured",
        "path": worktree.resolve().as_posix(),
    }

    (worktree / "README.md").write_text("# configured lane\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configured lane change",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)

    publish_payload = run_ethos("publish", "--json", cwd=worktree)

    assert publish_payload["ok"] is True
    assert publish_payload["data"]["publication"]["submit_branch"] == "review/configured"
    local_submit = publish_payload["data"]["publication"]["local_submit_package"]
    assert local_submit["kind"] == "submit_branch_plan"
    assert local_submit["source_branch"] == "lane/configured"
    assert local_submit["submit_branch"] == "review/configured"
    assert local_submit["remote_push"] == "not_performed"
    assert local_submit["remote_state"] == "deferred"
    assert local_submit["blocking"] is False
    assert local_submit["remote_availability"]["blocking"] is False
    assert local_submit["local_ci_fallback"]["kind"] == "local_ci_fallback"
    assert local_submit["local_ci_fallback"]["hosted_ci_status_claimed"] is False
    assert local_submit["required_steps"] == [
        "land work lane to candidate role",
        "fast-forward accepted root from candidate role",
        "run local-ci fallback when remote publication is unavailable",
        "create configured submit branch when remote publication is available",
    ]

    land_payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert land_payload["ok"] is True
    assert land_payload["data"]["candidate_update"]["branch"] == "stage/integration"
    assert git(candidate_path, "rev-parse", "HEAD") == work_head
    assert git(repo, "rev-parse", "integration") == accepted_head
    seed_executed_proof(candidate_path, work_head)

    closeout_payload = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert closeout_payload["ok"] is True
    accepted_update = closeout_payload["data"]["accepted_update"]
    assert accepted_update["ok"] is True
    assert accepted_update["state"] == "accepted_validated"
    assert accepted_update["branch"] == "integration"
    assert accepted_update["source_branch"] == "stage/integration"
    assert accepted_update["head"] == work_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["required_gaps"] == []
    assert accepted_update["proof_carry"]["state"] == "carried"
    assert accepted_update["proof_carry"]["source_verified"] is True
    assert accepted_update["proof_carry"]["target_verified"] is True
    assert accepted_update["proof_carry"]["same_head_only"] is True

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test")
    retire_payload = run_ethos(
        "lane",
        "retire-landed",
        "--branch",
        "lane/configured",
        "--expect-head",
        work_head,
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert retire_payload["ok"] is True
    assert retire_payload["summary"] == {
        "landed_lane_count": 1,
        "selected_branch": "lane/configured",
    }
    assert retire_payload["data"]["mutation"]["expect_head"] == work_head


def test_publish_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos_blocked("publish", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_publish_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos_blocked(
        "publish",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "protected_root_mutation" in payload["required_gaps"]


def test_publish_reports_local_readiness_without_remote_push() -> None:
    payload = run_ethos("publish", "--json")
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"
    submit_branch = load_branch_role_policy(Path.cwd()).submit_branch_for_source(branch)

    assert payload["data"]["remote_push"] == "not_performed"
    assert payload["data"]["remote_availability"]["blocking"] is False
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    assert payload["data"]["local_ci_fallback"]["kind"] == "local_ci_fallback"
    assert payload["data"]["local_ci_fallback"]["hosted_ci_status_claimed"] is False

    publication = payload["data"]["publication"]
    assert publication["mode"] == "local_readiness"
    assert publication["remote_push"] == "not_performed"
    assert publication["submit_branch"] == submit_branch
    assert publication["required_gaps"] == (
        [] if payload["ok"] else ["local_publish_readiness_blocked"]
    )
    assert publication["local_submit_package"]["kind"] == "submit_branch_plan"
    assert publication["local_submit_package"]["source_branch"] == branch
    assert publication["local_submit_package"]["submit_branch"] == submit_branch
    assert (
        publication["local_submit_package"]["local_ci_fallback"]["evidence_class"]
        == "local_fallback"
    )
    assert (
        "run local-ci fallback when remote publication is unavailable"
        in publication["local_submit_package"]["required_steps"]
    )


def test_publish_uses_configured_submit_branch_role_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["local_submit_package"]["source_branch"] == "lane/topic"
    assert publication["submit_branch"] == "review/topic"
    assert publication["local_submit_package"]["submit_branch"] == "review/topic"

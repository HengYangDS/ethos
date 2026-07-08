from __future__ import annotations

from pathlib import Path

from ethos_core.contracts.branch_roles import load_branch_role_policy
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import write_role_policy


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
    import ethos.surface.cli.root.lifecycle as lifecycle_cli

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
        lifecycle_cli,
        "completed_active_changes_report",
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
    assert publish_payload["summary"]["mode"] == "local_readiness"
    assert publish_payload["summary"]["local_readiness"] is True
    assert publish_payload["summary"]["remote_push"] == "not_performed"
    assert publish_payload["summary"]["remote_publication_state"] == "deferred"
    assert publish_payload["summary"]["hosted_ci_status_claimed"] is False
    assert publish_payload["summary"]["submit_branch"] == "review/configured"
    assert publish_payload["data"]["publication"]["submit_branch"] == "review/configured"
    local_submit = publish_payload["data"]["publication"]["local_submit_package"]
    assert local_submit["kind"] == "submit_branch_plan"
    assert local_submit["source_branch"] == "lane/configured"
    assert local_submit["submit_branch"] == "review/configured"
    assert local_submit["remote_push"] == "not_performed"
    assert local_submit["remote_state"] == "deferred"
    assert publish_payload["data"]["publication"]["remote_state"] == "deferred"
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
        "selected_retire_ready": True,
        "selected_required_gaps": [],
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

    assert payload["summary"]["mode"] == "local_readiness"
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["summary"]["remote_publication_state"] == "deferred"
    assert payload["summary"]["hosted_ci_status_claimed"] is False
    assert payload["data"]["remote_push"] == "not_performed"
    assert payload["data"]["remote_availability"]["blocking"] is False
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    assert payload["data"]["local_ci_fallback"]["kind"] == "local_ci_fallback"
    assert payload["data"]["local_ci_fallback"]["hosted_ci_status_claimed"] is False
    assert (
        "tools/ci/scripts/run-module-layout.sh"
        in payload["data"]["local_ci_fallback"]["owner_scripts"]
    )

    publication = payload["data"]["publication"]
    assert publication["mode"] == "local_readiness"
    assert publication["remote_push"] == "not_performed"
    assert publication["remote_state"] == "deferred"
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

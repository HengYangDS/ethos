from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.ethos_cli_runner import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


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
        "--holder-ref",
        "agent:test:case:agent-test",
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
    import ethos.surface.cli.root.lifecycle as lifecycle_cli  # noqa: PLC0415, RUF100 - local import isolates import-time state for this test

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
        "--holder-ref",
        "agent:test:case:agent-test",
        "--apply",
        "--json",
        cwd=repo,
    )

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:  # noqa: ARG001, RUF100 - test double preserves the patched callable signature
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
        "--holder-ref",
        "agent:test:case:agent-test",
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


def test_land_dry_run_requires_executed_proof_before_ready_state(tmp_path: Path) -> None:
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
        "--holder-ref",
        "agent:test:case:agent-test",
        "--apply",
        "--json",
        cwd=repo,
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

    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["proof_not_proven"]
    assert payload["next_actions"] == [f"ethos prove --execute --expect-head {work_head} --json"]
    assert payload["data"]["proof_readiness"] == {
        "kind": "executed_proof_readiness",
        "head": work_head,
        "state": "missing",
        "blocking": True,
        "required_gaps": ["proof_not_proven"],
        "next_action": f"ethos prove --execute --expect-head {work_head} --json",
        "local_readiness": False,
        "evidence_class": "local_readiness",
        "independent_verification": {
            "ok": True,
            "state": "disabled",
            "root": worktree.resolve().as_posix(),
            "mode": "disabled",
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "required_gaps": [],
        },
    }


def test_land_dry_run_reports_ready_after_executed_proof(tmp_path: Path) -> None:
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
        "--holder-ref",
        "agent:test:case:agent-test",
        "--apply",
        "--json",
        cwd=repo,
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
    seed_executed_proof(worktree, work_head)

    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is True
    assert payload["state"] == "ready_to_land"
    assert payload["required_gaps"] == []
    assert payload["data"]["proof_readiness"] == {
        "kind": "executed_proof_readiness",
        "head": work_head,
        "state": "proven",
        "blocking": False,
        "required_gaps": [],
        "next_action": "",
        "local_readiness": True,
        "evidence_class": "local_readiness",
        "independent_verification": {
            "ok": True,
            "state": "disabled",
            "root": worktree.resolve().as_posix(),
            "mode": "disabled",
            "receipt": {},
            "evidence_class": "local_readiness",
            "mints_authority": False,
            "required_gaps": [],
        },
    }
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "land",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "allow"
    assert mutation["decision"]["subject"]["action"] == "candidate.integrate"
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["source_head"] == work_head
    assert expected_state["source_ref"] == "refs/heads/work/feature"
    assert expected_state["target_ref"] == "refs/heads/candidate/dev"
    assert expected_state["holder_ref"] == "agent:test:case:agent-test"
    assert expected_state["lease_id"].startswith("lease:")
    assert expected_state["lease_epoch"] == 1
    assert mutation["decision"]["required_gaps"] == []
    assert mutation["decision"]["mints_authority"] is False
    assert "authorized" not in mutation


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
        "--holder-ref",
        "agent:test:case:agent-test",
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


def test_land_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked("land", "--apply", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    mutation = payload["data"]["mutation"]
    assert mutation["request"]["confirmation_present"] is False
    assert mutation["decision"]["verdict"] == "block"
    assert mutation["decision"]["required_gaps"] == payload["required_gaps"]
    assert "decision" not in {
        key: value for key, value in mutation.items() if isinstance(value, str)
    }


def test_cli_runner_rejects_implicit_apply_against_repository_checkout() -> None:
    args = ("land", "--apply", "--json")

    with pytest.raises(AssertionError, match="--apply calls must pass cwd"):
        run_ethos_blocked(*args)


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
    assert payload["state"] == "local_publish_ready"
    assert payload["required_gaps"] == []
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "publish",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "defer"
    assert mutation["decision"]["subject"]["action"] == "remote.publish"
    assert mutation["decision"]["required_gaps"] == []
    assert mutation["decision"]["next"]
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["source_ref"] == "refs/heads/dev"
    assert expected_state["source_head"] == head
    assert expected_state["target_ref"] == "refs/heads/dev"
    assert expected_state["remote"] == "origin"
    assert expected_state["remote_availability_state"] in {
        "unconfigured",
        "unavailable",
        "not_probed",
    }
    assert mutation["decision"]["decision_basis"]["identity_basis"] == "not_evaluated"


def test_publish_apply_defers_when_remote_transition_is_not_performed(tmp_path: Path) -> None:
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
        "--holder-ref",
        "agent:test:case:agent-test",
        "--apply",
        "--json",
        cwd=repo,
    )
    head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, head)

    payload = run_ethos_blocked(
        "publish",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["state"] == "publication_deferred"
    assert payload["required_gaps"] == []
    assert payload["summary"]["local_readiness"] is True
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "defer"


def test_publish_tolerates_git_pre_push_remote_arguments(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = run_ethos(
        "publish",
        "--json",
        "origin",
        "ssh://git@example.invalid/group/repo.git",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "local_publish_ready"
    assert payload["required_gaps"] == []
    assert payload["summary"]["remote_push"] == "not_performed"


def test_publish_rejects_non_hook_positional_arguments(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    completed = run_ethos_raw("publish", "--json", "unexpected", cwd=repo)

    assert completed.returncode != 0


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


def test_configured_branch_roles_drive_local_lifecycle_commands(  # noqa: PLR0915, RUF100 - coverage matrix exercises one cohesive command path
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
        "--holder-ref",
        "agent:test:case:agent-test",
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

    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    retire_payload = run_ethos(
        "lane",
        "retire",
        "landed",
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
        "selected_blockers": [],
    }
    assert retire_payload["data"]["mutation"]["expect_head"] == work_head


def test_publish_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked("publish", "--apply", "--json", cwd=repo)

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


def test_publish_reports_current_local_ci_fallback_evidence_when_manifest_matches_head(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "ok": True,
                "head": head,
                "command": "tools/ci/scripts/run-local-ci.sh",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)

    fallback = payload["data"]["local_ci_fallback"]
    evidence_status = fallback["evidence_status"]
    assert evidence_status["state"] == "current"
    assert evidence_status["current_head"] == head
    assert evidence_status["evidence_head"] == head
    assert evidence_status["path"] == "build/evidence/local-ci/fallback.json"
    assert payload["summary"]["next_publication_action"] == (
        "remote unavailable; local-ci fallback evidence is current at HEAD"
    )
    assert payload["next_actions"] == [
        "remote unavailable; local-ci fallback evidence is current at HEAD",
        "ethos report",
    ]


def test_publish_labels_current_fallback_as_unprobed_when_origin_is_configured(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    git(repo, "remote", "add", "origin", "ssh://example.invalid/ethos.git")
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "ok": True,
                "head": head,
                "command": "tools/ci/scripts/run-local-ci.sh",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["data"]["remote_availability"]["state"] == "not_probed"
    assert payload["summary"]["next_publication_action"] == (
        "remote availability not probed; local-ci fallback evidence is current at HEAD"
    )


def test_publish_reports_stale_local_ci_fallback_evidence_when_manifest_head_differs(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "ok": True,
                "head": "stale-head",
                "command": "tools/ci/scripts/run-local-ci.sh",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)

    evidence_status = payload["data"]["local_ci_fallback"]["evidence_status"]
    assert evidence_status["state"] == "stale"
    assert evidence_status["current_head"] == head
    assert evidence_status["evidence_head"] == "stale-head"
    assert payload["summary"]["next_publication_action"] == (
        "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
    )

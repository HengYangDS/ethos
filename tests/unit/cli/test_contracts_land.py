from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
import ethos.surface.cli.root.lifecycle as lifecycle_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.openspec.cli import openspec_base_command
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import init_repo_with_candidate
from tests.support.contract_helpers import lane_start_arguments
from tests.support.contract_helpers import seed_executed_proof
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.contract_helpers import write_role_policy
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path


def _expected_proof_readiness(
    worktree: Path, head: str, *, state: str, required_gaps: tuple[str, ...]
) -> dict[str, object]:
    blocking = bool(required_gaps)
    next_action = f"ethos prove --execute --expect-head {head} --json" if blocking else ""
    return {
        "kind": "proof_attestation_readiness",
        "head": head,
        "state": state,
        "blocking": blocking,
        "required_gaps": list(required_gaps),
        "next_action": next_action,
        "local_readiness": not blocking,
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


def _archive_fixture_change(
    monkeypatch: pytest.MonkeyPatch,
    worktree: Path,
) -> str:
    """Archive the fixture Change through the official OpenSpec CLI and advance its Lease."""
    completed_head = commit_fixture_file(
        worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    archive_command = openspec_base_command()
    assert archive_command is not None
    archive = subprocess.run(
        [*archive_command, "archive", "fixture-change", "--yes", "--json"],
        cwd=worktree,
        text=True,
        capture_output=True,
        check=False,
    )
    assert archive.returncode == 0, archive.stderr
    git(worktree, "add", ".")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "archive fixture change",
    )
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook = run_ethos(
        "hook",
        "ref-transaction",
        f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        completed_head,
        archived_head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook["ok"] is True
    return archived_head


def test_land_dry_run_reports_dirty_work_lane_gap(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    worktree = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, worktree), cwd=repo)
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "work_lane_dirty" in payload["required_gaps"]


def test_land_blocks_completed_active_openspec_change_before_candidate_landing(
    tmp_path: Path, monkeypatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    worktree = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, worktree), cwd=repo)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert openspec_mode == "shape"
        return {"ok": True, "required_gaps": [], "root": root.as_posix()}

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda *_args: {
            "command": ["openspec", "list", "--json"],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {
                "changes": [
                    {
                        "name": "sample-change",
                        "completedTasks": 1,
                        "totalTasks": 1,
                        "status": "complete",
                    }
                ]
            },
            "parse_error": "",
        },
    )
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["sample-change"]


def test_land_dry_run_reports_stale_candidate_base_with_refresh_action(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
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


def test_land_dry_run_requires_executed_proof_before_ready_state(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["proof_not_proven"]
    assert payload["next_actions"] == [f"ethos prove --execute --expect-head {work_head} --json"]
    assert payload["data"]["proof_readiness"] == _expected_proof_readiness(
        worktree, work_head, state="missing", required_gaps=("proof_not_proven",)
    )


def test_land_blocks_active_change_even_when_exact_head_is_proven(tmp_path: Path) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [
        "openspec_active_change_unarchived:fixture-change:work_lane"
    ]
    assert payload["next_actions"] == ["openspec archive fixture-change --yes --json"]
    assert payload["data"]["proof_readiness"] == {}
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "land",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "block"
    assert mutation["decision"]["subject"]["action"] == "candidate.integrate"
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["source_head"] == work_head
    assert expected_state["source_ref"] == "refs/heads/work/feature"
    assert expected_state["target_ref"] == "refs/heads/candidate/dev"
    assert expected_state["holder_ref"] == "agent:test:case:agent-test"
    assert expected_state["lease_id"].startswith("lease:")
    assert expected_state["lease_epoch"] == 1
    assert mutation["decision"]["required_gaps"] == payload["required_gaps"]
    assert mutation["decision"]["mints_authority"] is False
    assert "authorized" not in mutation


def test_land_apply_refuses_active_change_without_updating_candidate(tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)

    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [
        "openspec_active_change_unarchived:fixture-change:work_lane"
    ]
    assert payload["next_actions"] == ["openspec archive fixture-change --yes --json"]
    assert payload["data"]["candidate_update"] == {}
    assert git(candidate, "rev-parse", "HEAD") == candidate_head


def test_land_allows_officially_archived_work_lane_head(monkeypatch, tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    archived_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, archived_head)
    payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        archived_head,
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is True
    assert payload["state"] == "candidate_validated"
    assert payload["required_gaps"] == []
    assert git(candidate, "rev-parse", "HEAD") == archived_head


def test_lane_refresh_base_apply_rebases_stale_work_lane(tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
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


@pytest.mark.parametrize("command", ["land", "publish"])
def test_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path, command: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    payload = run_ethos_blocked(
        command, "--apply", "--authorize", "--expect-head", head, "--json", cwd=repo
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
    assert mutation["decision"]["verdict"] == "unknown"
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


def test_publish_blocks_exact_head_proof_gap_without_parallel_quality_verdict(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    gap = "proof_attestation_stale:quality-policy"
    monkeypatch.setattr(lifecycle_cli, "repository_context", lambda _repo: {"profile": "test"})
    monkeypatch.setattr(lifecycle_cli, "proof_gaps", lambda _repo, _head: [gap])
    payload = run_ethos("publish", "--json", cwd=repo)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [gap]
    assert payload["summary"]["local_readiness"] is False
    assert "hard_quality_floor" not in payload["data"]


def test_publish_apply_defers_when_remote_transition_is_not_performed(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    lease_head = git(worktree, "rev-parse", "HEAD")
    head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook = run_ethos(
        "hook",
        "ref-transaction",
        "refs/heads/work/feature",
        lease_head,
        head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook["ok"] is True
    seed_executed_proof(worktree, head)
    payload = run_ethos_blocked(
        "publish", "--apply", "--authorize", "--expect-head", head, "--json", cwd=worktree
    )
    assert payload["ok"] is False
    assert payload["state"] == "publication_deferred"
    assert payload["required_gaps"] == []
    assert payload["summary"]["local_readiness"] is True
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


@pytest.mark.parametrize(
    "arguments",
    [
        ("origin", "ssh://git@example.invalid/group/repo.git"),
        ("unexpected",),
    ],
    ids=("hidden-pre-push", "non-hook"),
)
def test_publish_rejects_positional_arguments(tmp_path: Path, arguments: tuple[str, ...]) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    assert run_ethos_raw("publish", "--json", *arguments, cwd=repo).returncode != 0


def test_publish_dry_run_blocks_release_root_active_openspec_residue(tmp_path: Path) -> None:
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
    assert payload["data"]["release_root_open_spec"] == {"required_gaps": [gap], "blocking": True}


def _prepare_configured_branch_roles(tmp_path: Path) -> tuple[Path, Path, Path, str]:
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
        proposal_branch_prefix="review/",
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
    start_payload = run_ethos(*lane_start_arguments(repo, worktree, name="configured"), cwd=repo)
    assert start_payload["ok"] is True
    assert start_payload["data"]["branch"] == "lane/configured"
    assert start_payload["data"]["base"] == "stage/integration"
    assert start_payload["summary"] == {
        "branch": "lane/configured",
        "path": worktree.resolve().as_posix(),
    }
    return repo, candidate_path, worktree, accepted_head


def _commit_configured_lane(monkeypatch, worktree: Path) -> str:
    lease_head = git(worktree, "rev-parse", "HEAD")
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
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook_payload = run_ethos(
        "hook",
        "ref-transaction",
        "refs/heads/lane/configured",
        lease_head,
        work_head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook_payload["ok"] is True
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    return work_head


def _assert_configured_publish(payload: dict[str, object]) -> None:
    assert payload["ok"] is True
    assert payload["summary"]["mode"] == "local_readiness"
    assert payload["summary"]["local_readiness"] is True
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["summary"]["remote_publication_state"] == "deferred"
    assert payload["summary"]["hosted_ci_status_claimed"] is False
    assert payload["summary"]["proposal_branch"] == "review/configured"
    assert payload["data"]["publication"]["proposal_branch"] == "review/configured"
    local_proposal = payload["data"]["publication"]["local_proposal_package"]
    assert local_proposal["kind"] == "proposal_branch_plan"
    assert local_proposal["source_branch"] == "lane/configured"
    assert local_proposal["proposal_branch"] == "review/configured"
    assert local_proposal["remote_push"] == "not_performed"
    assert local_proposal["remote_state"] == "deferred"
    assert payload["data"]["publication"]["remote_state"] == "deferred"
    assert local_proposal["blocking"] is False
    assert local_proposal["remote_availability"]["blocking"] is False
    assert local_proposal["local_ci_fallback"]["kind"] == "local_ci_fallback"
    assert local_proposal["local_ci_fallback"]["hosted_ci_status_claimed"] is False
    assert local_proposal["required_steps"] == [
        "land work lane to candidate role",
        "fast-forward accepted root from candidate role",
        "run local-ci fallback when remote publication is unavailable",
        "create configured proposal branch when remote publication is available",
    ]


def _land_configured_lane(
    repo: Path,
    candidate_path: Path,
    worktree: Path,
    accepted_head: str,
    work_head: str,
) -> None:
    land_payload = run_ethos(
        "land", "--apply", "--authorize", "--expect-head", work_head, "--json", cwd=worktree
    )
    assert land_payload["ok"] is True
    assert land_payload["data"]["candidate_update"]["branch"] == "stage/integration"
    assert land_payload["data"]["candidate_update"]["attestation"]["kind"] == "effect"
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
    assert accepted_update["attestation"]["kind"] == "effect"
    assert accepted_update["attestation"]["content"]["state"] == "applied"


def _retire_configured_lane(repo: Path, work_head: str) -> None:
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
    assert retire_payload["data"]["mutation"]["request"]["expect_head"] == work_head


def test_configured_branch_roles_drive_local_lifecycle_commands(
    monkeypatch, tmp_path: Path
) -> None:
    repo, candidate_path, worktree, accepted_head = _prepare_configured_branch_roles(tmp_path)
    work_head = _commit_configured_lane(monkeypatch, worktree)
    publish_payload = run_ethos("publish", "--json", cwd=worktree)
    _assert_configured_publish(publish_payload)
    _land_configured_lane(repo, candidate_path, worktree, accepted_head, work_head)
    _retire_configured_lane(repo, work_head)


def test_publish_invalid_topology_does_not_infer_origin_remote(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    (repo / ".ethos" / "release.toml").write_text("[publication]\n", encoding="utf-8")

    payload = run_ethos("publish", "--json", cwd=repo)

    assert "publication_topology_gitlab_remote_missing" in payload["required_gaps"]
    expected_state = payload["data"]["mutation"]["decision"]["subject"]["expected_state"]
    assert expected_state["remote"] == ""
    assert [target["remote"] for target in expected_state["remote_targets"]] == ["", ""]


def test_publish_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    payload = run_ethos_blocked("publish", "--apply", "--json", cwd=repo)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("evidence_head_kind", "expected_state", "expected_action", "expected_actions"),
    [
        (
            "current",
            "current",
            "remote unavailable; local-ci fallback evidence is current at HEAD",
            ("remote unavailable; local-ci fallback evidence is current at HEAD", "ethos status"),
        ),
        ("stale", "stale", "run tools/ci/scripts/run-local-ci.sh as local fallback evidence", None),
    ],
    ids=("current", "stale"),
)
def test_publish_reports_local_ci_fallback_evidence(
    tmp_path: Path,
    evidence_head_kind: str,
    expected_state: str,
    expected_action: str,
    expected_actions: tuple[str, ...] | None,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    evidence_head = head if evidence_head_kind == "current" else "stale-head"
    fallback = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "ok": True,
                "head": evidence_head,
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
    assert evidence_status["state"] == expected_state
    assert evidence_status["current_head"] == head
    assert evidence_status["evidence_head"] == evidence_head
    assert payload["summary"]["next_publication_action"] == expected_action
    if expected_actions is not None:
        assert payload["next_actions"] == list(expected_actions)


def test_publish_blocks_without_exact_head_plan_proof(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["ok"] is False
    assert "proof_not_proven" in payload["required_gaps"]


def test_prove_scope_helpers_bind_known_and_unknown_scopes_without_host_claims() -> None:
    known = proof_cli.proof_scope_binding("  docs  ")
    unknown = proof_cli.proof_scope_binding("custom scope")

    assert known["scope"] == "docs"
    assert known["accepted"] is True
    assert known["required_gaps"] == []
    assert unknown["scope"] == "custom scope"
    assert unknown["accepted"] is False
    assert unknown["required_gaps"] == ["unknown_proof_scope:custom scope"]
    assert proof_cli.host_probe_boundary(host=True, probe=False) == {
        "requested": True,
        "host": True,
        "probe": False,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "boundary_recorded",
    }


def test_prove_reports_plan_compile_and_admission_failures_as_public_gaps(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    def rejected_plan(*_args, **_kwargs):
        class RejectedPlan:
            verdict = "block"

            @staticmethod
            def gaps() -> tuple[str, ...]:
                return ("repository_subject_mismatch",)

        return RejectedPlan()

    monkeypatch.setattr(proof_cli, "proof_plan", rejected_plan)
    rejected = run_ethos_blocked("prove", "--json", cwd=repo)
    assert rejected["required_gaps"] == ["repository_subject_mismatch"]
    assert rejected["next_actions"] == ["repair the Commitment or repository facts"]

    monkeypatch.setattr(
        proof_cli,
        "proof_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("change_missing")),
    )
    missing = run_ethos_blocked("prove", "--json", cwd=repo)
    assert missing["required_gaps"] == ["change_missing"]
    assert missing["next_actions"] == ["ethos adopt"]


def test_prove_public_command_keeps_focused_host_probe_evidence_separate(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    class ReadyPlan:
        verdict = "pass"
        nodes: tuple[object, ...] = ()

        @staticmethod
        def gaps() -> tuple[str, ...]:
            return ()

        @staticmethod
        def ordered_nodes() -> tuple[object, ...]:
            return ()

        @staticmethod
        def to_dict() -> dict[str, object]:
            return {}

    monkeypatch.setattr(
        proof_cli.status_domain,
        "audit_for_root",
        lambda *_args, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {},
            "openspec": {},
        },
    )
    monkeypatch.setattr(proof_cli, "change_scope_paths_from_status", lambda *_args: ())
    monkeypatch.setattr(
        proof_cli,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": [], "summary": {}},
    )
    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: ReadyPlan())
    payload = run_ethos("prove", "--scope", "docs", "--host", "--probe", "--json", cwd=repo)

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["summary"]["boundary"] == "focused"
    assert payload["data"]["scope_binding"]["scope"] == "docs"
    assert payload["data"]["host_probe"] == {
        "requested": True,
        "host": True,
        "probe": True,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "boundary_recorded",
    }

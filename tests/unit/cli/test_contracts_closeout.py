from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import add_candidate_worktree

if TYPE_CHECKING:
    from pathlib import Path


def test_land_closeout_apply_fast_forwards_accepted_root_from_candidate(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
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
    assert payload["next_actions"] == [
        "ethos lane retire landed --branch <work-branch> --expect-head <work-lane-head>"
    ]
    accepted_update = payload["data"]["accepted_update"]
    assert accepted_update["ok"] is True
    assert accepted_update["state"] == "accepted_validated"
    assert accepted_update["branch"] == "dev"
    assert accepted_update["source_branch"] == "candidate/dev"
    assert accepted_update["head"] == candidate_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["required_gaps"] == []
    attestation = accepted_update["attestation"]
    assert attestation["predicate"] == "effect:git-ref-update"
    assert attestation["subject"]
    assert attestation["statement"]["result"]["state"] == "applied"
    assert attestation["statement"]["repository"].startswith("repository:")
    assert attestation["statement"]["input"]["head"] == accepted_head
    assert attestation["statement"]["output"]["head"] == candidate_head
    assert attestation["statement"]["freshness"]["head"] == candidate_head
    assert attestation["statement"]["output_digest"]
    assert not {"kind", "content", "mints_authority"} & set(attestation)
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert git(repo, "rev-parse", "HEAD") == candidate_head


def test_land_closeout_defers_control_replacement_without_signed_receipt(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / "src" / "ethos" / "adapters" / "admission"
    path.mkdir(parents=True, exist_ok=True)
    (path / "new_control.py").write_text("CONTROL = 'candidate'\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "replace admission control",
    )
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, candidate_head)
    payload = run_ethos_blocked(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        git(repo, "rev-parse", "HEAD"),
        "--json",
        cwd=repo,
    )
    control = payload["data"]["control_replacement"]
    assert control["required"] is True
    assert control["verdict"] == "unknown"
    assert payload["state"] == "deferred"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"
    assert "independent_verification_receipt_required" in payload["required_gaps"]
    bootstrap = payload["data"]["closeout_bootstrap"]
    verification = bootstrap["independent_verification"]
    assert verification["required"] is True
    assert verification["proof_floor_id"] == "ethos:control-replacement:v1"
    assert verification["receipt_option"] == "--independent-verification-receipt <absolute-path>"
    assert verification["trust_boundary"] == "protected-provider"
    assert verification["mints_authority"] is False
    assert git(repo, "rev-parse", "HEAD") != candidate_head


def test_land_closeout_audits_candidate_content_before_fast_forward(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, candidate_head)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert openspec_mode == "shape"
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


def test_land_closeout_dry_run_reports_expect_head_mismatch(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    payload = run_ethos("land", "--closeout", "--expect-head", candidate_head, "--json", cwd=repo)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["expect_head_mismatch"]
    assert payload["data"]["mutation"]["decision"]["verdict"] == "block"
    assert payload["data"]["closeout_bootstrap"]["required_gaps"] == ["expect_head_mismatch"]


def test_land_closeout_dry_run_reports_accepted_root_required(tmp_path: Path) -> None:
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
    assert payload["data"]["mutation"]["decision"]["verdict"] == "block"
    assert payload["data"]["closeout_bootstrap"]["required_gaps"] == ["accepted_root_required"]


def test_land_closeout_dry_run_reports_current_when_candidate_matches_accepted(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    accepted_head = git(repo, "rev-parse", "HEAD")
    payload = run_ethos("land", "--closeout", "--json", cwd=repo)
    assert payload["ok"] is True
    assert payload["state"] == "accepted_current"
    assert payload["required_gaps"] == []
    assert payload["next_actions"] == ["ethos publish"]
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "closeout",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "pass"
    assert mutation["decision"]["subject"]["action"] == "accepted.advance"
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["accepted_ref"] == "refs/heads/dev"
    assert expected_state["accepted_head"] == accepted_head
    assert expected_state["candidate_ref"] == "refs/heads/candidate/dev"
    assert expected_state["candidate_head"] == accepted_head
    assert mutation["decision"]["why"] == ["candidate_already_current"]
    assert payload["data"]["closeout_bootstrap"]["state"] == "current"
    assert payload["data"]["closeout_bootstrap"]["next_action"] == "ethos publish"


def test_land_closeout_apply_is_noop_when_candidate_matches_accepted_without_proof(
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
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )
    assert payload["ok"] is True
    assert payload["state"] == "accepted_current"
    assert payload["required_gaps"] == []
    assert payload["next_actions"] == ["ethos publish"]
    accepted_update = payload["data"]["accepted_update"]
    assert accepted_update["state"] == "accepted_current"
    assert accepted_update["head"] == accepted_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["attestation"] == {}
    assert git(repo, "rev-parse", "HEAD") == accepted_head


def test_land_closeout_exposes_bootstrap_package_for_current_runner(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
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
    assert bootstrap["state"] == "ready"
    assert bootstrap["accepted_head"] == accepted_head
    assert bootstrap["candidate_head"] == candidate_head
    assert bootstrap["proof_target"]["root"] == candidate.resolve().as_posix()
    verification = bootstrap["independent_verification"]
    assert verification["required"] is False
    assert verification["proof_floor_id"] == "ethos:control-replacement:v1"
    assert verification["receipt_option"] == "--independent-verification-receipt <absolute-path>"
    assert verification["trust_boundary"] == "protected-provider"
    assert verification["mints_authority"] is False


def test_land_closeout_bootstrap_proof_target_stays_candidate_when_blocked(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")
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
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    commit_fixture_file(candidate, "README.md", "# candidate change\n", "candidate change")

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert root.resolve() == candidate.resolve()
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
    payload = run_ethos("land", "--closeout", "--json", cwd=repo)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["root"] == candidate.as_posix()

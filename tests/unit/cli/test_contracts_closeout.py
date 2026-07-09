from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked

if TYPE_CHECKING:
    from pathlib import Path


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
    assert payload["next_actions"] == [
        "ethos lane retire-landed --branch <work-branch> --expect-head <work-lane-head>"
    ]
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
    assert payload["data"]["mutation"]["decision"] == "current"
    assert payload["data"]["mutation"]["current_head"] == accepted_head
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
    assert git(repo, "rev-parse", "HEAD") == accepted_head


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
    import ethos.surface.cli.root.lifecycle as lifecycle_cli

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
        lifecycle_cli,
        "completed_active_changes_report",
        fake_openspec_lifecycle,
        raising=False,
    )

    payload = run_ethos("land", "--closeout", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["root"] == candidate.as_posix()

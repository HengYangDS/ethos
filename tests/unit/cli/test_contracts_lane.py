from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.store import state
from ethos.repository.adoption.planner import adoption_plan

if TYPE_CHECKING:
    from pathlib import Path

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


def test_lane_status_reports_live_workspace_schema_validation() -> None:
    payload = run_ethos("lane", "status", "--json")

    validations = [
        diagnostic
        for diagnostic in payload["diagnostics"]
        if diagnostic.get("kind") == "schema_validation"
    ]
    assert validations == [
        {
            "kind": "schema_validation",
            "target": "data",
            "schema": "workspace-status.schema.json",
            "ok": True,
            "required_gaps": [],
        }
    ]


def test_lane_prewrite_command_rejects_accepted_root(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked(
        "lane",
        "prewrite",
        "README.md",
        "--root",
        repo.as_posix(),
        "--editor-root",
        repo.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["command"] == "lane prewrite"
    assert "protected_lane_prewrite_blocked" in payload["required_gaps"]


def test_lane_prewrite_command_requires_editor_root_for_work_lane(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    payload = run_ethos_blocked(
        "lane",
        "prewrite",
        "README.md",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["command"] == "lane prewrite"
    assert "editor_root_missing" in payload["required_gaps"]


def test_lane_prewrite_defaults_to_cwd_git_root_for_worktree_subdirectories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    nested = worktree / "packages" / "ethos"
    nested.mkdir(parents=True)

    payload = run_ethos(
        "lane",
        "prewrite",
        "README.md",
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=nested,
    )

    assert payload["ok"] is True
    assert payload["data"]["role"] == "work_lane"
    assert payload["data"]["editor_root"]["expected"] == worktree.resolve().as_posix()
    assert payload["data"]["paths"][0]["path"] == (worktree / "README.md").as_posix()


def test_hook_admit_pre_tool_blocks_accepted_root(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked(
        "hook",
        "admit",
        "pre-tool",
        "README.md",
        "--root",
        repo.as_posix(),
        "--editor-root",
        repo.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["command"] == "hook admit"
    assert payload["state"] == "blocked"
    assert payload["summary"] == {
        "layer": "pre-tool",
        "role": "accepted_root",
        "decision": "block",
    }
    assert payload["data"]["decision"] == {
        "action": "block",
        "reason": "protected_lane_prewrite_blocked",
    }
    assert "protected_lane_prewrite_blocked" in payload["required_gaps"]


def test_hook_admit_pre_run_blocks_mutation_risk_without_paths(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked(
        "hook",
        "admit",
        "pre-run",
        "--root",
        repo.as_posix(),
        "--editor-root",
        repo.as_posix(),
        "--require-editor-root",
        "--command",
        'python -c \'from pathlib import Path; Path("README.md").write_text("x")\'',
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["command"] == "hook admit"
    assert payload["state"] == "blocked"
    assert payload["data"]["command_risk"]["tracked_mutation_risk"] is True
    assert "hook_prerun_paths_required" in payload["required_gaps"]


def test_hook_install_wires_hooks_path(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    hooks_dir = repo / ".githooks"
    hooks_dir.mkdir()
    (hooks_dir / "pre-commit").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (hooks_dir / "pre-push").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (hooks_dir / "reference-transaction").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )

    payload = run_ethos(
        "hook",
        "install",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["command"] == "hook install"
    assert payload["state"] == "installed"
    assert payload["data"]["hooks_path"] == ".githooks"
    configured = git(repo, "config", "core.hooksPath")
    assert configured == ".githooks"


def test_hook_install_blocks_when_hook_script_missing(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked(
        "hook",
        "install",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert "hook_script_missing:.githooks/pre-commit" in payload["required_gaps"]


def test_lane_start_apply_creates_worktree_and_lease(tmp_path: Path) -> None:
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

    payload = run_ethos(
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

    assert payload["ok"] is True
    assert payload["command"] == "lane start"
    assert payload["data"]["branch"] == "work/feature"
    assert payload["data"]["worktree"] == {
        "branch": "work/feature",
        "path": worktree.resolve().as_posix(),
        "head": git(worktree, "rev-parse", "HEAD"),
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert git(worktree, "branch", "--show-current") == "work/feature"


def test_lane_start_accepts_claim_binding(tmp_path: Path) -> None:
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

    payload = run_ethos(
        "lane",
        "start",
        "feature",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--owner",
        "agent:test",
        "--claim-id",
        "sample-trust",
        "--apply",
        "--json",
        cwd=repo,
    )

    status = run_ethos("status", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is True
    assert payload["data"]["claim_id"] == "sample-trust"
    assert status["data"]["closeout_support"]["claim_id"] == "sample-trust"
    assert status["data"]["closeout_support"]["claim_binding"] == "bound"


def test_lane_bind_claim_applies_to_existing_work_lane(tmp_path: Path) -> None:
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

    payload = run_ethos(
        "lane",
        "bind-claim",
        "--claim-id",
        "sample-trust",
        "--apply",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    status = run_ethos("lane", "status", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["ok"] is True
    assert payload["command"] == "lane bind-claim"
    assert payload["state"] == "bound"
    assert payload["data"]["branch"] == "work/feature"
    assert payload["data"]["claim_id"] == "sample-trust"
    assert status["data"]["closeout_support"]["claim_id"] == "sample-trust"
    assert status["data"]["closeout_support"]["claim_binding"] == "bound"


def test_status_reports_foreign_work_lane_as_coordination_gap(tmp_path: Path) -> None:
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

    payload = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["coordination_gaps"] == ["foreign_work_lane_present"]
    lane = payload["data"]["foreign_work_lanes"][0]
    assert lane["path"] == worktree.as_posix()
    assert lane["head"] == git(worktree, "rev-parse", "HEAD")
    assert lane["branch"] == "work/feature"
    assert lane["lease_owner"] == "agent:test"
    assert lane["path_scope"] == []
    assert lane["coordination_state"] == "advisory"
    assert lane["current_actor_capability"] == "observe"
    assert lane["allowed_actions"] == ["observe"]
    assert lane["forbidden_actions"] == ["write", "land", "retire"]
    assert lane["write_policy"] == "owner_only"
    assert lane["retire_policy"] == "owner_handoff_or_maintainer_break_glass"
    assert lane["handoff_required"] is True


def test_status_marks_raw_git_worktree_without_ethos_lease(tmp_path: Path) -> None:
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
    raw_worktree = tmp_path / "repo-work-raw"
    git(repo, "worktree", "add", "-b", "work/raw", raw_worktree.as_posix(), "dev")

    root_payload = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    raw_payload = run_ethos(
        "status",
        "--root",
        raw_worktree.as_posix(),
        "--json",
        cwd=raw_worktree,
    )

    assert root_payload["ok"] is True
    assert root_payload["required_gaps"] == []
    assert root_payload["data"]["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_missing_lease:work/raw",
    ]
    assert root_payload["data"]["foreign_work_lanes"][0]["lease_state"] == "missing"
    assert root_payload["data"]["foreign_work_lanes"][0]["lease_owner"] == ""
    assert raw_payload["ok"] is True
    assert raw_payload["required_gaps"] == ["work_lane_missing_lease:work/raw"]
    assert raw_payload["data"]["closeout_support"]["supported"] is False
    assert raw_payload["data"]["closeout_support"]["required_gaps"] == [
        "work_lane_missing_lease:work/raw"
    ]


def test_status_reports_unbound_work_lane_ref_as_advisory_signal(tmp_path: Path) -> None:
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
    git(repo, "branch", "work/stale-ref", "dev")

    payload = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    bindings = {binding["branch"]: binding for binding in payload["data"]["branch_bindings"]}
    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["foreign_work_lanes"] == []
    assert payload["data"]["coordination_gaps"] == ["unbound_work_lane_ref_present"]
    assert payload["data"]["coordination"]["blocking"] is False
    assert payload["data"]["coordination"]["unbound_work_lane_count"] == 1
    assert payload["data"]["coordination"]["unbound_work_lane_refs"] == [
        {
            "branch": "work/stale-ref",
            "head": git(repo, "rev-parse", "dev"),
            "claim_id": "",
            "claim_binding": "missing",
            "relation_to_accepted": "ancestor_of_accepted",
            "next_action": (
                "retire unbound Work Lane ref after confirming no external owner depends on it"
            ),
        }
    ]
    assert (
        payload["data"]["coordination"]["next_action"]
        == "inspect or retire unbound Work Lane refs during coordination cleanup"
    )
    assert bindings["work/stale-ref"]["role"] == "work_lane"
    assert bindings["work/stale-ref"]["worktree_binding"] == "unbound"
    assert bindings["work/stale-ref"]["worktree_path"] == ""


def test_lane_candidate_apply_creates_candidate_branch(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate_path = tmp_path / "repo-candidate-dev"
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
        "lane",
        "candidate",
        "--root",
        repo.as_posix(),
        "--path",
        candidate_path.as_posix(),
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["command"] == "lane candidate"
    assert payload["state"] == "bootstrapped"
    assert payload["data"]["branch"] == "candidate/dev"
    assert git(repo, "rev-parse", "candidate/dev") == head
    assert git(candidate_path, "branch", "--show-current") == "candidate/dev"


def test_lane_candidate_apply_default_path_uses_configured_candidate_role(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    expected_candidate_path = tmp_path / "repo-stage-dev"
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
        "lane",
        "candidate",
        "--root",
        repo.as_posix(),
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "bootstrapped"
    assert payload["data"]["branch"] == "stage/dev"
    assert payload["data"]["path"] == expected_candidate_path.as_posix()
    assert git(expected_candidate_path, "branch", "--show-current") == "stage/dev"


def test_lane_retire_landed_summary_marks_selected_unmerged_lane_not_ready(
    monkeypatch, tmp_path: Path
) -> None:
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
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    active = tmp_path / "repo-work-active"
    git(repo, "worktree", "add", "-b", "work/active", active.as_posix(), "dev")
    (active / "README.md").write_text("# active\n", encoding="utf-8")
    git(active, "add", "README.md")
    git(
        active,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "active work",
    )
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/active",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    payload = run_ethos_blocked(
        "lane",
        "retire-landed",
        "--branch",
        "work/active",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["work_lane_not_merged"]
    assert payload["summary"] == {
        "landed_lane_count": 1,
        "selected_branch": "work/active",
        "selected_retire_ready": False,
        "selected_blockers": ["work_lane_not_merged"],
    }


def test_lane_retire_landed_dry_run_blocks_foreign_lane_without_authority(tmp_path: Path) -> None:
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
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    payload = run_ethos_blocked(
        "lane",
        "retire-landed",
        "--branch",
        "work/foreign",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-landed"
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert foreign.exists()


def test_lane_retire_landed_apply_requires_explicit_branch(tmp_path: Path) -> None:
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
    worktree = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", worktree.as_posix(), "dev")

    payload = run_ethos_blocked(
        "lane",
        "retire-landed",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-landed"
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["retire_branch_required"]
    assert worktree.exists()


def test_lane_retire_landed_apply_requires_expected_head(monkeypatch, tmp_path: Path) -> None:
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
    worktree = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", worktree.as_posix(), "dev")

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    payload = run_ethos_blocked(
        "lane",
        "retire-landed",
        "--branch",
        "work/landed",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-landed"
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["expect_head_required"]
    assert worktree.exists()


def test_lane_retire_landed_apply_removes_selected_branch(monkeypatch, tmp_path: Path) -> None:
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
    worktree = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", "work/landed", worktree.as_posix(), "dev")
    worktree_head = git(worktree, "rev-parse", "HEAD")

    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/landed",
        owner="agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")
    payload = run_ethos(
        "lane",
        "retire-landed",
        "--branch",
        "work/landed",
        "--expect-head",
        worktree_head,
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-landed"
    assert payload["ok"] is True
    assert payload["state"] == "retired"
    assert payload["data"]["mutation"]["expect_head"] == worktree_head
    assert not worktree.exists()


def test_lane_retire_unbound_apply_removes_matching_ref(tmp_path: Path) -> None:
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
    git(repo, "branch", "work/stale-ref", "dev")
    head = git(repo, "rev-parse", "work/stale-ref")

    payload = run_ethos(
        "lane",
        "retire-unbound",
        "--branch",
        "work/stale-ref",
        "--expect-head",
        head,
        "--reason",
        "superseded by accepted root",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-unbound"
    assert payload["ok"] is True
    assert payload["state"] == "retired_unbound"
    assert payload["data"]["retired_ref"] == "refs/heads/work/stale-ref"
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", "refs/heads/work/stale-ref"],
            cwd=repo,
            check=False,
        ).returncode
        == 1
    )


def test_lane_retire_unbound_apply_requires_authorization(tmp_path: Path) -> None:
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
    git(repo, "branch", "work/stale-ref", "dev")
    head = git(repo, "rev-parse", "work/stale-ref")

    payload = run_ethos_blocked(
        "lane",
        "retire-unbound",
        "--branch",
        "work/stale-ref",
        "--expect-head",
        head,
        "--reason",
        "superseded by accepted root",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire-unbound"
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["authorization_required"]

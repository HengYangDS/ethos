from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

from ethos.assistants.skill_packages import compute_skill_package_digest
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.branch_roles import load_branch_role_policy
from ethos_core.contracts.package_ontology import package_ontology_report
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw


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


def write_role_policy(
    repo: Path,
    *,
    release_branch: str = "main",
    accepted_branch: str = "dev",
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                f'release_branch = "{release_branch}"',
                f'accepted_branch = "{accepted_branch}"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
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
    exercising land mechanics seed the proof the same way the prove command does.
    """
    from ethos.adapters.mutation.proof import record_executed_proof

    record_executed_proof(repo, head=head, evidence_digest="sha256:test", gate_count=1)


def test_status_json_contract() -> None:
    payload = run_ethos("status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "status"
    assert payload["state"] in {"ready", "dirty"}
    assert payload["next_actions"]


def test_full_proof_requires_executed_evidence() -> None:
    payload = run_ethos("prove", "--full", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "full_proof_requires_execute" in payload["required_gaps"]


def test_prove_gapped_audit_points_to_real_audit_command(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        """---
subject: sample:bad
role: reference
state: active
relations:
  see_also: []
---

# Bad

Status: active.

Purpose: trigger a docs gap.

See also: none.

```bash
proof legacy objective
```
""",
        encoding="utf-8",
    )

    payload = run_ethos("prove", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert payload["next_actions"] == ["ethos audit --mode deep"]


def test_executed_proof_blocks_ethos_json_gate_failures(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "---\nsubject: sample:guide\nrole: guide\nstate: active\nrelations: {}\n---\n\n# Guide\n\nBody without required visible sections.",
        encoding="utf-8",
    )

    payload = run_ethos(
        "prove",
        "--execute",
        "--gate",
        "docs-registry",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    run = payload["data"]["evidence"]["runs"][0]
    assert run["action_id"] == "docs-registry"
    assert run["state"] == "blocked"
    assert run["verdict"] == "failed"
    assert run["diagnostics"][0]["required_gaps"] == [
        "missing_visible_section:docs/guide.md:status",
        "missing_visible_section:docs/guide.md:purpose",
        "missing_visible_section:docs/guide.md:see also",
    ]


def test_default_proof_reports_readiness_not_proven() -> None:
    payload = run_ethos("prove", "--json")

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["data"]["executed"] is False
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"planned"}
    assert all(run["trust_bearing"] is False for run in payload["data"]["evidence"]["runs"])


def test_prove_accepts_matching_expected_head() -> None:
    head = git(Path.cwd(), "rev-parse", "HEAD")

    payload = run_ethos("prove", "--expect-head", head, "--json")

    assert payload["ok"] is True
    assert payload["state"] == "ready"
    assert payload["required_gaps"] == []
    assert payload["data"]["expected_head"] == {
        "expected": head,
        "current": head,
        "ok": True,
    }


def test_prove_rejects_mismatched_expected_head() -> None:
    payload = run_ethos("prove", "--expect-head", "not-the-current-head", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "expected_head_mismatch" in payload["required_gaps"]
    assert payload["data"]["expected_head"]["expected"] == "not-the-current-head"
    assert payload["data"]["expected_head"]["ok"] is False


def test_init_apply_rejects_untracked_expected_head(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()

    payload = run_ethos_blocked(
        "init",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "untracked",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "git_repository_missing" in payload["required_gaps"]
    assert not (target / ".ethos" / "project.toml").exists()

    assert payload["data"]["mutation"] == {
        "apply": True,
        "authorized": True,
        "expect_head": "untracked",
        "current_head": "untracked",
    }


def test_adopt_apply_rejects_untracked_expected_head(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()

    payload = run_ethos_blocked(
        "adopt",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "untracked",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "git_repository_missing" in payload["required_gaps"]
    assert not (target / ".ethos" / "project.toml").exists()


def test_init_apply_flag_applies_scaffold_in_git_repo(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "sample")
    head = git(target, "rev-parse", "HEAD")

    payload = run_ethos(
        "init",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "applied"
    assert (target / ".ethos" / "project.toml").exists()

    status = run_ethos("status", "--root", target.as_posix(), "--json")
    docs = run_ethos("quality", "docs-registry", "--root", target.as_posix(), "--json")
    examples = run_ethos(
        "quality",
        "command-examples",
        "--root",
        target.as_posix(),
        "--json",
    )

    assert status["ok"] is True
    assert docs["ok"] is True
    assert examples["ok"] is True


def test_quality_package_ontology_reports_migration_state() -> None:
    payload = run_ethos("quality", "package-ontology", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality package-ontology"
    assert payload["data"]["migration_complete"] is True
    assert payload["data"]["migration_status"] == "complete"
    assert "ethos" in payload["data"]["target_packages"]
    assert "ethos-core" in payload["data"]["target_packages"]
    assert "ethos" not in payload["data"]["migration_hosts"]
    assert payload["data"]["distribution_status"]["distributions/npm"]["state"] == ("migrated")


def test_quality_asset_policy_command_reports_mechanical_quality_assets() -> None:
    payload = run_ethos("quality", "asset-policy", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality asset-policy"
    assert payload["state"] == "clean"
    assert payload["summary"]["asset_class_count"] >= 9
    asset_classes = {asset["class"] for asset in payload["data"]["asset_classes"]}
    assert {"python-code", "markdown-docs", "shell-scripts", "toml-config"} <= asset_classes


def test_quality_docs_command_reports_docs_profile_dimensions() -> None:
    payload = run_ethos("quality", "docs", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality docs"
    assert payload["state"] == "clean"
    checks = {check["id"]: check for check in payload["data"]["profile"]["checks"]}
    assert checks["link-integrity"]["tool_adapter"] == "lychee"
    assert checks["reader-purpose"]["dimensions"] == ["status", "purpose", "see_also"]
    assert payload["data"]["style_goals"] == ["faithful", "expressive", "elegant"]


def test_quality_proof_policy_command_reports_lattice() -> None:
    payload = run_ethos("quality", "proof-policy", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality proof-policy"
    assert payload["state"] == "clean"
    states = {state["state"]: state for state in payload["data"]["states"]}
    assert states["planned"]["trust_bearing"] is False
    assert states["proven"]["trust_bearing"] is True
    assert payload["data"]["trust_consumers"] == [
        "claim",
        "land",
        "publish",
        "release",
        "repository-governance",
    ]


def test_quality_tool_profiles_command_reports_adapter_boundaries() -> None:
    payload = run_ethos("quality", "tool-profiles", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality tool-profiles"
    adapters = {adapter["id"]: adapter for adapter in payload["data"]["tool_adapters"]}
    assert adapters["ruff"]["asset_classes"] == ["python-code"]
    assert adapters["lychee"]["asset_classes"] == ["markdown-docs"]
    assert adapters["shellcheck"]["asset_classes"] == ["shell-scripts"]
    assert adapters["taplo"]["asset_classes"] == ["toml-config"]


def test_quality_docs_registry_surfaces_all_required_gaps(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "---\nsubject: sample:guide\nrole: guide\nstate: active\nrelations: {}\n---\n\n# Guide\n\nBody without required visible sections.",
        encoding="utf-8",
    )

    payload = run_ethos(
        "quality",
        "docs-registry",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["required_gaps"] == [
        "missing_visible_section:docs/guide.md:status",
        "missing_visible_section:docs/guide.md:purpose",
        "missing_visible_section:docs/guide.md:see also",
    ]
    assert payload["data"]["required_gaps"] == payload["required_gaps"]


def test_emit_handles_closed_pipes(monkeypatch) -> None:
    import builtins

    from ethos.surface.cli._base import emit
    from ethos_core.result import EthosResult

    def closed_pipe(*args, **kwargs) -> None:
        raise BrokenPipeError

    monkeypatch.setattr(builtins, "print", closed_pipe)

    emit(EthosResult(command="status", ok=True, state="ready"), json_output=True)


def test_quality_package_ontology_rejects_retired_workspace_config(
    tmp_path: Path,
) -> None:
    for package in package_ontology_report()["target_packages"]:
        (tmp_path / "packages" / str(package)).mkdir(parents=True)
    (tmp_path / "distributions" / "npm").mkdir(parents=True)
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "workspace.toml").write_text(
        '[[package]]\nname = "ethos-kernel"\npath = "packages/ethos-kernel"\n',
        encoding="utf-8",
    )

    completed = run_ethos_raw(
        "quality",
        "package-ontology",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["ok"] is False
    assert "workspace_config_retired_product_family:ethos-kernel" in payload["required_gaps"]


def test_status_json_reports_live_workspace_schema_validation() -> None:
    payload = run_ethos("status", "--json")

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
    assert "schema_validation" not in payload["data"]


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


def test_lane_prewrite_command_requires_editor_root_for_work_lane(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

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
    assert payload["data"]["foreign_work_lanes"] == [
        {
            "path": worktree.as_posix(),
            "head": git(worktree, "rev-parse", "HEAD"),
            "branch": "work/feature",
            "role": "work_lane",
            "worktree_binding": "linked",
            "lease_owner": "agent:test",
            "lease_state": "leased",
            "claim_id": "",
            "claim_binding": "missing",
        }
    ]


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


def test_lane_retire_landed_apply_removes_selected_branch(tmp_path: Path) -> None:
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

    payload = run_ethos(
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
    assert payload["ok"] is True
    assert payload["state"] == "retired"
    assert not worktree.exists()


def test_plan_changed_returns_action_graph() -> None:
    payload = run_ethos("plan", "--changed", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "plan"
    assert "action_graph" in payload["data"]


def test_plan_changed_maps_repository_rules_to_required_gates(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    rules = repo / ".ethos" / "rules.toml"
    rules.write_text(
        """
[gates.unit]
command = "pytest tests/unit"
blocking = true

[[rule]]
id = "python-source"
risk = "source-change"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit-test"]
""".lstrip(),
        encoding="utf-8",
    )
    source = repo / "src" / "demo.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "add governed source",
    )
    source.write_text("VALUE = 2\n", encoding="utf-8")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["summary"]["matched_rule_count"] == 1
    assert payload["summary"]["required_gate_count"] == 1
    assert payload["data"]["matched_rules"][0]["id"] == "python-source"
    assert payload["data"]["matched_rules"][0]["matched_paths"] == ["src/demo.py"]
    assert payload["data"]["required_gates"] == [
        {"id": "unit", "command": "pytest tests/unit", "blocking": True}
    ]


def test_assistants_doctor_accepts_root_for_shadow_parity(tmp_path: Path) -> None:
    payload = run_ethos("assistants", "doctor", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "assistants doctor"


def test_repository_audit_reports_governed_repository_shape() -> None:
    payload = run_ethos("audit", "--mode", "shape", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "audit"
    context = payload["data"]["governance_context"]
    assert context["contract"] == "governed_repository"
    assert context["profile"] == "product"
    assert context["single_kernel"] is True
    assert context["kernel_chain"] == [
        "JudgmentSource",
        "Subject",
        "Commitment",
        "Change",
        "Evidence",
        "Claim",
        "Chronicle",
    ]
    # The head-of-chain nodes are real kernel models, not an inline dict — the
    # JudgmentSource carries the authority order and the Subject is the governed repo.
    assert context["judgment_source"]["authority"] == "system/authority.toml"
    assert context["judgment_source"]["policy_refs"][0] == "user_instruction"
    assert context["subject"]["kind"] == "repository"
    assert context["subject"]["id"] == str(Path.cwd())
    assert context["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert context["scorecard_commands"] == ["ethos report"]
    assert context["truth_boundary"] == "repository"
    assert context["profile_boundary"] == "profile_or_adapter"
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["data"]["openspec"]["mode"] == "shape"
    assert payload["required_gaps"] == []
    package_ontology = payload["data"]["package_ontology"]
    assert package_ontology["ok"] is True
    assert "canonical_packages" not in package_ontology
    assert package_ontology["migration_host_packages"] == []
    assert "ethos-core" in package_ontology["target_package_contract"]


def test_repository_audit_rejects_invalid_mode_as_json_gap() -> None:
    payload = run_ethos("audit", "--mode", "fastish", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "invalid"
    assert payload["required_gaps"] == ["invalid_audit_mode:fastish"]


def test_adopt_dry_run_does_not_write_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    payload = run_ethos("adopt", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "adopt"
    assert ".ethos/project.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()


def test_adopt_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    payload = run_ethos_blocked("adopt", "--root", str(repo), "--apply", "--json", cwd=repo)

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    assert not (repo / ".ethos/project.toml").exists()


def test_adopt_apply_accepts_authorized_matching_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
        "adopt",
        "--root",
        str(repo),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "applied"
    assert payload["data"]["mutation"] == {
        "apply": True,
        "authorized": True,
        "expect_head": head,
        "current_head": head,
    }
    assert (repo / ".ethos/project.toml").exists()


def test_quality_command_registry_rejects_retired_public_roots() -> None:
    payload = run_ethos("quality", "command-registry", "--json")

    assert payload["ok"] is True
    assert payload["data"]["retired_public_roots"] == []
    assert payload["data"]["retired_public_root_mentions"] == []
    assert "ethos status" in payload["data"]["public_commands"]
    assert "ethos intake" not in payload["data"]["public_commands"]
    assert "ethos lane" not in payload["data"]["public_commands"]
    assert "ethos parity" not in payload["data"]["public_commands"]
    assert "ethos intake" in payload["data"]["known_commands"]
    assert "ethos lane" in payload["data"]["known_commands"]
    assert "ethos parity" in payload["data"]["known_commands"]


def test_root_help_foregrounds_workflow_and_hides_maintainer_apps() -> None:
    completed = run_ethos_raw("--help")

    assert completed.returncode == 0
    assert "status" in completed.stdout
    assert "plan" in completed.stdout
    assert "prove" in completed.stdout
    assert "land" in completed.stdout
    assert "publish" in completed.stdout
    assert "report" in completed.stdout
    for maintainer in ("audit", "openspec", "quality", "campaign", "lane", "parity"):
        assert f"│ {maintainer} " not in completed.stdout
    for reference in ("doctor", "docs", "explain"):
        assert f"│ {reference} " not in completed.stdout


def test_quality_standard_registry_declares_adapter_boundaries() -> None:
    payload = run_ethos("quality", "standards", "--json")

    assert payload["ok"] is True
    adapters = payload["data"]["adapters"]
    for adapter in (
        "slsa",
        "sigstore",
        "opentelemetry",
        "dagger",
        "cue",
        "opa",
        "temporal",
        "mcp",
    ):
        assert adapter in adapters
        assert adapters[adapter]["boundary"]
        assert adapters[adapter]["fallback"]
        assert adapters[adapter]["exit_strategy"]


def test_quality_format_policy_reads_repository_policy() -> None:
    payload = run_ethos("quality", "format-policy", "--json")

    assert payload["ok"] is True
    assert payload["data"]["source"] == ".ethos/rules.toml"
    assert payload["data"]["artifacts"]["state_tracked_truth"] is False


def test_quality_schema_gate_and_commit_commands_are_available() -> None:
    for command in (
        ("quality", "schemas", "--json"),
        ("quality", "gates", "--json"),
        ("quality", "commits", "--json"),
        ("quality", "release", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_quality_help_lists_canonical_commands() -> None:
    completed = run_ethos_raw("quality", "--help")

    assert completed.returncode == 0
    commands = set(re.findall(r"^│\s+([a-z][a-z-]+)\s{2,}", completed.stdout, re.MULTILINE))
    assert commands == {
        "asset-policy",
        "claims",
        "code-size",
        "command-examples",
        "command-registry",
        "command-surface",
        "commits",
        "coupling-audit",
        "docs",
        "docs-registry",
        "evidence-freshness",
        "format-policy",
        "gates",
        "markdown-links",
        "npm",
        "package-ontology",
        "projection-drift",
        "proof-policy",
        "provenance",
        "release",
        "release-attestation",
        "release-policy",
        "sbom",
        "schemas",
        "shell",
        "standards",
        "tool-profiles",
        "toml",
        "types",
        "yaml",
    }


def test_openspec_uses_official_native_cli(monkeypatch) -> None:
    from ethos.adapters import openspec

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        if args == ("doctor", "--json"):
            payload = {"root": {"healthy": True}}
        elif args == ("list", "--json"):
            payload = {"changes": [{"name": "ethos-release-hardening", "status": "in-progress"}]}
        elif args == ("status", "--change", "ethos-release-hardening", "--json"):
            payload = {"isComplete": True, "schemaName": "spec-driven"}
        elif args == ("validate", "--all", "--strict", "--json"):
            payload = {"items": [], "summary": {"totals": {"failed": 0}}}
        else:
            raise AssertionError(f"unexpected OpenSpec command: {args}")
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec, "_run_json", fake_run_json)

    payload = run_ethos("openspec", "--change", "ethos-release-hardening", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "openspec"
    assert payload["data"]["official_cli"]["package"] == "@fission-ai/openspec"
    assert payload["data"]["schema_name"] == "spec-driven"
    assert payload["data"]["commands"]["validate"]["json"]["summary"]["totals"]["failed"] == 0


def test_openspec_lifecycle_flag_reports_lifecycle_summary(monkeypatch) -> None:
    def fake_report(root: Path, *, change: str | None = None, lifecycle: bool = False):
        return {
            "ok": True,
            "official_cli": {
                "package": "@fission-ai/openspec",
                "available": True,
                "base_command": ["openspec"],
            },
            "change": change,
            "schema_name": "spec-driven",
            "summary": {"change_count": 1, "validation": {}},
            "required_gaps": [],
            "commands": {},
            "lifecycle": {"enabled": lifecycle, "changes": []},
        }

    monkeypatch.setattr("ethos.cli.openspec_governance_report", fake_report)

    payload = run_ethos("openspec", "--change", "ethos-release-hardening", "--lifecycle", "--json")

    assert payload["ok"] is True
    assert payload["summary"]["lifecycle"] is True
    assert payload["data"]["lifecycle"] == {"enabled": True, "changes": []}


def test_full_gate_registry_includes_official_openspec_validation() -> None:
    payload = run_ethos("quality", "gates", "--json")

    assert payload["ok"] is True
    assert "self-audit" not in payload["data"]["gates"]
    assert payload["data"]["gates"]["repository-audit"]["command"][1:] == [
        "-m",
        "ethos.cli",
        "audit",
        "--mode",
        "shape",
        "--json",
    ]
    assert payload["data"]["gates"]["openspec"]["command"] == [
        "openspec",
        "validate",
        "--all",
        "--strict",
        "--json",
    ]


def test_prove_execute_can_select_real_gates() -> None:
    payload = run_ethos(
        "prove",
        "--execute",
        "--gate",
        "repository-audit",
        "--gate",
        "claims",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["state"] == "proven"
    assert payload["data"]["executed"] is True
    assert payload["summary"]["gate_count"] == 2
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"proven"}
    assert {run["verdict"] for run in payload["data"]["evidence"]["runs"]} == {"passed"}
    assert all(run["trust_bearing"] is True for run in payload["data"]["evidence"]["runs"])


def test_prove_execute_preserves_non_trust_bearing_gate_classification() -> None:
    payload = run_ethos(
        "prove",
        "--execute",
        "--gate",
        "ruff",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "trust_bearing_proof_missing" in payload["required_gaps"]
    assert payload["summary"]["gate_count"] == 1
    run = payload["data"]["evidence"]["runs"][0]
    assert run["action_id"] == "ruff"
    assert run["state"] == "executed"
    assert run["verdict"] == "passed"
    assert run["evidence_class"] == "diagnostic"
    assert run["trust_bearing"] is False


def test_adopt_gitlab_profile_is_available(tmp_path: Path) -> None:
    payload = run_ethos(
        "adopt",
        "--root",
        str(tmp_path),
        "--profile",
        "gitlab",
        "--dry-run",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["data"]["profile"] == "gitlab"
    assert ".gitlab-ci.yml" in payload["data"]["planned_files"]


def test_assistant_mcp_server_command_is_available() -> None:
    payload = run_ethos("assistants", "mcp-server", "--json")

    assert payload["ok"] is True
    assert payload["data"]["server"]["protocol"] == "mcp"


def test_playbooks_commands_expose_repo_local_skills() -> None:
    check = run_ethos("playbooks", "check", "--json")
    route = run_ethos("playbooks", "route", "--subject", "repository-governance", "--json")

    assert check["ok"] is True
    assert check["data"]["skills_root"] == ".agents/skills"
    assert "ethos-repository-governance" in check["data"]["skills"]
    assert route["ok"] is True
    assert route["data"]["selected"][0]["id"] == "ethos-repository-governance"


OFFICIAL_PLAYBOOK_SKILL = """---
name: sample-skill
description: Use when governing sample repositories with ETHOS.
---

# Sample Skill

## When to Use

Use this skill for sample governance work.

## Workflow

1. Read the repository guidance.
2. Run the focused ETHOS check.
3. Record evidence before making a claim.

## Evidence

Run `ethos report --json` and keep the output with the delivery note.

## Trust Boundary

Repository source, tests, schemas, docs, claims, evidence, and command JSON are truth.
"""


def write_v2_playbook_package(skills_root: Path, skill_id: str) -> str:
    package_dir = skills_root / skill_id
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_PLAYBOOK_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    package_manifest = package_dir / "package.toml"
    package_manifest.write_text(
        f"""
schema_version = 2
id = "{skill_id}"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[quality]
placeholder_allowed = false

[[capability]]
id = "ethos.status"
kind = "command_readonly"
command = ["ethos", "status", "--json"]
""".lstrip(),
        encoding="utf-8",
    )
    return package_manifest.as_posix()


def test_playbooks_accept_repo_local_activation_schema_with_path_globs(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    package_manifest = Path(write_v2_playbook_package(skills_root, "code-change"))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "code-change"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "implementation"
operation = "implement"
authority = "primary"
lifecycle = "active"
path_globs = ["src/**"]
intent_tokens = ["implement"]
pre_reads = ["README.md"]
post_checks = ["ethos prove"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )
    (root / "src").mkdir()
    (root / "src" / "code.py").write_text("VALUE = 1\n", encoding="utf-8")

    check = run_ethos("playbooks", "check", "--root", root.as_posix(), "--json")
    route = run_ethos("playbooks", "route", "--changed", "--root", root.as_posix(), "--json")

    assert check["ok"] is True
    assert check["data"]["records"][0]["id"] == "code-change"
    assert check["data"]["records"][0]["path_globs"] == ["src/**"]
    assert "changed-scope" in check["data"]["records"][0]["subjects"]
    assert route["ok"] is True
    assert route["data"]["selected"][0]["id"] == "code-change"
    assert "changed-scope" in route["data"]["selected"][0]["subjects"]
    assert route["data"]["selected"][0]["pre_reads"] == ["README.md"]
    assert route["data"]["selected"][0]["post_checks"] == ["ethos prove"]
    assert route["data"]["selected"][0]["matched_paths"] == ["src/code.py"]


def test_playbooks_changed_scope_without_changed_paths_selects_nothing(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    package_manifest = Path(write_v2_playbook_package(skills_root, "docs-governance"))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "docs-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "changed-scope"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["changed_paths"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["unmatched_paths"] == []


def test_playbooks_changed_scope_reports_matched_changed_path_evidence(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    package_manifest = Path(write_v2_playbook_package(skills_root, "docs-governance"))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "docs-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "changed-scope"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["data"]["changed_paths"] == ["docs/guide.md"]
    selected = payload["data"]["selected"][0]
    assert selected["id"] == "docs-governance"
    assert selected["matched_paths"] == ["docs/guide.md"]
    assert payload["data"]["unmatched_paths"] == []


def test_playbooks_changed_scope_reports_unmatched_changed_paths(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    package_manifest = Path(write_v2_playbook_package(skills_root, "docs-governance"))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "docs-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "changed-scope"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert payload["data"]["selected"] == []
    assert "src/app.py" in payload["data"]["unmatched_paths"]
    assert "playbook_changed_path_unmatched:src/app.py" in payload["required_gaps"]


def test_fleet_inspect_reports_external_adopter_shape(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()
    adoption_plan(tmp_path, profile="gitlab", apply=True)

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "fleet inspect"
    assert payload["data"]["adopter"]["root"] == str(tmp_path.resolve())
    assert payload["data"]["adopter"]["governance"]["ethos_config"] is True
    assert payload["data"]["adopter"]["governance"]["openspec"] is True
    assert payload["data"]["adopter"]["governance"]["skills"] is True


def test_fleet_inspect_accepts_current_docs_layout(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)
    (tmp_path / "docs" / "index.md").unlink()
    (tmp_path / "docs" / "current").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "current" / "README.md").write_text(
        "---\nsubject: docs:current\nrole: reference\nstate: current\nrelations: test\n---\n"
        "# Current Docs\n",
        encoding="utf-8",
    )

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["data"]["adopter"]["governance"]["docs"] is True


def test_quality_determinism_commands_are_available() -> None:
    for command in (
        ("quality", "command-surface", "--json"),
        ("quality", "format-policy", "--json"),
        ("quality", "projection-drift", "--json"),
        ("quality", "evidence-freshness", "--json"),
        ("quality", "command-examples", "--json"),
        ("quality", "coupling-audit", "--json"),
        ("quality", "docs-registry", "--json"),
        ("quality", "provenance", "--json"),
        ("quality", "claims", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_quality_coupling_audit_reports_git_native_boundary() -> None:
    payload = run_ethos("quality", "coupling-audit", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality coupling-audit"
    assert payload["required_gaps"] == []
    assert payload["data"]["git_native"]["strongly_bound"] is True
    assert payload["data"]["git_native"]["layer"] == "product_semantic_hard_binding"
    assert payload["data"]["openspec_governance"]["layer"] == ("mandatory_governance_dependency")
    assert payload["data"]["openspec_governance"]["not_a_second_command_plane"] is True
    assert payload["data"]["native_protocols"]["layer"] == "native_protocol_binding"
    assert payload["data"]["native_protocols"]["provider_optional"] is False
    assert payload["data"]["release_host_profile"]["provider"] == "gitlab"
    assert payload["data"]["product_toolchain"]["profile"] == "product-toolchain"
    assert payload["data"]["product_toolchain"]["layer"] == ("product_toolchain_binding")
    assert {
        "kind": "schema_validation",
        "target": "data",
        "schema": "coupling-audit.schema.json",
        "ok": True,
        "required_gaps": [],
    } in payload["diagnostics"]
    assert "schema_validation" not in payload["data"]


def test_prove_returns_evidence_and_provenance() -> None:
    payload = run_ethos("prove", "--objective", "cli contract", "--json")

    assert payload["ok"] is True
    assert payload["data"]["evidence"]["digest"]
    assert (
        payload["data"]["provenance"]["subject"][0]["digest"]["sha256"]
        == (payload["data"]["evidence"]["digest"])
    )


def test_prove_uses_repository_audit_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("prove", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert payload["data"]["repository_audit"]["governance_context"]["contract"] == (
        "governed_repository"
    )
    assert "posture" not in payload["data"]["repository_audit"]["governance_context"]
    assert payload["data"]["repository_audit"]["governance_context"]["profile"] == "generic"
    assert (
        payload["data"]["repository_audit"]["governance_context"]["subject"]["kind"]
        == "repository"
    )
    assert (
        payload["data"]["repository_audit"]["governance_context"]["subject"]["id"]
        == str(tmp_path.resolve())
    )
    assert payload["data"]["repository_audit"]["governance_context"]["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"]["transition_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"]["scorecard_commands"] == [
        "ethos report",
    ]


def test_report_uses_adopter_scorecard_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("report", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["summary"]["governance_gap_count"] == 0
    assert payload["data"]["scores"]["adopter_governance"] == 1
    assert payload["data"]["first_hour"] == {
        "proof_status": "ready",
        "evidence_gap_count": 0,
        "land_readiness": "local_readiness",
        "publish_readiness": "local_readiness",
        "hosted_ci_truth": "external-evidence",
        "next_action": "ethos prove",
    }


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
    seed_executed_proof(repo, accepted_head)

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
    assert payload["data"]["accepted_update"] == {
        "ok": True,
        "state": "accepted_validated",
        "branch": "dev",
        "source_branch": "candidate/dev",
        "head": candidate_head,
        "previous_head": accepted_head,
        "required_gaps": [],
    }
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
    seed_executed_proof(repo, accepted_head)

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
    assert bootstrap == {
        "kind": "closeout_bootstrap",
        "state": "ready",
        "accepted_root": repo.resolve().as_posix(),
        "audit_root": candidate.resolve().as_posix(),
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "blocking": False,
        "required_gaps": [],
        "command": (
            "ethos land --closeout --apply --authorize "
            f"--expect-head {accepted_head} --root {repo.resolve().as_posix()} --json"
        ),
        "next_action": "run closeout with a current ETHOS runner against accepted_root",
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


def test_configured_branch_roles_drive_local_lifecycle_commands(tmp_path: Path) -> None:
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
    assert publish_payload["data"]["publication"]["local_submit_package"] == {
        "kind": "submit_branch_plan",
        "source_branch": "lane/configured",
        "submit_branch": "review/configured",
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
            "create configured submit branch when remote publication is available",
        ],
    }

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
    assert closeout_payload["data"]["accepted_update"] == {
        "ok": True,
        "state": "accepted_validated",
        "branch": "integration",
        "source_branch": "stage/integration",
        "head": work_head,
        "previous_head": accepted_head,
        "required_gaps": [],
    }

    retire_payload = run_ethos(
        "lane",
        "retire-landed",
        "--branch",
        "lane/configured",
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
    assert payload["data"]["publication"] == {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "submit_branch": submit_branch,
        "local_submit_package": {
            "kind": "submit_branch_plan",
            "source_branch": branch,
            "submit_branch": submit_branch,
            "remote_push": "not_performed",
            "remote_state": "deferred",
            "blocking": False,
            "required_steps": [
                "land work lane to candidate role",
                "fast-forward accepted root from candidate role",
                "create configured submit branch when remote publication is available",
            ],
        },
        "required_gaps": [],
        "next_actions": ["create configured submit branch when remote publication is available"],
    }


def test_publish_uses_configured_submit_branch_role_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["local_submit_package"]["source_branch"] == "lane/topic"
    assert publication["submit_branch"] == "review/topic"
    assert publication["local_submit_package"]["submit_branch"] == "review/topic"


def test_assistant_projection_commands_are_available() -> None:
    manifest = run_ethos("assistants", "mcp-manifest", "--json")
    projections = run_ethos("assistants", "check-projections", "--json")
    doctor = run_ethos("assistants", "doctor", "--json")

    assert manifest["ok"] is True
    assert "ethos.status" in manifest["data"]["manifest"]["tools"]
    assert projections["ok"] is True
    assert projections["data"]["contract"]["truth"] == "repository-source-and-contracts"
    assert doctor["ok"] is True


def test_playbooks_route_accepts_changed_scope_alias_without_changed_paths(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "repository-governance"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "repository-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "playbooks route"
    assert payload["data"]["subject"] == "changed-scope"
    assert payload["data"]["changed"] is True
    assert payload["data"]["changed_paths"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["unmatched_paths"] == []


def test_product_playbook_activation_routes_evolution_campaigns() -> None:
    activation = tomllib.loads(Path(".agents/skills/activation.toml").read_text(encoding="utf-8"))
    record = next(
        item for item in activation["skill"] if item["id"] == "ethos-repository-governance"
    )

    assert "evolution/**" in record["path_globs"]
    assert ".agents/skills/**" in record["path_globs"]


def test_playbooks_changed_scope_route_requires_explicit_subject(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "ethos-repository-governance"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "ethos-repository-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["changed_paths"] == []


def test_playbooks_changed_scope_route_ignores_id_and_subject_substrings(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "changed-scope-helper"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "changed-scope-helper"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "changed-scope-shadow"
operation = "inspect"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["changed_paths"] == []


def test_playbooks_route_rejects_name_only_activation_entries(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "changed-scope-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Changed Scope Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "changed-scope-router"
path = ".agents/skills/changed-scope-router/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos playbooks route --changed"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add unsupported route",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert "skill_missing_id" in payload["required_gaps"]
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]


def test_playbooks_strict_mode_rejects_activation_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "escape-skill"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "escape-skill"
path = "../outside/SKILL.md"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert "playbook_skill_path_escape:escape-skill" in payload["required_gaps"]


def test_playbooks_strict_mode_requires_activation_path_to_match_package_entrypoint(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "entrypoint-skill"))
    alternate = skills_root / "entrypoint-skill" / "ALT.md"
    alternate.write_text(OFFICIAL_PLAYBOOK_SKILL, encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "entrypoint-skill"
path = ".agents/skills/entrypoint-skill/ALT.md"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert "skill_package_entrypoint_mismatch:entrypoint-skill" in payload["required_gaps"]


def test_playbooks_report_rejects_name_only_skill_activation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "unsupported-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Unsupported Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "unsupported-router"
subjects = ["repository-governance"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "check", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert "skill_missing_id" in payload["required_gaps"]
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]


def test_playbooks_strict_mode_rejects_placeholder_v1_skill(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "placeholder" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Placeholder\n\nThin routing note.\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
id = "placeholder"
path = ".agents/skills/placeholder/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["data"]["mode"] == "v2-strict"
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]
    assert "skill_package_manifest_missing:placeholder" in payload["required_gaps"]
    assert "skill_quality_missing_frontmatter:placeholder" in payload["required_gaps"]


def test_playbooks_removed_compatibility_mode_is_not_available(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")

    completed = run_ethos_raw(
        "playbooks",
        "route",
        "--changed",
        "--mode",
        "compat",
        "--root",
        str(root),
        "--json",
    )

    assert completed.returncode != 0
    assert "unsupported playbook mode: compat" in completed.stderr


def test_report_uses_strict_playbooks_for_external_adopter_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skill_path = skills_root / "unsupported-router" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Unsupported Router\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
name = "unsupported-router"
path = ".agents/skills/unsupported-router/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos playbooks route --changed"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("report", "--root", str(root), "--json")

    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert payload["data"]["playbooks"]["mode"] == "v2-strict"
    assert "skill_missing_id" in payload["data"]["playbooks"]["required_gaps"]
    assert (
        "playbook_activation_unsupported_version:1" in payload["data"]["playbooks"]["required_gaps"]
    )


def test_product_playbooks_strict_mode_passes_after_v2_migration() -> None:
    payload = run_ethos("playbooks", "check", "--mode", "v2-strict", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["registry"]["digest"].startswith("sha256:")
    assert payload["data"]["package_quality"]["ok"] is True


def test_projection_drift_reports_registry_and_generator_digest_state() -> None:
    payload = run_ethos("quality", "projection-drift", "--json")

    assert payload["ok"] is True
    assert payload["data"]["registry"]["digest"].startswith("sha256:")
    assert payload["data"]["registry"]["expected_digest"].startswith("sha256:")
    assert payload["data"]["registry"]["ok"] is True
    assert payload["data"]["generator"]["digest"].startswith("sha256:")
    assert payload["data"]["generator"]["expected_digest"].startswith("sha256:")
    assert payload["data"]["generator"]["ok"] is True
    assert payload["data"]["inputs"][0]["path"] == ".agents/skills/activation.toml"
    assert payload["data"]["inputs"][0]["digest"].startswith("sha256:")


def test_playbooks_v2_gate_can_execute() -> None:
    payload = run_ethos("prove", "--execute", "--gate", "playbooks-v2", "--json")

    assert payload["ok"] is True
    assert payload["data"]["executed"] is True
    assert payload["data"]["evidence"]["runs"][0]["action_id"] == "playbooks-v2"
    assert payload["data"]["evidence"]["runs"][0]["state"] == "proven"


def test_campaign_hypotheses_are_visible() -> None:
    payload = run_ethos("campaign", "hypotheses", "--json")

    assert payload["ok"] is True
    assert payload["data"]["hypotheses"]


def test_campaign_status_reports_manifest_steps() -> None:
    payload = run_ethos("campaign", "status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "campaign status"
    assert payload["summary"]["active_campaign_count"] >= 1
    assert payload["data"]["campaigns"]
    campaign = next(
        item
        for item in payload["data"]["campaigns"]
        if item["id"] == "terminal-openspec-productization"
    )
    assert campaign["step_summary"]["total"] >= 8
    assert {"planned", "active", "closed"} <= set(campaign["step_summary"])
    assert campaign["lane_topology"]["mode"] == "strict_serial"
    assert campaign["lane_topology"]["active_step"] == "hooked-write-admission"
    assert campaign["lane_topology"]["next_planned_step"] == "adopter-openspec-scaffold"
    assert {
        "ordinal",
        "depends_on",
        "openspec_change",
        "work_lane",
        "claim_id",
        "closeout",
    } <= set(campaign["steps"][0])


def test_campaign_closeout_reports_local_campaign_packages() -> None:
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"
    expected_submit = load_branch_role_policy(Path.cwd()).submit_branch_for_source(branch)
    evidence = json.loads(
        Path("evidence/parity/alphasim-dmgr-shadow.json").read_text(encoding="utf-8")
    )
    target = Path(str(evidence["target"]))

    payload = run_ethos(
        "campaign",
        "closeout",
        "--adopter",
        "alphasim-dmgr",
        "--target",
        target.as_posix(),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["command"] == "campaign closeout"
    assert payload["state"] == "local_ready"
    assert payload["summary"]["remote_state"] == "deferred"
    assert payload["summary"]["parity_pending_count"] == len(
        payload["data"]["parity"]["pending_packages"]
    )
    assert payload["data"]["remote_publication"] == {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": "remote publication adapter unavailable",
    }

    packages = payload["data"]["packages"]
    assert set(packages) == {
        "local_closeout",
        "trust_closeout",
        "campaign",
        "intake_projection",
        "publication",
        "release",
        "parity",
        "shadow_parity",
    }
    assert packages["local_closeout"]["target_branch"] == "candidate/dev"
    assert packages["campaign"]["kind"] == "campaign_closeout"
    assert packages["campaign"]["active_count"] >= 1
    assert packages["campaign"]["campaigns"]
    assert (
        packages["local_closeout"]["required_gaps"]
        == payload["data"]["workspace"]["closeout_support"]["required_gaps"]
    )
    assert packages["publication"]["remote_push"] == "not_performed"
    assert packages["publication"]["local_submit_package"]["source_branch"] == branch
    assert packages["publication"]["local_submit_package"]["submit_branch"] == expected_submit
    assert packages["release"]["ok"] is True
    assert packages["parity"]["pending_count"] == len(payload["data"]["parity"]["pending_packages"])
    assert packages["parity"]["pending_count"] == payload["summary"]["parity_pending_count"]
    assert packages["parity"]["blocking"] is False
    assert packages["parity"]["required_gaps"] == payload["data"]["parity"]["required_gaps"]
    assert packages["shadow_parity"] == payload["data"]["shadow_parity"]["execution_packages"][0]
    assert packages["shadow_parity"]["state"] in {"matched", "invalid", "not_run"}
    assert packages["shadow_parity"]["evidence_path"] == (
        "evidence/parity/alphasim-dmgr-shadow.json"
    )
    assert packages["shadow_parity"]["blocking"] == bool(packages["shadow_parity"]["required_gaps"])
    assert packages["intake_projection"]["kind"] == "intake_projection"
    assert packages["intake_projection"]["truth_boundary"] == "projection-evidence"
    assert packages["trust_closeout"]["kind"] == "trust_closeout"
    assert packages["trust_closeout"]["claim_report_ok"] is True
    assert packages["trust_closeout"]["promotion_ready"] is True
    assert packages["trust_closeout"]["executed_proof_evidence"] is True
    assert packages["shadow_parity"]["provenance"]["mode"] == "tracked_evidence"
    assert (
        payload["data"]["provenance"]["shadow_parity"] == (packages["shadow_parity"]["provenance"])
    )
    assert payload["data"]["provenance"]["closeout"] == {
        "mode": "local_only",
        "remote_state": "deferred",
    }
    validation = validate_schema_instance("campaign-closeout.schema.json", payload["data"])
    assert validation["ok"] is True


def test_intake_status_is_public_read_only_surface() -> None:
    payload = run_ethos("intake", "status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "intake status"
    assert payload["data"]["truth_boundary"] == "adopter-ledger"
    assert payload["data"]["projection"]["truth_boundary"] == "projection-evidence"
    assert payload["data"]["projection"]["repository_truth"] is False
    assert payload["data"]["provider"] == "unconfigured"


def test_intake_status_rejects_empty_configuration(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    (root / ".ethos" / "intake.toml").write_text("", encoding="utf-8")

    payload = run_ethos("intake", "status", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "invalid"
    assert payload["data"]["configured"] is False
    assert payload["data"]["provider"] == "invalid"
    assert "intake_provider_missing:.ethos/intake.toml" in payload["required_gaps"]


def test_docs_command_uses_registry_for_discovery() -> None:
    payload = run_ethos("docs", "agent-projections", "--json")

    assert payload["ok"] is True
    assert payload["data"]["path"] == "docs/architecture/agent-projections.md"


def test_report_scorecard_is_derived_from_governance_checks() -> None:
    payload = run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["scores"]["distribution_adapter"] == 1
    assert payload["data"]["scores"]["claims"] == 1
    assert payload["data"]["scores"]["docs"] == 1
    assert payload["data"]["scores"]["assistant_projection"] == 1
    assert payload["data"]["scores"]["openspec"] == 1
    assert payload["data"]["scores"]["playbooks"] == 1
    assert payload["data"]["scores"]["adoption_scaffold"] == 1
    assert payload["data"]["scores"]["parity_ledger"] == 1
    scorecards = {item["id"]: item for item in payload["data"]["scorecards"]}
    assert scorecards["skills-v2"]["ok"] is True
    assert scorecards["skills-v2"]["mode"] == "v2-strict"
    assert scorecards["skills-v2"]["score"] == scorecards["skills-v2"]["max_score"]
    assert payload["data"]["parity"]["ledger"]["summary"]["unclassified_count"] == 0
    assert payload["data"]["parity"]["gaps"]["ok"] is True
    assert payload["data"]["parity"]["gaps"]["required_gaps"] == []
    assert payload["summary"]["parity_pending_count"] == len(
        payload["data"]["parity"]["gaps"]["required_gaps"]
    )
    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["data"]["parity"]["gaps"]["pending_packages"] == []
    assert payload["summary"]["governance_gap_count"] == 0
    assert "self_audit" not in payload["data"]
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["data"]["gap_layers"]["governance_audit"] == {
        "scope": "governance_audit",
        "blocking": True,
        "ok": True,
        "required_gaps": [],
        "gap_count": 0,
    }
    assert payload["data"]["gap_layers"]["capability_parity"] == {
        "scope": "capability_parity",
        "blocking": False,
        "ok": True,
        "required_gaps": payload["data"]["parity"]["gaps"]["required_gaps"],
        "gap_count": payload["summary"]["parity_pending_count"],
    }
    parity_note = payload["data"]["parity"]["scope"]["note"].lower()
    assert "raw/cache" not in parity_note
    assert "backend retirement" not in parity_note
    assert "domain profile parity" in parity_note
    assert payload["next_actions"] == ["ethos prove --full"]


def test_shadow_parity_evidence_page_records_accepted_classification() -> None:
    path = Path("evidence/shadow-parity-accepted-classification-2026-07-01.md")

    text = path.read_text(encoding="utf-8")

    assert "subject: ethos:evidence:shadow-parity-accepted-classification" in text
    assert "accepted_differences" in text
    assert "external_product_repository_audit_gap" in text
    assert "changed_route_noop" in text
    assert "report_parity_evidence_refresh_bootstrap" in text
    assert "legacy_changed_route_noop" not in text
    assert "shadow_parity_digest" in text


def test_capability_parity_ledger_documents_shadow_evidence_provenance() -> None:
    text = Path("docs/governance/capability-parity-ledger.md").read_text(encoding="utf-8")

    assert "shadow parity evidence freshness" in text
    assert "target_head" in text
    assert "command_sha256" in text
    assert "tracked_evidence" in text
    assert "planned_shadow_run" in text


def test_retired_self_command_group_is_not_available() -> None:
    completed = run_ethos_raw("self", "audit", "--mode", "shape", "--json")

    assert completed.returncode != 0
    assert 'Unknown command "self"' in (completed.stderr or completed.stdout)


def test_init_command_is_adoption_alias_without_writing(tmp_path: Path) -> None:
    payload = run_ethos("init", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "init"
    assert "openspec/config.yaml" in payload["data"]["planned_files"]
    assert ".agents/skills/activation.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()


def test_quality_types_enforces_ty_policy_tiers() -> None:
    import json as _json

    completed = run_ethos_raw("quality", "types", "--json")
    payload = _json.loads(completed.stdout)

    assert payload["command"] == "quality types"
    packages = payload["data"]["packages"]
    # Zero-tolerance tier packages must report a zero limit; ratchet tiers a baseline.
    # ethos-core absorbs the former ethos-contracts and ethos-quality zero-tolerance
    # packages; ethos remains the ratchet-tier runtime.
    assert packages["packages/ethos-core"]["limit"] == 0
    assert packages["packages/ethos-core"]["tier"] == "zero_tolerance"
    assert packages["packages/ethos"]["tier"] == "ratchet"
    assert packages["packages/ethos"]["limit"] > 0
    # The gate binds its verdict to exit status (fail-closed): a breach exits non-zero.
    assert completed.returncode == (0 if payload["ok"] else 1)

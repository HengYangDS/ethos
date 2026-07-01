from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ethos_assistants.skill_packages import compute_skill_package_digest
from ethos_contracts.branch_roles import load_branch_role_policy
from ethos_contracts.package_ontology import package_ontology_report
from ethos_repository.planner import adoption_plan
from ethos_repository.schema_validation import validate_schema_instance

from tests.support.ethos_cli_runner import run_ethos, run_ethos_raw


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
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    (repo / ".ethos" / "workspace.toml").write_text(
        "\n".join(
            [
                "[branch_roles]",
                'release_branch = "main"',
                'accepted_branch = "dev"',
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


def test_executed_proof_blocks_ethos_json_gate_failures(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "\n".join(
            [
                "---",
                "subject: sample:guide",
                "role: guide",
                "state: active",
                "relations: {}",
                "---",
                "",
                "# Guide",
                "",
                "Body without required visible sections.",
            ]
        ),
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

    payload = run_ethos(
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

    payload = run_ethos(
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
    assert "ethos-quality" in payload["data"]["target_packages"]
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
        "\n".join(
            [
                "---",
                "subject: sample:guide",
                "role: guide",
                "state: active",
                "relations: {}",
                "---",
                "",
                "# Guide",
                "",
                "Body without required visible sections.",
            ]
        ),
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

    from ethos.cli import _emit
    from ethos_core.result import EthosResult

    def closed_pipe(*args, **kwargs) -> None:
        raise BrokenPipeError

    monkeypatch.setattr(builtins, "print", closed_pipe)

    _emit(EthosResult(command="status", ok=True, state="ready"), json_output=True)


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

    payload = run_ethos(
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

    payload = run_ethos(
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

    payload = run_ethos(
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
    assert payload["data"]["governance_context"] == {
        "contract": "governed_repository",
        "profile": "product",
        "subject": {
            "kind": "repository",
            "root": str(Path.cwd()),
        },
        "single_kernel": True,
        "kernel_chain": [
            "JudgmentSource",
            "Subject",
            "Commitment",
            "Change",
            "Evidence",
            "Claim",
            "Chronicle",
        ],
        "shared_commands": [
            "ethos status",
            "ethos plan",
            "ethos prove",
            "ethos land",
            "ethos publish",
        ],
        "transition_commands": [
            "ethos status",
            "ethos plan",
            "ethos prove",
            "ethos land",
            "ethos publish",
        ],
        "scorecard_commands": [
            "ethos report",
        ],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
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

    payload = run_ethos("adopt", "--root", str(repo), "--apply", "--json", cwd=repo)

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
        "package-ontology",
        "projection-drift",
        "proof-policy",
        "provenance",
        "release",
        "release-attestation",
        "release-policy",
        "sbom",
        "schemas",
        "standards",
        "tool-profiles",
    }


def test_openspec_uses_official_native_cli(monkeypatch) -> None:
    from ethos_adapters import openspec_native

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

    monkeypatch.setattr(openspec_native, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_native, "_run_json", fake_run_json)

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
    skill_path = skills_root / "code-change" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Code Change\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "code-change"
path_globs = ["src/**"]
intent_tokens = ["implement"]
pre_reads = ["README.md"]
post_checks = ["ethos prove"]
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
    skill_path = skills_root / "docs-governance" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Docs Governance\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "docs-governance"
path = ".agents/skills/docs-governance/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["docs/**"]
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
    skill_path = skills_root / "docs-governance" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Docs Governance\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "docs-governance"
path = ".agents/skills/docs-governance/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["docs/**"]
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
    skill_path = skills_root / "docs-governance" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Docs Governance\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "docs-governance"
path = ".agents/skills/docs-governance/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["docs/**"]
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
    assert payload["data"]["product_toolchain"]["layer"] == (
        "product_toolchain_binding"
    )
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
    assert payload["data"]["repository_audit"]["governance_context"]["subject"] == {
        "kind": "repository",
        "root": str(tmp_path.resolve()),
    }
    assert payload["data"]["repository_audit"]["governance_context"]["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"][
        "transition_commands"
    ] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert payload["data"]["repository_audit"]["governance_context"][
        "scorecard_commands"
    ] == [
        "ethos report",
    ]


def test_report_uses_adopter_scorecard_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("report", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert payload["data"]["governance_context"] == payload["data"]["repository_audit"][
        "governance_context"
    ]
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


def test_land_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos("land", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_land_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
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


def test_publish_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos("publish", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_publish_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos(
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
    skill_path = skills_root / "repository-governance" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Repository Governance\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
id = "repository-governance"
path = ".agents/skills/repository-governance/SKILL.md"
subjects = ["repository-governance"]
commands = ["ethos status"]
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


def test_playbooks_changed_scope_route_requires_explicit_subject(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "ethos-repository-governance" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# ETHOS Repository Governance\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
id = "ethos-repository-governance"
path = ".agents/skills/ethos-repository-governance/SKILL.md"
subjects = ["repository-governance"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
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
    skill_path = skills_root / "changed-scope-helper" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Changed Scope Helper\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
id = "changed-scope-helper"
path = ".agents/skills/changed-scope-helper/SKILL.md"
subjects = ["changed-scope-shadow"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["changed_paths"] == []


def test_playbooks_route_accepts_legacy_name_activation_entries(tmp_path: Path) -> None:
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
        "add legacy route",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert len(payload["data"]["selected"]) == 1
    selected = payload["data"]["selected"][0]
    assert selected["id"] == "changed-scope-router"
    assert selected["path"] == ".agents/skills/changed-scope-router/SKILL.md"
    assert selected["subjects"] == ["changed-scope"]
    assert selected["commands"] == ["ethos playbooks route --changed"]
    assert selected["boundary"] == "thin-playbook-projection"
    assert selected["matched_paths"] == ["src/app.py"]


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


def test_playbooks_report_infers_legacy_name_skill_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "legacy-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Legacy Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "legacy-router"
subjects = ["repository-governance"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "check", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["records"][0]["path"] == ".agents/skills/legacy-router/SKILL.md"


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
    assert "playbook_activation_legacy_version:1" in payload["required_gaps"]
    assert "skill_package_manifest_missing:placeholder" in payload["required_gaps"]
    assert "skill_quality_missing_frontmatter:placeholder" in payload["required_gaps"]


def test_playbooks_legacy_compat_preserves_v1_route_with_advisory_gaps(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "legacy-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Legacy Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
name = "legacy-router"
path = ".agents/skills/legacy-router/SKILL.md"
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
        "add legacy route",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos(
        "playbooks",
        "route",
        "--changed",
        "--mode",
        "legacy-compat",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["mode"] == "legacy-compat"
    assert payload["data"]["selected"][0]["id"] == "legacy-router"
    assert payload["data"]["selected"][0]["subjects"] == ["changed-scope"]
    assert "playbook_activation_legacy_version:1" in payload["data"]["advisory_gaps"]
    assert "skill_package_manifest_missing:legacy-router" in payload["data"]["advisory_gaps"]


def test_report_uses_legacy_compat_playbooks_for_external_adopter_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skill_path = skills_root / "legacy-router" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Legacy Router\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
name = "legacy-router"
path = ".agents/skills/legacy-router/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos playbooks route --changed"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("report", "--root", str(root), "--json")

    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert payload["data"]["playbooks"]["mode"] == "legacy-compat"
    assert payload["data"]["gap_layers"]["playbook_projection"]["required_gaps"] == []
    assert (
        "skill_package_manifest_missing:legacy-router"
        in payload["data"]["playbooks"]["advisory_gaps"]
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


def test_campaign_closeout_reports_local_campaign_packages() -> None:
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"
    expected_submit = load_branch_role_policy(Path.cwd()).submit_branch_for_source(branch)
    evidence = json.loads(
        Path("docs/evidence/parity/alphasim-dmgr-shadow.json").read_text(encoding="utf-8")
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
        "intake_projection",
        "publication",
        "release",
        "parity",
        "shadow_parity",
    }
    assert packages["local_closeout"]["target_branch"] == "candidate/dev"
    assert (
        packages["local_closeout"]["required_gaps"]
        == payload["data"]["workspace"]["closeout_support"]["required_gaps"]
    )
    assert packages["publication"]["remote_push"] == "not_performed"
    assert packages["publication"]["local_submit_package"]["source_branch"] == branch
    assert packages["publication"]["local_submit_package"]["submit_branch"] == expected_submit
    assert packages["release"]["ok"] is True
    assert packages["parity"]["pending_count"] == len(
        payload["data"]["parity"]["pending_packages"]
    )
    assert packages["parity"]["pending_count"] == 0
    assert packages["parity"]["required_gaps"] == []
    assert packages["shadow_parity"]["kind"] == "shadow_parity_evidence"
    assert packages["shadow_parity"]["state"] == "matched"
    assert packages["shadow_parity"]["evidence_path"] == (
        "docs/evidence/parity/alphasim-dmgr-shadow.json"
    )
    assert packages["shadow_parity"]["blocking"] is False
    assert packages["shadow_parity"]["required_gaps"] == []
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
    assert payload["data"]["governance_context"] == payload["data"]["repository_audit"][
        "governance_context"
    ]
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
    path = Path("docs/evidence/shadow-parity-accepted-classification-2026-07-01.md")

    text = path.read_text(encoding="utf-8")

    assert "subject: ethos:evidence:shadow-parity-accepted-classification" in text
    assert "accepted_differences" in text
    assert "external_product_repository_audit_gap" in text
    assert "legacy_changed_route_noop" in text
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
    assert "Unknown command \"self\"" in (completed.stderr or completed.stdout)


def test_init_command_is_adoption_alias_without_writing(tmp_path: Path) -> None:
    payload = run_ethos("init", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "init"
    assert "openspec/config.yaml" in payload["data"]["planned_files"]
    assert ".agents/skills/activation.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()

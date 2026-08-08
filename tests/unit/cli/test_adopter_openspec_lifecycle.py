from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.observation as openspec_audit
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.intent import compile_intent_context
from ethos.adapters.openspec.lifecycle.report import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.report import lifecycle_report
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.openspec.lifecycle.report import selected_change
from ethos.adapters.openspec.observation import active_change_names_in_ref
from ethos.adapters.openspec.observation import protected_branch_active_change_report
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.contracts.semantic import Commitment
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_openspec_runner_is_repository_locked_without_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETHOS_OPENSPEC_BIN", "/tmp/untrusted-openspec")
    monkeypatch.setenv("ETHOS_NPX_CACHE_DIR", "/tmp/untrusted-npx-cache")
    monkeypatch.setenv("PATH", "/tmp/untrusted-path")

    command = openspec_cli.openspec_base_command()

    assert command is not None
    assert command[-1].endswith("node_modules/@fission-ai/openspec/bin/openspec.js")
    assert openspec_cli.OFFICIAL_PACKAGE == "@fission-ai/openspec"
    manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert manifest["dependencies"][openspec_cli.OFFICIAL_PACKAGE] == openspec_cli.OFFICIAL_VERSION
    assert openspec_cli.verify_official_cli(command)["verdict"] == "pass"
    assert all(token not in command for token in ("npx", "openspec", "/tmp/untrusted-openspec"))
    assert os.environ["PATH"] == "/tmp/untrusted-path"


def test_bundled_openspec_runner_requires_the_packaged_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package = tmp_path / "node_modules/@fission-ai/openspec/package.json"
    entry = package.parent / "bin/openspec.js"
    declaration = tmp_path / "package.json"
    package.parent.mkdir(parents=True)
    entry.parent.mkdir()
    package.write_text(
        json.dumps(
            {"name": openspec_cli.OFFICIAL_PACKAGE, "version": openspec_cli.OFFICIAL_VERSION}
        ),
        encoding="utf-8",
    )
    declaration.write_text(
        json.dumps(
            {"dependencies": {openspec_cli.OFFICIAL_PACKAGE: openspec_cli.OFFICIAL_VERSION}}
        ),
        encoding="utf-8",
    )
    entry.touch()
    source_command = openspec_cli.openspec_base_command()
    assert source_command is not None
    command = (source_command[0], entry.as_posix())
    monkeypatch.setattr(openspec_cli, "_DISTRIBUTION_DECLARATION", declaration)
    monkeypatch.setattr(openspec_cli, "_DISTRIBUTION_PACKAGE", package)
    monkeypatch.setattr(openspec_cli, "_DISTRIBUTION_ENTRY", entry)
    monkeypatch.setattr(openspec_cli, "_DISTRIBUTION_LOCK", tmp_path / "package-lock.json")

    report = openspec_cli.verify_official_cli(command)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "openspec_root_pin_mismatch",
        "openspec_lock_version_mismatch",
    ]


def test_openspec_18_status_contract_exposes_artifact_graph() -> None:
    payload = {
        "changeName": "example",
        "schemaName": "spec-driven",
        "isComplete": False,
        "applyRequires": ["tasks"],
        "artifactPaths": {"tasks": {"outputPath": "tasks.md"}},
        "artifacts": [
            {"id": "proposal", "status": "done", "requires": []},
            {
                "id": "tasks",
                "status": "blocked",
                "requires": ["proposal"],
                "missingDeps": ["proposal"],
            },
        ],
        "root": {"path": "/tmp/repository", "source": "nearest"},
    }

    assert openspec_cli.status_contract_gaps(payload) == []
    assert openspec_cli.status_contract_gaps(payload | {"artifacts": []}) == [
        "openspec_status_artifact_graph_missing"
    ]


def test_intent_context_rejects_unmapped_requirements_as_model_gap(tmp_path: Path) -> None:
    change = tmp_path / "openspec" / "changes" / "example"
    specs = change / "specs" / "contracts"
    specs.mkdir(parents=True)
    (specs / "spec.md").write_text(
        "## ADDED Requirements\n\n### Requirement: Portable result\n",
        encoding="utf-8",
    )

    _context, gaps = compile_intent_context(
        tmp_path,
        commitment=Commitment(
            id="change:example",
            intent="Prove portable results.",
            subjects=("repository:example",),
        ),
        config={},
        status={"changeName": "example", "schemaName": "spec-driven", "artifacts": []},
        apply={"contextFiles": {"behavior-contracts": [str(specs / "spec.md")]}, "tasks": []},
    )

    assert gaps == ("model_gap",)


def test_selected_change_requires_an_explicit_request_to_exist() -> None:
    rows = official_change_rows(
        {
            "changes": [
                {"name": "active", "completedTasks": 0, "totalTasks": 1, "status": "in-progress"}
            ]
        }
    )

    assert rows is not None
    assert selected_change(rows, "missing") is None


def test_selected_change_returns_the_only_active_commitment() -> None:
    rows = official_change_rows(
        {
            "changes": [
                {"name": "complete", "completedTasks": 1, "totalTasks": 1, "status": "complete"},
                {
                    "name": "active",
                    "completedTasks": 0,
                    "totalTasks": 1,
                    "status": "in-progress",
                    "lastModified": "2026-07-30",
                },
            ]
        }
    )

    assert rows is not None
    assert selected_change(rows, None) == "active"


def test_selected_change_fails_closed_for_multiple_active_commitments() -> None:
    rows = official_change_rows(
        {
            "changes": [
                {
                    "name": "older",
                    "completedTasks": 0,
                    "totalTasks": 1,
                    "status": "in-progress",
                    "lastModified": "2026-01-01",
                },
                {
                    "name": "newer",
                    "completedTasks": 0,
                    "totalTasks": 0,
                    "status": "no-tasks",
                    "lastModified": "2026-07-30",
                },
            ]
        }
    )

    assert rows is not None
    assert selected_change(rows, None) is None


def _write_valid_accepted_specs(repo: Path) -> None:
    openspec = repo / "openspec"
    specs = openspec / "specs"
    (specs / "contracts").mkdir(parents=True)
    (openspec / "config.yaml").write_text(
        "schema: spec-driven\n"
        "context: test repository\n"
        "rules:\n"
        "  proposal: [write intent]\n"
        "  specs: [write requirements]\n"
        "  tasks: [track work]\n"
        "  design: [record decisions]\n",
        encoding="utf-8",
    )
    (specs / "README.md").write_text("# Specs\n", encoding="utf-8")
    (specs / "contracts" / "spec.md").write_text(
        "## Purpose\n\n"
        "Define the accepted contracts capability used to validate repository changes.\n\n"
        "## Requirements\n\n"
        "### Requirement: Accepted contract\n\n"
        "The repository SHALL expose one accepted contract.\n\n"
        "#### Scenario: Contract is read\n\n"
        "- **WHEN** governance reads the capability\n"
        "- **THEN** the accepted contract is available\n",
        encoding="utf-8",
    )


def _enable_openspec(repo: Path, *material_paths: str) -> None:
    profile = RepositoryProfileDeclaration.bootstrap(repo.name).model_copy(
        update={"openspec": OpenSpecPolicy(material_paths=material_paths or ("openspec/**",))}
    )
    (repo / ".ethos" / "profile.toml").write_text(
        render_repository_profile(RepositoryProfileDeclaration.model_validate(profile)),
        encoding="utf-8",
    )


def _official_change_views(
    repo: Path,
    name: str,
    *,
    completed: int,
    total: int,
    capabilities: tuple[str, ...] = (),
) -> tuple[dict[str, object], dict[str, object]]:
    artifacts = [
        {"id": "proposal", "status": "done", "requires": []},
        {"id": "specs", "status": "done", "requires": ["proposal"]},
        {"id": "design", "status": "done", "requires": ["proposal"]},
        {"id": "tasks", "status": "done", "requires": ["specs", "design"]},
    ]
    return (
        {
            "changeName": name,
            "schemaName": "spec-driven",
            "changeRoot": str(repo / "openspec" / "changes" / name),
            "isComplete": True,
            "artifactPaths": {
                "specs": {
                    "existingOutputPaths": [
                        str(repo / "openspec" / "changes" / name / "specs" / capability / "spec.md")
                        for capability in capabilities
                    ]
                }
            },
            "artifacts": artifacts,
            "root": {"path": str(repo), "source": "nearest"},
        },
        {
            "changeName": name,
            "state": "all_done" if completed == total else "ready",
            "progress": {"total": total, "complete": completed, "remaining": total - completed},
            "tasks": [
                {
                    "id": str(index + 1),
                    "description": f"Task {index + 1}",
                    "done": index < completed,
                }
                for index in range(total)
            ],
            "instruction": "Continue.",
            "root": {"path": str(repo), "source": "nearest"},
        },
    )


def test_official_config_report_uses_closed_verdicts(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")

    missing = official_config_report(repo)
    assert missing["verdict"] == "block"
    assert "ok" not in missing

    _write_valid_accepted_specs(repo)
    valid = official_config_report(repo)
    assert valid["verdict"] == "pass"
    assert "ok" not in valid

    config = repo / "openspec" / "config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8") + "defaultStore: private\n", encoding="utf-8"
    )
    assert official_config_report(repo)["required_gaps"] == [
        "openspec_config_default_store_forbidden"
    ]


def test_protected_branch_report_preserves_unknown_git_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    class FailedProcess:
        returncode = 128
        stdout = ""
        stderr = "fatal: cannot read ref"

    monkeypatch.setattr(openspec_audit, "run_git", lambda *_a, **_k: FailedProcess())

    report = protected_branch_active_change_report(repo, current_branch="work/change")

    assert report["verdict"] == "unknown"
    assert report["required_gaps"]
    assert "ok" not in report


def test_active_change_ref_report_preserves_unknown_git_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")

    class FailedProcess:
        returncode = 128
        stdout = ""
        stderr = "fatal: cannot read tree"

    monkeypatch.setattr(openspec_audit, "run_git", lambda *_a, **_k: FailedProcess())

    report = active_change_names_in_ref(repo, "candidate/dev")

    assert report["verdict"] == "unknown"
    assert report["changes"] == []
    assert report["required_gaps"] == ["openspec_ref_tree_unavailable:candidate/dev"]


def test_complete_change_remains_scope_authority_until_archive(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo, "docs/governance/**")
    carrier = repo / "openspec" / "changes" / "completed-change"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:completed-change"\n'
        'intent = "Historical work."\nsubjects = ["repository:self"]\n'
        'scope = ["docs/governance/**"]\n',
        encoding="utf-8",
    )
    (carrier / "tasks.md").write_text("- [x] Historical work complete\n", encoding="utf-8")

    status, apply = _official_change_views(repo, "completed-change", completed=1, total=1)
    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(
            change=None,
            lifecycle=True,
            changed_paths=("docs/governance/new-policy.md",),
            require_workspace=False,
        ),
        list_payload={
            "changes": [
                {
                    "name": "completed-change",
                    "completedTasks": 1,
                    "totalTasks": 1,
                    "status": "complete",
                }
            ]
        },
        status_payload=status,
        apply_payload=apply,
    )

    assert [change["name"] for change in lifecycle["changes"]] == ["completed-change"]
    assert lifecycle["scope_binding"]["state"] == "covered"
    assert lifecycle["scope_binding"]["covered_paths"] == [
        {
            "path": "docs/governance/new-policy.md",
            "changes": ["completed-change"],
        }
    ]
    assert lifecycle["scope_binding"]["required_gaps"] == []

    explicitly_selected = lifecycle_report(
        repo,
        request=OpenSpecRequest(
            change="completed-change",
            lifecycle=True,
            changed_paths=("docs/governance/new-policy.md",),
            require_workspace=False,
        ),
        list_payload={
            "changes": [
                {
                    "name": "completed-change",
                    "completedTasks": 1,
                    "totalTasks": 1,
                    "status": "complete",
                }
            ]
        },
        status_payload=status,
        apply_payload=apply,
    )

    assert explicitly_selected["scope_binding"]["state"] == "covered"


def test_lifecycle_observes_official_state_without_predictive_archive(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    write_active_commitment(repo, change_id="active")
    commands: list[tuple[str, ...]] = []

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        commands.append(args)
        if args[0] == "doctor":
            payload = {"root": {"healthy": True}}
        elif args[0] == "list":
            payload = {
                "changes": [
                    {
                        "name": "active",
                        "completedTasks": 0,
                        "totalTasks": 1,
                        "status": "in-progress",
                    }
                ]
            }
        elif args[0] == "status":
            payload, _ = _official_change_views(repo, "active", completed=0, total=1)
        elif args[:2] == ("instructions", "apply"):
            _, payload = _official_change_views(repo, "active", completed=0, total=1)
        elif args[:2] == ("instructions", "archive"):
            payload = {
                "changeName": "active",
                "root": {"path": str(repo), "source": "nearest"},
            }
        else:
            payload = {"items": [], "summary": {}}
        return {
            "command": [*map(str, _base), *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(openspec_cli, "run_json", run_json)

    report = openspec_governance_report(repo, lifecycle=True)

    assert report["required_gaps"] == []
    assert "archive_preflight" not in report["lifecycle"]["changes"][0]
    assert [command[:2] for command in commands] == [
        ("config", "list"),
        ("doctor", "--json"),
        ("list", "--json"),
        ("status", "--change"),
        ("instructions", "apply"),
        ("instructions", "archive"),
        ("validate", "--all"),
    ]


def test_completed_active_report_blocks_official_completed_change(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
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
                    {"name": "ready", "completedTasks": 1, "totalTasks": 1, "status": "complete"}
                ]
            },
            "parse_error": "",
        },
    )

    report = completed_active_changes_report(repo)

    assert report["verdict"] == "block"
    assert report["completed_changes"] == ["ready"]
    assert report["required_gaps"] == ["openspec_completed_change_unarchived:ready"]


def test_plan_surfaces_transition_plan_block_as_top_level_block(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    carrier = repo / "governance"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:foreign"\nintent = "foreign"\n'
        'subjects = ["repository:foreign"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "foreign contract")
    (repo / ".ethos" / "profile.toml").write_text(
        'profile_id = "adopter"\ncommitment = "governance/commitment.toml"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/profile.toml")
    git(repo, "commit", "-m", "select foreign contract")

    payload = run_ethos(
        "plan",
        "--change",
        "foreign",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["verdict"] == "block"
    assert payload["state"] == "gapped"
    assert "repository_subject_mismatch" in payload["required_gaps"]


def test_plan_emits_one_transition_plan_without_parallel_read_models(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--json")

    assert "transition_plan" in payload["data"]
    assert "workflow_runtime" not in payload["data"]
    assert "domain_contracts" not in payload["data"]
    assert not {"status", "plan", "prove"} & {
        node["id"] for node in payload["data"]["transition_plan"]["nodes"]
    }

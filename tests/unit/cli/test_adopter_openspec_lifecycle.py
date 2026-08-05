from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
import ethos.repository.openspec.audit as openspec_audit
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.report import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.report import lifecycle_report
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.openspec.lifecycle.report import selected_change
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.contracts.plan import TransitionPlan
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.openspec.audit import active_change_names_in_ref
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.openspec.audit import openspec_shape_report
from ethos.repository.openspec.audit import protected_branch_active_change_report
from ethos.repository.openspec.audit import protected_branch_active_change_required_gaps
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import write_active_commitment
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path


def test_openspec_runner_is_repository_locked_17_without_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETHOS_OPENSPEC_BIN", "/tmp/untrusted-openspec")
    monkeypatch.setenv("ETHOS_NPX_CACHE_DIR", "/tmp/untrusted-npx-cache")
    monkeypatch.setenv("PATH", "/tmp/untrusted-path")

    command = openspec_cli.openspec_base_command()

    assert command is not None
    assert command[-1].endswith("node_modules/@fission-ai/openspec/bin/openspec.js")
    assert openspec_cli.OFFICIAL_PACKAGE == "@fission-ai/openspec"
    assert openspec_cli.OFFICIAL_VERSION == "1.7.0"
    assert openspec_cli.verify_official_cli(command)["verdict"] == "pass"
    assert all(token not in command for token in ("npx", "openspec", "/tmp/untrusted-openspec"))
    assert os.environ["PATH"] == "/tmp/untrusted-path"


def test_openspec_17_status_contract_exposes_artifact_graph() -> None:
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


def test_repository_locked_openspec_17_resolves_project_schema_and_guidance(
    tmp_path: Path,
) -> None:
    command = openspec_cli.openspec_base_command()
    assert command is not None
    repo = init_git_repo(tmp_path / "custom-schema")
    schema = repo / "openspec" / "schemas" / "intent-to-proof"
    templates = schema / "templates"
    templates.mkdir(parents=True)
    (repo / "openspec" / "config.yaml").write_text(
        "schema: intent-to-proof\n"
        "context: governed custom workflow\n"
        "rules:\n"
        "  intent: [state explicit non-goals]\n"
        "operations:\n"
        "  apply:\n"
        "    guidance: [prefer deletion over compatibility]\n",
        encoding="utf-8",
    )
    (schema / "schema.yaml").write_text(
        "name: intent-to-proof\n"
        "version: 1\n"
        "artifacts:\n"
        "  - id: intent\n"
        "    generates: intent.md\n"
        "    description: bounded intent\n"
        "    template: intent.md\n"
        "    requires: []\n"
        "  - id: verification\n"
        "    generates: verification.md\n"
        "    description: evidence map\n"
        "    template: verification.md\n"
        "    requires: [intent]\n"
        "apply:\n"
        "  requires: [verification]\n"
        "  tracks: null\n",
        encoding="utf-8",
    )
    (templates / "intent.md").write_text("# Intent\n", encoding="utf-8")
    (templates / "verification.md").write_text("# Verification\n", encoding="utf-8")

    validated = openspec_cli.run_json(
        repo, command, ("schema", "validate", "intent-to-proof", "--json")
    )
    created = openspec_cli.run_json(repo, command, ("new", "change", "custom-change", "--json"))
    status = openspec_cli.run_json(repo, command, ("status", "--change", "custom-change", "--json"))
    intent = openspec_cli.run_json(
        repo,
        command,
        ("instructions", "intent", "--change", "custom-change", "--json"),
    )
    apply = openspec_cli.run_json(
        repo,
        command,
        ("instructions", "apply", "--change", "custom-change", "--json"),
    )

    assert validated["json"]["valid"] is True
    assert created["exit_code"] == 0
    assert status["json"]["schemaName"] == "intent-to-proof"
    assert [artifact["id"] for artifact in status["json"]["artifacts"]] == [
        "intent",
        "verification",
    ]
    assert intent["json"]["unlocks"] == ["verification"]
    assert intent["json"]["context"] == "governed custom workflow"
    assert intent["json"]["rules"] == ["state explicit non-goals"]
    assert apply["json"]["missingArtifacts"] == ["verification"]
    assert apply["json"]["operationGuidance"] == ["prefer deletion over compatibility"]


def test_openspec_17_generated_codex_skill_follows_resolved_schema_contract(
    tmp_path: Path,
) -> None:
    command = openspec_cli.openspec_base_command()
    assert command is not None
    repo = tmp_path / "projection"
    templates = repo / "openspec" / "schemas" / "intent-to-proof" / "templates"
    templates.mkdir(parents=True)
    (repo / "openspec" / "config.yaml").write_text(
        "schema: intent-to-proof\n",
        encoding="utf-8",
    )
    (templates.parent / "schema.yaml").write_text(
        "name: intent-to-proof\n"
        "version: 1\n"
        "artifacts:\n"
        "  - id: intent\n"
        "    generates: intent.md\n"
        "    description: bounded intent\n"
        "    template: intent.md\n"
        "    requires: []\n"
        "  - id: verification\n"
        "    generates: verification.md\n"
        "    description: exact evidence\n"
        "    template: verification.md\n"
        "    requires: [intent]\n"
        "apply:\n"
        "  requires: [verification]\n"
        "  tracks: null\n",
        encoding="utf-8",
    )
    (templates / "intent.md").write_text("# Intent\n", encoding="utf-8")
    (templates / "verification.md").write_text("# Verification\n", encoding="utf-8")
    home = tmp_path / "home"
    codex_home = tmp_path / "codex"
    config_home = tmp_path / "config"
    (config_home / "openspec").mkdir(parents=True)
    (config_home / "openspec" / "config.json").write_text(
        json.dumps(
            {
                "profile": "custom",
                "delivery": "skills",
                "workflows": ["apply"],
                "telemetry": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            *command,
            "init",
            repo.as_posix(),
            "--tools",
            "codex",
            "--profile",
            "custom",
            "--force",
            "--no-animation",
        ],
        cwd=repo,
        env=os.environ
        | {
            "HOME": home.as_posix(),
            "CODEX_HOME": codex_home.as_posix(),
            "XDG_CONFIG_HOME": config_home.as_posix(),
            "OPENSPEC_TELEMETRY": "0",
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=openspec_cli.OPENSPEC_COMMAND_TIMEOUT_SECONDS,
    )

    assert completed.returncode == 0, completed.stderr
    assert (repo / "openspec" / "config.yaml").read_text(encoding="utf-8") == (
        "schema: intent-to-proof\n"
    )
    apply_skill = (repo / ".codex" / "skills" / "openspec-apply-change" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert 'openspec status --change "<name>" --json' in apply_skill
    assert 'openspec instructions apply --change "<name>" --json' in apply_skill
    assert "Other schemas: follow the contextFiles from CLI output" in apply_skill
    assert "Use contextFiles from CLI output, don't assume specific file names" in apply_skill
    assert not (codex_home / "prompts").exists()


def test_openspec_17_instructions_contract_covers_apply_and_archive() -> None:
    apply = {
        "changeName": "example",
        "state": "blocked",
        "progress": {"total": 0, "complete": 0, "remaining": 0},
        "tasks": [],
        "missingArtifacts": ["tasks"],
        "instruction": "Create tasks first.",
        "root": {"path": "/tmp/repository", "source": "nearest"},
    }
    archive = {
        "changeName": "example",
        "root": {"path": "/tmp/repository", "source": "nearest"},
    }

    assert openspec_cli.instructions_contract_gaps("apply", apply) == []
    assert openspec_cli.instructions_contract_gaps("archive", archive) == []


def test_openspec_17_rejects_default_store_and_accepts_archive_no_op() -> None:
    result = {
        "archive": {
            "change": "example",
            "archivedAs": "2026-08-05-example",
            "path": "/tmp/repository/openspec/changes/archive/2026-08-05-example",
            "specsUpdated": False,
            "totals": {"added": 0, "modified": 0, "removed": 0, "renamed": 0},
            "warnings": [],
        },
        "root": {"path": "/tmp/repository", "source": "nearest"},
    }

    assert openspec_cli.config_contract_gaps({"defaultStore": "private"}) == [
        "openspec_default_store_forbidden"
    ]
    archive = result["archive"]
    assert archive["path"].endswith("/openspec/changes/archive/2026-08-05-example")
    assert archive["specsUpdated"] is False
    assert archive["warnings"] == []


def test_repository_locked_openspec_17_characterizes_skip_specs_and_nested_archive(
    tmp_path: Path,
) -> None:
    command = openspec_cli.openspec_base_command()
    assert command is not None

    skip = init_git_repo(tmp_path / "skip")
    _write_characterization_workspace(skip, "skip-only", skip_specs=True)
    skip_status = openspec_cli.run_json(
        skip, command, ("status", "--change", "skip-only", "--json")
    )
    skip_apply = openspec_cli.run_json(
        skip,
        command,
        ("instructions", "apply", "--change", "skip-only", "--json"),
    )
    skip_archive = openspec_cli.run_json(skip, command, ("archive", "skip-only", "--yes", "--json"))

    assert (
        next(
            artifact for artifact in skip_status["json"]["artifacts"] if artifact["id"] == "specs"
        )["status"]
        == "skipped"
    )
    assert skip_apply["json"]["state"] == "all_done"
    archive_path = str(skip_archive["json"]["archive"]["path"])
    assert archive_path.rsplit("/", 1)[-1].endswith("-skip-only")
    assert skip_archive["json"]["archive"].get("warnings", []) == []
    assert skip_archive["json"]["archive"]["specsUpdated"] is False

    nested = init_git_repo(tmp_path / "nested")
    _write_characterization_workspace(nested, "nested-change", capability="platform/contracts")
    nested_status = openspec_cli.run_json(
        nested, command, ("status", "--change", "nested-change", "--json")
    )
    nested_archive = openspec_cli.run_json(
        nested, command, ("archive", "nested-change", "--yes", "--json")
    )

    assert nested_status["json"]["artifactPaths"]["specs"]["existingOutputPaths"][0].endswith(
        "/specs/platform/contracts/spec.md"
    )
    assert nested_archive["json"]["archive"]["specsUpdated"] is True
    assert (nested / "openspec/specs/platform/contracts/spec.md").is_file()


def test_lifecycle_projects_official_artifacts_and_task_progress(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo, "docs/governance/**")
    write_active_commitment(repo, change_id="material-change", scope=("docs/governance/**",))

    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(
            change="material-change",
            lifecycle=True,
            changed_paths=("docs/governance/policy.md",),
        ),
        list_payload={
            "changes": [
                {
                    "name": "material-change",
                    "completedTasks": 1,
                    "totalTasks": 2,
                    "status": "in-progress",
                }
            ]
        },
        status_payload={
            "changeName": "material-change",
            "schemaName": "spec-driven",
            "isComplete": True,
            "artifactPaths": {
                "proposal": {"existingOutputPaths": [str(repo / "proposal.md")]},
                "specs": {
                    "existingOutputPaths": [
                        str(
                            repo
                            / "openspec/changes/material-change/specs/platform/contracts/spec.md"
                        )
                    ]
                },
            },
            "artifacts": [
                {"id": "proposal", "status": "done", "requires": []},
                {"id": "specs", "status": "done", "requires": ["proposal"]},
            ],
            "root": {"path": str(repo), "source": "nearest"},
        },
        apply_payload={
            "changeName": "material-change",
            "state": "ready",
            "progress": {"total": 2, "complete": 1, "remaining": 1},
            "tasks": [
                {"id": "1", "description": "Done", "done": True},
                {"id": "2", "description": "Pending", "done": False},
            ],
            "instruction": "Continue.",
            "root": {"path": str(repo), "source": "nearest"},
        },
    )

    change = lifecycle["changes"][0]
    assert change["artifacts"] == [
        {"id": "proposal", "status": "done", "requires": []},
        {"id": "specs", "status": "done", "requires": ["proposal"]},
    ]
    assert change["capabilities"] == ["platform/contracts"]
    assert change["progress"] == {"total": 2, "complete": 1, "remaining": 1}
    assert lifecycle["scope_binding"]["state"] == "covered"


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


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"changes": {}},
        {"changes": ["active"]},
        {"changes": [{"name": "active", "completedTasks": 0, "totalTasks": 1}]},
        {"changes": [{"name": "active", "completedTasks": 0, "totalTasks": 1, "status": "future"}]},
    ],
)
def test_completed_active_report_blocks_unreadable_official_list(
    monkeypatch, tmp_path: Path, payload: dict[str, object]
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
            "json": payload,
            "parse_error": "",
        },
    )

    report = completed_active_changes_report(repo)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_list_unreadable"]


def test_governance_report_blocks_missing_explicit_change(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    write_active_commitment(repo, change_id="active")

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        payload = (
            {"root": {"healthy": True}}
            if args[0] == "doctor"
            else {
                "changes": [
                    {
                        "name": "active",
                        "completedTasks": 0,
                        "totalTasks": 1,
                        "status": "in-progress",
                    }
                ]
            }
            if args[0] == "list"
            else {"items": [], "summary": {}}
        )
        return {
            "command": [*_base, *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(openspec_cli, "run_json", run_json)

    report = openspec_governance_report(repo, change="missing", lifecycle=True)

    assert report["verdict"] == "block"
    assert report["change"] is None
    assert report["required_gaps"] == ["openspec_requested_change_missing:missing"]


def test_governance_report_blocks_ambiguous_implicit_change(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    write_active_commitment(repo, change_id="first")
    write_active_commitment(repo, change_id="second")

    def run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]):
        payload = (
            {"root": {"healthy": True}}
            if args[0] == "doctor"
            else {
                "changes": [
                    {
                        "name": "first",
                        "completedTasks": 0,
                        "totalTasks": 1,
                        "status": "in-progress",
                    },
                    {"name": "second", "completedTasks": 0, "totalTasks": 0, "status": "no-tasks"},
                ]
            }
            if args[0] == "list"
            else {"items": [], "summary": {}}
        )
        return {
            "command": [*_base, *args],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(openspec_cli, "run_json", run_json)

    report = openspec_governance_report(repo, lifecycle=True)

    assert report["verdict"] == "block"
    assert report["change"] is None
    assert report["required_gaps"] == ["openspec_active_change_ambiguous:first,second"]


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


def _write_characterization_workspace(
    repo: Path,
    change: str,
    *,
    skip_specs: bool = False,
    capability: str = "",
) -> None:
    _write_valid_accepted_specs(repo)
    root = repo / "openspec" / "changes" / change
    root.mkdir(parents=True)
    (root / ".openspec.yaml").write_text(
        "schema: spec-driven\n" + ("skip_specs: true\n" if skip_specs else ""),
        encoding="utf-8",
    )
    (root / "proposal.md").write_text(
        "## Why\n\nCharacterize OpenSpec.\n\n## What Changes\n\n- Verify official behavior.\n",
        encoding="utf-8",
    )
    (root / "design.md").write_text("## Context\n\nCharacterization.\n", encoding="utf-8")
    (root / "tasks.md").write_text("- [x] Characterize\n", encoding="utf-8")
    if capability:
        spec = root / "specs" / capability / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(
            "## ADDED Requirements\n\n"
            "### Requirement: Nested capability\n\n"
            "The system SHALL discover a nested capability.\n\n"
            "#### Scenario: Nested capability is archived\n\n"
            "- **WHEN** the change is archived\n"
            "- **THEN** the accepted nested capability is created\n",
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


def test_official_config_report_accepts_project_local_schema_artifacts(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    config = repo / "openspec" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "schema: intent-to-proof\n",
        encoding="utf-8",
    )

    assert official_config_report(repo) == {
        "verdict": "pass",
        "path": config.as_posix(),
        "required_gaps": [],
    }


def test_protected_branch_report_preserves_unknown_git_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    class FailedProcess:
        returncode = 128
        stdout = ""
        stderr = "fatal: cannot read ref"

    monkeypatch.setattr(
        "ethos.repository.openspec.audit.subprocess.run", lambda *_a, **_k: FailedProcess()
    )

    report = protected_branch_active_change_report(repo, current_branch="work/change")

    assert report["verdict"] == "unknown"
    assert report["required_gaps"]
    assert "ok" not in report


def test_publication_gaps_preserve_unknown_protected_branch_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    monkeypatch.setattr(
        openspec_audit,
        "protected_branch_active_change_report",
        lambda _root, **_kwargs: {
            "verdict": "unknown",
            "records": [],
            "required_gaps": ["openspec_ref_tree_unavailable:main"],
        },
    )

    assert protected_branch_active_change_required_gaps(repo, current_branch="dev") == [
        "openspec_ref_tree_unavailable:main"
    ]


def test_protected_branch_residue_blocks_only_its_advisory_subreport(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    _write_valid_accepted_specs(repo)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt openspec")
    git(repo, "checkout", "-b", "main")
    carrier = repo / "openspec" / "changes" / "release-residue"
    carrier.mkdir(parents=True)
    (carrier / "proposal.md").write_text("# Residue\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "seed release residue")
    git(repo, "checkout", "dev")

    report = openspec_shape_report(repo)

    assert report["verdict"] == "pass"
    assert report["protected_branch_residue"]["verdict"] == "block"
    assert report["protected_branch_residue"]["advisory_gaps"]


def test_shape_report_preserves_unknown_protected_branch_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    _write_valid_accepted_specs(repo)
    monkeypatch.setattr(
        openspec_audit,
        "_branch_report",
        lambda _root, branch: {
            "verdict": "unknown",
            "state": "unknown",
            "branch": branch,
            "required_gaps": [f"openspec_branch_unavailable:{branch}"],
        },
    )

    report = openspec_shape_report(repo)

    assert report["verdict"] == "unknown"
    assert any(gap.startswith("openspec_branch_unavailable:") for gap in report["required_gaps"])


def test_active_change_ref_report_preserves_unknown_git_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")

    class FailedProcess:
        returncode = 128
        stdout = ""
        stderr = "fatal: cannot read tree"

    monkeypatch.setattr(
        "ethos.repository.openspec.audit.subprocess.run", lambda *_a, **_k: FailedProcess()
    )

    report = active_change_names_in_ref(repo, "candidate/dev")

    assert report["verdict"] == "unknown"
    assert report["changes"] == []
    assert report["required_gaps"] == ["openspec_ref_tree_unavailable:candidate/dev"]


def test_lifecycle_default_residue_uses_closed_verdict(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")

    report = lifecycle_report(
        repo,
        request=OpenSpecRequest(change=None, lifecycle=False),
        list_payload={"changes": []},
    )

    residue = report["protected_branch_residue"]
    assert residue["verdict"] == "pass"
    assert "ok" not in residue


def test_fresh_adopter_without_material_change_does_not_require_openspec_workspace(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(repo, lifecycle=True, require_workspace=False)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_active_change_missing"]


def test_fresh_adopter_material_change_requires_explicit_openspec_change(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(
        repo,
        lifecycle=True,
        changed_paths=("docs/governance/policy.md",),
        require_workspace=False,
    )

    assert report["verdict"] == "block"
    assert "openspec_active_change_missing" in report["required_gaps"]


@pytest.mark.parametrize(
    ("relative", "expected_gap"),
    [
        (
            "families.toml",
            "openspec_specs_root_entry_unexpected:families.toml",
        ),
        (
            "contracts/capability.toml",
            "openspec_spec_capability_entry_unexpected:contracts:capability.toml",
        ),
        (
            "contracts/notes.md",
            "openspec_spec_capability_entry_unexpected:contracts:notes.md",
        ),
    ],
)
def test_openspec_shape_rejects_non_spec_capability_carriers(
    tmp_path: Path, relative: str, expected_gap: str
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo, "docs/governance/**")
    _write_valid_accepted_specs(repo)
    assert openspec_shape_report(repo)["required_gaps"] == []
    unexpected = repo / "openspec" / "specs" / relative
    unexpected.parent.mkdir(parents=True, exist_ok=True)
    unexpected.write_text("retired or unexpected\n", encoding="utf-8")

    report = openspec_shape_report(repo)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [expected_gap]


def test_commitment_scope_is_the_only_active_material_coverage(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo, "docs/governance/**")
    carrier = repo / "openspec" / "changes" / "material-change"
    (carrier / "specs" / "repository-governance").mkdir(parents=True)
    (carrier / "proposal.md").write_text("# Material change\n", encoding="utf-8")
    (carrier / "design.md").write_text("# Design\n", encoding="utf-8")
    (carrier / "tasks.md").write_text("- [ ] Change policy\n", encoding="utf-8")
    (carrier / "specs" / "repository-governance" / "spec.md").write_text(
        "# Repository governance\n",
        encoding="utf-8",
    )
    (carrier / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:material-change"\n'
        'intent = "Change governance policy."\nsubjects = ["repository:self"]\n'
        'scope = ["docs/governance/**"]\n',
        encoding="utf-8",
    )
    report = openspec_governance_report(
        repo,
        lifecycle=True,
        changed_paths=("docs/governance/policy.md",),
        require_workspace=False,
    )

    assert [artifact["id"] for artifact in report["lifecycle"]["changes"][0]["artifacts"]] == [
        "proposal",
        "specs",
        "design",
        "tasks",
    ]
    assert report["lifecycle"]["scope_binding"]["state"] == "covered"
    assert report["lifecycle"]["scope_binding"]["covered_paths"] == [
        {"path": "docs/governance/policy.md", "changes": ["material-change"]}
    ]
    assert (
        "openspec_material_path_uncovered:docs/governance/policy.md" not in report["required_gaps"]
    )


def test_lifecycle_uses_delta_spec_directories_as_capability_truth(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    carrier = repo / "openspec" / "changes" / "plain-proposal"
    (carrier / "specs" / "contracts").mkdir(parents=True)
    (carrier / "proposal.md").write_text(
        "## Why\n\nChange contracts.\n\n"
        "## Capabilities\n\n- `contracts`: portable contracts\n\n"
        "## Out of Scope\n\n- Other capabilities.\n",
        encoding="utf-8",
    )
    (carrier / "design.md").write_text("# Design\n", encoding="utf-8")
    (carrier / "tasks.md").write_text("- [ ] Implement\n", encoding="utf-8")
    (carrier / "specs" / "contracts" / "spec.md").write_text("# Contracts\n", encoding="utf-8")
    (carrier / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:plain-proposal"\n'
        'intent = "Change contracts."\nsubjects = ["repository:self"]\n',
        encoding="utf-8",
    )

    status, apply = _official_change_views(
        repo, "plain-proposal", completed=0, total=1, capabilities=("contracts",)
    )
    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(change="plain-proposal", lifecycle=True),
        list_payload={
            "changes": [
                {
                    "name": "plain-proposal",
                    "completedTasks": 0,
                    "totalTasks": 1,
                    "status": "in-progress",
                }
            ]
        },
        status_payload=status,
        apply_payload=apply,
    )

    assert lifecycle["required_gaps"] == []
    assert lifecycle["changes"][0]["capabilities"] == ["contracts"]
    assert "proposal_protocol" not in lifecycle["changes"][0]


def test_invalid_commitment_is_a_gap_without_material_paths(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo, "docs/governance/**")
    carrier = repo / "openspec" / "changes" / "invalid-contract"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text("not = [valid\n", encoding="utf-8")

    status, apply = _official_change_views(repo, "invalid-contract", completed=0, total=1)
    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(change=None, lifecycle=True),
        list_payload={
            "changes": [
                {
                    "name": "invalid-contract",
                    "completedTasks": 0,
                    "totalTasks": 1,
                    "status": "in-progress",
                }
            ]
        },
        status_payload=status,
        apply_payload=apply,
    )

    assert "commitment_invalid:invalid-contract" in lifecycle["required_gaps"]


def test_complete_change_is_reviewed_but_cannot_authorize_new_material_writes(
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
    assert lifecycle["scope_binding"]["state"] == "uncovered"
    assert lifecycle["scope_binding"]["covered_paths"] == []
    assert lifecycle["scope_binding"]["required_gaps"] == [
        "openspec_material_path_uncovered:docs/governance/new-policy.md"
    ]

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

    assert explicitly_selected["scope_binding"]["state"] == "uncovered"


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


def test_completed_active_report_does_not_revalidate_historical_archives(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    archive = repo / "openspec" / "changes" / "archive" / "not-a-canonical-archive"
    archive.mkdir(parents=True)

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda *_args: {
            "command": ["openspec", "list", "--json"],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {"changes": []},
            "parse_error": "",
        },
    )

    report = completed_active_changes_report(repo)

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert "archive_closeout" not in report


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


def test_shape_report_does_not_use_historical_archive_identity_as_current_verdict(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    _write_valid_accepted_specs(repo)
    archive = repo / "openspec" / "changes" / "archive" / "not-a-canonical-archive"
    archive.mkdir(parents=True)

    report = openspec_shape_report(repo)

    assert report["verdict"] == "pass"
    assert not any(gap.startswith("openspec_archive_") for gap in report["required_gaps"])


def test_complete_adopter_plan_calls_openspec(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "required_gaps": ["openspec_active_change_missing"],
        },
    )
    plan = run_ethos("plan", "--root", repo.as_posix(), "--json")

    assert plan["verdict"] == "block"
    assert "openspec_active_change_missing" in plan["required_gaps"]
    assert plan["data"]["commitment"]["id"].startswith("repository:")
    assert plan["data"]["transition_plan"]["verdict"] == "block"
    assert plan["data"]["profile_adapter"]["verdict"] == "block"


def test_plan_rejects_profile_selected_change_without_openspec_carrier(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    selected = repo / "governance"
    selected.mkdir(parents=True)
    (selected / "commitment.toml").write_text(
        'schema_version = 1\nid = "change:selected"\nintent = "Selected."\n'
        'subjects = ["repository:self"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    (repo / ".ethos" / "profile.toml").write_text(
        'profile_id = "adopter"\ncommitment = "governance/commitment.toml"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add selected change")
    payload = run_ethos(
        "plan",
        "--change",
        "selected",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["proof_floor_empty"]
    assert payload["data"]["commitment"]["id"] == "change:selected"


def test_plan_uses_explicit_openspec_profile_commitment(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    _enable_openspec(repo)
    write_active_commitment(repo, change_id="selected")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "select OpenSpec change")

    payload = run_ethos(
        "plan",
        "--change",
        "selected",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["proof_floor_empty"]
    assert payload["data"]["commitment"]["id"] == "change:selected"
    assert payload["data"]["profile_adapter"]["change"] == "selected"


def test_complete_adopter_commands_require_openspec_layout(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")

    commands = ("status", "plan", "prove", "land")
    completed = [
        run_ethos_raw(command, "--root", repo.as_posix(), "--json") for command in commands
    ]
    payloads = [json.loads(result.stdout) for result in completed]

    assert (repo / "openspec/config.yaml").is_file()
    assert not (repo / "system").exists()
    assert not (repo / "pyproject.toml").exists()
    assert not (repo / "src" / "ethos").exists()
    assert [payload["command"] for payload in payloads] == list(commands)
    assert all(result.stdout and not result.stderr for result in completed)
    assert all(
        not any(
            gap.startswith(("repository_doc_missing:", "schema_missing:"))
            for gap in payload["required_gaps"]
        )
        for payload in payloads
    )
    assert any("openspec_active_change_missing" in payload["required_gaps"] for payload in payloads)


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


def test_plan_projects_explicit_proof_capacity_without_fixed_worker_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    commitment_path = repo / ".ethos" / "commitment.toml"
    commitment_path.write_text(
        commitment_path.read_text(encoding="utf-8") + 'risks = ["uncertain cutover"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.workspace_status",
        lambda *_args, **_kwargs: {
            "root": repo.as_posix(),
            "branch": "dev",
            "head": git(repo, "rev-parse", "HEAD"),
            "role": "accepted_root",
            "dirty": False,
            "changed_paths": [],
            "role_policy": {"candidate_branch": "candidate/dev"},
            "foreign_work_lanes": [
                {
                    "branch": "work/alternative",
                    "coordination_state": "overlap",
                    "base_commitment_digest": load_profile_commitment(repo).digest(),
                    "path_scope": ["src/ethos/example.py"],
                }
            ],
        },
    )
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning._peer_proof_cost",
        lambda *_args, **_kwargs: 3,
    )

    payload = run_ethos(
        "plan",
        "--proof-node-capacity",
        "7",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["data"]["coordination_strategy"] == {
        "state": "compete",
        "reason": "alternative_realizations_admitted",
        "proof_capacity": 7,
        "proof_cost": 3,
        "risk_count": 1,
        "peer_count": 1,
        "alternative_count": 1,
        "conflict_count": 0,
        "unknown_count": 0,
        "branches": ["work/alternative"],
        "admission_order": ["work/alternative"],
        "queue_age_seconds": {"work/alternative": 0},
        "backpressure": "open",
        "candidate_progress": {
            "observation": "git_reflog",
            "ref": "candidate/dev",
            "advance_count": 0,
            "interval_seconds": None,
            "latest_interval_seconds": None,
            "latest_advance_age_seconds": None,
            "advances_per_hour": None,
            "behind_accepted": 0,
        },
        "proof_capacity_available": 7,
    }
    assert "worker_count" not in payload["data"]["coordination_strategy"]
    assert "competitor_limit" not in payload["data"]["coordination_strategy"]


def test_prove_does_not_run_nodes_from_a_blocked_plan(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    admitted = proof_plan(repo, head=git(repo, "rev-parse", "HEAD"))
    blocked = TransitionPlan.compile(
        inputs=admitted.inputs,
        closure={
            "commitment": admitted.commitment,
            "prior_attestations": admitted.prior_attestations,
            "policy": admitted.policy,
            "effect": admitted.effect,
        },
        permissions=admitted.permissions,
        facts=admitted.facts,
        nodes=admitted.nodes,
        required_gaps=("blocked-plan",),
    )
    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: blocked)
    monkeypatch.setattr(
        proof_cli.LocalGateRunner,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner called")),
    )

    payload = run_ethos_blocked(
        "prove",
        "--execute",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["required_gaps"] == ["blocked-plan"]


def test_adopt_cli_applies_the_reviewed_identity_and_plan(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "adopter")
    reviewed = adoption_plan(target)

    payload = run_ethos(
        "adopt",
        "--apply",
        "--authorize",
        "--expect-head",
        git(target, "rev-parse", "HEAD"),
        "--repository-id",
        str(reviewed["repository_id"]),
        "--expect-plan-digest",
        str(reviewed["plan_digest"]),
        "--root",
        target.as_posix(),
        "--json",
    )

    assert payload["state"] == "applied"
    assert payload["data"]["repository_id"] == reviewed["repository_id"]
    assert payload["data"]["plan_digest"] == reviewed["plan_digest"]

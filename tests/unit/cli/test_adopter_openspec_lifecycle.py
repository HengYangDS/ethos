from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.report import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.report import lifecycle_report
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.openspec.lifecycle.report import selected_change
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.openspec.audit import openspec_shape_report
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


def test_selected_change_requires_an_explicit_request_to_exist() -> None:
    rows = official_change_rows({"changes": [{"name": "active", "status": "in-progress"}]})

    assert rows is not None
    assert selected_change(rows, "missing") is None


def test_selected_change_returns_the_only_active_commitment() -> None:
    rows = official_change_rows(
        {
            "changes": [
                {"name": "complete", "status": "complete"},
                {"name": "active", "status": "in-progress", "lastModified": "2026-07-30"},
            ]
        }
    )

    assert rows is not None
    assert selected_change(rows, None) == "active"


def test_selected_change_fails_closed_for_multiple_active_commitments() -> None:
    rows = official_change_rows(
        {
            "changes": [
                {"name": "older", "status": "in-progress", "lastModified": "2026-01-01"},
                {"name": "newer", "status": "archiving", "lastModified": "2026-07-30"},
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
        {"changes": [{"name": "active"}]},
        {"changes": [{"name": "active", "status": "future"}]},
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

    assert report["ok"] is False
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
            else {"changes": [{"name": "active", "status": "in-progress"}]}
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

    assert report["ok"] is False
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
                    {"name": "first", "status": "in-progress"},
                    {"name": "second", "status": "no-tasks"},
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

    assert report["ok"] is False
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


def _enable_openspec(repo: Path, *material_paths: str) -> None:
    profile = RepositoryProfileDeclaration.bootstrap(repo.name).model_copy(
        update={"openspec": OpenSpecPolicy(material_paths=material_paths or ("openspec/**",))}
    )
    (repo / ".ethos" / "profile.toml").write_text(
        render_repository_profile(RepositoryProfileDeclaration.model_validate(profile)),
        encoding="utf-8",
    )


def test_fresh_adopter_without_material_change_does_not_require_openspec_workspace(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(repo, lifecycle=True, require_workspace=False)

    assert report["ok"] is True
    assert report["state"] == "not_applicable"
    assert report["required_gaps"] == []
    assert report["lifecycle"]["scope_binding"]["state"] == "not_applicable"


def test_fresh_adopter_material_change_does_not_require_openspec_workspace(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(
        repo,
        lifecycle=True,
        changed_paths=("docs/governance/policy.md",),
        require_workspace=False,
    )

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["lifecycle"]["scope_binding"]["state"] == "not_applicable"


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

    assert report["ok"] is False
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

    assert report["lifecycle"]["changes"][0]["carriers"] == {
        "proposal": True,
        "design": True,
        "tasks": True,
        "delta_specs": True,
        "commitment": True,
    }
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

    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(change="plain-proposal", lifecycle=True),
        list_payload={"changes": [{"name": "plain-proposal", "status": "in-progress"}]},
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

    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(change=None, lifecycle=True),
        list_payload={"changes": [{"name": "invalid-contract", "status": "in-progress"}]},
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

    lifecycle = lifecycle_report(
        repo,
        request=OpenSpecRequest(
            change=None,
            lifecycle=True,
            changed_paths=("docs/governance/new-policy.md",),
            require_workspace=False,
        ),
        list_payload={"changes": [{"name": "completed-change", "status": "complete"}]},
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
        list_payload={"changes": [{"name": "completed-change", "status": "complete"}]},
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
            payload = {"changes": [{"name": "active", "status": "in-progress"}]}
        elif args[0] == "status":
            payload = {"schemaName": "spec-driven", "isComplete": True}
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
    assert [command[0] for command in commands] == ["doctor", "list", "status", "validate"]


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

    assert report["ok"] is True
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
            "json": {"changes": [{"name": "ready", "status": "complete"}]},
            "parse_error": "",
        },
    )

    report = completed_active_changes_report(repo)

    assert report["ok"] is False
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

    assert report["ok"] is True
    assert not any(gap.startswith("openspec_archive_") for gap in report["required_gaps"])


def test_generic_adopter_plan_does_not_call_openspec(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    monkeypatch.setattr(
        "ethos.surface.cli.root.planning.openspec_governance_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("OpenSpec called")),
    )
    plan = run_ethos("plan", "--root", repo.as_posix(), "--json")

    assert plan["ok"] is False
    assert plan["required_gaps"] == ["proof_floor_empty"]
    assert plan["data"]["commitment"]["id"].startswith("repository:")
    assert plan["data"]["transition_plan"]["verdict"] == "block"
    assert "profile_adapter" not in plan["data"]


def test_plan_uses_profile_selected_commitment_without_openspec(tmp_path: Path) -> None:
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

    assert payload["ok"] is False
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

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["proof_floor_empty"]
    assert payload["data"]["commitment"]["id"] == "change:selected"
    assert payload["data"]["profile_adapter"]["change"] == "selected"


def test_generic_adopter_commands_do_not_require_product_layout(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")

    commands = ("status", "plan", "prove", "land")
    completed = [
        run_ethos_raw(command, "--root", repo.as_posix(), "--json") for command in commands
    ]
    payloads = [json.loads(result.stdout) for result in completed]

    assert not (repo / "openspec").exists()
    assert not (repo / "system").exists()
    assert not (repo / "pyproject.toml").exists()
    assert not (repo / "src" / "ethos").exists()
    assert [payload["command"] for payload in payloads] == list(commands)
    assert all(result.stdout and not result.stderr for result in completed)
    assert all(
        not any(
            gap.startswith(("openspec_", "repository_doc_missing:", "schema_missing:"))
            for gap in payload["required_gaps"]
        )
        for payload in payloads
    )


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

    assert payload["ok"] is False
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


def test_prove_does_not_run_nodes_from_a_blocked_plan(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    blocked = proof_plan(repo, head=git(repo, "rev-parse", "HEAD")).model_copy(
        update={"validation_issues": ("blocked-plan",)}
    )
    monkeypatch.setattr("ethos.repository.context._contextual_authority", lambda *_args: {})

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

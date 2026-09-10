"""Explicit package/adopter OpenSpec claim-state matrices.

{
  "status": [
    ["package.status.artifact-graph-present", [{"id": "x", "status": "done", "requires": []}], []],
    ["package.status.artifact-graph-missing", [], ["openspec_status_artifact_graph_missing"]]
  ],
  "selection": [
    ["package.selection.explicit-missing",
     [{"name": "active", "completedTasks": 0, "totalTasks": 1, "status": "in-progress"}],
     "missing", null],
    ["package.selection.single-active",
     [{"name": "complete", "completedTasks": 1, "totalTasks": 1, "status": "complete"},
      {"name": "active", "completedTasks": 0, "totalTasks": 1, "status": "in-progress"}],
     null, "active"],
    ["package.selection.multiple-active",
     [{"name": "older", "completedTasks": 0, "totalTasks": 1, "status": "in-progress"},
      {"name": "newer", "completedTasks": 0, "totalTasks": 0, "status": "no-tasks"}],
     null, null]
  ],
  "config": [
    ["adopter.config.missing", null, "block", null],
    ["adopter.config.valid", "schema: spec-driven\\n", "pass", null],
    ["adopter.config.forbidden-default-store",
     "schema: spec-driven\\ndefaultStore: private\\n", "block",
     ["openspec_config_default_store_forbidden"]]
  ],
  "unknown": [
    ["adopter.git.protected-branch-unknown", "protected", null],
    ["adopter.git.active-ref-unknown", "active",
     [[], ["openspec_ref_tree_unavailable:candidate/dev"]]]
  ],
  "commands": [
    ["config", "list"], ["doctor", "--json"], ["list", "--json"],
    ["status", "--change"], ["instructions", "apply"],
    ["instructions", "archive"], ["validate", "--all"], ["show", "active"]
  ],
  "receipt": {
    "command": [], "exit_code": 0, "stdout": "", "stderr": "",
    "json": {}, "parse_error": ""
  }
}
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import ethos.adapters.openspec.cli as cli
import ethos.adapters.openspec.lifecycle.report as life
import ethos.adapters.openspec.observation as observation
import tests.support.governed_repository as fixture
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.intent import compile_intent_context
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.openspec.audit import official_config_report
from tests.support.semantic import commitment_fixture

ROOT = Path(__file__).resolve().parents[3]
MATRIX, _ = json.JSONDecoder().raw_decode(__doc__[__doc__.index("{") :])


def _change(name, done=0, total=1, status="in-progress"):
    return {"name": name, "completedTasks": done, "totalTasks": total, "status": status}


def _repo(tmp_path, material="openspec/**"):
    repo = fixture.init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    fixture.write_test_profile(repo, openspec={"material_paths": [material]})
    return repo


def _views(repo, name):
    """Read native artifact and task observations instead of fabricating their schema."""
    command = cli.openspec_base_command()
    assert command is not None
    return (
        cli.run_json(repo, command, ("status", "--change", name, "--json"))["json"],
        cli.run_json(repo, command, ("instructions", "apply", "--change", name, "--json"))["json"],
    )


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_package_runner_claim_matrix(monkeypatch, tmp_path):
    env = {"ETHOS_OPENSPEC_BIN": "/tmp/untrusted-openspec", "PATH": "/tmp/untrusted-path"}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    command = cli.openspec_base_command()
    assert command is not None
    assert command[-1].endswith("node_modules/@fission-ai/openspec/bin/openspec.js")
    assert (
        cli.OFFICIAL_PACKAGE,
        json.loads((ROOT / "package.json").read_text())["dependencies"][cli.OFFICIAL_PACKAGE],
    ) == (
        "@fission-ai/openspec",
        cli.OFFICIAL_VERSION,
    )
    assert cli.verify_official_cli(command)["verdict"] == "pass"
    assert all(token not in command for token in ("npx", "openspec", env["ETHOS_OPENSPEC_BIN"]))
    assert os.environ["PATH"] == env["PATH"]
    package, declaration = (
        tmp_path / "node_modules/@fission-ai/openspec/package.json",
        tmp_path / "package.json",
    )
    entry = package.parent / "bin/openspec.js"
    _write(package, json.dumps({"name": cli.OFFICIAL_PACKAGE, "version": cli.OFFICIAL_VERSION}))
    _write(declaration, json.dumps({"dependencies": {cli.OFFICIAL_PACKAGE: cli.OFFICIAL_VERSION}}))
    _write(entry, "")
    keys = "_DISTRIBUTION_DECLARATION _DISTRIBUTION_PACKAGE _DISTRIBUTION_ENTRY _DISTRIBUTION_LOCK"
    for key, value in zip(
        keys.split(), (declaration, package, entry, tmp_path / "package-lock.json"), strict=True
    ):
        monkeypatch.setattr(cli, key, value)
    report = cli.verify_official_cli((command[0], entry.as_posix()))
    assert (report["verdict"], report["required_gaps"]) == (
        "block",
        ["openspec_root_pin_mismatch", "openspec_lock_version_mismatch"],
    )


def test_package_projection_claim_matrices():
    for claim, artifacts, gaps in MATRIX["status"]:
        assert cli.status_contract_gaps({"artifacts": artifacts}) == gaps, claim
    for claim, changes, selected, expected in MATRIX["selection"]:
        rows = life.official_change_rows({"changes": changes})
        assert rows is not None, claim
        assert life.selected_change(rows, selected) == expected, claim


@pytest.mark.parametrize("marker", ["-", "*", "+", "1.", ""])
def test_intent_context_preserves_native_source_and_interpretation_boundary(
    tmp_path, marker, monkeypatch
):
    """Native formatting cannot erase the user's zero-winner constraint."""
    spec = tmp_path / "openspec/changes/example/specs/contracts/spec.md"
    content = (
        "## ADDED Requirements\n\n### Requirement: Portable result\n\n"
        "The system SHALL permit zero winners.\n\n#### Scenario: All drop\n\n"
        "- **WHEN** no candidate is suitable\n- **THEN** preserve useful results\n\n"
        "```md\n## Open Questions\n- Not a real question\n```\n\n"
        f"## Out of Scope\n\n{marker} Require one winner,\n"
        "   even after testing.\n\n"
        f"## Open Questions\n\n{marker} Who decides value?\n\n"
        "## Next section\n\nNot an unresolved question.\n"
    )
    _write(spec, content)
    reads, read = [], Path.read_bytes

    def observe(path):
        reads.append(path)
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", observe)
    arguments = {
        "commitment": commitment_fixture(id="change:example", acceptance=("Require one winner",)),
        "config": {},
        "status": {"changeName": "example", "schemaName": "spec-driven", "artifacts": []},
        "apply": {"contextFiles": {"specs": [str(spec), str(spec)]}, "tasks": []},
    }
    context, gaps = compile_intent_context(tmp_path, **arguments)
    assert (gaps, context["negative_scope"], context["ambiguities"]) == (
        (),
        ["Require one winner,\neven after testing."],
        ["Who decides value?"],
    )
    assert context["requirements"] == ["contracts:Portable result"]
    assert context["edge_cases"] == ["contracts:Portable result:All drop"]
    assert context["interpretation_state"] == "not_assessed"
    assert context["duplicate_requirements"] == []
    assert "conflicts" not in context
    assert context["sources"] == {
        spec.relative_to(tmp_path).as_posix(): {
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }
    }
    assert reads == [spec]
    assert context == compile_intent_context(tmp_path, **arguments)[0]
    json.dumps(context)


@pytest.mark.parametrize(
    "fault", ["missing", "escape", "invalid", "undecodable", "absent", "empty", "nonstring"]
)
def test_intent_context_never_silently_drops_unavailable_sources(tmp_path, fault):
    """Incomplete source observations cannot claim a complete context."""
    source = tmp_path / "intent.md"
    source.write_bytes(b"\xff" if fault == "undecodable" else b"User constraint.\n")
    values = {
        "missing": [str(tmp_path / "missing.md")],
        "escape": [str(tmp_path.parent / "outside.md")],
        "invalid": "not-a-path-list",
        "undecodable": [str(source)],
        "absent": [],
        "empty": [],
        "nonstring": [None],
    }
    context, gaps = compile_intent_context(
        tmp_path,
        commitment=commitment_fixture(id="change:example"),
        config={},
        status={},
        apply={} if fault == "absent" else {"contextFiles": {"proposal": values[fault]}},
    )
    assert gaps
    assert all(gap.startswith("openspec_context_") for gap in gaps)
    assert context["source_state"] == "incomplete"


def test_adopter_config_claim_matrix(tmp_path):
    for claim, content, verdict, gaps in MATRIX["config"]:
        root = tmp_path / claim
        if content:
            _write(root / "openspec/config.yaml", content)
        report = official_config_report(root)
        assert (report["verdict"], "ok" in report) == (verdict, False), claim
        assert gaps is None or report["required_gaps"] == gaps, claim


@pytest.mark.parametrize(
    ("state", "detail"),
    [row[1:] for row in MATRIX["unknown"]],
    ids=[row[0] for row in MATRIX["unknown"]],
)
def test_adopter_unknown_git_claim_matrix(monkeypatch, tmp_path, state, detail):
    repo = fixture.init_git_repo(tmp_path / "adopter")
    failed = type("P", (), {"returncode": 128, "stdout": "", "stderr": "fatal"})()
    monkeypatch.setattr(observation, "run_git", lambda *_a, **_k: failed)
    report = (
        observation.protected_branch_active_change_report(repo, current_branch="work/change")
        if state == "protected"
        else observation.active_change_names_in_ref(repo, "candidate/dev")
    )
    assert (report["verdict"], bool(report["required_gaps"]), "ok" in report) == (
        "unknown",
        True,
        False,
    )
    if detail:
        assert [report["changes"], report["required_gaps"]] == detail


def test_adopter_completed_scope_claim_matrix(tmp_path):
    repo = _repo(tmp_path, "docs/governance/**")
    fixture.write_active_commitment(
        repo, change_id="completed-change", scope=("docs/governance/**",)
    )
    tasks = repo / "openspec/changes/completed-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    status, apply = _views(repo, "completed-change")
    changes = {"changes": [_change("completed-change", 1, status="complete")]}
    reports = [
        life.lifecycle_report(
            repo,
            request=life.OpenSpecRequest(
                change=selected,
                lifecycle=True,
                changed_paths=("docs/governance/new-policy.md",),
                require_workspace=False,
            ),
            list_payload=changes,
            status_payload=status,
            apply_payload=apply,
        )
        for selected in (None, "completed-change")
    ]
    binding = reports[0]["scope_binding"]
    assert [item["name"] for item in reports[0]["changes"]] == ["completed-change"]
    assert [item["scope_binding"]["state"] for item in reports] == [
        "attributed",
        "attributed",
    ]
    assert (binding["covered_paths"], binding["required_gaps"]) == (
        [{"path": "docs/governance/new-policy.md", "changes": ["completed-change"]}],
        [],
    )


def test_adopter_lifecycle_claim_matrix(monkeypatch, tmp_path):
    """Exercise official projection instead of a second hand-written protocol."""
    repo, commands = _repo(tmp_path), []
    fixture.git(repo, "checkout", "-b", "work/intent")
    fixture.write_active_commitment(repo, change_id="active")
    run = cli.run_json

    def observed(root, base, args):
        commands.append(args)
        return run(root, base, args)

    monkeypatch.setattr(cli, "run_json", observed)
    report = openspec_governance_report(repo, lifecycle=True)
    assert report["required_gaps"] == []
    assert "archive_preflight" not in report["lifecycle"]["changes"][0]
    assert [item[:2] for item in commands] == [tuple(item) for item in MATRIX["commands"]]
    assert report["intent_context"]["source_state"] == "complete"
    tasks = repo / "openspec/changes/active/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    report = completed_active_changes_report(repo)
    assert (report["verdict"], report["completed_changes"], report["required_gaps"]) == (
        "block",
        ["active"],
        ["openspec_completed_change_unarchived:active"],
    )

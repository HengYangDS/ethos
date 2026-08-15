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
    ["instructions", "archive"], ["validate", "--all"]
  ],
  "view": {
    "status": {
      "changeName": "$NAME", "schemaName": "spec-driven",
      "changeRoot": "$ROOT/openspec/changes/$NAME", "isComplete": true,
      "artifactPaths": {"specs": {"existingOutputPaths": []}},
      "artifacts": [
        {"id": "proposal", "status": "done", "requires": []},
        {"id": "specs", "status": "done", "requires": []},
        {"id": "design", "status": "done", "requires": []},
        {"id": "tasks", "status": "done", "requires": []}
      ],
      "root": {"path": "$ROOT", "source": "nearest"}
    },
    "apply": {
      "changeName": "$NAME", "state": "$STATE",
      "progress": {"total": 1, "complete": "$DONE", "remaining": "$REMAINING"},
      "tasks": [{"id": "1", "description": "Task 1", "done": "$BOOL"}],
      "instruction": "Continue.", "root": {"path": "$ROOT", "source": "nearest"}
    }
  },
  "receipt": {
    "command": [], "exit_code": 0, "stdout": "", "stderr": "",
    "json": {}, "parse_error": ""
  }
}
"""

from __future__ import annotations

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
from tests.support.ethos_cli_runner import run_ethos
from tests.support.semantic import commitment_v2

ROOT = Path(__file__).resolve().parents[3]
MATRIX, _ = json.JSONDecoder().raw_decode(__doc__[__doc__.index("{") :])


def _change(name, done=0, total=1, status="in-progress"):
    return {"name": name, "completedTasks": done, "totalTasks": total, "status": status}


def _repo(tmp_path, material="openspec/**"):
    repo = fixture.init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    fixture.write_test_profile(repo, openspec={"material_paths": [material]})
    return repo


def _views(repo, name, state="ready"):
    done = state == "complete"
    values = {
        "$ROOT": str(repo),
        "$NAME": name,
        '"$STATE"': json.dumps("all_done" if done else "ready"),
        '"$DONE"': str(int(done)),
        '"$REMAINING"': str(int(not done)),
        '"$BOOL"': str(done).lower(),
    }
    encoded = json.dumps(MATRIX["view"])
    for old, new in values.items():
        encoded = encoded.replace(old, new)
    view = json.loads(encoded)
    return view["status"], view["apply"]


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


def test_package_intent_claim_matrix(tmp_path):
    spec = tmp_path / "openspec/changes/example/specs/contracts/spec.md"
    _write(spec, "## ADDED Requirements\n\n### Requirement: Portable result\n")
    context, gaps = compile_intent_context(
        tmp_path,
        commitment=commitment_v2(
            id="change:example",
            intent="Prove portable results.",
            subjects=("repository:example",),
            hypotheses=(
                {
                    "id": "hypothesis:bounded-input",
                    "kind": "hypothesis:causal",
                    "body": {"proposition": "A bounded input remains serializable."},
                },
            ),
        ),
        config={},
        status={"changeName": "example", "schemaName": "spec-driven", "artifacts": []},
        apply={"contextFiles": {"behavior-contracts": [str(spec)]}, "tasks": []},
    )
    assert gaps == ("model_gap",)
    assert context["assumptions"] == [
        {
            "id": "hypothesis:bounded-input",
            "kind": "hypothesis:causal",
            "body": {"proposition": "A bounded input remains serializable."},
        }
    ]
    json.dumps(context)


def test_package_intent_accepts_prettier_aligned_traceability_table(tmp_path):
    spec = tmp_path / "openspec/changes/example/specs/contracts/spec.md"
    tasks = tmp_path / "openspec/changes/example/tasks.md"
    _write(spec, "## ADDED Requirements\n\n### Requirement: Portable result\n")
    _write(
        tasks,
        """# Tasks

- [ ] 1.1 Prove portable results.

## Requirement To Task To Proof

| Requirement                              | Task     | Proof                           |
| ---------------------------------------- | -------- | ------------------------------- |
| `contracts:Portable result`              | `1.1`    | `tests:portable-result`         |
""",
    )

    context, gaps = compile_intent_context(
        tmp_path,
        commitment=commitment_v2(
            id="change:example", intent="Prove portable results.", subjects=("repository:example",)
        ),
        config={},
        status={"changeName": "example", "schemaName": "spec-driven", "artifacts": []},
        apply={
            "contextFiles": {"behavior-contracts": [str(spec)], "tasks": [str(tasks)]},
            "tasks": [{"id": "1", "description": "1.1 Prove portable results.", "done": False}],
        },
    )

    assert gaps == ()
    assert context["requirement_edges"] == [
        {
            "requirement": "contracts:Portable result",
            "task": "1.1",
            "proof": "tests:portable-result",
        }
    ]


def test_package_intent_expands_capability_traceability_to_coarse_task(tmp_path):
    spec = tmp_path / "openspec/changes/example/specs/contracts/spec.md"
    tasks = tmp_path / "openspec/changes/example/tasks.md"
    _write(
        spec,
        "## ADDED Requirements\n\n"
        "### Requirement: Portable result\n\n"
        "### Requirement: Exact receipt\n",
    )
    _write(
        tasks,
        """# Tasks

- [ ] **1. Promote the model.**

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `contracts:*` | `1` | `tests:contracts` |
""",
    )

    context, gaps = compile_intent_context(
        tmp_path,
        commitment=commitment_v2(
            id="change:example", intent="Prove portable results.", subjects=("repository:example",)
        ),
        config={},
        status={"changeName": "example", "schemaName": "spec-driven", "artifacts": []},
        apply={
            "contextFiles": {"behavior-contracts": [str(spec)], "tasks": [str(tasks)]},
            "tasks": [{"id": "1", "description": "**1. Promote the model.**", "done": False}],
        },
    )

    assert gaps == ()
    assert context["requirement_edges"] == [
        {"requirement": "contracts:Portable result", "task": "1", "proof": "tests:contracts"},
        {"requirement": "contracts:Exact receipt", "task": "1", "proof": "tests:contracts"},
    ]


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
    status, apply = _views(repo, "completed-change", "complete")
    changes = {"changes": [_change("completed-change", 1, status="complete")]}
    request = {
        "lifecycle": True,
        "changed_paths": ("docs/governance/new-policy.md",),
        "require_workspace": False,
    }
    reports = [
        life.lifecycle_report(
            repo,
            request=life.OpenSpecRequest(change=selected, **request),
            list_payload=changes,
            status_payload=status,
            apply_payload=apply,
        )
        for selected in (None, "completed-change")
    ]
    binding = reports[0]["scope_binding"]
    assert [item["name"] for item in reports[0]["changes"]] == ["completed-change"]
    assert [item["scope_binding"]["state"] for item in reports] == ["covered", "covered"]
    assert (binding["covered_paths"], binding["required_gaps"]) == (
        [{"path": "docs/governance/new-policy.md", "changes": ["completed-change"]}],
        [],
    )


def test_adopter_lifecycle_claim_matrix(monkeypatch, tmp_path):
    repo, commands = _repo(tmp_path), []
    fixture.write_active_commitment(repo, change_id="active")
    status, apply = _views(repo, "active")
    root = {"path": str(repo), "source": "nearest"}
    payloads = [
        {},
        {"root": {"healthy": True}},
        {"changes": [_change("active")]},
        status,
        apply,
        {"changeName": "active", "root": root},
        {"items": [], "summary": {}},
    ]
    command_payloads = dict(
        zip((" ".join(row) for row in MATRIX["commands"]), payloads, strict=True)
    )

    def run_json(_root, base, args):
        commands.append(args)
        return MATRIX["receipt"] | {
            "command": [*base, *args],
            "json": command_payloads[" ".join(args[:2])],
        }

    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(cli, "run_json", run_json)
    report = openspec_governance_report(repo, lifecycle=True)
    assert (report["required_gaps"], "archive_preflight" in report["lifecycle"]["changes"][0]) == (
        [],
        False,
    )
    assert [item[:2] for item in commands] == [tuple(item) for item in MATRIX["commands"]]
    payload = {"changes": [_change("ready", 1, status="complete")]}
    monkeypatch.setattr(
        cli, "run_json", lambda *_a: MATRIX["receipt"] | {"command": ["openspec"], "json": payload}
    )
    report = completed_active_changes_report(repo)
    assert (report["verdict"], report["completed_changes"], report["required_gaps"]) == (
        "block",
        ["ready"],
        ["openspec_completed_change_unarchived:ready"],
    )


def test_adopter_plan_claim_matrix_rejects_legacy_commitment_carrier(tmp_path):
    repo = _repo(tmp_path)
    data = run_ethos("plan", "--root", repo.as_posix(), "--json")["data"]
    assert ("transition_plan" in data, "workflow_runtime" in data, "domain_contracts" in data) == (
        True,
        False,
        False,
    )
    assert not {"status", "plan", "prove"} & {
        node["id"] for node in data["transition_plan"]["nodes"]
    }
    carrier = repo / "governance/commitment.toml"
    _write(
        carrier,
        'schema_version = 1\nid = "change:foreign"\nintent = "foreign"\n'
        'subjects = ["repository:foreign"]\nscope = ["**"]\n',
    )
    fixture.git(repo, "add", ".")
    fixture.git(repo, "commit", "-m", "foreign contract")
    (repo / ".ethos/profile.toml").write_text(
        'profile_id = "adopter"\ncommitment = "governance/commitment.toml"\n'
    )
    fixture.git(repo, "add", ".ethos/profile.toml")
    fixture.git(repo, "commit", "-m", "select foreign contract")
    blocked = run_ethos("plan", "--change", "foreign", "--root", repo.as_posix(), "--json")
    assert (blocked["verdict"], blocked["state"]) == ("block", "gapped")
    assert "commitment_invalid:governance/commitment.toml" in blocked["required_gaps"]

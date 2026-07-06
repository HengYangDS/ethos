# ruff: noqa: ARG005, TC002, TC003, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos import cli
from ethos.adapters import config
from ethos.adapters.admission import core as admission
from ethos.adapters.admission import prewrite
from ethos.adapters.mutation import core as mutation_core
from ethos.adapters.store import retrieval
from ethos.repository import audit
from ethos.repository.evidence import parity
from ethos.repository.policy import coupling
from ethos.repository.registry import docs as docs_registry
from ethos.surface.cli import _gate_runner
from ethos_core.action_graph import ActionNode
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.result import EthosResult


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["cmd"], returncode, stdout, stderr)


def test_admission_prewrite_and_hook_success_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        prewrite, "workspace_status", lambda root: {"role": ROLE_ACCEPTED_ROOT, "branch": "dev"}
    )
    monkeypatch.setattr(prewrite.subprocess, "run", lambda *args, **kwargs: cp(returncode=1))
    outside = prewrite.prewrite_guard(
        root=tmp_path, paths=[tmp_path.parent / "outside.md"], editor_root=tmp_path
    )
    assert outside["error"] == "prewrite_path_outside_worktree"
    blocked = prewrite.prewrite_guard(
        root=tmp_path, paths=[tmp_path / "README.md"], editor_root=tmp_path
    )
    assert blocked["error"] == "protected_lane_prewrite_blocked"
    monkeypatch.setattr(
        prewrite, "workspace_status", lambda root: {"role": ROLE_WORK_LANE, "branch": "work/x"}
    )
    missing_editor = prewrite.prewrite_guard(root=tmp_path, paths=[tmp_path / "README.md"])
    assert missing_editor["error"] == "editor_root_missing"
    mismatch = prewrite.prewrite_guard(
        root=tmp_path, paths=[], editor_root=tmp_path / "other", require_editor_root=True
    )
    assert mismatch["error"] == "editor_root_mismatch"

    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda root: {
            "role": ROLE_ACCEPTED_ROOT,
            "branch": "dev",
            "dirty": False,
            "changed_paths": [],
        },
    )
    assert admission.hook_admission_report(root=tmp_path, layer="pre-tool")["required_gaps"] == [
        "protected_root_pretool_paths_required"
    ]
    monkeypatch.setattr(
        admission,
        "prewrite_guard",
        lambda **kwargs: {"ok": True, "role": "work_lane", "branch": "work/x"},
    )
    assert (
        admission.hook_admission_report(
            root=tmp_path, layer="pre-run", paths=[tmp_path / "a"], command="rm a"
        )["decision"]["reason"]
        == "prewrite_admitted"
    )
    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda root: {
            "role": ROLE_WORK_LANE,
            "branch": "work/x",
            "dirty": False,
            "changed_paths": ["a.md"],
        },
    )
    post = admission.hook_admission_report(
        root=tmp_path, layer="post-write", paths=[tmp_path / "a.md"]
    )
    assert post["state"] == "admitted"
    assert admission.hook_admission_report(root=tmp_path, layer="git")["state"] == "fallback"
    assert admission._relative(tmp_path, tmp_path.parent / "outside.md").endswith("outside.md")

    policy = SimpleNamespace(
        accepted_branch="dev",
        candidate_branch="candidate/dev",
        role_for_branch=lambda branch: ROLE_ACCEPTED_ROOT if branch == "dev" else "work_lane",
    )
    monkeypatch.setattr(
        "ethos_core.contracts.branch_roles.load_branch_role_policy", lambda root: policy
    )
    monkeypatch.setattr("ethos.adapters.mutation.core._proof_gaps", lambda root, head: [])
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: cp(returncode=0))
    assert (
        admission.push_admission_report(
            root=tmp_path, target_ref="refs/heads/dev", pushed_head="h1"
        )["ok"]
        is True
    )
    assert (
        admission.ref_move_admission_report(
            root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
        )["ok"]
        is True
    )


def test_cli_wrappers_emit_expected_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    emitted: list[EthosResult] = []
    monkeypatch.setattr(
        cli, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )
    monkeypatch.setattr(cli, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(
        cli,
        "workspace_status",
        lambda repo: {
            "dirty": False,
            "branch": "dev",
            "changed_paths": [],
            "required_gaps": [],
            "candidate": {},
        },
    )
    monkeypatch.setattr(
        cli._prove,
        "workspace_status_validation",
        lambda repo, payload: {"ok": False, "required_gaps": ["bad"]},
    )
    monkeypatch.setattr(cli._prove, "workspace_status_validation_gaps", lambda validation: ("bad",))
    cli.status(json_output=True)
    assert emitted[-1].state == "invalid"
    assert emitted[-1].summary["role"] == ""
    assert emitted[-1].summary["foreign_work_lane_count"] == 0
    assert emitted[-1].summary["unbound_work_lane_count"] == 0
    assert emitted[-1].summary["coordination_blocking"] is False

    monkeypatch.setattr(
        cli._prove,
        "workspace_status_validation",
        lambda repo, payload: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(cli._prove, "workspace_status_validation_gaps", lambda validation: ())
    monkeypatch.setattr(
        cli,
        "evaluate_mutation",
        lambda *args, **kwargs: mutation_core.MutationDecision(ok=True, state="land_ready"),
    )
    monkeypatch.setattr(
        cli._land,
        "repository_audit_after_admission",
        lambda repo, decision: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        cli,
        "openspec_completed_active_changes_report",
        lambda repo: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        cli,
        "candidate_base_report",
        lambda root: {"ok": False, "required_gaps": ["candidate_base_stale"], "state": "blocked"},
    )
    monkeypatch.setattr(cli._gitio, "current_head", lambda repo: "h1")
    cli.land(json_output=True)
    assert emitted[-1].state == "blocked"

    monkeypatch.setattr(
        cli,
        "candidate_base_report",
        lambda root: {"ok": True, "required_gaps": [], "state": "base_current"},
    )
    cli.land(json_output=True)
    assert emitted[-1].state == "ready_to_land"

    monkeypatch.setattr(
        cli,
        "apply_land_to_candidate",
        lambda **kwargs: {"ok": True, "required_gaps": [], "state": "candidate_validated"},
    )
    cli.land(apply=True, authorize=True, expect_head="h1", json_output=True)
    assert emitted[-1].state == "candidate_validated"

    monkeypatch.setattr(
        cli._land,
        "repository_audit_after_admission",
        lambda repo, decision: {"ok": False, "required_gaps": ["audit_gap"]},
    )
    monkeypatch.setattr(
        cli,
        "load_branch_role_policy",
        lambda repo: SimpleNamespace(submit_branch_for_source=lambda branch: "submit/dev"),
    )
    cli.publish(json_output=True)
    assert emitted[-1].required_gaps == ("audit_gap",)

    cli.doctor(init_state=True, json_output=True)
    assert emitted[-1].summary["state_db_exists"] is True
    monkeypatch.setattr(
        cli,
        "openspec_governance_report",
        lambda repo, change=None, lifecycle=False: {
            "ok": False,
            "change": change,
            "schema_name": "",
            "required_gaps": ["gap"],
        },
    )
    cli.openspec(change="c", lifecycle=True, json_output=True)
    assert emitted[-1].command == "openspec" and emitted[-1].state == "gapped"
    monkeypatch.setattr(
        cli,
        "_load_command_groups",
        lambda argv: emitted.append(EthosResult(command="load", ok=True, state=",".join(argv))),
    )
    monkeypatch.setattr(
        cli, "app", lambda: emitted.append(EthosResult(command="app", ok=True, state="called"))
    )
    monkeypatch.setattr("sys.argv", ["ethos", "status"])
    cli.main()
    assert emitted[-2].command == "load" and emitted[-1].command == "app"


def test_audit_coupling_config_and_misc_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert config.rules_config(tmp_path) == {}
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        "[quality]\ncode_size={max=1}\n", encoding="utf-8"
    )
    assert config.code_size_policy(tmp_path) == {"max": 1}
    assert config.code_size_policy(tmp_path / "missing") == {}

    doc = tmp_path / "doc.md"
    assert audit._front_matter_ok(doc) is False
    doc.write_text("no frontmatter", encoding="utf-8")
    assert audit._front_matter_ok(doc) is False
    doc.write_text(
        "---\nsubject: s\nrole: r\nstate: active\nrelations: []\n---\n", encoding="utf-8"
    )
    assert audit._front_matter_ok(doc) is True
    changes = tmp_path / "openspec" / "changes" / "done"
    changes.mkdir(parents=True)
    (changes / "tasks.md").write_text("- [x] one\n- [X] two\n", encoding="utf-8")
    assert audit._completed_unarchived_changes(tmp_path / "openspec") == [
        "openspec_completed_change_unarchived:done"
    ]
    (tmp_path / ".githooks").mkdir()
    (tmp_path / ".githooks" / "pre-commit").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        audit.subprocess, "run", lambda *args, **kwargs: cp(stdout="other\n", returncode=0)
    )
    gaps = audit._write_admission_armed_gaps(tmp_path)
    assert "write_admission_not_armed:pre-push_script_missing" in gaps
    assert "write_admission_not_armed:reference-transaction_script_missing" in gaps
    assert "write_admission_not_armed:core.hooksPath" in gaps
    assert audit._openspec_shape_report(tmp_path)["ok"] is False
    assert audit._openspec_provider_missing_report(tmp_path)["required_gaps"] == [
        "openspec_reporter_not_configured"
    ]

    assert (
        coupling._release_report(tmp_path / "no-project")["host_profile"]["layer"]
        == "profile_or_adapter_binding"
    )
    (tmp_path / ".ethos" / "branch-roles.toml").write_text("[bad\n", encoding="utf-8")
    meta = coupling._branch_role_policy_metadata(tmp_path)
    assert meta["default_policy"] is True
    corrupted = {
        **coupling.BINDING_CONTRACTS["openspec_workspace"],
        "id": "openspec_workspace",
        "layer": "wrong",
        "owns_product_semantics": True,
        "not_product_substrate": False,
    }
    gaps = coupling._binding_taxonomy_gaps(
        "openspec_workspace", corrupted, coupling.BINDING_CONTRACTS["openspec_workspace"]
    )
    assert "binding_registry_layer:openspec_workspace:wrong" in gaps
    assert "binding_registry_product_semantics:openspec_workspace" in gaps
    assert "binding_registry_product_substrate:openspec_workspace" in gaps
    registry_gaps = coupling._binding_registry_gaps(
        [{**corrupted, "id": ""}, {**corrupted, "label": "bad"}, {**corrupted, "label": "bad"}]
    )
    assert "binding_registry_missing_id" in registry_gaps
    assert "binding_registry_duplicate:openspec_workspace" in registry_gaps
    assert "binding_registry_unknown_layer:openspec_workspace:wrong" in registry_gaps
    assert "binding_registry_ui_projection:openspec_workspace:label" in registry_gaps


def test_remaining_helper_edges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # gate runner non-ethos JSON command returns None via line 36.
    assert (
        _gate_runner.run_inprocess_cli_gate(
            ActionNode(id="x", kind="command", command=("python", "script.py", "--json")), tmp_path
        )
        is None
    )
    monkeypatch.setattr(_gate_runner, "_load_command_groups", lambda argv: None)
    monkeypatch.setattr(
        _gate_runner,
        "app",
        lambda argv, exit_on_error=False: (_ for _ in ()).throw(SystemExit("bad")),
    )
    result = _gate_runner.run_inprocess_cli_gate(
        ActionNode(id="x", kind="command", command=("ethos", "status", "--json")), tmp_path
    )
    assert result is not None and result.exit_code == 1

    monkeypatch.setattr(docs_registry, "known_commands", lambda: {"ethos custom"})
    assert docs_registry._known_ethos_command("ethos custom") is True
    assert docs_registry._command_root("env") == ""
    assert (
        docs_registry._has_command_example(
            [{"scope": "current", "command": "env X=1 ethos land --json"}], "ethos land"
        )
        is True
    )
    unfinished = tmp_path / "unfinished.md"
    unfinished.write_text("```bash\nethos prove \\\n --json\n", encoding="utf-8")
    assert docs_registry._bash_logical_commands(unfinished) == [(2, "ethos prove --json")]

    assert (
        parity._command_matches_identity(
            "ethos parity shadow --adopter a --target /t --execute --json", adopter="a", target="/t"
        )
        is True
    )
    assert (
        parity._command_matches_identity(
            "ethos parity shadow --adopter b --target /t --execute --json", adopter="a", target="/t"
        )
        is False
    )
    payload = parity.build_tracked_parity_evidence(
        adopter="a",
        target=tmp_path,
        shadow={"ok": True, "required_gaps": []},
        current_product_head="p",
        current_target_head="t",
        timeout_seconds=1,
    )
    payload["shadow"]["comparison_count"] = 0
    gaps = parity._validate_parity_evidence(payload, "a", target=tmp_path)
    assert "parity_evidence_invalid:a:comparison_count" in gaps

    assert (
        retrieval._empty_selection("q", query_digest="d", diagnostics=[])["untrusted_context_label"]
        == "UNTRUSTED CONTEXT"
    )
    monkeypatch.setattr(retrieval, "_tracked_files", lambda root: [])
    assert retrieval._allowed_sources(tmp_path) == []

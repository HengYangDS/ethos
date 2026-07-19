# ruff: noqa: ARG005, TC002, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.admission.closeout_intent.core as closeout_intent
import ethos.adapters.admission.core as admission
import ethos.adapters.admission.prewrite as admission_prewrite
import ethos.adapters.admission.shell as admission_shell
import ethos.adapters.config as adapters_config
import ethos.adapters.store.retrieval.query as retrieval_query
import ethos.adapters.store.retrieval.sources as retrieval_sources
import ethos.cli as cli_entrypoint
import ethos.repository.audit as repository_audit
import ethos.repository.evidence.parity.validation as parity_validation
import ethos.repository.evidence.shadow.payload as shadow_payload
import ethos.repository.policy.coupling.registry as coupling_registry
import ethos.repository.policy.coupling.release as coupling_release
import ethos.repository.policy.gates as policy_gates
import ethos.repository.registry.docs.commands as docs_commands
import ethos.surface.cli._base as cli_base
import ethos.surface.cli.hook.core as admission_cli
import ethos.surface.cli.root.inspection as inspection_cli
import ethos.surface.cli.root.lifecycle as lifecycle_cli
import ethos.surface.cli.root.reference as reference_cli
import ethos.surface.cli.root.registry as root_registry
import ethos_core.contracts.lifecycle.core as lifecycle_contract
from ethos.repository.design.integrity import front_matter_ok
from ethos.repository.openspec.audit import active_change_violations_for_role
from ethos.repository.openspec.audit import completed_unarchived_changes
from ethos.repository.openspec.audit import openspec_provider_missing_report
from ethos.surface.cli import _gate_runner
from ethos_core.action_graph.core import ActionNode
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.registry.declarations import load_coupling_declaration
from ethos_core.result import EthosResult
from tests.support.subprocesses import completed as cp


def test_hook_admit_next_actions_prefer_admission_report_actions() -> None:
    for report, expected in (
        (
            {
                "ok": False,
                "next_actions": [
                    "set ETHOS_ACTOR=agent-a and rerun the blocked command, or obtain lane handoff",
                    "ethos lane prewrite <path>",
                ],
            },
            (
                "set ETHOS_ACTOR=agent-a and rerun the blocked command, or obtain lane handoff",
                "ethos lane prewrite <path>",
            ),
        ),
        ({"ok": True}, ()),
        ({"ok": False}, ("ethos lane prewrite <path>",)),
    ):
        assert admission_cli._hook_admit_next_actions(report) == expected  # noqa: RUF100, SLF001 - exact private branch coverage


def test_prewrite_block_next_actions_cover_holderless_mismatch() -> None:
    assert admission._prewrite_block_next_actions(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        {
            "work_lane_lease": {
                "reason": "lease_holder_mismatch:work/x",
                "holder_ref": "",
            }
        }
    ) == ["set ETHOS_ACTOR to the current holder_ref or obtain handoff"]


def test_admission_prewrite_and_hook_success_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        admission_prewrite,
        "_prewrite_status",
        lambda root: {"role": ROLE_ACCEPTED_ROOT, "branch": "dev"},
    )
    monkeypatch.setattr(
        admission_prewrite.subprocess, "run", lambda *args, **kwargs: cp(returncode=1)
    )
    outside = admission_prewrite.prewrite_guard(
        root=tmp_path, paths=[tmp_path.parent / "outside.md"], editor_root=tmp_path
    )
    assert outside["error"] == "prewrite_path_outside_worktree"
    blocked = admission_prewrite.prewrite_guard(
        root=tmp_path, paths=[tmp_path / "README.md"], editor_root=tmp_path
    )
    assert blocked["error"] == "protected_lane_prewrite_blocked"
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    monkeypatch.setattr(
        admission_prewrite,
        "_prewrite_status",
        lambda root: {
            "root": root.as_posix(),
            "role": ROLE_WORK_LANE,
            "branch": "work/x",
            "worktrees": [
                {
                    "path": root.as_posix(),
                    "branch": "work/x",
                    "head": "a" * 40,
                    "worktree_binding": "current",
                }
            ],
        },
    )
    monkeypatch.setattr(
        admission_prewrite,
        "leases_by_branch",
        lambda worktrees, current_path: {
            "work/x": {
                "holder_ref": "agent:test:case:agent-a",
                "lease_id": "lease:test",
                "epoch": 1,
                "expected_head": "a" * 40,
            }
        },
    )
    monkeypatch.setattr(admission_prewrite, "_current_head", lambda root: "a" * 40)
    missing_editor = admission_prewrite.prewrite_guard(
        root=tmp_path, paths=[tmp_path / "README.md"]
    )
    assert missing_editor["error"] == "editor_root_missing"
    mismatch = admission_prewrite.prewrite_guard(
        root=tmp_path,
        paths=[],
        editor_root=tmp_path / "other",
        require_editor_root=True,
    )
    assert mismatch["error"] == "editor_root_mismatch"

    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda root, **_kwargs: {
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
    assert admission.hook_admission_report(
        root=tmp_path, layer="pre-run", command="git stash push -u"
    )["required_gaps"] == ["git_stash_forbidden"]
    assert admission.hook_admission_report(
        root=tmp_path, layer="pre-run", command="git -C /repo stash pop"
    )["required_gaps"] == ["git_stash_forbidden"]
    assert (
        admission.hook_admission_report(root=tmp_path, layer="pre-run", command="git stash list")[
            "decision"
        ]["reason"]
        == "command_observe_only"
    )
    monkeypatch.setattr(
        admission,
        "workspace_status",
        lambda root, **_kwargs: {
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
    assert admission._relative(tmp_path, tmp_path.parent / "outside.md").endswith("outside.md")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch

    for command, forbidden, operation, reason in (
        ("git stash", True, "push", "stash_is_hidden_change_carrier"),
        ("git stash -u", True, "push", "stash_is_hidden_change_carrier"),
        ("git stash '", True, "'", "stash_is_hidden_change_carrier"),
        (
            "git --git-dir=/tmp/repo/.git stash clear",
            True,
            "clear",
            "stash_is_hidden_change_carrier",
        ),
        ("git --bare", False, "", "not_git_stash"),
        ("git -C", False, "", "not_git_stash"),
    ):
        assert admission_shell.git_stash_policy(command) == {
            "forbidden": forbidden,
            "operation": operation,
            "reason": reason,
        }
    for command, role, risk, reason in (
        ("", ROLE_WORK_LANE, False, "observe_only_command"),
        ("git --bare", ROLE_WORK_LANE, False, "observe_only_command"),
        ("git branch --list", ROLE_WORK_LANE, False, "observe_only_command"),
        ("git worktree list", ROLE_WORK_LANE, False, "observe_only_command"),
        (
            "git branch -D old",
            ROLE_WORK_LANE,
            True,
            "command_text_matches_mutation_pattern",
        ),
        ("cat README.md", ROLE_ACCEPTED_ROOT, False, "observe_only_command"),
        ("git status", ROLE_ACCEPTED_ROOT, False, "observe_only_command"),
        ("git branch --list", ROLE_ACCEPTED_ROOT, False, "observe_only_command"),
        ("ethos status --json", ROLE_ACCEPTED_ROOT, False, "observe_only_command"),
        (
            "python scripts/task.py",
            ROLE_ACCEPTED_ROOT,
            True,
            "protected_role_unknown_command_requires_paths",
        ),
        (
            "git worktree remove ../x",
            ROLE_ACCEPTED_ROOT,
            True,
            "protected_role_unknown_command_requires_paths",
        ),
    ):
        assert admission_shell.command_risk(command, role=role) == {
            "tracked_mutation_risk": risk,
            "reason": reason,
        }
    assert admission_shell._is_protected_read_command([]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_command_is_read_only(["git"]) is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_command_is_read_only(["git", "stash", "show"]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["--"]) is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["--set-upstream-to=origin/dev"]) is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["--list", "-vv"]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["--format", "%(refname)"]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["--unknown"]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_branch_is_read_only(["dev"]) is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_worktree_is_read_only([]) is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._git_worktree_is_read_only(["remove"]) is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._first_non_option(["--json"]) is None  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert admission_shell._first_non_option(["--json", "status"]) == "status"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch

    policy = SimpleNamespace(
        accepted_branch="dev",
        candidate_branch="candidate/dev",
        role_for_branch=lambda branch: ROLE_ACCEPTED_ROOT if branch == "dev" else "work_lane",
    )
    monkeypatch.setattr(
        "ethos_core.contracts.branch.roles.load_branch_role_policy", lambda root: policy
    )
    monkeypatch.setattr("ethos.adapters.mutation.core.proof_gaps", lambda root, head: [])

    def admitted_git(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        # A sanctioned accepted-ref advance: new_value IS the live candidate head and
        # the move fast-forwards, so `rev-parse candidate/dev` resolves to it and both
        # is-ancestor checks (containment, fast-forward) succeed.
        argv = args[0] if args else []
        if isinstance(argv, list) and argv[:2] == ["git", "rev-parse"]:
            return cp(stdout="new\n")
        return cp(returncode=0)

    monkeypatch.setattr(subprocess, "run", admitted_git)
    # pushed_head must be the live candidate head ("new" per the mock) and remote_head
    # empty (skips the fast-forward check), so the accepted-branch push topology gate
    # (candidate-containment + ==candidate_head) admits the sanctioned advance.
    assert (
        admission.push_admission_report(
            root=tmp_path, target_ref="refs/heads/dev", pushed_head="new"
        )["ok"]
        is True
    )
    # A sanctioned accepted-ref advance also carries a matching closeout-intent marker
    # (official closeout writes one before its CAS); without it the move blocks as a raw
    # ref move. The marker must carry the digests admission expects: no proof is seeded
    # here so the expected evidence_digest is "" (skipped), and the gate_policy_digest
    # must equal the live one — computed against the PROMOTED head's committed tree, as
    # both official closeout and the hook now do (tree_ref=new_value).
    closeout_intent.write_closeout_intent(
        root=tmp_path,
        transition=closeout_intent.CloseoutTransition(
            ref_name="refs/heads/dev",
            old_value="old",
            new_value="new",
            candidate_head="new",
        ),
        evidence_digest="",
        gate_policy_digest=policy_gates.gate_policy_digest(tmp_path, tree_ref="new"),
    )
    assert (
        admission.ref_move_admission_report(
            root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
        )["ok"]
        is True
    )


def test_lifecycle_json_helpers_tolerate_malformed_payloads() -> None:
    assert lifecycle_cli._gap_tuple({"required_gaps": "not-a-list"}) == ()  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert lifecycle_cli._first_string(()) == ""  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    for value, default, expected in (
        (3, 0, 3),
        ("4", 0, 4),
        ("bad", 7, 7),
        (object(), 0, 0),
    ):
        assert lifecycle_cli._int_value(value, default=default) == expected  # noqa: RUF100, SLF001 - exact private branch coverage


def test_cli_wrappers_emit_expected_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    emitted: list[EthosResult] = []
    for module in (inspection_cli, lifecycle_cli, reference_cli):
        monkeypatch.setattr(
            module,
            "emit",
            lambda result, json_output, enforce=True: emitted.append(result),
        )
        monkeypatch.setattr(module, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(
        inspection_cli,
        "workspace_status",
        lambda repo, **_kwargs: {
            "dirty": False,
            "branch": "dev",
            "changed_paths": [],
            "required_gaps": [],
            "candidate": {},
        },
    )
    monkeypatch.setattr(
        lifecycle_cli,
        "workspace_status",
        lambda repo, **_kwargs: {
            "role": "work_lane",
            "branch": "dev",
            "dirty": False,
            "changed_paths": [],
            "required_gaps": [],
            "candidate": {},
            "closeout_support": {"supported": True, "required_gaps": []},
        },
    )
    monkeypatch.setattr(
        inspection_cli,
        "workspace_status_validation",
        lambda repo, payload: {"ok": False, "required_gaps": ["bad"]},
    )
    monkeypatch.setattr(
        inspection_cli, "workspace_status_validation_gaps", lambda validation: ("bad",)
    )
    inspection_cli.status(json_output=True)
    assert emitted[-1].state == "invalid"
    assert emitted[-1].summary["role"] == ""
    assert emitted[-1].summary["foreign_work_lane_count"] == 0
    assert emitted[-1].summary["unbound_work_lane_count"] == 0
    assert emitted[-1].summary["missing_lease_count"] == 0
    assert emitted[-1].summary["dirty_foreign_work_lane_count"] == 0
    assert emitted[-1].summary["coordination_advisory_count"] == 0
    assert emitted[-1].summary["coordination_blocking"] is False

    monkeypatch.setattr(
        inspection_cli,
        "workspace_status_validation",
        lambda repo, payload: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(inspection_cli, "workspace_status_validation_gaps", lambda validation: ())
    monkeypatch.setattr(
        lifecycle_cli,
        "evaluate_mutation",
        lambda *args, **kwargs: lifecycle_contract.MutationEvaluation(ok=True, state="land_ready"),
    )
    monkeypatch.setattr(
        lifecycle_cli.land_core,
        "repository_audit_after_admission",
        lambda repo, decision: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        lifecycle_cli,
        "completed_active_changes_report",
        lambda repo: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        lifecycle_cli,
        "candidate_base_report",
        lambda root, status=None: {
            "ok": False,
            "required_gaps": ["candidate_base_stale"],
            "state": "blocked",
        },
    )
    monkeypatch.setattr(lifecycle_cli.git, "current_head", lambda repo: "h1")
    monkeypatch.setattr(
        lifecycle_cli,
        "proof_readiness_report",
        lambda repo, current_head: {
            "kind": "executed_proof_readiness",
            "head": current_head,
            "state": "proven",
            "blocking": False,
            "required_gaps": [],
            "next_action": "",
        },
    )
    lifecycle_cli.land(json_output=True)
    assert emitted[-1].state == "blocked"

    monkeypatch.setattr(
        lifecycle_cli,
        "candidate_base_report",
        lambda root, status=None: {
            "ok": True,
            "required_gaps": [],
            "state": "base_current",
        },
    )
    lifecycle_cli.land(json_output=True)
    assert emitted[-1].state == "ready_to_land"

    monkeypatch.setattr(
        lifecycle_cli,
        "apply_land_to_candidate",
        lambda **kwargs: {
            "ok": True,
            "required_gaps": [],
            "state": "candidate_validated",
        },
    )
    lifecycle_cli.land(apply=True, authorize=True, expect_head="h1", json_output=True)
    assert emitted[-1].state == "candidate_validated"

    monkeypatch.setattr(
        lifecycle_cli.land_core,
        "repository_audit_after_admission",
        lambda repo, decision: {"ok": False, "required_gaps": ["audit_gap"]},
    )
    monkeypatch.setattr(
        lifecycle_cli,
        "load_branch_role_policy",
        lambda repo: SimpleNamespace(submit_branch_for_source=lambda branch: "submit/dev"),
    )
    lifecycle_cli.publish(json_output=True)
    assert emitted[-1].required_gaps == ("audit_gap",)

    inspection_cli.doctor(init_state=True, json_output=True)
    assert emitted[-1].summary["state_db_exists"] is True
    monkeypatch.setattr(
        reference_cli,
        "openspec_governance_report",
        lambda repo, change=None, lifecycle=False: {
            "ok": False,
            "change": change,
            "schema_name": "",
            "required_gaps": ["gap"],
        },
    )
    reference_cli.openspec(change="c", lifecycle=True, json_output=True)
    assert emitted[-1].command == "openspec" and emitted[-1].state == "gapped"
    monkeypatch.setattr(
        cli_entrypoint,
        "load_command_groups",
        lambda argv: emitted.append(EthosResult(command="load", ok=True, state=",".join(argv))),
    )
    monkeypatch.setattr(
        cli_entrypoint,
        "app",
        lambda: emitted.append(EthosResult(command="app", ok=True, state="called")),
    )
    monkeypatch.setattr("sys.argv", ["ethos", "status"])
    cli_entrypoint.main()
    assert emitted[-2].command == "load" and emitted[-1].command == "app"

    monkeypatch.setattr(root_registry, "load_root_commands", lambda: None)
    monkeypatch.setattr(
        cli_base,
        "load_command_groups",
        lambda argv: emitted.append(
            EthosResult(command="runpy-load", ok=True, state=",".join(argv))
        ),
    )
    monkeypatch.setattr(
        cli_base,
        "app",
        lambda: emitted.append(EthosResult(command="runpy-app", ok=True, state="called")),
    )
    monkeypatch.delitem(sys.modules, "ethos.cli", raising=False)
    runpy.run_module("ethos.cli", run_name="__main__")
    assert emitted[-2].command == "runpy-load" and emitted[-1].command == "runpy-app"


def test_audit_coupling_config_and_misc_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert adapters_config.rules_config(tmp_path) == {}
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        "[quality]\ncode_size={max=1}\n", encoding="utf-8"
    )
    assert adapters_config.code_size_policy(tmp_path) == {"max": 1}
    assert adapters_config.code_size_policy(tmp_path / "missing") == {}

    doc = tmp_path / "doc.md"
    assert front_matter_ok(doc) is False
    doc.write_text("no frontmatter", encoding="utf-8")
    assert front_matter_ok(doc) is False
    doc.write_text(
        "---\nsubject: s\nrole: r\nstate: active\nrelations: []\n---\n",
        encoding="utf-8",
    )
    assert front_matter_ok(doc) is True
    changes = tmp_path / "openspec" / "changes" / "done"
    changes.mkdir(parents=True)
    (changes / "tasks.md").write_text("- [x] one\n- [X] two\n", encoding="utf-8")
    assert completed_unarchived_changes(tmp_path / "openspec") == [
        "openspec_completed_change_unarchived:done"
    ]
    assert active_change_violations_for_role(tmp_path / "openspec", "work_lane") == []
    assert active_change_violations_for_role(tmp_path / "openspec", "accepted_root") == [
        "openspec_active_change_unarchived:done:accepted_root"
    ]
    assert active_change_violations_for_role(tmp_path / "openspec", "candidate") == [
        "openspec_active_change_unarchived:done:candidate"
    ]
    (tmp_path / ".githooks").mkdir()
    (tmp_path / ".githooks" / "pre-commit").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        repository_audit.subprocess,
        "run",
        lambda *args, **kwargs: cp(stdout="other\n", returncode=0),
    )
    gaps = repository_audit._write_admission_armed_gaps(tmp_path)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert "write_admission_not_armed:pre-push_script_missing" in gaps
    assert "write_admission_not_armed:reference-transaction_script_missing" in gaps
    assert "write_admission_not_armed:core.hooksPath" in gaps
    assert repository_audit.openspec_shape_report(tmp_path)["ok"] is False
    assert openspec_provider_missing_report(tmp_path)["required_gaps"] == [
        "openspec_reporter_not_configured"
    ]

    assert (
        coupling_release.release_report(tmp_path / "no-project")["host_profile"]["layer"]
        == "profile_or_adapter_binding"
    )
    (tmp_path / ".ethos" / "branch-roles.toml").write_text("[bad\n", encoding="utf-8")
    meta = coupling_registry.branch_role_policy_metadata(tmp_path)
    assert meta["default_policy"] is True
    corrupted = {
        **load_coupling_declaration().binding("openspec_workspace").projection(),
        "id": "openspec_workspace",
        "layer": "wrong",
        "owns_product_semantics": True,
        "not_product_substrate": False,
    }
    gaps = coupling_registry.binding_taxonomy_gaps(
        "openspec_workspace",
        corrupted,
        load_coupling_declaration().binding("openspec_workspace"),
    )
    assert "binding_registry_layer:openspec_workspace:wrong" in gaps
    assert "binding_registry_product_semantics:openspec_workspace" in gaps
    assert "binding_registry_product_substrate:openspec_workspace" in gaps
    registry_gaps = coupling_registry.binding_registry_gaps(
        [
            {**corrupted, "id": ""},
            {**corrupted, "label": "bad"},
            {**corrupted, "label": "bad"},
        ]
    )
    assert "binding_registry_missing_id" in registry_gaps
    assert "binding_registry_duplicate:openspec_workspace" in registry_gaps
    assert "binding_registry_unknown_layer:openspec_workspace:wrong" in registry_gaps
    assert "binding_registry_ui_projection:openspec_workspace:label" in registry_gaps


def test_remaining_helper_edges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # gate runner non-ethos JSON command returns None via line 36.
    assert (
        _gate_runner.run_inprocess_cli_gate(
            ActionNode(id="x", kind="command", command=("python", "script.py", "--json")),
            tmp_path,
        )
        is None
    )
    assert (
        _gate_runner.run_inprocess_cli_gate(
            ActionNode(id="no-json", kind="command", command=("ethos", "status")),
            tmp_path,
        )
        is None
    )
    monkeypatch.setattr(_gate_runner, "load_command_groups", lambda argv: None)
    monkeypatch.setattr(
        _gate_runner,
        "app",
        lambda argv, exit_on_error=False: (_ for _ in ()).throw(SystemExit("bad")),
    )
    result = _gate_runner.run_inprocess_cli_gate(
        ActionNode(id="x", kind="command", command=("ethos", "status", "--json")),
        tmp_path,
    )
    assert result is not None and result.exit_code == 1
    module_result = _gate_runner.run_inprocess_cli_gate(
        ActionNode(
            id="module",
            kind="command",
            command=("python", "-m", "ethos.cli", "status", "--json"),
        ),
        tmp_path,
    )
    assert module_result is not None and module_result.exit_code == 1

    missing_cwd = tmp_path / "missing-cwd"
    missing_cwd.mkdir()
    monkeypatch.chdir(missing_cwd)
    missing_cwd.rmdir()
    missing_result = _gate_runner.run_inprocess_cli_gate(
        ActionNode(id="missing-cwd", kind="command", command=("ethos", "status", "--json")),
        tmp_path,
    )
    assert missing_result is not None
    assert missing_result.exit_code == 1
    assert "FileNotFoundError" in missing_result.stderr

    assert _gate_runner._current_cwd() == tmp_path  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    missing_root = tmp_path / "missing-root"
    missing_root.mkdir()
    missing_previous = tmp_path / "missing-previous"
    missing_previous.mkdir()
    missing_root.rmdir()
    missing_previous.rmdir()
    _gate_runner._restore_cwd(missing_previous, missing_root)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert Path.cwd() == Path("/")
    monkeypatch.chdir(tmp_path)

    attempted: list[Path] = []

    class UnavailableCwdError(OSError):
        pass

    def always_unavailable(candidate: Path) -> None:
        attempted.append(candidate)
        raise UnavailableCwdError

    monkeypatch.setattr(_gate_runner.os, "chdir", always_unavailable)
    _gate_runner._restore_cwd(None, missing_root)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert attempted == [missing_root, Path("/")]

    monkeypatch.setattr(docs_commands, "known_commands", lambda: {"ethos custom"})
    assert docs_commands.known_ethos_command("ethos custom") is True
    assert docs_commands.command_root("env") == ""
    assert (
        docs_commands.has_command_example(
            [{"scope": "product", "command": "env X=1 ethos land --json"}], "ethos land"
        )
        is True
    )
    unfinished = tmp_path / "unfinished.md"
    unfinished.write_text("```bash\nethos prove \\\n --json\n", encoding="utf-8")
    assert docs_commands.bash_logical_commands(unfinished) == [(2, "ethos prove --json")]

    assert (
        parity_validation.command_matches_identity(
            "ethos parity shadow --adopter a --target /t --execute --json",
            adopter="a",
            target="/t",
        )
        is True
    )
    assert (
        parity_validation.command_matches_identity(
            "ethos parity shadow --adopter b --target /t --execute --json",
            adopter="a",
            target="/t",
        )
        is False
    )
    payload = shadow_payload.build_tracked_parity_evidence(
        adopter="a",
        target=tmp_path,
        shadow={"ok": True, "required_gaps": []},
        current_product_head="p",
        current_target_head="t",
        timeout_seconds=1,
    )
    payload["shadow"]["comparison_count"] = 0
    gaps = parity_validation.validate_parity_evidence(payload, "a", target=tmp_path)
    assert "parity_evidence_invalid:a:comparison_count" in gaps

    assert (
        retrieval_query.empty_selection("q", query_digest="d", diagnostics=[])[
            "untrusted_context_label"
        ]
        == "UNTRUSTED CONTEXT"
    )
    monkeypatch.setattr(retrieval_sources, "tracked_files", lambda root: [])
    assert retrieval_sources.allowed_sources(tmp_path) == []


# fmt: on

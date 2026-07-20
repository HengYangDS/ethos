"""Coverage-closure v3: clidomain reachable branches (100% no-exemption)."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import ethos.adapters.repo.coordination as repo_coordination
import ethos.adapters.repo.git as repo_git
import ethos.adapters.shadow.core as shadow
import ethos.adapters.shadow.execution as shadow_execution
import ethos.adapters.shadow.identity as shadow_identity
import ethos.cli as cli_entry
import ethos.domain.land.core as land_core
import ethos.domain.land.intake.core as intake
import ethos.domain.reporting.gaps as reporting_gaps
import ethos.surface.cli.hook.core as hook
import ethos.surface.cli.root.inspection as inspection_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.domain import orient
from ethos.domain import status
from ethos_core.contracts.lifecycle.core import MutationEvaluation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _init_git_repo(path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Init a throwaway git repo with a deterministic identity and one commit."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "cov"], check=True, capture_output=True)  # fmt: skip
    subprocess.run(["git", "-C", str(path), "config", "user.email", "cov@example.test"], check=True, capture_output=True)  # fmt: skip
    subprocess.run(["git", "-C", str(path), "commit", "--allow-empty", "-m", "init"], check=True, capture_output=True)  # fmt: skip
    return path


def test_missing_gate_dependency_revisits_shared_dependency() -> None:
    command = proof_cli.missing_gate_dependency_next_actions(selected_gate_ids=("build", "ruff"), validation_gaps=("missing_dependency:build->unit-architecture",), current_head="HEADSHA")  # fmt: skip
    assert command == ("ethos prove --execute --gate unit-architecture --gate ruff --gate build --expect-head HEADSHA --json",)  # fmt: skip


def test_missing_gate_dependency_unknown_gate_and_absent_dependency() -> None:
    command = proof_cli.missing_gate_dependency_next_actions(selected_gate_ids=("ghost-gate",), validation_gaps=("missing_dependency:foo->schemas",), current_head="HEADSHA")  # fmt: skip
    assert command == ()


def test_status_human_output_prints_orientation_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    repo = _init_git_repo(tmp_path, monkeypatch)
    inspection_cli.status(root=repo, json_output=False)
    printed = capsys.readouterr().out
    assert printed.strip()
    assert "capability=" in printed


def test_orient_human_output_prints_orientation_lines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    repo = _init_git_repo(tmp_path, monkeypatch)
    inspection_cli.orient(root=repo, json_output=False)
    printed = capsys.readouterr().out
    assert printed.strip()
    assert "capability=" in printed


def test_doctor_skips_state_init_when_flag_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    repo = _init_git_repo(tmp_path, monkeypatch)
    inspection_cli.doctor(root=repo, init_state=False, json_output=True)
    printed = capsys.readouterr().out
    assert '"initialized": false' in printed
    assert not (repo / ".ethos" / "state" / "state.sqlite").exists()


def test_closeout_audit_root_returns_repo_when_decision_blocked(tmp_path: Path) -> None:
    result = land_core.closeout_audit_root(tmp_path, MutationEvaluation(ok=False, state="blocked"))
    assert result == tmp_path


def test_closeout_audit_root_resolves_candidate_when_admitted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:  # fmt: skip
    repo = _init_git_repo(tmp_path, monkeypatch)
    result = land_core.closeout_audit_root(repo, MutationEvaluation(ok=True, state="accepted"))
    assert result == repo


def test_next_actions_falls_back_to_report_next_actions() -> None:
    packet = orient.orientation_packet(status_payload={"root": "/repo", "branch": "release/next", "role": "release_root", "dirty": False, "changed_paths": [], "closeout_support": {}, "coordination": {}, "foreign_work_lanes": []}, report_payload={"next_actions": ["ethos report --json"]})  # fmt: skip
    assert packet["next_actions"] == ["ethos report --json"]


def test_advisory_next_actions_skips_non_matching_gap() -> None:
    assert reporting_gaps.advisory_next_actions(("some_unrelated_gap",)) == ()


def test_adoption_mutation_gaps_flags_head_mismatch() -> None:
    gaps = status.adoption_mutation_gaps(apply=True, authorize=True, expect_head="abc123", current_head="def456")  # fmt: skip
    assert gaps == ("expected_head_mismatch",)


def test_status_worktree_gaps_mergescloseout_support_gaps() -> None:
    gaps = status.status_worktree_gaps({"required_gaps": ["g1"], "closeout_support": {"required_gaps": ["c1"]}})  # fmt: skip
    assert gaps == ["g1", "c1"]


def test_hook_admit_handles_non_dict_decision(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:  # fmt: skip
    monkeypatch.setattr(hook, "resolve_root", lambda root: tmp_path)  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setattr(hook, "hook_admission_report", lambda *_args, **_kwargs: {"ok": True, "state": "admitted", "layer": "pre-commit", "role": "work_lane", "required_gaps": [], "decision": None})  # fmt: skip
    emitted: list[object] = []
    monkeypatch.setattr(hook, "emit", lambda result, json_output, enforce=True: emitted.append(result))  # noqa: ARG005 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    hook.admit("pre-commit", root=tmp_path, json_output=True)
    result = emitted[-1]
    assert result.summary["decision"] == ""


def test_cli_module_entrypoint_invokes_main() -> None:
    completed = subprocess.run([sys.executable, "-m", "ethos.cli", "--help"], check=False, capture_output=True, text=True)  # fmt: skip
    assert completed.returncode == 0
    assert "Usage:" in completed.stdout


def test_adapter_and_domain_remaining_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    monkeypatch.setattr(shadow, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(shadow_execution, "run_external", lambda *_a, **_k: {"exit_code": 1, "json": {}})  # fmt: skip
    verdict = {"ok": True, "command": "status", "required_gaps": []}
    monkeypatch.setattr(shadow_execution, "run_embedded", lambda *_a, **_k: {"exit_code": 0, "json": verdict, "required_gaps": []})  # fmt: skip
    monkeypatch.setattr(shadow.shadow_semantics, "semantic_diff", lambda *_a: {})
    monkeypatch.setattr(shadow.shadow_semantics, "false_negative_gaps", lambda *_a: ["miss"])
    monkeypatch.setattr(shadow.shadow_semantics, "accepted_semantic_differences", lambda *_a: [])
    monkeypatch.setattr(shadow.shadow_identity, "identity_envelope", lambda *_a, **_k: {})
    gaps = shadow.run_shadow_parity(tmp_path)["required_gaps"]
    assert gaps == ["external_command_failed:status", "shadow_false_negative:status"]
    monkeypatch.setattr(shadow_execution, "embedded_backend", lambda *_a: {"argv": ["ok"]})
    assert shadow_execution.embedded_ethos_command(tmp_path, ("status",)) == ["ok"]
    (tmp_path / "pyproject.toml").write_text('tool = "x"\n', encoding="utf-8")
    assert shadow_execution.pyproject_tool(tmp_path) == {}
    completed = subprocess.CompletedProcess([], 0, "\n?? a\n", "")
    monkeypatch.setattr(shadow_identity.subprocess, "run", lambda *_a, **_k: completed)
    assert shadow_identity.changed_paths(tmp_path) == ["a"]
    (tmp_path / "evidence").mkdir()
    assert shadow_identity.evidence_input(tmp_path, "evidence")["kind"] == "directory"
    os.mkfifo(tmp_path / "fifo")
    assert shadow_identity.evidence_input(tmp_path, "fifo") is None
    assert repo_coordination.branch_path_scope(tmp_path, branch="", candidate_branch="candidate") == ((), "unknown")  # fmt: skip
    monkeypatch.setattr(repo_git, "git_stdout", lambda *_a: "url")
    monkeypatch.setattr(repo_git.subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 1, "", "no"))  # fmt: skip
    assert repo_git.remote_availability(tmp_path)["reason"] == "ls_remote_failed"
    assert orient._capability(role="unknown", dirty=False, closeout={}, temporary_probe_count=0)["candidate_action"] == "unknown"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    context = {"role": "unknown", "dirty": False, "gaps": [], "closeout": {}, "report_payload": None, "command_prefix": "", "advisory_next_actions": []}  # fmt: skip
    assert orient._next_actions(context) == ["ethos status --json"]  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip


def test_intake_and_cli_remaining_edges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / ".ethos/intake.toml"
    config.parent.mkdir()
    config.write_text('provider = "github"\n', encoding="utf-8")
    assert intake.intake_projection_report(tmp_path)["provider"] == "github"
    monkeypatch.setattr(intake.subprocess, "run", lambda *_a, **_k: (_ for _ in ()).throw(OSError()))  # fmt: skip
    assert intake._git_head(tmp_path) == ""  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    monkeypatch.setattr(intake.subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 1, "x", ""))  # fmt: skip
    assert intake._git_head(tmp_path) == ""  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    monkeypatch.setattr(intake.subprocess, "run", lambda *_a, **_k: subprocess.CompletedProcess([], 0, "head\n", ""))  # fmt: skip
    assert intake._git_head(tmp_path) == "head"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    called: list[object] = []
    monkeypatch.setattr(cli_entry, "load_command_groups", lambda args: called.append(args))  # noqa: PLW0108 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    monkeypatch.setattr(cli_entry, "app", lambda args: called.append(args))  # noqa: PLW0108 coverage closure preserves the explicit argv contract  # fmt: skip
    monkeypatch.setattr(sys, "argv", ["ethos", "status"])
    cli_entry.main()
    assert called == [["status"], ["status"]]


def test_doctor_initializes_state_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    repo = _init_git_repo(tmp_path, monkeypatch)
    inspection_cli.doctor(root=repo, init_state=True, json_output=True)
    assert (repo / ".ethos/state/state.sqlite").exists()
    assert capsys.readouterr().out

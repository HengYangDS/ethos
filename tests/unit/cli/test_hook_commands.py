"""The hook commands' halves: report projection, installation and its executable recovery."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.application.hook.admission as admission
import ethos.application.hook.installation as installation
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.hook.rollback import RESTORE_ACTION
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.application.catalog import invoke

if TYPE_CHECKING:
    from pathlib import Path

_MOVE = {"ref_name": "refs/heads/topic/example", "old_value": "a" * 40, "new_value": "b" * 40}


def _raising(failure: Exception):
    return lambda *_a, **_k: (_ for _ in ()).throw(failure)


@pytest.mark.parametrize(
    "failure",
    [
        OSError("readonly"),
        ValueError("invalid runtime"),
        ValueError("hook_runtime_installed_supply_unavailable:/missing/runtime/old"),
        ValueError("hook_runtime_installed_supply_invalid:/missing/runtime/old"),
        ValueError("state_schema_migration_requires_reset"),
        ValueError("state_reset_authorization_required"),
        ProcessExecutionError(
            "process_creation_failed", reason="missing_binary", command=("python",), cwd="/fixture"
        ),
        GitExecutionError(
            "git_process_spawn_failed", reason="missing_binary", command=("git",), cwd="/fixture"
        ),
    ],
)
def test_install_failure_preserves_diagnostics_and_executable_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    monkeypatch.setattr(installation, "install_hook_launchers", _raising(failure))
    monkeypatch.setattr(installation, "state_schema_report", _raising(ValueError("unavailable")))
    result = invoke("hook install", tmp_path, {})
    state = str(failure).startswith("state_")
    assert (result.verdict, result.state, result.summary["wired"]) == ("block", "blocked", False)
    assert result.required_gaps == ((str(failure) if state else f"hook_install_failed:{failure}"),)
    reset = " --reset-state --authorize" if state else ""
    if "hook_runtime_installed_supply_" in str(failure):
        assert "/missing/runtime/old" not in result.next_action
        assert "--runtime" in result.next_action
        assert result.user_decision_required is True
    else:
        assert result.next_action == f"ethos hook install --root {tmp_path}{reset} --json"
    if state:
        assert result.data["state_schema"] == {
            "expected_state": "current",
            "observed_state": "unavailable",
        }
    if isinstance(failure, ProcessExecutionError):
        assert result.to_dict()["data"]["process_failure"] == {
            "code": str(failure),
            "reason": "missing_binary",
            "command": ["git"] if isinstance(failure, GitExecutionError) else ["python"],
            "cwd": "/fixture",
            "cause": "",
        }


@pytest.mark.parametrize("deferred", [False, True])
def test_install_projects_runtime_and_retains_deferred_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, deferred: bool
) -> None:
    runtime = {
        "hooks_path": str(tmp_path / "hooks"),
        "python": str(tmp_path / "python"),
        "current": True,
        "scripts": ["commit-msg", "pre-commit", "pre-push", "reference-transaction"],
        "linked_worktrees": [
            {"path": str(tmp_path), "state": "repaired"},
            {"path": str(tmp_path / "linked"), "state": "checked"},
        ],
        "generation_cleanup": {
            "state": "deferred" if deferred else "complete",
            "checked": ["old", "current"],
            "removed": [] if deferred else ["old"],
            "retained": ["current"],
        },
        "required_gaps": ["hook_runtime_cleanup_deferred"] if deferred else [],
    }
    monkeypatch.setattr(installation, "install_hook_launchers", lambda *_a, **_k: runtime)
    result = invoke("hook install", tmp_path, {})
    assert result.to_dict()["data"] == runtime
    assert result.verdict == ("block" if deferred else "pass")
    assert result.summary["wired"] is True
    assert result.state == ("installed_cleanup_deferred" if deferred else "installed")
    assert (
        result.summary["linked_worktrees_checked"],
        result.summary["linked_worktrees_repaired"],
        result.summary["generated_paths_removed"],
    ) == (2, 1, 0 if deferred else 1)
    assert result.next_action == (
        f"ethos hook install --root {tmp_path} --json" if deferred else ""
    )


def test_a_refused_rollback_reports_its_exact_gap_and_the_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal is not wrapped as an install failure; its next action restores first."""
    refusal = RollbackRefusalError("runtime_rollback_declaration_repaired", RESTORE_ACTION)
    monkeypatch.setattr(installation, "install_hook_launchers", _raising(refusal))
    result = invoke("hook install", tmp_path, {})
    assert (result.verdict, result.required_gaps, result.next_action) == (
        "block",
        ("runtime_rollback_declaration_repaired",),
        RESTORE_ACTION,
    )


@pytest.mark.parametrize(
    ("verdict", "gap", "action", "expected_action"),
    [
        ("block", "actor_missing", "set ETHOS_ACTOR=owner", "set ETHOS_ACTOR=owner"),
        ("block", "path_uncovered", None, "ethos lane prewrite <path>"),
        ("pass", None, None, ""),
    ],
)
def test_hook_admit_projects_report_action_before_fallback(
    tmp_path, monkeypatch, verdict, gap, action, expected_action
):
    report = {
        "verdict": verdict,
        "state": "blocked" if gap else "admitted",
        "layer": "pre-tool",
        "role": "work_lane",
        "required_gaps": [gap] if gap else [],
    }
    if action is not None:
        report["next_action"] = action
    monkeypatch.setattr(admission, "hook_admission_report", lambda **_kwargs: report)
    result = invoke("hook admit", tmp_path, {"layer": "pre-tool", "paths": ("README.md",)})
    assert (result.verdict, result.next_action) == (verdict, expected_action)


def test_ref_transaction_policy_failure_emits_actionable_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "resolve_ref_move_policy", _raising(ValueError("missing")))
    result = invoke("hook ref-transaction", tmp_path, _MOVE)
    assert (result.verdict, result.required_gaps, result.next_action) == (
        "block",
        ("ref_move_policy_unavailable",),
        "ethos land --closeout",
    )


@pytest.mark.parametrize("decision", [None, "allow"])
def test_ref_transaction_summary_omits_non_mapping_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, decision: object
) -> None:
    policy = SimpleNamespace(role_for_branch=lambda _branch: "topic")
    monkeypatch.setattr(admission, "resolve_ref_move_policy", lambda *_args: policy)
    report = {"verdict": "pass", "state": "admitted", "branch": "topic/example"}
    monkeypatch.setattr(
        admission, "ref_move_admission_report", lambda **_k: report | {"decision": decision}
    )
    assert invoke("hook ref-transaction", tmp_path, _MOVE).summary["decision"] == ""

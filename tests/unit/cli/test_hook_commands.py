from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.hook.commands as commands
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GitExecutionError
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.result import EthosResult


@pytest.fixture
def emitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[EthosResult]:
    results: list[EthosResult] = []
    monkeypatch.setattr(commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(commands, "emit", lambda result, **_kwargs: results.append(result))
    return results


def test_commit_range_grammar_requires_named_coordinates() -> None:
    help_result = run_ethos_raw("hook", "commit-range", "--help")
    assert help_result.returncode == 0, help_result.stderr
    assert "TARGET-REF" not in help_result.stdout.splitlines()[0]
    for option in ("--target-ref", "--proposed-head", "--remote-head", "--remote"):
        assert option in help_result.stdout
    rejected = run_ethos_raw(
        "hook", "commit-range", "refs/heads/dev", "a" * 40, "b" * 40, "origin", "--json"
    )
    assert rejected.returncode != 0
    assert "--target-ref requires an argument" in rejected.stderr


def test_commit_range_command_forwards_explicit_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emitted: list[EthosResult]
) -> None:
    expected = {
        "target_ref": "refs/heads/dev",
        "proposed_head": "a" * 40,
        "remote_head": "b" * 40,
        "remote_name": "origin",
        "trusted_baseline": "c" * 40,
    }

    def admit(root: Path, **coordinates: str) -> dict[str, object]:
        assert root == tmp_path
        assert coordinates == expected
        return {
            "verdict": "pass",
            "state": "admitted",
            "target_ref": "refs/heads/dev",
            "update_kind": "existing",
            "checked_commit_count": 1,
            "revisions": ["a" * 40],
        }

    monkeypatch.setattr(commands, "commit_range_admission_report", admit)
    result = run_ethos_raw(
        *(
            f"hook commit-range --target-ref refs/heads/dev --proposed-head {'a' * 40} "
            f"--remote-head {'b' * 40} --remote origin --trusted-baseline {'c' * 40} --json"
        ).split()
    )
    assert result.returncode == 0, result.stderr
    assert emitted[-1].verdict == "pass"
    assert emitted[-1].data["revisions"] == ("a" * 40,)


@pytest.mark.parametrize(
    ("hook", "expected", "calls"), [("post-commit", 1, 0), ("pre-commit", 23, 1)]
)
def test_hook_run_validates_name_and_propagates_runtime_exit(
    monkeypatch: pytest.MonkeyPatch,
    emitted: list[EthosResult],
    hook: str,
    expected: int,
    calls: int,
) -> None:
    executed: list[object] = []
    monkeypatch.setattr(commands, "execute_hook", lambda *_a, **_k: executed.append(1) or 23)
    with pytest.raises(SystemExit) as stopped:
        commands.run_hook(hook, ("arg",))
    assert stopped.value.code == expected
    assert len(executed) == calls
    assert emitted == []


@pytest.mark.parametrize(
    "failure",
    [
        OSError("readonly"),
        ValueError("invalid runtime"),
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emitted: list[EthosResult], failure: Exception
) -> None:
    monkeypatch.setattr(
        commands, "install_hook_launchers", lambda *_a, **_k: (_ for _ in ()).throw(failure)
    )
    monkeypatch.setattr(
        commands,
        "state_schema_report",
        lambda _root: (_ for _ in ()).throw(ValueError("unavailable")),
    )
    commands.install(json_output=True)
    result = emitted[-1]
    state = str(failure).startswith("state_")
    assert (result.verdict, result.state, result.summary["wired"]) == ("block", "blocked", False)
    assert result.required_gaps == ((str(failure) if state else f"hook_install_failed:{failure}"),)
    reset = " --reset-state --authorize" if state else ""
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emitted: list[EthosResult], *, deferred: bool
) -> None:
    runtime = {
        "hooks_path": str(tmp_path / "hooks"),
        "python": str(tmp_path / "python"),
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
    monkeypatch.setattr(commands, "install_hook_launchers", lambda *_a, **_k: runtime)
    commands.install()
    result = emitted[-1]
    assert result.to_dict()["data"] == runtime
    assert result.verdict == ("block" if deferred else "pass")
    assert result.summary["wired"] is (not deferred)
    assert (
        result.summary["linked_worktrees_checked"],
        result.summary["linked_worktrees_repaired"],
        result.summary["generated_paths_removed"],
    ) == (2, 1, 0 if deferred else 1)
    assert result.next_action == (
        f"ethos hook install --root {tmp_path} --json" if deferred else ""
    )


@pytest.mark.parametrize("verdict", ["pass", "unknown"])
def test_pre_push_preserves_remote_and_never_upgrades_unknown_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, emitted: list[EthosResult], verdict: str
) -> None:
    def admit(**coordinates: object) -> dict[str, object]:
        assert coordinates["remote_name"] == "github"
        return {
            "verdict": verdict,
            "state": "observed",
            "target_branch": "dev",
            "role": "accepted_root",
            "remote_name": "github",
            "decision": {"action": "allow"},
            "required_gaps": [] if verdict == "pass" else ["push_admission_facts_unavailable"],
        }

    monkeypatch.setattr(commands, "push_admission_report", admit)
    commands.pre_push(
        "refs/heads/dev",
        "a" * 40,
        options=commands.PushOptions(remote_head="b" * 40, remote="github"),
    )
    result = emitted[-1]
    assert result.verdict == verdict
    assert result.summary["remote"] == "github"
    assert result.next_action == (
        "" if verdict == "pass" else f"ethos status --root {tmp_path} --json"
    )

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.hook.commands as hook_commands
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_commit_range_help_exposes_required_coordinates_only_as_named_options() -> None:
    completed = run_ethos_raw("hook", "commit-range", "--help")

    assert completed.returncode == 0, completed.stderr
    usage = completed.stdout.splitlines()[0]
    assert "TARGET-REF" not in usage
    assert "PROPOSED-HEAD" not in usage
    assert "REMOTE-HEAD" not in usage
    assert " REMOTE " not in usage
    for option in ("--target-ref", "--proposed-head", "--remote-head", "--remote"):
        assert option in completed.stdout


def test_commit_range_rejects_positional_coordinates() -> None:
    completed = run_ethos_raw(
        "hook",
        "commit-range",
        "refs/heads/dev",
        "a" * 40,
        "b" * 40,
        "origin",
        "--root",
        ".",
        "--json",
    )

    assert completed.returncode != 0
    assert "--target-ref requires an argument" in completed.stderr


def test_commit_range_command_uses_explicit_coordinates_without_mutation(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    policy = repo / ".ethos/workspace.toml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        'signing_required = false\nsigning_format = "ssh"\n',
        encoding="utf-8",
    )
    (repo / "change.txt").write_text("change\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fix: validate range")
    proposed = git(repo, "rev-parse", "HEAD")

    completed = run_ethos_raw(
        "hook",
        "commit-range",
        "--target-ref",
        "refs/heads/dev",
        "--proposed-head",
        proposed,
        "--remote-head",
        baseline,
        "--remote",
        "origin",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["command"] == "hook commit-range"
    assert payload["verdict"] == "pass"
    assert payload["state"] == "admitted"
    assert payload["summary"] == {
        "target_ref": "refs/heads/dev",
        "update_kind": "existing",
        "checked_commit_count": 1,
    }
    assert payload["data"]["baseline_commit"] == baseline
    assert payload["data"]["proposed_commit"] == proposed
    assert payload["data"]["revisions"] == [proposed]
    assert payload["data"]["required_gaps"] == []
    assert git(repo, "rev-parse", "HEAD") == proposed


def test_hook_run_refuses_unknown_hook_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[object] = []
    monkeypatch.setattr(hook_commands, "execute_hook", lambda *_args, **_kwargs: called.append(1))
    with pytest.raises(SystemExit) as stopped:
        hook_commands.run_hook("post-commit")
    assert stopped.value.code == 1
    assert called == []


def test_hook_run_propagates_semantic_runtime_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "execute_hook", lambda *_args, **_kwargs: 23)
    with pytest.raises(SystemExit) as stopped:
        hook_commands.run_hook("pre-commit", ("arg",))
    assert stopped.value.code == 23


@pytest.mark.parametrize("failure", [OSError("readonly"), ValueError("invalid runtime")])
def test_hook_install_emits_fail_closed_error_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        hook_commands,
        "install_hook_launchers",
        lambda _root, **_kwargs: (_ for _ in ()).throw(failure),
    )
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    hook_commands.install(json_output=True)

    result = emitted[-1]
    assert (result.verdict, result.state) == ("block", "blocked")
    assert result.required_gaps == (f"hook_install_failed:{failure}",)
    assert result.summary["wired"] is False
    assert result.next_action == f"ethos hook install --root {tmp_path.resolve()} --json"


def test_hook_install_emits_runtime_binding_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emitted: list[object] = []
    runtime = {
        "hooks_path": str(tmp_path / "hooks"),
        "python": str(tmp_path / "python"),
        "scripts": ["commit-msg", "pre-commit", "pre-push", "reference-transaction"],
        "linked_worktrees": [
            {"path": str(tmp_path), "state": "repaired"},
            {"path": str(tmp_path / "linked"), "state": "checked"},
        ],
        "generation_cleanup": {
            "checked": [str(tmp_path / "old"), str(tmp_path / "current")],
            "removed": [str(tmp_path / "old")],
            "retained": [str(tmp_path / "current")],
        },
    }
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "install_hook_launchers", lambda _root, **_kwargs: runtime)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    hook_commands.install()

    result = emitted[-1]
    assert (result.verdict, result.state) == ("pass", "installed")
    assert result.data["hooks_path"] == runtime["hooks_path"]
    assert result.data["python"] == runtime["python"]
    assert tuple(result.data["scripts"]) == tuple(runtime["scripts"])
    assert [dict(item) for item in result.data["linked_worktrees"]] == runtime["linked_worktrees"]
    assert {
        key: list(value) for key, value in result.data["generation_cleanup"].items()
    } == runtime["generation_cleanup"]
    assert result.summary == {
        "hooks_path": runtime["hooks_path"],
        "python": runtime["python"],
        "wired": True,
        "pack_refs_disabled": True,
        "linked_worktrees_checked": 2,
        "linked_worktrees_repaired": 1,
        "generated_paths_removed": 1,
        "generation_cleanup": "",
        "legacy_runtime_locator": "",
        "state_transition": "",
    }
    assert result.next_action == ""


def test_hook_install_blocks_until_deferred_cleanup_converges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emitted: list[object] = []
    runtime = {
        "hooks_path": str(tmp_path / "hooks"),
        "python": str(tmp_path / "python"),
        "scripts": ["commit-msg", "pre-commit", "pre-push", "reference-transaction"],
        "required_gaps": ["hook_runtime_cleanup_deferred"],
        "linked_worktrees": [],
        "generation_cleanup": {
            "state": "deferred",
            "checked": [str(tmp_path / "old")],
            "removed": [],
            "retained": [str(tmp_path / "current")],
            "deferred": [str(tmp_path / "old")],
            "error": "cleanup failed",
        },
    }
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "install_hook_launchers", lambda _root, **_kwargs: runtime)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    hook_commands.install()

    result = emitted[-1]
    assert (result.verdict, result.state) == ("block", "blocked")
    assert result.required_gaps == ("hook_runtime_cleanup_deferred",)
    assert result.next_action == f"ethos hook install --root {tmp_path.resolve()} --json"

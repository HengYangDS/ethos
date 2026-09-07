from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.hook.commands as hook_commands
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path


def test_commit_range_grammar_requires_named_coordinates() -> None:
    help_result = run_ethos_raw("hook", "commit-range", "--help")

    assert help_result.returncode == 0, help_result.stderr
    usage = help_result.stdout.splitlines()[0]
    assert all(name not in usage for name in ("TARGET-REF", "PROPOSED-HEAD", "REMOTE-HEAD"))
    for option in ("--target-ref", "--proposed-head", "--remote-head", "--remote"):
        assert option in help_result.stdout
    rejected = run_ethos_raw(
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

    assert rejected.returncode != 0
    assert "--target-ref requires an argument" in rejected.stderr


def test_commit_range_command_forwards_explicit_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposed, remote, baseline = "a" * 40, "b" * 40, "c" * 40
    calls: list[tuple[Path, dict[str, object]]] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        hook_commands,
        "commit_range_admission_report",
        lambda root, **kwargs: (
            calls.append((root, kwargs))
            or {
                "verdict": "pass",
                "state": "admitted",
                "target_ref": kwargs["target_ref"],
                "update_kind": "existing",
                "checked_commit_count": 1,
                "revisions": [kwargs["proposed_head"]],
                "required_gaps": [],
            }
        ),
    )

    completed = run_ethos_raw(
        "hook",
        "commit-range",
        "--target-ref",
        "refs/heads/dev",
        "--proposed-head",
        proposed,
        "--remote-head",
        remote,
        "--remote",
        "origin",
        "--trusted-baseline",
        baseline,
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert calls == [
        (
            tmp_path,
            {
                "target_ref": "refs/heads/dev",
                "proposed_head": proposed,
                "remote_head": remote,
                "remote_name": "origin",
                "trusted_baseline": baseline,
            },
        )
    ]
    assert (payload["verdict"], payload["data"]["revisions"]) == ("pass", [proposed])


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

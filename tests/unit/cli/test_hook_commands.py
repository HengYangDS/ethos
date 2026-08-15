from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.hook.commands as hook_commands

if TYPE_CHECKING:
    from pathlib import Path


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
        lambda _root: (_ for _ in ()).throw(failure),
    )
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    hook_commands.install(json_output=True)

    result = emitted[-1]
    assert (result.verdict, result.state) == ("block", "blocked")
    assert result.required_gaps == (f"hook_install_failed:{failure}",)
    assert result.summary["wired"] is False


def test_hook_install_emits_runtime_binding_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emitted: list[object] = []
    runtime = {
        "hooks_path": str(tmp_path / "hooks"),
        "python": str(tmp_path / "python"),
        "scripts": ["pre-commit", "pre-push", "reference-transaction"],
    }
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "install_hook_launchers", lambda _root: runtime)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    hook_commands.install()

    result = emitted[-1]
    assert (result.verdict, result.state) == ("pass", "installed")
    assert dict(result.data) == runtime | {"scripts": tuple(runtime["scripts"])}
    assert result.summary == {
        "hooks_path": runtime["hooks_path"],
        "python": runtime["python"],
        "wired": True,
        "pack_refs_disabled": True,
    }

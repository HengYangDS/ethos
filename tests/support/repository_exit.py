"""Shared repository-exit setup: an adopted repository, its exit state, and an exact apply."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.repo.runtime.retirement as retirement
from ethos.adapters.repo.config_effects import config_values
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.exit_plan import exit_preview
from ethos.adapters.repo.hook.preimage import ACTIVATION_KEYS
from ethos.application.adoption import adopt_repository
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialized_activation_case

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from ethos.result import EthosResult


class Crash(BaseException):
    """Stop an exit the way a killed process would: no compensation runs."""


def observe_no_foreign_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Observe an empty process table on Windows, where a standard user cannot read them all.

    The exit fails closed on an unreadable process by design; these scenarios test the exit itself.
    """
    if os.name == "nt":
        monkeypatch.setattr(retirement, "process_commands", lambda *_a, **_k: "")


def adopted_with_own_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, hooks: str = ".githooks"
) -> tuple[Path, Path, dict[str, tuple[str, ...]]]:
    """Adopt a repository whose own hooks path ETHOS replaces; return its config before that."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    observe_no_foreign_processes(monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", hooks).returncode == 0
    before = config_values(repo, ACTIVATION_KEYS, scope="local")
    install_hook_launchers(repo)
    return repo, common, before


def exit_state(repo: Path, common: Path) -> dict[str, object]:
    """Every ETHOS file and the repository's activation keys.

    Locks and SQLite's WAL sidecars, which a read-only observation of a WAL database creates,
    carry no state of their own.
    """
    files = {
        path.relative_to(common).as_posix(): path.read_bytes()
        for path in sorted((common / "ethos").rglob("*"))
        if path.is_file() and not path.name.endswith((".lock", "-wal", "-shm"))
    }
    return {"files": files, "config": config_values(repo, ACTIVATION_KEYS, scope="local")}


def apply_exit(repo: Path, **overrides: Any) -> EthosResult:
    """Apply the current preview with the exact request, unless a test overrides a part of it."""
    request: dict[str, Any] = {
        "apply": True,
        "authorize": True,
        "expect_head": current_head(repo),
        "expect_plan_digest": exit_preview(repo)["plan_digest"],
    }
    return adopt_repository(repo, exit_repository=True, **(request | overrides))

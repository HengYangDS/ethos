"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.config_effects as config_effects
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_config_effect_failures_report_the_exact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = subprocess.CompletedProcess([], 2, "", "config failed")
    monkeypatch.setattr(config_effects, "run_git", lambda *_args, **_kwargs: failure)
    with pytest.raises(ValueError, match="config failed"):
        config_effects.config_values(tmp_path, ("core.hooksPath",), scope="local")
    with pytest.raises(ValueError, match="config failed"):
        config_effects.replace_config_values(tmp_path, {"core.hooksPath": ()}, scope="local")


def test_exact_config_is_recognized_without_rewriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Matching keys are observed without removal and re-addition; differing keys apply."""
    repo = init_git_repo(tmp_path / "repo")
    config_effects.set_common_config(repo, {"gc.packRefs": "false"})
    native = config_effects.run_git
    writes: list[tuple[str, ...]] = []

    def observed(root: Path, *args: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "--unset-all" in args or "--add" in args:
            writes.append(args)
        return native(root, *args, **kwargs)

    monkeypatch.setattr(config_effects, "run_git", observed)
    config_effects.set_common_config(repo, {"gc.packRefs": "false"})
    config_effects.unset_worktree_config(repo, ("core.fsmonitor",))
    assert writes == []

    config_effects.set_common_config(repo, {"gc.packRefs": "true"})
    assert writes
    assert config_effects.config_values(repo, ("gc.packRefs",), scope="local") == {
        "gc.packRefs": ("true",)
    }

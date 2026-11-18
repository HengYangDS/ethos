"""Shared fixtures for runtime generation retirement tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ethos.adapters.repo.git import git_common_dir
from tests.support.governed_repository import init_git_repo

NEEDS_A_CLOSED_DIRECTORY = pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="a directory that its owner cannot search needs POSIX modes and no superuser",
)


def generation_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a repository whose hooks and runtime each select one immutable generation."""
    repo = init_git_repo(tmp_path / "repo")
    common = Path(git_common_dir(repo))
    hooks, runtime = common / "ethos/hooks" / ("a" * 64), common / "ethos/runtime" / ("a" * 64)
    for path in (hooks, runtime):
        path.mkdir(parents=True)
        (path / "selected").write_bytes(b"selected immutable payload")
    (runtime.parent / "CURRENT").write_text(runtime.name + "\n", encoding="ascii")
    return repo, hooks, runtime

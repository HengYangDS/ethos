"""Observe a working tree through an isolated Git index and object store."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Iterator


class WorktreePostimage(NamedTuple):
    """One isolated Git index projection of the current working content."""

    tree: str
    changed_paths: tuple[str, ...]
    environment: dict[str, str]


@contextmanager
def observe_worktree_postimage(root: Path, *, previous: str) -> Iterator[WorktreePostimage]:
    """Project the complete worktree through a quarantined index and object store."""
    common = Path(git_common_dir(root))
    with tempfile.TemporaryDirectory(prefix="ethos-postimage-") as temporary:
        workspace = Path(temporary)
        objects = workspace / "objects"
        objects.mkdir()
        environment = {
            "GIT_INDEX_FILE": (workspace / "index").as_posix(),
            "GIT_OBJECT_DIRECTORY": objects.as_posix(),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": (common / "objects").as_posix(),
        }
        run_git(root, "read-tree", previous, env=environment)
        staged = run_git(root, "add", "--all", check=False, env=environment)
        if staged.returncode:
            raise ValueError(staged.stderr.strip() or "git_effect_postimage_stage_failed")
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        changed = tuple(
            run_git(
                root,
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACMRTD",
                env=environment,
            ).stdout.splitlines()
        )
        yield WorktreePostimage(tree, changed, environment)

"""Observe a working tree through an isolated Git index and object store."""

from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Generator


class WorktreePostimage(NamedTuple):
    """One isolated content tree and its explicitly requested changed-path projection."""

    tree: str
    changed_paths: tuple[str, ...]
    environment: dict[str, str]


@contextmanager
def observe_worktree_postimage(
    root: Path, *, previous: str, include_paths: bool = True, only: tuple[str, ...] = ()
) -> Generator[WorktreePostimage]:
    """Project complete native content; enumerate changed paths only when requested.

    With `only`, the tree is the previous one with the worktree's content at those pathspecs;
    a pathspec that names no file of either adds nothing.
    """
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
        # Git refuses to add a pathspec that names no file of the tree or of the worktree, so
        # each one is listed first. A listed name is bytes, which nothing here decodes.
        listing = ("ls-files", "--cached", "--others", "--exclude-standard", "-z", "--")
        named = tuple(
            pathspec
            for pathspec in only
            if run_git(root, *listing, pathspec, text=False, env=environment).stdout
        )
        if named or not only:
            limited = ("--", *named) if named else ()
            staged = run_git(root, "add", "--all", *limited, check=False, env=environment)
            if staged.returncode:
                raise ValueError(staged.stderr.strip() or "git_effect_postimage_stage_failed")
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        changed = (
            tuple(
                run_git(
                    root,
                    "diff",
                    "--cached",
                    "--name-only",
                    "--diff-filter=ACMRTD",
                    env=environment,
                ).stdout.splitlines()
            )
            if include_paths
            else ()
        )
        yield WorktreePostimage(tree, changed, environment)


def observe_execution_source(root: Path, head: str, tree: str) -> dict[str, str]:
    """Observe native working content and staged correspondence without editing the index."""
    try:
        staged = run_git(
            root,
            "diff",
            "--cached",
            "--quiet",
            "--no-ext-diff",
            head,
            "--",
            check=False,
            observation=True,
        )
        with observe_worktree_postimage(root, previous=head, include_paths=False) as observed:
            worktree = observed.tree
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        message = f"proof_execution_source_unavailable:{error}"
        raise ValueError(message) from error
    if staged.returncode not in {0, 1}:
        message = f"proof_execution_source_unavailable:{staged.stderr.strip()}"
        raise ValueError(message)
    return {"worktree": worktree, "index": tree if staged.returncode == 0 else ""}

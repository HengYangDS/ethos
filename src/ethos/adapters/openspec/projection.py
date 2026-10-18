"""Expose official OpenSpec artifacts from one exact Git tree."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def openspec_tree_projection(repo: Path, tree_ref: str | None) -> Generator[Path]:
    """Materialize `openspec/**` of one tree in a disposable root; None reads the worktree."""
    if tree_ref is None:
        yield repo
        return
    paths = run_git(
        repo,
        "ls-tree",
        "-r",
        "-z",
        "--name-only",
        tree_ref,
        "--",
        "openspec",
    ).stdout
    if not paths:
        msg = "openspec_tree_projection_missing"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix="ethos-openspec-tree-") as directory:
        projection = Path(directory)
        environment = {"GIT_INDEX_FILE": (projection / "index").as_posix()}
        run_git(repo, "read-tree", tree_ref, env=environment)
        run_git(
            repo,
            "checkout-index",
            f"--prefix={projection.as_posix()}/",
            "--stdin",
            "-z",
            env=environment,
            stdin=paths,
        )
        yield projection

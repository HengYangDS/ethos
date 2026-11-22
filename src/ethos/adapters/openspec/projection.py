"""Expose official OpenSpec artifacts from one exact Git tree."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.openspec.configuration import OPENSPEC_SKILL_RECORD
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.contracts.paradigm.declaration import binding_path
from ethos.repository.profile import repository_profile_from_text

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping


@contextmanager
def openspec_tree_projection(
    repo: Path,
    tree_ref: str | None,
    *,
    carriers: tuple[str, ...] = (),
    environment: Mapping[str, str] | None = None,
) -> Generator[Path]:
    """Materialize `openspec/**` of one tree in a disposable root; None reads the worktree.

    `carriers` names further files of that tree to materialize beside it; a tree that holds
    none of them and no `openspec/` then projects as an empty root. `environment` names the
    object store of a tree that the shared store does not hold; the index is always the
    projection's own.
    """
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
        *carriers,
        env=environment,
    ).stdout
    if not paths and not carriers:
        msg = "openspec_tree_projection_missing"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix="ethos-openspec-tree-") as directory:
        projection = Path(directory)
        own = {**(environment or {}), "GIT_INDEX_FILE": (projection / "index").as_posix()}
        run_git(repo, "read-tree", tree_ref, env=own)
        run_git(
            repo,
            "checkout-index",
            f"--prefix={projection.as_posix()}/",
            "--stdin",
            "-z",
            env=own,
            stdin=paths,
        )
        yield projection


def report_carriers(
    repo: Path, tree_ref: str, *, environment: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    """Name the files outside `openspec/` that an official report reads through its root.

    They are the profile, the release binding, OpenSpec's record of its shared skills, and the
    authority files that the profile declares for supplemental metadata. The profile is the
    tree's own, and a tree without one declares none.
    """
    try:
        profile = load_committed_repository_profile(repo, tree_ref, environment=environment)
    except ValueError:
        profile = repository_profile_from_text(repo, exists=False, text="")
    policy = profile.declaration.openspec if profile.declaration is not None else None
    metadata = (*policy.capability_metadata, *policy.specs_root_metadata) if policy else ()
    return (
        binding_path("profile"),
        binding_path("release"),
        OPENSPEC_SKILL_RECORD.as_posix(),
        *(item.authority_ref for item in metadata),
    )

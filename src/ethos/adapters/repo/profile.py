"""Committed repository profile observation adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import repository_profile_from_text

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def load_committed_repository_profile(
    root: Path,
    tree_ref: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> RepositoryProfile:
    """Load one profile from an exact committed Git tree."""
    result = run_git(
        root,
        "show",
        f"{tree_ref}:.ethos/profile.toml",
        check=False,
        env=environment,
    )
    if result.returncode == 0:
        return repository_profile_from_text(root, exists=True, text=result.stdout)
    commit = run_git(
        root,
        "rev-parse",
        "--verify",
        f"{tree_ref}^{{commit}}",
        check=False,
        env=environment,
    )
    if commit.returncode == 0:
        return repository_profile_from_text(root, exists=False, text="")
    message = "repository_tree_ref_invalid"
    raise ValueError(message)


def repository_identity(
    root: Path,
    *,
    tree_ref: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Return the profile-bound repository identity without inventing a Commitment."""
    profile = (
        load_committed_repository_profile(root, tree_ref, environment=environment)
        if tree_ref is not None
        else load_repository_profile(root)
    )
    if profile.state != "valid" or profile.declaration is None:
        raise ValueError(INVALID_PROFILE_ERROR)
    return f"repository:{profile.declaration.profile_id}"

"""Committed repository profile observation adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import repository_profile_from_text

if TYPE_CHECKING:
    from pathlib import Path


def load_committed_repository_profile(root: Path, tree_ref: str) -> RepositoryProfile:
    """Load one profile from an exact committed Git tree."""
    result = run_git(root, "show", f"{tree_ref}:.ethos/profile.toml", check=False)
    if result.returncode == 0:
        return repository_profile_from_text(root, exists=True, text=result.stdout)
    commit = run_git(root, "rev-parse", "--verify", f"{tree_ref}^{{commit}}", check=False)
    if commit.returncode == 0:
        return repository_profile_from_text(root, exists=False, text="")
    message = "repository_tree_ref_invalid"
    raise ValueError(message)

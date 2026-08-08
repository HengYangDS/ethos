"""Apply and attest exact repository-local Git configuration effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def set_local_config(root: Path, values: dict[str, str]) -> Attestation:
    """Set or recognize one exact local configuration projection."""
    before = {key: _value(root, key) for key in values}
    state = "recognized" if before == values else "applied"
    if state == "applied":
        for key, value in values.items():
            completed = run_git(root, "config", "--local", key, value, check=False)
            if completed.returncode:
                raise ValueError(completed.stderr.strip() or "git_config_effect_failed")
    after = {key: _value(root, key) for key in values}
    if after != values:
        message = "git_config_effect_postcondition_failed"
        raise ValueError(message)
    repository = load_repository_commitment(root)
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:git-config",
            operation="git.config.local",
            command=("git", "config", "--local"),
            subject={"keys": tuple(values)},
            before=before,
            after=after,
        ),
        state=state,
        commitment_digest=repository.digest(),
        repository_id=repository.id,
    )


def set_worktree_config(root: Path, values: dict[str, str]) -> None:
    """Set one exact worktree-local Git configuration projection."""
    completed = run_git(root, "config", "extensions.worktreeConfig", "true", check=False)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_config_effect_failed")
    for key, value in values.items():
        completed = run_git(root, "config", "--worktree", key, value, check=False)
        if completed.returncode:
            raise ValueError(completed.stderr.strip() or "git_config_effect_failed")
    after = {key: _worktree_value(root, key) for key in values}
    if after != values:
        message = "git_config_effect_postcondition_failed"
        raise ValueError(message)


def _value(root: Path, key: str) -> str:
    completed = run_git(root, "config", "--local", "--get", key, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _worktree_value(root: Path, key: str) -> str:
    completed = run_git(root, "config", "--worktree", "--get", key, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""

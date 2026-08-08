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
    before = _values(root, values, scope="local")
    state = "recognized" if before == values else "applied"
    if state == "applied":
        _set_values(root, values, scope="local")
    after = _values(root, values, scope="local")
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
    _set_values(root, values, scope="worktree")
    if _values(root, values, scope="worktree") != values:
        message = "git_config_effect_postcondition_failed"
        raise ValueError(message)


def _set_values(root: Path, values: dict[str, str], *, scope: str) -> None:
    for key, value in values.items():
        completed = run_git(root, "config", f"--{scope}", key, value, check=False)
        if completed.returncode:
            raise ValueError(completed.stderr.strip() or "git_config_effect_failed")


def _values(root: Path, values: dict[str, str], *, scope: str) -> dict[str, str]:
    observed = {}
    for key in values:
        completed = run_git(root, "config", f"--{scope}", "--get", key, check=False)
        observed[key] = completed.stdout.strip() if completed.returncode == 0 else ""
    return observed

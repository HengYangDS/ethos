"""Apply and attest exact repository-local Git configuration effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect

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


def set_common_config(root: Path, values: dict[str, str]) -> None:
    """Set one exact Git-common configuration projection."""
    replace_config_values(root, {key: (value,) for key, value in values.items()}, scope="local")


def unset_worktree_config(root: Path, keys: tuple[str, ...]) -> None:
    """Remove owned worktree-local projections and prove their absence."""
    replace_config_values(root, dict.fromkeys(keys, ()), scope="worktree")


def config_values(root: Path, keys: tuple[str, ...], *, scope: str) -> dict[str, tuple[str, ...]]:
    """Observe all values for exact Git configuration keys."""
    result: dict[str, tuple[str, ...]] = {}
    for key in keys:
        completed = run_git(root, "config", f"--{scope}", "--get-all", key, check=False)
        if completed.returncode not in {0, 1}:
            raise ValueError(completed.stderr.strip() or "git_config_observation_failed")
        result[key] = tuple(completed.stdout.splitlines()) if completed.returncode == 0 else ()
    return result


def replace_config_values(
    root: Path,
    values: dict[str, tuple[str, ...]],
    *,
    scope: str,
) -> None:
    """Replace exact Git configuration values and prove the postcondition."""
    for key, expected in values.items():
        removed = run_git(root, "config", f"--{scope}", "--unset-all", key, check=False)
        if removed.returncode not in {0, 5}:
            raise ValueError(removed.stderr.strip() or "git_config_effect_failed")
        for value in expected:
            added = run_git(root, "config", f"--{scope}", "--add", key, value, check=False)
            if added.returncode:
                raise ValueError(added.stderr.strip() or "git_config_effect_failed")
    if config_values(root, tuple(values), scope=scope) != values:
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

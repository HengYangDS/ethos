"""Apply and attest exact repository-local Git configuration effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path


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
    """Recognize exact values, replace only differing keys and prove the postcondition."""
    before = config_values(root, tuple(values), scope=scope)
    for key, expected in values.items():
        if before[key] == expected:
            continue
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

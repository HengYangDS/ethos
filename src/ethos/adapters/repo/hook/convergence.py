"""Transactional convergence of repository-family Git hook bindings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.config_effects import set_worktree_config
from ethos.adapters.repo.git import run_git


@dataclass(frozen=True, slots=True)
class WorktreeHookBinding:
    """One linked worktree and its prior hook configuration."""

    root: Path
    hooks_path: str
    pack_refs: str


def converge_worktree_hooks(root: Path, hooks: Path) -> tuple[Path, ...]:
    """Bind every linked worktree to one hook root or restore all prior values."""
    bindings = tuple(_binding(path) for path in _worktrees(root))
    values = {"core.hooksPath": hooks.as_posix(), "gc.packRefs": "false"}
    try:
        for binding in bindings:
            set_worktree_config(binding.root, values)
        _require_converged(bindings, hooks)
    except (OSError, ValueError):
        for binding in bindings:
            _restore(binding)
        raise
    return tuple(binding.root for binding in bindings)


def _require_converged(bindings: tuple[WorktreeHookBinding, ...], hooks: Path) -> None:
    if any(_binding(binding.root).hooks_path != hooks.as_posix() for binding in bindings):
        message = "hook_worktree_binding_postcondition_failed"
        raise ValueError(message)


def _worktrees(root: Path) -> tuple[Path, ...]:
    completed = run_git(root, "worktree", "list", "--porcelain")
    return tuple(
        Path(line.removeprefix("worktree ")).resolve()
        for line in completed.stdout.splitlines()
        if line.startswith("worktree ")
    )


def _binding(root: Path) -> WorktreeHookBinding:
    return WorktreeHookBinding(
        root=root,
        hooks_path=_value(root, "core.hooksPath"),
        pack_refs=_value(root, "gc.packRefs"),
    )


def _value(root: Path, key: str) -> str:
    completed = run_git(root, "config", "--worktree", "--get", key, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _restore(binding: WorktreeHookBinding) -> None:
    for key, value in (
        ("core.hooksPath", binding.hooks_path),
        ("gc.packRefs", binding.pack_refs),
    ):
        args = (
            ("config", "--worktree", key, value)
            if value
            else (
                "config",
                "--worktree",
                "--unset-all",
                key,
            )
        )
        completed = run_git(binding.root, *args, check=False)
        if completed.returncode not in {0, 5}:
            message = "hook_worktree_binding_rollback_failed"
            raise ValueError(message)

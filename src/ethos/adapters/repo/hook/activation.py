"""Activate and retire Git-common hook/runtime generations."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import cast

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.hook_runtime_install as runtime_install
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_command
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.binding import HookRuntimeBinding
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection

_ACTIVATION_KEYS = ("extensions.worktreeConfig", "gc.packRefs", "core.hooksPath")
_WORKTREE_ACTIVATION_KEYS = ("core.hooksPath", "gc.packRefs")
_ACTIVE_CONSUMER_DIRECTORIES = ("operations", "transactions", "ref-intent")


def install_hook_launchers(root: Path, *, python: Path | None = None) -> HookRuntimeBinding:
    """Install and activate one common-dir hook/runtime generation."""
    repo = root.resolve()
    source_python = Path(sys.executable) if python is None else python
    if not source_python.is_absolute() or not source_python.is_file():
        message = "hook_runtime_python_invalid"
        raise ValueError(message)
    expected_build, build_source = expected_runtime_build(repo)
    runtime = runtime_install.materialize_hook_runtime(
        repo,
        source_python,
        expected_build=expected_build,
        build_source=build_source,
    )
    common = Path(git_common_dir(repo))
    hooks = runtime_install.materialize_hook_launchers(common / "ethos" / "hooks")
    _consumer_text(repo, common)
    linked = _linked_worktree_paths(repo)
    common_before = config_effects.config_values(repo, _ACTIVATION_KEYS, scope="local")
    current_before = _runtime_selection_bytes(common)
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]] = {}
    try:
        binding, cleanup_plan = _activate_common_runtime(
            repo,
            common,
            runtime.parent,
            hooks,
            linked,
            worktrees_before,
            expected_build=expected_build,
        )
    except (OSError, ValueError) as error:
        try:
            _restore_failed_activation(
                repo,
                common,
                common_before,
                worktrees_before,
                current_before,
            )
        except ValueError as compensation_error:
            raise compensation_error from error
        raise
    cleanup = _apply_generation_cleanup(cleanup_plan)
    legacy = common / "ethos-runtime-python"
    present = legacy.exists() or legacy.is_symlink()
    if present:
        legacy.unlink()
    cast("dict[str, object]", binding)["legacy_runtime_locator"] = {
        "path": legacy.as_posix(),
        "state": "retired" if present else "absent",
        "removed": present,
    }
    expected_common = _expected_common_activation(hooks)
    cast("dict[str, object]", binding)["linked_worktrees"] = [
        {
            "path": worktree.as_posix(),
            "state": (
                "repaired"
                if common_before != expected_common or any(worktrees_before[worktree].values())
                else "checked"
            ),
        }
        for worktree in linked
    ]
    cast("dict[str, object]", binding)["generation_cleanup"] = cleanup
    return binding


def _activate_common_runtime(
    repo: Path,
    common: Path,
    runtime: Path,
    hooks: Path,
    linked: tuple[Path, ...],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
    *,
    expected_build: runtime_install.BuildIdentity,
) -> tuple[HookRuntimeBinding, dict[str, tuple[Path, ...]]]:
    """Select and post-observe one common runtime/hook activation."""
    activate_runtime(common, runtime)
    config_effects.set_common_config(repo, {"extensions.worktreeConfig": "true"})
    worktrees_before.update(
        {
            worktree: config_effects.config_values(
                worktree, _WORKTREE_ACTIVATION_KEYS, scope="worktree"
            )
            for worktree in linked
        }
    )
    config_effects.set_common_config(
        repo,
        {"gc.packRefs": "false", "core.hooksPath": hooks.as_posix()},
    )
    for worktree in linked:
        config_effects.unset_worktree_config(worktree, _WORKTREE_ACTIVATION_KEYS)
    _require_common_activation(repo, linked, hooks, expected_build=expected_build)
    cleanup_plan = _generation_cleanup_plan(repo, hooks, runtime)
    binding = hook_runtime_binding(repo, expected_build=expected_build)
    if binding["hooks_path"] != hooks.as_posix():
        message = "hook_runtime_activation_drift"
        raise ValueError(message)
    if binding["required_gaps"]:
        message = "hook_runtime_activation_invalid:" + ",".join(binding["required_gaps"])
        raise ValueError(message)
    return binding, cleanup_plan


def _restore_failed_activation(
    repo: Path,
    common: Path,
    common_before: dict[str, tuple[str, ...]],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
    current_before: bytes | None,
) -> None:
    """Attempt every activation compensation and report the complete boundary."""
    errors: list[str] = []
    try:
        _restore_activation(repo, common_before, worktrees_before)
    except (OSError, ValueError) as error:
        errors.append(str(error) or error.__class__.__name__)
    try:
        restore_runtime_selection(common, current_before)
    except OSError as error:
        errors.append(str(error) or error.__class__.__name__)
    if errors:
        message = "hook_runtime_activation_compensation_failed:" + ",".join(errors)
        raise ValueError(message)


def _runtime_selection_bytes(common: Path) -> bytes | None:
    selector = common / "ethos" / "runtime" / "CURRENT"
    try:
        return selector.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        message = "hook_runtime_current_invalid"
        raise ValueError(message) from error


def _linked_worktree_paths(root: Path) -> tuple[Path, ...]:
    """Return every readable worktree sharing the repository common directory."""
    completed = run_git(root, "worktree", "list", "--porcelain", "-z", check=False)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "hook_runtime_worktrees_unreadable")
    paths = tuple(
        Path(field.removeprefix("worktree ")).resolve()
        for field in completed.stdout.split("\0")
        if field.startswith("worktree ")
    )
    if not paths or any(not path.is_dir() for path in paths):
        message = "hook_runtime_worktrees_unreadable"
        raise ValueError(message)
    return paths


def _expected_common_activation(hooks: Path) -> dict[str, tuple[str, ...]]:
    return {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("false",),
        "core.hooksPath": (hooks.as_posix(),),
    }


def _require_common_activation(
    root: Path,
    worktrees: tuple[Path, ...],
    hooks: Path,
    *,
    expected_build: runtime_install.BuildIdentity,
) -> None:
    if config_effects.config_values(
        root, _ACTIVATION_KEYS, scope="local"
    ) != _expected_common_activation(hooks):
        message = "hook_runtime_common_activation_drift"
        raise ValueError(message)
    for worktree in worktrees:
        if config_effects.config_values(worktree, _WORKTREE_ACTIVATION_KEYS, scope="worktree") != {
            "core.hooksPath": (),
            "gc.packRefs": (),
        }:
            message = "hook_runtime_worktree_activation_drift"
            raise ValueError(message)
        binding = hook_runtime_binding(worktree, expected_build=expected_build)
        if binding["hooks_path"] != hooks.as_posix():
            message = "hook_runtime_activation_drift"
            raise ValueError(message)
        if binding["required_gaps"]:
            message = "hook_runtime_activation_invalid:" + ",".join(binding["required_gaps"])
            raise ValueError(message)


def _restore_activation(
    root: Path,
    common: dict[str, tuple[str, ...]],
    worktrees: dict[Path, dict[str, tuple[str, ...]]],
) -> None:
    errors: list[str] = []
    for worktree, values in worktrees.items():
        try:
            config_effects.replace_config_values(worktree, values, scope="worktree")
        except ValueError as error:
            errors.append(str(error) or error.__class__.__name__)
    try:
        config_effects.replace_config_values(root, common, scope="local")
    except ValueError as error:
        errors.append(str(error) or error.__class__.__name__)
    if errors:
        message = "hook_runtime_activation_compensation_failed:" + ",".join(errors)
        raise ValueError(message)


def _generation_cleanup_plan(
    root: Path,
    hooks: Path,
    runtime: Path,
) -> dict[str, tuple[Path, ...]]:
    common = Path(git_common_dir(root))
    hooks_root = common / "ethos" / "hooks"
    runtime_root = common / "ethos" / "runtime"
    candidates = (
        _generated_directories(hooks_root)
        + _generated_directories(runtime_root)
        + _legacy_hook_directories(common)
    )
    consumers = _consumer_text(root, common) + "\n" + _config_text(root)
    retained = {
        path
        for path in candidates
        if path.as_posix() in consumers or f"ethos/{path.parent.name}/{path.name}" in consumers
    }
    retained.update((hooks, runtime))
    retained.add(current_runtime(common).root)
    removable = tuple(sorted(set(candidates) - retained, key=lambda path: path.as_posix()))
    return {
        "checked": tuple(sorted(candidates, key=lambda path: path.as_posix())),
        "removed": removable,
        "retained": tuple(sorted(retained, key=lambda path: path.as_posix())),
    }


def _generated_directories(root: Path) -> tuple[Path, ...]:
    if root.is_symlink():
        message = "hook_runtime_generation_root_invalid"
        raise ValueError(message)
    if not root.exists():
        return ()
    if not root.is_dir():
        message = "hook_runtime_generation_root_invalid"
        raise ValueError(message)
    return tuple(
        path
        for path in root.iterdir()
        if path.is_dir()
        and not path.is_symlink()
        and len(path.name) == 64
        and not (set(path.name) - set("0123456789abcdef"))
    )


def _legacy_hook_directories(common: Path) -> tuple[Path, ...]:
    """Return exact directories created by the retired hook layout."""
    return tuple(
        path
        for path in common.iterdir()
        if path.is_dir()
        and not path.is_symlink()
        and (
            path.name == "ethos-hooks"
            or (
                path.name.startswith("ethos-hooks-")
                and len(path.name.removeprefix("ethos-hooks-")) == 64
                and not (set(path.name.removeprefix("ethos-hooks-")) - set("0123456789abcdef"))
            )
        )
    )


def _consumer_text(root: Path, common: Path) -> str:
    texts = [_process_commands(root)]
    for name in _ACTIVE_CONSUMER_DIRECTORIES:
        directory = common / "ethos" / name
        if directory.is_symlink():
            message = "hook_runtime_consumers_unknown"
            raise ValueError(message)
        if not directory.exists():
            continue
        if not directory.is_dir():
            message = "hook_runtime_consumers_unknown"
            raise ValueError(message)
        for path in directory.rglob("*"):
            if path.is_symlink():
                message = "hook_runtime_consumers_unknown"
                raise ValueError(message)
            if path.is_dir():
                continue
            if not path.is_file():
                message = "hook_runtime_consumers_unknown"
                raise ValueError(message)
            try:
                texts.append(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as error:
                message = "hook_runtime_consumers_unknown"
                raise ValueError(message) from error
    return "\n".join(texts)


def _config_text(root: Path) -> str:
    texts = []
    for worktree in _linked_worktree_paths(root):
        completed = run_git(
            worktree,
            "config",
            "--show-origin",
            "--get-regexp",
            ".*",
            check=False,
        )
        if completed.returncode not in {0, 1}:
            message = "hook_runtime_consumers_unknown"
            raise ValueError(message)
        texts.append(completed.stdout)
    return "\n".join(texts)


def _process_commands(root: Path) -> str:
    command = (
        (
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | % CommandLine",
        )
        if os.name == "nt"
        else ("ps", "-axo", "command=")
    )
    completed = run_command(root, command)
    if completed.returncode:
        message = "hook_runtime_consumers_unknown"
        raise ValueError(message)
    return completed.stdout


def _apply_generation_cleanup(plan: dict[str, tuple[Path, ...]]) -> dict[str, list[str]]:
    removed = plan["removed"]
    for path in removed:
        if path.is_symlink() or not path.is_dir():
            message = "hook_runtime_generation_cleanup_invalid"
            raise ValueError(message)
        shutil.rmtree(path)
    if any(path.exists() or path.is_symlink() for path in removed):
        message = "hook_runtime_generation_cleanup_failed"
        raise ValueError(message)
    if any(path.is_symlink() or not path.is_dir() for path in plan["retained"]):
        message = "hook_runtime_generation_cleanup_failed"
        raise ValueError(message)
    return {key: [path.as_posix() for path in paths] for key, paths in plan.items()}

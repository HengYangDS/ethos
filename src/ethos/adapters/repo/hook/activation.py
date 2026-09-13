"""Activate and retire Git-common hook/runtime generations."""

from __future__ import annotations

import os
import shutil
import sqlite3
import stat
import sys
import uuid
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import cast

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import hook_generation_digest
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.observation import HookRuntimeBinding
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.retirement import retire_generations
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.store.state.schema import prepare_state_transition
from ethos.adapters.store.state.schema import state_database

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity

_ACTIVATION_KEYS = ("extensions.worktreeConfig", "gc.packRefs", "core.hooksPath")
_WORKTREE_ACTIVATION_KEYS = ("core.hooksPath", "gc.packRefs")


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def install_hook_launchers(
    root: Path,
    *,
    python: Path | None = None,
    reset_state: bool = False,
    authorized: bool = False,
) -> HookRuntimeBinding:
    """Install and activate one common-dir hook/runtime generation."""
    if reset_state and not authorized:
        _fail("state_reset_authorization_required")
    repo = root.resolve()
    source_python = python or Path(sys.executable)
    if not source_python.is_absolute() or not source_python.is_file():
        _fail("hook_runtime_python_invalid")
    expected_build, build_source = expected_runtime_build(repo)
    runtime = runtime_materialization.materialize_runtime(
        repo, source_python, expected_build=expected_build, build_source=build_source
    )
    common = Path(git_common_dir(repo))
    hooks = materialize_hook_launchers(common / "ethos" / "hooks")
    linked = _linked_worktree_paths(repo)
    common_before = config_effects.config_values(repo, _ACTIVATION_KEYS, scope="local")
    binding, state_transition, worktrees_before = _activate_with_state(
        repo,
        common,
        runtime.parent,
        hooks,
        linked,
        common_before=common_before,
        current_before=_runtime_selection_bytes(common),
        reset_state=reset_state,
        expected_build=expected_build,
    )
    binding["state_transition"] = state_transition
    binding["legacy_runtime_locator"] = _retire_legacy_locator(common)
    binding["linked_worktrees"] = [
        {
            "path": worktree.as_posix(),
            "state": (
                "repaired"
                if common_before != _common_activation(hooks)
                or any(worktrees_before[worktree].values())
                else "checked"
            ),
        }
        for worktree in linked
    ]
    cleanup = retire_generations(repo, hooks=hooks, runtime=runtime.parent)
    if cleanup["state"] == "deferred" or binding["legacy_runtime_locator"]["state"] == "retained":
        binding["required_gaps"].append("hook_runtime_cleanup_deferred")
        binding["next_action"] = "ethos hook install --json"
    binding["generation_cleanup"] = cleanup
    return binding


def _activate_with_state(
    repo: Path,
    common: Path,
    runtime: Path,
    hooks: Path,
    linked: tuple[Path, ...],
    *,
    common_before: dict[str, tuple[str, ...]],
    current_before: bytes | None,
    reset_state: bool,
    expected_build: BuildIdentity,
) -> tuple[
    HookRuntimeBinding,
    dict[str, object],
    dict[Path, dict[str, tuple[str, ...]]],
]:
    database = state_database(repo)
    database.parent.mkdir(parents=True, exist_ok=True)
    database_existed = database.exists()
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]] = {}
    activated = False
    try:
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("begin immediate")
            state_transition = prepare_state_transition(connection, reset=reset_state)
            activated = True
            binding = _activate_common_runtime(
                repo,
                common,
                runtime,
                hooks,
                linked,
                worktrees_before,
                expected_build=expected_build,
            )
            connection.commit()
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        if activated:
            _restore_failed_activation(
                repo,
                common,
                common_before,
                worktrees_before,
                current_before,
                selected_runtime=f"{runtime.name}\n".encode("ascii"),
            )
        if not database_existed:
            database.unlink(missing_ok=True)
            _remove_state_sidecars(database)
        if isinstance(error, sqlite3.Error):
            _fail(f"state_activation_failed:{error}", error)
        raise
    if not database_existed:
        _remove_state_sidecars(database)
    return binding, state_transition, worktrees_before


def _retire_legacy_locator(common: Path) -> dict[str, object]:
    legacy = common / "ethos-runtime-python"
    present = legacy.exists() or legacy.is_symlink()
    try:
        if present:
            legacy.unlink()
    except OSError as error:
        message = str(error) or error.__class__.__name__
        return {"path": legacy.as_posix(), "state": "retained", "removed": False, "error": message}
    state = "retired" if present else "absent"
    return {"path": legacy.as_posix(), "state": state, "removed": present}


def _remove_state_sidecars(database: Path) -> None:
    for suffix in ("-wal", "-shm"):
        database.with_name(database.name + suffix).unlink(missing_ok=True)


def materialize_hook_launchers(generations: Path) -> Path:
    """Materialize or repair one immutable content-addressed hook generation."""
    if generations.parent.is_symlink() or generations.is_symlink():
        _fail("hook_generation_root_invalid")
    expected = {name: hook_launcher(name) for name in HOOK_NAMES}
    target = generations / hook_generation_digest(expected)
    if target.is_symlink():
        _fail("hook_launcher_projection_invalid")
    try:
        _require_launcher_projection(target, expected)
    except ValueError:
        pass
    else:
        return target
    generations.mkdir(parents=True, exist_ok=True)
    staging = generations / f".generation-{target.name[:12]}-{uuid.uuid4().hex}"
    backup = generations / f".replaced-{target.name[:12]}-{uuid.uuid4().hex}"
    had_target = target.is_dir()
    try:
        staging.mkdir()
        for name, content in expected.items():
            launcher = staging / name
            launcher.write_text(content, encoding="utf-8", newline="\n")
            launcher.chmod(0o755)
        _require_launcher_projection(staging, expected)
        if had_target:
            target.rename(backup)
        try:
            staging.rename(target)
            _require_launcher_projection(target, expected)
        except (OSError, ValueError):
            if target.is_dir():
                shutil.rmtree(target)
            if had_target and backup.is_dir():
                backup.rename(target)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        return target
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _require_launcher_projection(hooks: Path, expected: dict[str, str]) -> None:
    try:
        valid = (
            not hooks.is_symlink()
            and {path.name for path in hooks.iterdir()} == expected.keys()
            and all(
                not (path := hooks / name).is_symlink()
                and path.is_file()
                and path.read_bytes() == content.encode()
                and (os.name == "nt" or stat.S_IMODE(path.stat().st_mode) == 0o755)
                for name, content in expected.items()
            )
        )
    except OSError as error:
        _fail("hook_launcher_projection_invalid", error)
    if not valid:
        _fail("hook_launcher_projection_invalid")


def _activate_common_runtime(
    repo: Path,
    common: Path,
    runtime: Path,
    hooks: Path,
    linked: tuple[Path, ...],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
    *,
    expected_build: BuildIdentity,
) -> HookRuntimeBinding:
    """Select and post-observe one common runtime/hook activation."""
    selected = activate_runtime(common, runtime, expected_current=_runtime_selection_bytes(common))
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
    _require_common_activation(repo, linked, hooks)
    binding = hook_runtime_binding(repo, expected_build=expected_build, selected_runtime=selected)
    if binding["hooks_path"] != hooks.as_posix():
        _fail("hook_runtime_activation_drift")
    if binding["required_gaps"]:
        reason = "hook_runtime_activation_invalid:" + ",".join(binding["required_gaps"])
        if observation := binding.get("contract_observation"):
            raise ProcessExecutionError(
                reason,
                reason=str(observation["reason"]),
                command=tuple(cast("list[str]", observation["command"])),
                cwd=str(observation["cwd"]),
                observation=observation,
            )
        _fail(reason)
    if expected_runtime_build(repo)[0] != expected_build:
        _fail("hook_runtime_expected_build_stale")
    return binding


def _restore_failed_activation(
    repo: Path,
    common: Path,
    common_before: dict[str, tuple[str, ...]],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
    current_before: bytes | None,
    *,
    selected_runtime: bytes | None = None,
) -> None:
    """Attempt every activation compensation and report the complete boundary."""
    errors: list[str] = []
    try:
        _restore_activation(repo, common_before, worktrees_before)
    except (OSError, ValueError) as error:
        errors.append(str(error) or error.__class__.__name__)
    try:
        current = _runtime_selection_bytes(common)
        if current != current_before:
            restore_runtime_selection(common, current_before, expected_current=selected_runtime)
    except (OSError, ValueError) as error:
        errors.append(str(error) or error.__class__.__name__)
    if errors:
        raise ValueError("hook_runtime_activation_compensation_failed:" + ",".join(errors))


def _runtime_selection_bytes(common: Path) -> bytes | None:
    selector = common / "ethos" / "runtime" / "CURRENT"
    try:
        return selector.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        _fail("hook_runtime_current_invalid", error)


def _common_activation(hooks: Path) -> dict[str, tuple[str, ...]]:
    return {
        "extensions.worktreeConfig": ("true",),
        "gc.packRefs": ("false",),
        "core.hooksPath": (hooks.as_posix(),),
    }


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
        _fail("hook_runtime_worktrees_unreadable")
    return paths


def _require_common_activation(
    root: Path,
    worktrees: tuple[Path, ...],
    hooks: Path,
) -> None:
    if config_effects.config_values(root, _ACTIVATION_KEYS, scope="local") != _common_activation(
        hooks
    ):
        _fail("hook_runtime_common_activation_drift")
    if any(
        config_effects.config_values(worktree, _WORKTREE_ACTIVATION_KEYS, scope="worktree")
        != dict.fromkeys(_WORKTREE_ACTIVATION_KEYS, ())
        for worktree in worktrees
    ):
        _fail("hook_runtime_worktree_activation_drift")


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
        raise ValueError("hook_runtime_activation_compensation_failed:" + ",".join(errors))

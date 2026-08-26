"""Activate and retire Git-common hook/runtime generations."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import cast

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_command
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import HookRuntimeBinding
from ethos.adapters.repo.hook.binding import hook_generation_digest
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.repo.runtime.selection import runtime_selection_transaction

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity

_ACTIVATION_KEYS = ("extensions.worktreeConfig", "gc.packRefs", "core.hooksPath")
_WORKTREE_ACTIVATION_KEYS = ("core.hooksPath", "gc.packRefs")
_ACTIVE_CONSUMER_DIRECTORIES = ("operations", "transactions", "ref-intent")


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def install_hook_launchers(root: Path, *, python: Path | None = None) -> HookRuntimeBinding:
    """Install and activate one common-dir hook/runtime generation."""
    repo = root.resolve()
    source_python = python or Path(sys.executable)
    if not source_python.is_absolute() or not source_python.is_file():
        _fail("hook_runtime_python_invalid")
    expected_build, build_source = expected_runtime_build(repo)
    runtime = runtime_materialization.materialize_runtime(
        repo,
        source_python,
        expected_build=expected_build,
        build_source=build_source,
    )
    common = Path(git_common_dir(repo))
    hooks = materialize_hook_launchers(common / "ethos" / "hooks")
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
                selected_runtime=f"{runtime.parent.name}\n".encode("ascii"),
            )
        except ValueError as compensation_error:
            raise compensation_error from error
        raise
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
    cast("dict[str, object]", binding)["generation_cleanup"] = _apply_generation_cleanup(
        common,
        cleanup_plan,
        expected_current=f"{runtime.parent.name}\n".encode("ascii"),
    )
    return binding


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
) -> tuple[HookRuntimeBinding, dict[str, tuple[Path, ...]]]:
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
    _require_common_activation(
        repo,
        linked,
        hooks,
    )
    cleanup_plan = _generation_cleanup_plan(repo, hooks, runtime, selected_runtime=selected)
    binding = hook_runtime_binding(
        repo,
        expected_build=expected_build,
        selected_runtime=selected,
    )
    if binding["hooks_path"] != hooks.as_posix():
        _fail("hook_runtime_activation_drift")
    if binding["required_gaps"]:
        _fail("hook_runtime_activation_invalid:" + ",".join(binding["required_gaps"]))
    if expected_runtime_build(repo)[0] != expected_build:
        _fail("hook_runtime_expected_build_stale")
    return binding, cleanup_plan


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
) -> None:
    if config_effects.config_values(
        root, _ACTIVATION_KEYS, scope="local"
    ) != _expected_common_activation(hooks):
        _fail("hook_runtime_common_activation_drift")
    empty = dict.fromkeys(_WORKTREE_ACTIVATION_KEYS, ())
    for worktree in worktrees:
        if (
            config_effects.config_values(worktree, _WORKTREE_ACTIVATION_KEYS, scope="worktree")
            != empty
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


def _generation_cleanup_plan(
    root: Path,
    hooks: Path,
    runtime: Path,
    *,
    selected_runtime: SelectedRuntime,
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
    retained.add(selected_runtime.root)
    removable = tuple(sorted(set(candidates) - retained, key=lambda path: path.as_posix()))
    return {
        "checked": tuple(sorted(candidates, key=lambda path: path.as_posix())),
        "removed": removable,
        "retained": tuple(sorted(retained, key=lambda path: path.as_posix())),
    }


def _generated_directories(root: Path) -> tuple[Path, ...]:
    if root.is_symlink() or runtime_filesystem.is_junction(root):
        _fail("hook_runtime_generation_root_invalid")
    if not root.exists():
        return ()
    if not root.is_dir():
        _fail("hook_runtime_generation_root_invalid")
    generated: list[Path] = []
    for path in root.iterdir():
        if len(path.name) != 64 or set(path.name) - set("0123456789abcdef"):
            continue
        if path.is_symlink() or runtime_filesystem.is_junction(path) or not path.is_dir():
            _fail("hook_runtime_generation_root_invalid")
        generated.append(path)
    return tuple(generated)


def _legacy_hook_directories(common: Path) -> tuple[Path, ...]:
    """Return exact directories created by the retired hook layout."""
    prefix = "ethos-hooks-"
    generated: list[Path] = []
    for path in common.iterdir():
        matches = path.name == "ethos-hooks" or (
            path.name.startswith(prefix)
            and len(path.name.removeprefix(prefix)) == 64
            and not set(path.name.removeprefix(prefix)) - set("0123456789abcdef")
        )
        if not matches:
            continue
        if path.is_symlink() or runtime_filesystem.is_junction(path) or not path.is_dir():
            _fail("hook_runtime_generation_root_invalid")
        generated.append(path)
    return tuple(generated)


def _consumer_text(root: Path, common: Path) -> str:
    texts = [_process_commands(root)]
    for name in _ACTIVE_CONSUMER_DIRECTORIES:
        directory = common / "ethos" / name
        if directory.is_symlink():
            _fail("hook_runtime_consumers_unknown")
        if not directory.exists():
            continue
        if not directory.is_dir():
            _fail("hook_runtime_consumers_unknown")
        for path in (item for item in directory.rglob("*") if not item.is_dir()):
            if path.is_symlink():
                _fail("hook_runtime_consumers_unknown")
            if not path.is_file():
                _fail("hook_runtime_consumers_unknown")
            try:
                texts.append(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as error:
                _fail("hook_runtime_consumers_unknown", error)
    return "\n".join(texts)


def _config_text(root: Path) -> str:
    def read(worktree: Path) -> str:
        completed = run_git(
            worktree,
            "config",
            "--show-origin",
            "--get-regexp",
            ".*",
            check=False,
        )
        if completed.returncode not in {0, 1}:
            _fail("hook_runtime_consumers_unknown")
        return completed.stdout

    return "\n".join(map(read, _linked_worktree_paths(root)))


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
        _fail("hook_runtime_consumers_unknown")
    return completed.stdout


def _apply_generation_cleanup(
    common: Path,
    plan: dict[str, tuple[Path, ...]],
    *,
    expected_current: bytes,
) -> dict[str, list[str]]:
    with runtime_selection_transaction(common, expected_current=expected_current):
        for path in plan["removed"]:
            if path.is_symlink() or runtime_filesystem.is_junction(path) or not path.is_dir():
                _fail("hook_runtime_generation_cleanup_invalid")
            runtime_materialization.remove_generated_tree(path)
        if any(path.exists() or path.is_symlink() for path in plan["removed"]) or any(
            path.is_symlink() or not path.is_dir() for path in plan["retained"]
        ):
            _fail("hook_runtime_generation_cleanup_failed")
    return {key: [path.as_posix() for path in paths] for key, paths in plan.items()}

"""Activate and retire Git-common hook/runtime generations."""

from __future__ import annotations

import shutil
import sqlite3
import sys
import uuid
from contextlib import closing
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import Timeout

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import load_hook_contract
from ethos.adapters.repo.hook.binding import require_hook_projection
from ethos.adapters.repo.hook.observation import HookRuntimeBinding
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.hook.preimage import ACTIVATION_KEYS
from ethos.adapters.repo.hook.preimage import REF_STORAGE_CONFIG
from ethos.adapters.repo.hook.preimage import WORKTREE_ACTIVATION_KEYS
from ethos.adapters.repo.hook.preimage import exit_receipt_path
from ethos.adapters.repo.hook.preimage import file_bytes
from ethos.adapters.repo.hook.preimage import hooks_preimage_path
from ethos.adapters.repo.hook.preimage import record_hooks_preimage
from ethos.adapters.repo.hook.preimage import restore_file
from ethos.adapters.repo.hook.rollback import require_accepting_runtime
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.adapters.repo.runtime.materialization.host_retention import retire_unused_installations
from ethos.adapters.repo.runtime.pin_selection import PinSelection
from ethos.adapters.repo.runtime.pin_selection import follow_accepted_pin
from ethos.adapters.repo.runtime.pin_selection import receipt_departure
from ethos.adapters.repo.runtime.retirement import operational_reference_paths
from ethos.adapters.repo.runtime.retirement import retire_generations
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import named_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from ethos.adapters.repo.runtime.selection import rollback_gap
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.runtime.selection import runtime_selection_lock
from ethos.adapters.repo.runtime.selection import selected_runtime_path
from ethos.adapters.repo.worktree_list import raw_worktree_records
from ethos.adapters.store.state.schema import prepare_state_transition
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.outcome import refuse

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.authority import RuntimeBuild
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity


class HookActivationError(ValueError):
    """Carry a failed observation through activation compensation to its caller."""

    def __init__(self, reason: str, observation: dict[str, object]) -> None:
        super().__init__(reason)
        self.observation = observation


def install_hook_launchers(
    root: Path,
    *,
    python: Path | None = None,
    installed_runtime: Path | None = None,
    reset_state: bool = False,
    authorized: bool = False,
    reason: str = "",
) -> HookRuntimeBinding:
    """Install and activate one common-dir hook/runtime generation.

    Without a named runtime the accepted pin decides what is selected. A named runtime other than
    that pin is a departure, which needs `reason` and a lane and leaves a receipt.
    """
    if reset_state and not authorized:
        refuse("state_reset_authorization_required")
    repo = root.resolve()
    source_python = python or Path(sys.executable)
    if not source_python.is_absolute() or not source_python.is_file():
        refuse("hook_runtime_python_invalid")
    pinned, expected, receipt = _supply_selection(repo, installed_runtime, reason)
    installed_runtime, kept = pinned.runtime, pinned.kept
    expected_build, build_source = expected.identity, expected.source
    common = Path(git_common_dir(repo))
    # Retention reads a held selection lock as a selection in progress, so it is held from the
    # selector read before the pins that record this repository until the selector writes.
    with runtime_selection_lock(common):
        current_before = _runtime_selection_bytes(common)
        # A selection the pin leaves in place is activated as it stands, neither built nor pinned.
        runtime = (
            kept / "python"
            if kept
            else runtime_materialization.materialize_runtime(
                repo,
                source_python,
                expected_build=expected_build,
                build_source=build_source,
                installed_runtime=installed_runtime,
            )
        )
        required = _required_build(expected)
        rollback_supply = _rollback_supply(common, runtime.parent, current_before, required)
        hooks = materialize_hook_launchers(common / "ethos" / "hooks")
        linked = linked_worktree_paths(repo)
        common_before = config_effects.config_values(repo, ACTIVATION_KEYS, scope="local")
        binding, state_transition, worktrees_before = _activate_with_state(
            repo,
            common,
            runtime.parent,
            hooks,
            linked,
            common_before=common_before,
            current_before=current_before,
            reset_state=reset_state,
            expected_build=expected_build,
            installed_runtime=installed_runtime or kept,
        )
        binding["state_transition"] = state_transition
        _record_rollback(common, binding, rollback_supply, required)
    if pinned.state:
        binding["runtime_pin"] = pinned.report()
    if receipt:
        binding["selection_receipt"] = receipt
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
    # A malformed selector named no predecessor, so any runtime generation may be the rollback.
    unnamed = rollback_supply.get("state") == "unavailable" and "runtime" not in rollback_supply
    cleanup = retire_generations(
        repo, hooks=hooks, runtime=runtime.parent, unnamed_predecessor=unnamed
    )
    if cleanup["state"] == "deferred" or binding["legacy_runtime_locator"]["state"] == "retained":
        binding["required_gaps"].append("hook_runtime_cleanup_deferred")
    binding["generation_cleanup"] = cleanup
    binding["host_store_cleanup"] = _retire_host_store(repo)
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
    installed_runtime: Path | None = None,
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
    records = {
        path: file_bytes(path) for path in (hooks_preimage_path(common), exit_receipt_path(common))
    }
    try:
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("begin immediate")
            state_transition = prepare_state_transition(connection, reset=reset_state)
            selected = activate_runtime(common, runtime, expected_current=current_before)
            activated = True
            binding = _activate_common_runtime(
                repo,
                hooks,
                linked,
                worktrees_before,
                expected_build=expected_build,
                selected_runtime=selected,
                installed_runtime=installed_runtime,
            )
            # What this adoption replaced, kept for a faithful exit; an earlier exit's receipt no
            # longer describes the repository once it is adopted again.
            record_hooks_preimage(common, common_before, worktrees_before)
            exit_receipt_path(common).unlink(missing_ok=True)
            connection.commit()
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        failures = _restore_records(records)
        if activated:
            _restore_failed_activation(
                repo,
                common,
                common_before,
                worktrees_before,
                current_before,
                selected_runtime=runtime_selection_bytes(common, runtime),
            )
        if not database_existed:
            database.unlink(missing_ok=True)
            _remove_state_sidecars(database)
        if failures:
            refuse("hook_runtime_activation_compensation_failed:" + ",".join(failures), cause=error)
        if isinstance(error, sqlite3.Error):
            refuse(f"state_activation_failed:{error}", cause=error)
        raise
    if not database_existed:
        _remove_state_sidecars(database)
    return binding, state_transition, worktrees_before


def _restore_records(records: dict[Path, bytes | None]) -> list[str]:
    """Return each exit record to its bytes before the activation, naming each that cannot be."""
    failures: list[str] = []
    for path, content in records.items():
        try:
            restore_file(path, content)
        except OSError as failure:
            failures.append(str(failure) or type(failure).__name__)
    return failures


def _hold_rollback(common: Path, runtime: Path) -> None:
    """Name the preserved predecessor as this repository's rollback supply."""
    selector = common.resolve() / "ethos/runtime/ROLLBACK"
    staged = selector.with_name(f".ROLLBACK-{uuid.uuid4().hex}")
    staged.write_bytes(runtime_selection_bytes(common.resolve(), runtime))
    staged.replace(selector)


def _supply_selection(
    repo: Path, named: Path | None, reason: str
) -> tuple[PinSelection, RuntimeBuild, dict[str, str]]:
    """Resolve what this activation selects, and receipt a named departure from the accepted pin.

    Without a named runtime the accepted pin decides. Before anything is pinned, a runtime to
    select must accept the root's declaration.
    """
    pinned = PinSelection("", named) if named else follow_accepted_pin(repo, settle=True)
    expected = expected_runtime_build(repo, installed_runtime=pinned.runtime or pinned.kept)
    receipt: dict[str, str] = {}
    if pinned.runtime is not None:
        target = require_accepting_runtime(repo, pinned.runtime)
        if named:
            receipt = receipt_departure(repo, target, reason)
    return pinned, expected, receipt


def _required_build(expected: RuntimeBuild) -> BuildIdentity | None:
    """Name the one build an install admits, where the root's accepted source names the build."""
    return None if expected.invoking else expected.identity


def _record_rollback(
    common: Path,
    binding: HookRuntimeBinding,
    supply: dict[str, str],
    required: BuildIdentity | None,
) -> None:
    """Report the predecessor's supply and hold it; else release a held rollback that cannot run.

    Releasing is the one repair that status names for a rollback no install of this root admits.
    """
    if supply:
        binding["rollback_supply"] = supply
    if supply.get("state") == "preserved":
        _hold_rollback(common, Path(supply["runtime"]))
        return
    with suppress(OSError, UnicodeError, ValueError):
        held = named_runtime(common, "ROLLBACK")
        if held is not None and (gap := rollback_gap(held, required)):
            (common / "ethos/runtime/ROLLBACK").unlink()
            binding.pop("rollback", None)
            binding["rollback_released"] = {"runtime": held.as_posix(), "reason": gap}


def _retire_host_store(repo: Path) -> dict[str, object]:
    """Retire host installations no recorded consumer needs; a failure only defers it."""
    root = host_store_root()
    if root is None:
        return {"state": "unavailable"}
    try:
        report = retire_unused_installations(
            root / "installations", in_use=lambda: operational_reference_paths(repo)
        )
    except (OSError, ValueError, Timeout) as error:
        return {"state": "deferred", "error": str(error) or type(error).__name__}
    return {"state": "complete", **report}


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
        refuse("hook_generation_root_invalid")
    contract = load_hook_contract()
    expected = contract["launchers"]
    target = generations / contract["generation_digest"]
    if target.is_symlink():
        refuse("hook_launcher_projection_invalid")
    try:
        require_hook_projection(target, contract)
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
        require_hook_projection(staging, contract)
        if had_target:
            target.rename(backup)
        try:
            staging.rename(target)
            require_hook_projection(target, contract)
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


def _activate_common_runtime(
    repo: Path,
    hooks: Path,
    linked: tuple[Path, ...],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
    *,
    expected_build: BuildIdentity,
    selected_runtime: SelectedRuntime,
    installed_runtime: Path | None = None,
) -> HookRuntimeBinding:
    """Select and post-observe one common runtime/hook activation."""
    config_effects.set_common_config(repo, {"extensions.worktreeConfig": "true"})
    worktrees_before.update(
        {
            worktree: config_effects.config_values(
                worktree, WORKTREE_ACTIVATION_KEYS, scope="worktree"
            )
            for worktree in linked
        }
    )
    config_effects.set_common_config(
        repo,
        {**REF_STORAGE_CONFIG, "core.hooksPath": hooks.as_posix()},
    )
    for worktree in linked:
        config_effects.unset_worktree_config(worktree, WORKTREE_ACTIVATION_KEYS)
    _require_common_activation(repo, linked, hooks)
    binding = hook_runtime_binding(
        repo, expected_build=expected_build, selected_runtime=selected_runtime
    )
    if binding["hooks_path"] != hooks.as_posix():
        refuse("hook_runtime_activation_drift")
    if binding["required_gaps"]:
        reason = "hook_runtime_activation_invalid:" + ",".join(binding["required_gaps"])
        if observation := binding.get("contract_observation"):
            raise HookActivationError(reason, observation)
        refuse(reason)
    observed = expected_runtime_build(repo, installed_runtime=installed_runtime)
    if observed.identity != expected_build:
        refuse("hook_runtime_expected_build_stale")
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


def _rollback_supply(
    common: Path, successor: Path, before: bytes | None, required: BuildIdentity | None
) -> dict[str, str]:
    """Classify the predecessor; malformed selector bytes name none and stay CAS-protected.

    A predecessor that no install of this root would admit is no rollback: it is neither pinned
    nor held, and the report names why. One that is pinned is proved by the pin itself, which
    validates its payload and its wheel in the host store.
    """
    if before is None:
        return {}
    try:
        previous = current_runtime(common)
    except (OSError, ValueError) as error:
        try:
            located = {"runtime": selected_runtime_path(common).as_posix()}
        except ValueError as selection:
            selector = common / "ethos" / "runtime" / "CURRENT"
            if str(selection) != "hook_runtime_current_invalid" or selector.is_symlink():
                raise
            located = {}
        return {"state": "unavailable", **located, "reason": str(error) or type(error).__name__}
    if previous.root == successor:
        return {}
    if gap := rollback_gap(previous.root, required):
        return {"state": "unrunnable", "runtime": previous.root.as_posix(), "reason": gap}
    preserved = runtime_materialization.pin_installed_runtime(previous, consumer=common)
    return {
        "state": "preserved",
        "runtime": preserved.as_posix(),
        "runtime_digest": previous.digest,
        "wheel_sha256": previous.wheel_sha256,
        "source_commit": previous.build.source_commit,
        "source_tree": previous.build.source_tree,
    }


def _runtime_selection_bytes(common: Path) -> bytes | None:
    selector = common / "ethos" / "runtime" / "CURRENT"
    try:
        return selector.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        refuse("hook_runtime_current_invalid", cause=error)


def _common_activation(hooks: Path) -> dict[str, tuple[str, ...]]:
    return {
        "extensions.worktreeConfig": ("true",),
        **{key: (value,) for key, value in REF_STORAGE_CONFIG.items()},
        "core.hooksPath": (hooks.as_posix(),),
    }


def linked_worktree_paths(root: Path) -> tuple[Path, ...]:
    """Return every readable worktree sharing the repository common directory."""
    paths = tuple(
        Path(record["worktree"]).resolve()
        for record in raw_worktree_records(root, gap="hook_runtime_worktrees_unreadable")
    )
    if not paths or any(not path.is_dir() for path in paths):
        refuse("hook_runtime_worktrees_unreadable")
    return paths


def _require_common_activation(
    root: Path,
    worktrees: tuple[Path, ...],
    hooks: Path,
) -> None:
    if config_effects.config_values(root, ACTIVATION_KEYS, scope="local") != _common_activation(
        hooks
    ):
        refuse("hook_runtime_common_activation_drift")
    if any(
        config_effects.config_values(worktree, WORKTREE_ACTIVATION_KEYS, scope="worktree")
        != dict.fromkeys(WORKTREE_ACTIVATION_KEYS, ())
        for worktree in worktrees
    ):
        refuse("hook_runtime_worktree_activation_drift")


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

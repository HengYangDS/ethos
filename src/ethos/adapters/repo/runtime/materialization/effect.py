"""Atomically materialize and post-observe immutable runtime generations."""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

from filelock import FileLock
from platformdirs import user_data_path

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.filesystem import remove_owned_path
from ethos.adapters.repo.runtime.filesystem import require_exclusive_inodes
from ethos.adapters.repo.runtime.filesystem import require_no_junctions
from ethos.adapters.repo.runtime.filesystem import runtime_python
from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.dependency_supply import (
    prepare_locked_requirements,
)
from ethos.adapters.repo.runtime.materialization.input_resolution import is_selected_runtime_source
from ethos.adapters.repo.runtime.materialization.input_resolution import (
    resolve_locked_environment_python,
)
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_project
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_wheel
from ethos.adapters.repo.runtime.materialization.input_resolution import selected_runtime_source
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import (
    observe_runtime_environment,
)
from ethos.adapters.repo.runtime.materialization.python_environment import (
    require_python_image_source,
)
from ethos.adapters.repo.runtime.materialization.python_environment import same_python_path
from ethos.adapters.repo.runtime.materialization.python_image import materialize_python_image
from ethos.adapters.repo.runtime.materialization.python_image import render_console_script
from ethos.adapters.repo.runtime.selection import require_runtime_selection_scope
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.runtime.selection import selected_runtime_path
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.adapters.repo.runtime.transition import materialize_package_wheel

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def materialize_runtime(
    repo: Path,
    source_python: Path,
    *,
    expected_build: BuildIdentity,
    build_source: Path | None = None,
    installed_runtime: Path | None = None,
) -> Path:
    """Select admitted installed supply or materialize an exact repository runtime."""
    invoking_source = Path(__file__).resolve().parents[6]
    package_source = build_source or invoking_source
    project = build_source or resolve_runtime_project(package_source)
    if installed_runtime is not None:
        common = Path(git_common_dir(repo))
        runtime_selection_bytes(common, installed_runtime)
        selected = require_selected_runtime(installed_runtime, expected_build=expected_build)
        require_runtime_selection_scope(common, selected)
        if not _runtime_supply_current(selected, project):
            _fail("hook_runtime_installed_supply_invalid")
        return _pin_installed_runtime(selected, project) / "python"
    runtime_root = Path(git_common_dir(repo)) / "ethos" / "runtime"
    if runtime_root.parent.is_symlink() or runtime_root.is_symlink():
        _fail("hook_runtime_root_invalid")
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    try:
        if reusable := _reusable_runtime(repo, expected_build, project, invoking_source):
            return reusable / "python"
        dependency_python = (
            resolve_locked_environment_python(project)
            if build_source is not None
            else source_python
        )
        python_facts = require_python_image_source(dependency_python)
        interpreter = Path(python_facts["executable"]).resolve()
        environment = observe_runtime_environment(
            project,
            interpreter,
            python_facts=python_facts,
        )
        reuse_selected_closure = build_source is None and is_selected_runtime_source(package_source)
        locked_requirements = (
            None
            if reuse_selected_closure
            else prepare_locked_requirements(
                project,
                work,
                dependency_python,
                require_build_tools=build_source is not None,
            )
        )
        wheel = resolve_runtime_wheel(
            package_source,
            work / "wheel",
            python=dependency_python,
        )
        artifact = materialize_package_wheel(
            repo,
            wheel,
            expected_build=expected_build,
            collision="hook_runtime_wheel_digest_collision",
        )
        target = materialize_runtime_generation(
            runtime_root,
            project,
            interpreter,
            artifact,
            environment,
            dependency_python=None if reuse_selected_closure else dependency_python,
            python_facts=python_facts,
            locked_requirements=locked_requirements,
        )
        return target / "python"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _host_runtime_store() -> Path:
    """Choose user-owned installed supply independently of package-manager files."""
    if declared := os.environ.get("XDG_DATA_HOME"):
        root = Path(declared)
        if not root.is_absolute():
            _fail("hook_runtime_host_store_invalid")
        return root.resolve() / "ethos/installations"
    return user_data_path("ethos", appauthor=False).resolve() / "installations"


def _pin_installed_runtime(selected: SelectedRuntime, project: Path) -> Path:
    """Pin the runtime and its exact wheel as one reusable installation."""
    store = _host_runtime_store()
    # Abbreviate only the directory index; OWNER and the runtime retain full identity.
    installation = store / selected.digest[:16]
    target = installation / "runtime" / selected.digest
    if selected.root.resolve() == target.resolve():
        return selected.root
    if store.is_symlink() or installation.is_symlink():
        _fail("hook_runtime_host_store_invalid")
    store.mkdir(parents=True, mode=0o700, exist_ok=True)
    with FileLock(
        store / "install.lock", timeout=10, fallback_to_soft=False, preserve_lock_file=True
    ):
        _recover_pin_staging(store)
        if installation.exists():
            owner = installation / "OWNER"
            if (
                owner.is_symlink()
                or not owner.is_file()
                or owner.read_text() != selected.digest + "\n"
            ):
                _fail("hook_runtime_host_store_conflict")
            try:
                pinned = require_selected_runtime(target, expected_build=selected.build)
                complete = _runtime_supply_current(pinned, project)
            except (OSError, ValueError) as error:
                _fail("hook_runtime_host_store_conflict", error)
            if not complete:
                _fail("hook_runtime_host_store_conflict")
            return pinned.root
        staging = store / f".pin-{uuid.uuid4().hex}"
        marker = staging.with_name(staging.name + ".owner")
        marker.write_text(selected.digest + "\n", encoding="utf-8")
        try:
            staging.mkdir(mode=0o700)
            (staging / "OWNER").write_text(selected.digest + "\n", encoding="utf-8")
            staged_runtime = staging / "runtime" / selected.digest
            staged_runtime.parent.mkdir(parents=True)
            shutil.copytree(selected.root, staged_runtime, symlinks=True)
            wheel = _runtime_supply_wheel(selected, project)
            if wheel is None:
                _fail("hook_runtime_installed_supply_invalid")
            staged_package = staging / "packages" / selected.wheel_sha256
            staged_package.mkdir(parents=True)
            try:
                shutil.copyfile(wheel, staged_package / wheel.name)
            except OSError as error:
                _fail("hook_runtime_installed_supply_invalid", error)
            pinned = require_selected_runtime(
                staged_runtime, expected_root=target, expected_build=selected.build
            )
            if not _runtime_supply_current(pinned, project):
                _fail("hook_runtime_host_store_copy_invalid")
            staging.rename(installation)
            return require_selected_runtime(target, expected_build=selected.build).root
        finally:
            remove_generated_tree(staging)
            marker.unlink(missing_ok=True)


def _recover_pin_staging(store: Path) -> None:
    """Reclaim only marked imports after the sole host-store writer has exited."""
    for work in sorted(store.glob(".pin-*")):
        if work.name.endswith(".owner"):
            continue
        marker = work.with_name(work.name + ".owner")
        if (
            not _valid_pin_name(work.name)
            or work.is_symlink()
            or not work.is_dir()
            or marker.is_symlink()
            or not marker.is_file()
        ):
            _fail("hook_runtime_host_store_residue_unreviewed")
        digest = marker.read_text(encoding="utf-8")
        if not _valid_pin_marker(digest):
            _fail("hook_runtime_host_store_residue_unreviewed")
        remove_generated_tree(work)
        marker.unlink()
    for marker in store.glob(".pin-*.owner"):
        if (
            not _valid_pin_name(marker.name.removesuffix(".owner"))
            or marker.is_symlink()
            or not marker.is_file()
            or not _valid_pin_marker(marker.read_text(encoding="utf-8"))
        ):
            _fail("hook_runtime_host_store_residue_unreviewed")
        marker.unlink()


def _valid_pin_name(value: str) -> bool:
    return (
        value.startswith(".pin-")
        and len(value) == 37
        and all(character in "0123456789abcdef" for character in value[5:])
    )


def _valid_pin_marker(value: str) -> bool:
    return (
        len(value) == 65
        and value.endswith("\n")
        and all(character in "0123456789abcdef" for character in value[:-1])
    )


def _reusable_runtime(
    repo: Path,
    expected_build: BuildIdentity,
    project: Path,
    invoking_source: Path,
) -> Path | None:
    common = Path(git_common_dir(repo)).resolve()
    try:
        candidate = selected_runtime_path(common)
    except ValueError as error:
        if str(error) == "hook_runtime_current_missing":
            return None
        raise
    external = candidate.parent != common / "ethos/runtime"
    try:
        selected = require_selected_runtime(candidate, expected_build=expected_build)
        require_runtime_selection_scope(common, selected)
        if _runtime_supply_current(selected, project):
            return selected.root
    except (OSError, ValueError) as error:
        if external:
            if str(error) == "hook_runtime_repository_private":
                raise
            absent = _target_absent(candidate)
            if absent and (
                invoking := _compatible_invoking_runtime(invoking_source, expected_build, project)
            ):
                return invoking
            condition = "unavailable" if absent else "invalid"
            _fail(f"hook_runtime_installed_supply_{condition}:{candidate}", error)
    if external:
        _fail(f"hook_runtime_installed_supply_invalid:{candidate}")
    return None


def _target_absent(path: Path) -> bool:
    """Distinguish an absent target from an inaccessible or invalid one."""
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        pass
    return False


def _compatible_invoking_runtime(
    source: Path, expected_build: BuildIdentity, project: Path
) -> Path | None:
    """Reuse only the invoking immutable package with the exact required closure."""
    try:
        invoking = selected_runtime_source(source)
        if (
            invoking is not None
            and invoking.build == expected_build
            and _runtime_supply_current(invoking, project)
        ):
            return invoking.root
    except (OSError, ValueError):
        pass
    return None


def _runtime_supply_current(selected: SelectedRuntime, project: Path) -> bool:
    """Check the installed entry, lock and exact wheel without copying supply."""
    return _runtime_supply_wheel(selected, project) is not None


def _runtime_supply_wheel(selected: SelectedRuntime, project: Path) -> Path | None:
    """Return the sole exact wheel in a complete installed runtime carrier."""
    if selected.dependency_lock_sha256 != file_sha256(project / "uv.lock"):
        return None
    if os.name != "nt":
        entry = selected.python.with_name("ethos")
        if not os.access(entry, os.X_OK) or entry.read_text() != render_console_script("ethos"):
            return None
    package_root = selected.root.parent.parent / "packages" / selected.wheel_sha256
    if package_root.is_symlink() or not package_root.is_dir():
        return None
    wheels = tuple(
        path
        for path in package_root.glob("ethos-*.whl")
        if path.is_file() and not path.is_symlink()
    )
    return (
        wheels[0] if len(wheels) == 1 and file_sha256(wheels[0]) == selected.wheel_sha256 else None
    )


def materialize_runtime_generation(
    runtime_root: Path,
    source: Path,
    interpreter: Path,
    artifact: PackageArtifact,
    environment: RuntimeEnvironment,
    *,
    dependency_python: Path | None = None,
    python_facts: dict[str, str] | None = None,
    locked_requirements: Path | None,
) -> Path:
    staging = runtime_root / f".runtime-build-{uuid.uuid4().hex}"
    try:
        materialize_python_image(
            staging / "python",
            source,
            interpreter,
            artifact.path,
            dependency_python=dependency_python,
            python_facts=python_facts,
            locked_requirements=locked_requirements,
        )
        target, created = publish_runtime_generation(runtime_root, staging, artifact, environment)
        try:
            require_runtime_execution(target, smoke=created)
        except BaseException:
            if created:
                remove_generated_tree(target, ignore_errors=True)
            raise
        return target
    finally:
        remove_generated_tree(staging, ignore_errors=True)


def publish_runtime_generation(
    runtime_root: Path,
    staging: Path,
    artifact: PackageArtifact,
    environment: RuntimeEnvironment,
) -> tuple[Path, bool]:
    """Seal and atomically expose owned staged bytes without executing the candidate.

    Return the exact target and whether this call created it; callers must not
    remove a reused generation when their later executable qualification fails.
    The caller owns staging cleanup and performs any required runtime execution
    in its own, credential-free qualification boundary.
    """
    manifest = staging / "manifest.json"
    if (
        staging.is_symlink()
        or not staging.is_dir()
        or runtime_root.is_symlink()
        or staging.parent.resolve() != runtime_root.resolve()
        or manifest.exists()
        or manifest.is_symlink()
    ):
        _fail("hook_runtime_staging_invalid")
    _seal_runtime_payload(staging)
    runtime_files = runtime_file_inventory(staging)
    digest = runtime_digest(
        wheel_sha256=artifact.sha256,
        build=artifact.build,
        environment=environment,
        runtime_files=runtime_files,
    )
    target = runtime_root / digest
    _finalize_runtime(staging, target, artifact, environment, runtime_files)
    runtime_root.mkdir(parents=True, exist_ok=True)
    if target.is_dir():
        require_runtime_identity(target, artifact, environment)
        return target, False
    try:
        staging.rename(target)
    except FileExistsError:
        require_runtime_identity(target, artifact, environment)
        return target, False
    try:
        require_runtime_identity(target, artifact, environment)
    except BaseException:
        remove_generated_tree(target, ignore_errors=True)
        raise
    return target, True


def _finalize_runtime(
    runtime: Path,
    target: Path,
    artifact: PackageArtifact,
    environment: RuntimeEnvironment,
    runtime_files: dict[str, str],
) -> None:
    python = runtime_python(runtime / "python")
    if not python.is_file():
        _fail("hook_runtime_python_missing")
    (runtime / "manifest.json").write_bytes(
        runtime_manifest_bytes(
            digest=target.name,
            wheel_sha256=artifact.sha256,
            build=artifact.build,
            environment=environment,
            runtime_files=runtime_files,
        )
    )
    _remove_write_permissions(runtime / "manifest.json")
    _remove_write_permissions(runtime)


def _seal_runtime_payload(runtime: Path) -> None:
    """Remove write permission from every executable payload entry."""
    require_no_junctions(runtime, error="hook_runtime_generation_tree_invalid")
    require_exclusive_inodes(runtime, error="hook_runtime_generation_hardlink_invalid")
    for path in sorted(runtime.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_symlink():
            _remove_write_permissions(path)


def _remove_write_permissions(path: Path) -> None:
    path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o222)


def remove_generated_tree(path: Path, *, ignore_errors: bool = False) -> None:
    """Remove an owned generated tree even after its payload has been sealed."""
    if not path.exists():
        return
    try:
        require_no_junctions(path, error="hook_runtime_generation_tree_invalid")
        require_exclusive_inodes(path, error="hook_runtime_generation_hardlink_invalid")
        remove_owned_path(path)
    except OSError:
        if not ignore_errors:
            raise


def require_runtime_identity(
    runtime: Path,
    artifact: PackageArtifact,
    environment: RuntimeEnvironment,
) -> None:
    """Verify exact sealed bytes and metadata without launching their interpreter."""
    manifest = load_runtime_manifest_bytes((runtime / "manifest.json").read_bytes())
    if (
        manifest.digest != runtime.name
        or manifest.wheel_sha256 != artifact.sha256
        or manifest.build != artifact.build
        or manifest.environment != environment
        or manifest.runtime_files != runtime_file_inventory(runtime)
    ):
        _fail("hook_runtime_manifest_invalid")


def require_runtime_execution(runtime: Path, *, smoke: bool = False) -> None:
    """Qualify relocation and optional product behavior outside the signing boundary."""
    python = runtime_python(runtime / "python")
    facts = observe_python_facts(python)
    prefix = (runtime / "python").resolve().as_posix()
    if not all(same_python_path(facts[key], prefix) for key in ("prefix", "base_prefix")):
        _fail("hook_runtime_python_not_relocatable")
    if smoke:
        command = (python, "-B", "-I", "-m", "ethos.cli", "--version")
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode or not completed.stdout.strip():
            detail = ":".join(
                (
                    "hook_runtime_module_smoke_failed",
                    f"command={shlex.join(tuple(str(part) for part in command))}",
                    f"returncode={completed.returncode}",
                    f"stdout={completed.stdout.strip()}",
                    f"stderr={completed.stderr.strip()}",
                )
            )
            _fail(detail)

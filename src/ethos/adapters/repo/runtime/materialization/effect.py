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
    package_source = build_source or Path(__file__).resolve().parents[6]
    project = build_source or resolve_runtime_project(package_source)
    if installed_runtime is not None:
        runtime_selection_bytes(Path(git_common_dir(repo)), installed_runtime)
        selected = require_selected_runtime(installed_runtime, expected_build=expected_build)
        if not _runtime_supply_current(selected, project):
            _fail("hook_runtime_installed_supply_invalid")
        return selected.root / "python"
    runtime_root = Path(git_common_dir(repo)) / "ethos" / "runtime"
    if runtime_root.parent.is_symlink() or runtime_root.is_symlink():
        _fail("hook_runtime_root_invalid")
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    try:
        if reusable := _reusable_runtime(repo, expected_build, project):
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
            work,
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


def _reusable_runtime(
    repo: Path,
    expected_build: BuildIdentity,
    project: Path,
) -> Path | None:
    common = Path(git_common_dir(repo)).resolve()
    try:
        candidate = selected_runtime_path(common)
    except ValueError as error:
        if str(error) == "hook_runtime_current_missing":
            return None
        raise
    try:
        selected = require_selected_runtime(candidate, expected_build=expected_build)
        if _runtime_supply_current(selected, project):
            return selected.root
    except (OSError, ValueError) as error:
        if candidate.parent != common / "ethos/runtime":
            _fail(f"hook_runtime_installed_supply_unavailable:{candidate}", error)
    if candidate.parent != common / "ethos/runtime":
        _fail(f"hook_runtime_installed_supply_unavailable:{candidate}")
    return None


def _runtime_supply_current(selected: SelectedRuntime, project: Path) -> bool:
    """Check the installed entry, lock and exact wheel without copying supply."""
    if selected.dependency_lock_sha256 != file_sha256(project / "uv.lock"):
        return False
    if os.name != "nt":
        entry = selected.python.with_name("ethos")
        if not os.access(entry, os.X_OK) or entry.read_text() != render_console_script("ethos"):
            return False
    package_root = selected.root.parent.parent / "packages" / selected.wheel_sha256
    if package_root.is_symlink() or not package_root.is_dir():
        return False
    wheels = tuple(
        path
        for path in package_root.glob("ethos-*.whl")
        if path.is_file() and not path.is_symlink()
    )
    return len(wheels) == 1 and file_sha256(wheels[0]) == selected.wheel_sha256


def materialize_runtime_generation(
    runtime_root: Path,
    work: Path,
    source: Path,
    interpreter: Path,
    artifact: PackageArtifact,
    environment: RuntimeEnvironment,
    *,
    dependency_python: Path | None = None,
    python_facts: dict[str, str] | None = None,
    locked_requirements: Path | None,
) -> Path:
    del work
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
    *,
    expected_root: Path | None = None,
) -> None:
    """Verify exact sealed bytes and metadata without launching their interpreter."""
    manifest = load_runtime_manifest_bytes((runtime / "manifest.json").read_bytes())
    digest = (expected_root or runtime).name
    if (
        manifest.digest != digest
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

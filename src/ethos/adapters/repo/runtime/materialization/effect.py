"""Atomically materialize and post-observe immutable runtime generations."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.filesystem import require_exclusive_inodes
from ethos.adapters.repo.runtime.filesystem import require_no_junctions
from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_owned_interpreter
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_project
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_wheel
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import (
    observe_runtime_environment,
)
from ethos.adapters.repo.runtime.materialization.python_image import materialize_python_image
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import runtime_entrypoint
from ethos.adapters.repo.runtime.selection import runtime_python
from ethos.adapters.repo.runtime.transition import ReleaseArtifact
from ethos.adapters.repo.runtime.transition import materialize_release_wheel

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity


def _fail(reason: str, cause: Exception | None = None) -> NoReturn:
    raise ValueError(reason) from cause


def materialize_runtime(
    repo: Path,
    source_python: Path,
    *,
    expected_build: BuildIdentity,
    build_source: Path | None = None,
) -> Path:
    """Build and atomically install one wheel-qualified common-dir runtime."""
    package_source = build_source or Path(__file__).resolve().parents[6]
    project = build_source or resolve_runtime_project(package_source)
    runtime_root = Path(git_common_dir(repo)) / "ethos" / "runtime"
    if runtime_root.parent.is_symlink() or runtime_root.is_symlink():
        _fail("hook_runtime_root_invalid")
    work = runtime_root / f".build-{uuid.uuid4().hex}"
    try:
        interpreter = resolve_owned_interpreter(package_source, source_python)
        python_facts = observe_python_facts(interpreter)
        environment = observe_runtime_environment(
            project,
            interpreter,
            python_facts=python_facts,
        )
        if reusable := _reusable_runtime(repo, expected_build, environment):
            return reusable / "python"
        wheel = resolve_runtime_wheel(package_source, work / "wheel")
        artifact = materialize_release_wheel(
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
            python_facts=python_facts,
            locked=build_source is not None,
        )
        return target / "python"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _reusable_runtime(
    repo: Path,
    expected_build: BuildIdentity,
    environment: RuntimeEnvironment,
) -> Path | None:
    common = Path(git_common_dir(repo))
    try:
        selected = current_runtime(common, expected_build=expected_build)
    except ValueError:
        return None
    observed_environment = RuntimeEnvironment(
        selected.python_abi,
        selected.python_version,
        selected.python_implementation,
        selected.dependency_lock_sha256,
        selected.platform,
        selected.architecture,
    )
    if observed_environment != environment:
        return None
    package_root = common / "ethos" / "packages" / selected.wheel_sha256
    if package_root.is_symlink() or not package_root.is_dir():
        return None
    wheels = tuple(
        path
        for path in package_root.glob("ethos-*.whl")
        if path.is_file() and not path.is_symlink()
    )
    if len(wheels) != 1 or file_sha256(wheels[0]) != selected.wheel_sha256:
        return None
    return selected.root


def materialize_runtime_generation(
    runtime_root: Path,
    work: Path,
    source: Path,
    interpreter: Path,
    artifact: ReleaseArtifact,
    environment: RuntimeEnvironment,
    *,
    python_facts: dict[str, str] | None = None,
    locked: bool,
) -> Path:
    staging = runtime_root / f".runtime-build-{uuid.uuid4().hex}"
    try:
        materialize_python_image(
            staging / "python",
            source,
            interpreter,
            artifact.path,
            work,
            python_facts=python_facts,
            locked=locked,
        )
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
            require_runtime_generation(target, artifact, environment)
            return target
        try:
            staging.rename(target)
        except FileExistsError:
            require_runtime_generation(target, artifact, environment)
        else:
            try:
                require_runtime_generation(target, artifact, environment, smoke=True)
            except (OSError, ValueError):
                remove_generated_tree(target, ignore_errors=True)
                raise
    finally:
        remove_generated_tree(staging, ignore_errors=True)
    return target


def _finalize_runtime(
    runtime: Path,
    target: Path,
    artifact: ReleaseArtifact,
    environment: RuntimeEnvironment,
    runtime_files: dict[str, str],
) -> None:
    python = runtime_python(runtime / "python")
    entrypoint = runtime_entrypoint(runtime / "python")
    if not python.is_file():
        _fail("hook_runtime_python_missing")
    if not entrypoint.is_file():
        _fail("hook_runtime_entrypoint_missing")
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
        for parent, directories, files in os.walk(path, topdown=False):
            base = Path(parent)
            for name in files:
                child = base / name
                if not child.is_symlink():
                    child.chmod(stat.S_IMODE(child.stat().st_mode) | stat.S_IWUSR)
            for name in directories:
                child = base / name
                if not child.is_symlink():
                    child.chmod(stat.S_IMODE(child.stat().st_mode) | stat.S_IRWXU)
        path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IRWXU)
        shutil.rmtree(path)
    except OSError:
        if not ignore_errors:
            raise


def require_runtime_generation(
    runtime: Path,
    artifact: ReleaseArtifact,
    environment: RuntimeEnvironment,
    *,
    expected_root: Path | None = None,
    smoke: bool = False,
) -> None:
    """Post-observe one exact immutable runtime generation."""
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
    python = runtime_python(runtime / "python")
    facts = observe_python_facts(python)
    prefix = (runtime / "python").resolve().as_posix()
    if facts["prefix"] != prefix or facts["base_prefix"] != prefix:
        _fail("hook_runtime_python_not_relocatable")
    if smoke:
        completed = subprocess.run(
            (runtime_entrypoint(runtime / "python"), "--version"),
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode or not completed.stdout.strip():
            _fail("hook_runtime_entrypoint_smoke_failed")

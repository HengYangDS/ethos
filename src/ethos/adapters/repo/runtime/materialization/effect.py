"""Atomically materialize and post-observe immutable runtime generations."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_owned_interpreter
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_project
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_runtime_wheel
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import (
    observe_runtime_environment,
)
from ethos.adapters.repo.runtime.materialization.python_image import materialize_python_image
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
        wheel = resolve_runtime_wheel(package_source, work / "wheel")
        artifact = materialize_release_wheel(
            repo,
            wheel,
            expected_build=expected_build,
            collision="hook_runtime_wheel_digest_collision",
        )
        interpreter = resolve_owned_interpreter(package_source, source_python)
        environment = observe_runtime_environment(project, interpreter)
        target = materialize_runtime_generation(
            runtime_root,
            work,
            project,
            interpreter,
            artifact,
            environment,
            locked=build_source is not None,
        )
        return target / "python"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def materialize_runtime_generation(
    runtime_root: Path,
    work: Path,
    source: Path,
    interpreter: Path,
    artifact: ReleaseArtifact,
    environment: RuntimeEnvironment,
    *,
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
            locked=locked,
        )
        runtime_files = runtime_file_inventory(staging)
        digest = runtime_digest(
            wheel_sha256=artifact.sha256,
            build=artifact.build,
            environment=environment,
            runtime_files=runtime_files,
        )
        target = runtime_root / digest
        _finalize_runtime(staging, target, artifact, environment)
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
                shutil.rmtree(target, ignore_errors=True)
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def _finalize_runtime(
    runtime: Path,
    target: Path,
    artifact: ReleaseArtifact,
    environment: RuntimeEnvironment,
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
            runtime_files=runtime_file_inventory(runtime),
        )
    )
    require_runtime_generation(runtime, artifact, environment, expected_root=target)


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

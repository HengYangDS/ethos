"""Reusable scenarios for immutable runtime and hook contract tests."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.transition as identity_transition
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256
from ethos.adapters.repo.runtime.materialization.python_environment import (
    observe_runtime_environment,
)
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity

if TYPE_CHECKING:
    import pytest

    from ethos.adapters.repo.hook.binding import HookRuntimeBinding
    from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def install_fixture_hook_runtime(root: Path) -> HookRuntimeBinding:
    """Install a small valid runtime for non-runtime governance fixtures."""
    common = Path(git_common_dir(root))
    runtime_root = common / "ethos/runtime"
    staging = runtime_root / f".fixture-{uuid.uuid4().hex}"
    package = b"ethos fixture wheel\n"
    wheel_sha256 = hashlib.sha256(package).hexdigest()
    wheel = common / "ethos/packages" / wheel_sha256 / "ethos-fixture.whl"
    build = expected_runtime_build(root)[0]
    environment = observe_runtime_environment(REPOSITORY_ROOT, Path(sys.executable))
    try:
        create_fixture_python(staging / "python")
        runtime_files = runtime_file_inventory(staging)
        digest = runtime_digest(
            wheel_sha256=wheel_sha256,
            build=build,
            environment=environment,
            runtime_files=runtime_files,
        )
        target = runtime_root / digest
        (staging / "manifest.json").write_bytes(
            runtime_manifest_bytes(
                digest=digest,
                wheel_sha256=wheel_sha256,
                build=build,
                environment=environment,
                runtime_files=runtime_files,
            )
        )
        runtime_root.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(staging)
        else:
            staging.rename(target)
        wheel.parent.mkdir(parents=True, exist_ok=True)
        wheel.write_bytes(package)
        assert file_sha256(wheel) == wheel_sha256
        activate_runtime(common, target)
        return install_hook_launchers(root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def create_fixture_python(target: Path) -> None:
    """Create an executable fixture image backed by the test environment."""
    scripts = target / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir(parents=True)
    source_python = Path(sys.executable).absolute()
    fixture_python = scripts / ("python.exe" if os.name == "nt" else "python")
    shutil.copy2(source_python, fixture_python)
    target.joinpath("pyvenv.cfg").write_text(
        f"home = {Path(sys.base_prefix).as_posix()}\n"
        "include-system-site-packages = false\n"
        f"version = {platform.python_version()}\n"
        f"executable = {source_python.as_posix()}\n",
        encoding="utf-8",
    )
    fixture_python.chmod(0o755)
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    relative_site = (
        Path("Lib/site-packages") if os.name == "nt" else Path(f"lib/{version}/site-packages")
    )
    site_packages = target / relative_site
    source_site = Path(sys.prefix) / relative_site
    site_packages.mkdir(parents=True, exist_ok=True)
    (site_packages / "ethos-fixture.pth").write_text(
        f"{(REPOSITORY_ROOT / 'src').as_posix()}\n{source_site.resolve().as_posix()}\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        return


def git_process(root: Path, *args: object, stdin: str = "") -> subprocess.CompletedProcess[str]:
    """Run Git and retain the complete process result for assertion-rich scenarios."""
    return subprocess.run(
        ("git", *(str(arg) for arg in args)),
        cwd=root,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def runtime_executable(runtime: Path, name: str) -> Path:
    """Return one platform-native executable path inside a Python image."""
    directory = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return runtime / directory / f"{name}{suffix}"


def runtime_build(commit: str, tree: str, *, release: bool = False) -> BuildIdentity:
    """Construct one exact test build identity."""
    return build_identity(
        product="0.2.0-alpha.2",
        source_commit=commit,
        source_tree=tree,
        release=release,
    )


def materialize_runtime_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    package_identity: BuildIdentity | None = None,
) -> tuple[Path, Path]:
    """Materialize one deterministic immutable runtime without host package mutation."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    source = tmp_path / "installed" / "a" / "b" / "c" / "d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    source_python = Path(sys.executable)
    monkeypatch.setattr(
        runtime_materialization,
        "resolve_runtime_wheel",
        lambda *_args, **_kwargs: wheel,
    )
    identity = package_identity or runtime_build_identity(REPOSITORY_ROOT)
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda *_args: identity)
    monkeypatch.setattr(
        runtime_materialization,
        "resolve_runtime_project",
        lambda _source: REPOSITORY_ROOT,
    )
    locked_requirements = tmp_path / "locked-requirements.txt"
    locked_requirements.write_text("fixture==1\n", encoding="utf-8")

    def prepare_requirements(project: Path, *_args: object, **_kwargs: object) -> Path:
        assert project == REPOSITORY_ROOT
        return locked_requirements

    monkeypatch.setattr(
        runtime_materialization,
        "prepare_locked_requirements",
        prepare_requirements,
    )

    def materialize_python(
        target: Path,
        _source: Path,
        _interpreter: Path,
        _wheel: Path,
        *,
        dependency_python: Path | None = None,
        python_facts: dict[str, str] | None = None,
        locked_requirements: Path | None,
    ) -> None:
        assert python_facts is not None
        assert locked_requirements == tmp_path / "locked-requirements.txt"
        assert dependency_python == source_python
        runtime_python = runtime_executable(target, "python")
        runtime_python.parent.mkdir(parents=True)
        runtime_python.write_bytes(b"python")
        runtime_python.chmod(0o755)
        package = target / "lib/python3.14/site-packages/ethos/module.py"
        package.parent.mkdir(parents=True)
        package.write_text("original\n", encoding="utf-8")

    monkeypatch.setattr(runtime_materialization, "materialize_python_image", materialize_python)

    def require_runtime(
        runtime: Path,
        artifact: identity_transition.PackageArtifact,
        _environment: RuntimeEnvironment,
        **kwargs: object,
    ) -> None:
        require_selected_runtime(
            runtime,
            expected_root=kwargs.get("expected_root"),
            expected_build=artifact.build,
        )

    monkeypatch.setattr(runtime_materialization, "require_runtime_generation", require_runtime)
    return repo, runtime_materialization.materialize_runtime(
        repo,
        source_python,
        expected_build=identity,
        build_source=REPOSITORY_ROOT,
    )


def linked_runtime_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path, Path]:
    """Construct two linked worktrees sharing one materialized runtime."""
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime",
        lambda *_args, **_kwargs: runtime,
    )
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    assert git_process(repo, "add", "tracked.txt").returncode == 0
    assert (
        git_process(
            repo,
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "base",
        ).returncode
        == 0
    )
    linked = tmp_path / "linked"
    assert git_process(repo, "worktree", "add", "-q", "-b", "work/linked", linked).returncode == 0
    common = Path(git_common_dir(repo))
    return repo, linked, runtime, common / "ethos" / "hooks"


def candidate_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    status: str,
) -> Path:
    """Bind one candidate-worktree observation for reference-transition scenarios."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    policy = type(
        "Policy",
        (),
        {
            "candidate_branch": "candidate/dev",
            "accepted_branch": "dev",
            "release_branch": "main",
            "release_mirror": "independent",
            "role_for_branch": lambda _self, _branch: "accepted",
        },
    )()
    monkeypatch.setattr(hook_runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        hook_runtime,
        "worktree_records",
        lambda *_args, **_kwargs: [
            {"branch": "candidate/dev", "path": candidate, "head": "b" * 40}
        ],
    )
    monkeypatch.setattr(
        hook_runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, status, ""),
    )
    return candidate

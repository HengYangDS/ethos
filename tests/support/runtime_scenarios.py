"""Reusable scenarios for immutable runtime and hook contract tests."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.materialization.python_image as runtime_python_image
import ethos.adapters.repo.runtime.transition as identity_transition
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity

if TYPE_CHECKING:
    import pytest

    from ethos.adapters.repo.runtime.manifest import RuntimeEnvironment

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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


def runtime_build(commit: str, tree: str, *, accepted: bool = False) -> BuildIdentity:
    """Construct one exact test build identity."""
    return build_identity(
        product="0.2.0-alpha.1",
        source_commit=commit,
        source_tree=tree,
        channel="accepted" if accepted else "development",
        acceptance_state="accepted" if accepted else "unaccepted",
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
    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", lambda *_args: wheel)
    identity = package_identity or runtime_build_identity(REPOSITORY_ROOT)
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda *_args: identity)
    monkeypatch.setattr(
        runtime_materialization,
        "resolve_runtime_project",
        lambda _source: REPOSITORY_ROOT,
    )
    monkeypatch.setattr(
        runtime_materialization, "resolve_owned_interpreter", lambda *_args: source_python
    )

    def materialize_python(
        target: Path,
        _source: Path,
        _interpreter: Path,
        _wheel: Path,
        _work: Path,
        *,
        python_facts: dict[str, str] | None = None,
        locked: bool,
    ) -> None:
        assert python_facts is not None
        assert locked is False
        runtime_python = runtime_executable(target, "python")
        runtime_python.parent.mkdir(parents=True)
        runtime_python.write_bytes(b"python")
        runtime_python.chmod(0o755)
        entrypoint = runtime_executable(target, "ethos")
        entrypoint.write_text(runtime_python_image.render_console_script("ethos"), encoding="utf-8")
        entrypoint.chmod(0o755)
        package = target / "lib/python3.14/site-packages/ethos/module.py"
        package.parent.mkdir(parents=True)
        package.write_text("original\n", encoding="utf-8")

    def python_facts(python: Path) -> dict[str, str]:
        prefix = python.parent.parent if python != source_python else source_python.parent.parent
        return {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "architecture": platform.machine(),
            "prefix": prefix.resolve().as_posix(),
            "base_prefix": prefix.resolve().as_posix(),
        }

    monkeypatch.setattr(runtime_materialization, "materialize_python_image", materialize_python)
    monkeypatch.setattr(runtime_materialization, "observe_python_facts", python_facts)

    def require_runtime(
        runtime: Path,
        artifact: identity_transition.ReleaseArtifact,
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

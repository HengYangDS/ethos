"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.hook.binding as hook_binding
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import runtime_command
from tests.support.ethos_cli_runner import run_ethos
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def test_hook_binding_follows_the_exact_configured_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = hook_activation.materialize_hook_launchers(common / "ethos" / "hooks")
    activate_runtime(common, venv.parent)
    for arguments in (
        ("config", "extensions.worktreeConfig", "true"),
        ("config", "--worktree", "core.hooksPath", generation.as_posix()),
    ):
        assert git_process(repo, *arguments).returncode == 0

    observed = hook_runtime_binding(repo)
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert observed["hooks_path"] == generation.as_posix()
    assert observed["required_gaps"] == []
    assert projected["data"]["hook_runtime"] == observed
    expected = runtime_build("c" * 40, "d" * 40)

    stale = hook_runtime_binding(repo, expected_build=expected)

    assert stale["source_commit"] == observed["source_commit"]
    assert stale["source_tree"] == observed["source_tree"]
    assert (stale["expected_source_commit"], stale["expected_source_tree"]) == (
        "c" * 40,
        "d" * 40,
    )
    assert not stale["current"]
    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["next_action"] == runtime_command(
        repo, "hook", "install", "--root", repo.as_posix(), "--json"
    )


def test_hook_binding_reports_non_utf8_launcher_as_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _venv = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = hook_activation.materialize_hook_launchers(common / "ethos" / "hooks")
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        git_process(
            repo, "config", "--worktree", "core.hooksPath", generation.as_posix()
        ).returncode
        == 0
    )
    (generation / "pre-push").write_bytes(b"\xff")

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:pre-push_launcher_drift" in observed["required_gaps"]


def test_hook_runtime_observation_rejects_launcher_drift(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    report = install_hook_launchers(repo)
    launcher = Path(str(report["hooks_path"])) / "pre-push"
    launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    observed = hook_runtime_binding(repo)

    assert observed["required_gaps"] == ["write_admission_not_armed:pre-push_launcher_drift"]


@pytest.mark.parametrize("configured_form", ["absolute", "relative"])
def test_hook_binding_rejects_a_symlinked_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_form: str
) -> None:
    repo, _venv = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    generation = hook_activation.materialize_hook_launchers(common / "ethos" / "hooks")
    alias = generation.with_name("f" * 64)
    alias.symlink_to(generation, target_is_directory=True)
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    configured = (
        alias.relative_to(repo).as_posix() if configured_form == "relative" else alias.as_posix()
    )
    assert git_process(repo, "config", "--worktree", "core.hooksPath", configured).returncode == 0

    observed = hook_runtime_binding(repo)

    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


def test_hook_binding_rejects_a_symlinked_generation_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _venv = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    real = common / "external-hooks"
    root = common / "ethos" / "hooks"
    real.mkdir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_generation_root_invalid"):
        hook_activation.materialize_hook_launchers(root)


def test_hook_binding_rejects_a_configured_path_outside_the_common_generation_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    external = tmp_path / "external-hooks"
    external.mkdir()
    assert git_process(repo, "config", "extensions.worktreeConfig", "true").returncode == 0
    assert (
        git_process(repo, "config", "--worktree", "core.hooksPath", external.as_posix()).returncode
        == 0
    )

    observed = hook_runtime_binding(repo)

    assert observed["hooks_path"] == external.as_posix()
    assert "write_admission_not_armed:core.hooksPath" in observed["required_gaps"]


def test_hook_binding_primitives_reject_invalid_hook_projections() -> None:
    with pytest.raises(ValueError, match="hook_name_invalid"):
        hook_binding.hook_launcher("post")
    with pytest.raises(ValueError, match="hook_launcher_projection_invalid"):
        hook_binding.hook_generation_digest({"pre-commit": "only"})


def test_hook_binding_reports_unavailable_source_and_generation_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert (
        subprocess.run(
            ("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=False
        ).returncode
        == 0
    )
    common = repo / ".git"
    generations = common / "ethos/hooks"
    generation = generations / ("a" * 64)
    generation.mkdir(parents=True)
    assert (
        subprocess.run(
            ("git", "config", "core.hooksPath", generation.as_posix()), cwd=repo, check=False
        ).returncode
        == 0
    )
    monkeypatch.setattr(hook_binding, "_selected_runtime", lambda *_args: (None, "runtime_current"))
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_build",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_source",
        lambda _repo: (_ for _ in ()).throw(ValueError("missing")),
    )
    report = hook_binding.hook_runtime_binding(repo)
    assert (
        "write_admission_not_armed:runtime_expected_source_unavailable" in report["required_gaps"]
    )

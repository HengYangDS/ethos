from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.git as git_adapter
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_git_execution_rejects_observation_overrides_and_spawn_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match="git_observation_environment_override_forbidden"):
        git_adapter.run_git(repo, "status", observation=True, env={"PATH": "/tmp"})

    executable = Path(git_adapter.git_executable({"PATH": str(Path("/usr/bin"))}))
    monkeypatch.setattr(git_adapter.shutil, "which", lambda *_args, **_kwargs: str(tmp_path))
    with pytest.raises(git_adapter.GitExecutionError) as invalid:
        git_adapter.git_executable({"PATH": executable.parent.as_posix()})
    assert (invalid.value.code, invalid.value.reason) == (
        "git_executable_unavailable",
        "resolved_executable_invalid",
    )

    monkeypatch.setattr(
        git_adapter.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("spawn rejected")),
    )
    with pytest.raises(git_adapter.GitExecutionError) as spawn:
        git_adapter.run_command(repo, (executable.as_posix(), "status"))
    assert (spawn.value.code, spawn.value.reason) == (
        "git_process_spawn_failed",
        "process_creation_failed",
    )


def test_git_command_and_remote_failures_preserve_stable_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match="command_capture_output_required"):
        git_adapter.run_command(repo, ("ignored",), capture_output=False)

    git(repo, "remote", "add", "origin", "ssh://example.invalid/repo.git")
    baseline = git_adapter.remote_availability_not_probed(repo)
    assert baseline["state"] == "not_probed"

    monkeypatch.setattr(git_adapter, "remote_availability_not_probed", lambda *_args: baseline)
    monkeypatch.setattr(
        git_adapter,
        "_execute",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(("git", "ls-remote"), 0.01)
        ),
    )
    timed_out = git_adapter.remote_availability(repo, timeout_seconds=0.01)
    assert (timed_out["state"], timed_out["reason"]) == ("unavailable", "timeout")


@pytest.mark.parametrize(
    ("returncode", "state"),
    [(0, "available"), (23, "unavailable")],
)
def test_remote_availability_classifies_git_exit_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    state: str,
) -> None:
    repo = init_git_repo(tmp_path / str(returncode))
    git(repo, "remote", "add", "origin", "ssh://example.invalid/repo.git")
    baseline = git_adapter.remote_availability_not_probed(repo)
    monkeypatch.setattr(git_adapter, "remote_availability_not_probed", lambda *_args: baseline)
    monkeypatch.setattr(
        git_adapter,
        "_execute",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ("git", "ls-remote"), returncode, "", "remote rejected"
        ),
    )

    observed = git_adapter.remote_availability(repo)

    assert observed["state"] == state
    assert observed["available"] is (returncode == 0)
    if returncode:
        assert (observed["exit_code"], observed["reason"]) == (23, "ls_remote_failed")


def test_run_command_removes_only_explicit_inherited_environment_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    observed: dict[str, str] = {}
    monkeypatch.setenv("PSModulePath", "pwsh-modules")
    monkeypatch.setenv("ETHOS_PRESERVED", "inherited")

    def capture_execute(
        _root: Path,
        command: tuple[str, ...],
        *,
        env: dict[str, str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        observed.update(env)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(git_adapter, "_execute", capture_execute)

    git_adapter.run_command(
        repo,
        ("tool",),
        env={"ETHOS_ADDED": "explicit"},
        remove_env=("PSModulePath",),
    )

    assert "PSModulePath" not in observed
    assert observed["ETHOS_PRESERVED"] == "inherited"
    assert observed["ETHOS_ADDED"] == "explicit"

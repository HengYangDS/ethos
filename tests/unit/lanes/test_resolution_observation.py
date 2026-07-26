from __future__ import annotations

import os
import subprocess

from ethos.adapters.mutation.resolution import _observation as observation
from ethos.adapters.repo import git as git_adapter


def test_git_observation_environment_is_isolated(monkeypatch, tmp_path) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_COUNT"):
        monkeypatch.setenv(name, "hostile")
    monkeypatch.setattr(git_adapter.subprocess, "run", run)

    git_adapter.run_git(tmp_path, "status", observation=True)
    _, kwargs = calls[0]

    assert kwargs["env"] == {
        "PATH": os.environ["PATH"],
        "LC_ALL": "C",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
    }
    assert kwargs["shell"] is False


def test_default_git_execution_does_not_inherit_observation_profile(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def run(argv, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(git_adapter.subprocess, "run", run)

    git_adapter.run_git(tmp_path, "update-ref", "refs/heads/dev", "a" * 40)

    assert calls[0]["env"] is None


def test_resolution_observation_uses_one_git_profile(monkeypatch, tmp_path) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def run_git(_root, *args, **kwargs):
        calls.append((args, kwargs))
        raw = kwargs.get("text") is False
        stdout = b"" if raw else ""
        if args[:2] == ("rev-parse", "refs/heads/work/example"):
            stdout = "a" * 40
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=b"" if raw else "")

    monkeypatch.setattr(
        observation,
        "workspace_status",
        lambda _root: {"worktrees": [{"branch": "work/example", "path": tmp_path.as_posix()}]},
    )
    monkeypatch.setattr(observation, "leases_by_branch", lambda _root: {})
    monkeypatch.setattr(observation, "run_git", run_git)

    lane, gaps = observation.observe_lane(tmp_path, "work/example")

    assert lane.head == "a" * 40
    assert gaps == []
    assert calls
    assert all(kwargs["observation"] is True for _, kwargs in calls)
    assert next(kwargs for args, kwargs in calls if args[0] == "ls-files")["text"] is False

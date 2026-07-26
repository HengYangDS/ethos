from __future__ import annotations

import os
import subprocess

import ethos.adapters.mutation.resolution.observation as observation
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
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(observation.subprocess, "run", run)

    vars(observation)["_git_run"](tmp_path, "status")
    argv, kwargs = calls[0]

    assert argv == ["git", "status"]
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

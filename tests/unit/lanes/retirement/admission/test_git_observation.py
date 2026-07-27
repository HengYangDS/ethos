from __future__ import annotations

import os
import stat
import subprocess
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.resolution.observation as observation_adapter
from ethos.adapters.mutation.resolution.observation import observe_ownerless_git
from tests.support.contract_helpers import git
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _assert_fixed_git_call(args: list[str], kwargs: dict[str, object]) -> None:
    assert args[0] == "git"
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["shell"] is False
    assert kwargs["env"] == {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", os.defpath),
    }
    assert not {"executable", "text", "encoding", "universal_newlines"} & kwargs.keys()


def test_ownerless_git_observation_uses_fixed_literal_byte_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    expected_head = git(repo, "rev-parse", "work/orphan")
    real_run = subprocess.run
    calls: list[tuple[list[str], dict[str, object]]] = []
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_CONFIG_COUNT",
        "XDG_CONFIG_HOME",
    ):
        monkeypatch.setenv(name, "/hostile/inherited/value")

    def recording_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((list(args), dict(kwargs)))
        return cast("subprocess.CompletedProcess[bytes]", real_run(args, **kwargs))

    monkeypatch.setattr(observation_adapter.subprocess, "run", recording_run)
    facts = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert facts.observation.head == expected_head
    assert calls
    for args, kwargs in calls:
        _assert_fixed_git_call(args, kwargs)


def test_same_path_ref_and_head_delete_recreate_changes_registration_token(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    first = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    git(repo, "worktree", "remove", lane.as_posix())
    git(repo, "branch", "-D", "work/orphan")
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), first.observation.head)
    second = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert second.observation.path == first.observation.path
    assert second.observation.head == first.observation.head
    assert second.registration_token != first.registration_token
    assert second.observation.lane_incarnation_id != first.observation.lane_incarnation_id
    assert stat.S_ISDIR(second.registration_token.worktree_identity.mode)

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.prewrite import has_control_character
from ethos.adapters.store import state
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    import pytest


def test_path_token_control_character_detector_covers_ascii_controls() -> None:
    assert has_control_character("README.md") is False
    assert has_control_character("README.md\nAGENTS.md") is True
    assert has_control_character("README.md\x7fAGENTS.md") is True


def test_pre_tool_hook_rejects_control_character_path_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[Path("README.md\nAGENTS.md")],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["decision"] == {
        "action": "block",
        "reason": "prewrite_path_invalid_control_character",
    }
    assert report["admission"]["paths"] == [
        {
            "path": "README.md\nAGENTS.md",
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": "path_invalid_control_character",
        }
    ]
    assert "prewrite_path_invalid_control_character" in report["required_gaps"]


def test_hook_admit_cli_preserves_control_character_path_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    payload = run_ethos_blocked(
        "hook",
        "admit",
        "pre-tool",
        "README.md\nAGENTS.md",
        "--root",
        worktree.as_posix(),
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )

    assert payload["data"]["decision"] == {
        "action": "block",
        "reason": "prewrite_path_invalid_control_character",
    }
    assert payload["data"]["target_paths"] == ["README.md\nAGENTS.md"]
    assert payload["data"]["admission"]["paths"][0]["path"] == "README.md\nAGENTS.md"

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.prewrite import has_control_character
from ethos.adapters.admission.prewrite import has_path_whitespace
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import leased_worktree


@pytest.fixture
def worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = init_repo(tmp_path / "repo")
    worktree = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    return worktree


def test_path_token_control_character_detector_covers_ascii_controls() -> None:
    assert has_control_character("README.md") is False
    assert has_control_character("README.md\nAGENTS.md") is True
    assert has_control_character("README.md\x7fAGENTS.md") is True


def test_path_token_whitespace_detector_marks_ambiguous_subjects() -> None:
    assert has_path_whitespace("README.md") is False
    assert has_path_whitespace("README.md .gitignore") is True
    assert has_path_whitespace("README.md\t.gitignore") is True


@pytest.mark.parametrize(
    ("token", "kind"),
    [
        ("README.md\nAGENTS.md", "control_character"),
        ("README.md .gitignore", "whitespace"),
    ],
    ids=["control-character", "whitespace"],
)
def test_pre_tool_hook_rejects_invalid_path_tokens(
    worktree: Path,
    token: str,
    kind: str,
) -> None:
    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[Path(token)],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["decision"] == {
        "action": "block",
        "reason": f"prewrite_path_invalid_{kind}",
    }
    assert report["admission"]["paths"] == [
        {
            "path": token,
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": f"path_invalid_{kind}",
        }
    ]
    assert f"prewrite_path_invalid_{kind}" in report["required_gaps"]


def test_hook_admit_cli_preserves_control_character_path_token(
    worktree: Path,
) -> None:
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

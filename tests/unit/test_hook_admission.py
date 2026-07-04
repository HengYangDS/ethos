from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.hook_admission import hook_admission_report

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def test_context_hook_rejects_stale_target_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    other = init_repo(tmp_path / "other")

    report = hook_admission_report(
        root=repo,
        layer="context",
        expected_root=other,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["decision"] == {
        "action": "block",
        "reason": "hook_context_root_mismatch",
    }
    assert report["target_root"] == repo.resolve().as_posix()
    assert report["expected_root"] == other.resolve().as_posix()
    assert "hook_context_root_mismatch" in report["required_gaps"]


def test_pre_tool_hook_blocks_protected_root_before_mutation(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-tool",
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["role"] == "accepted_root"
    assert report["decision"] == {
        "action": "block",
        "reason": "protected_lane_prewrite_blocked",
    }
    assert report["admission"]["error"] == "protected_lane_prewrite_blocked"
    assert "protected_lane_prewrite_blocked" in report["required_gaps"]


def test_pre_tool_hook_admits_owned_work_lane_with_editor_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")

    report = hook_admission_report(
        root=worktree,
        layer="pre-tool",
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["state"] == "admitted"
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": "allow",
        "reason": "prewrite_admitted",
    }
    assert report["admission"]["ok"] is True


def test_pre_run_hook_blocks_mutation_risk_without_target_paths(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = hook_admission_report(
        root=repo,
        layer="pre-run",
        command='python -c \'from pathlib import Path; Path("README.md").write_text("x")\'',
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["command_risk"] == {
        "tracked_mutation_risk": True,
        "reason": "command_text_matches_mutation_pattern",
    }
    assert report["decision"] == {
        "action": "block",
        "reason": "hook_prerun_paths_required",
    }
    assert "hook_prerun_paths_required" in report["required_gaps"]


def test_post_write_hook_fuses_protected_root_dirty_state(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "README.md").write_text("# changed\n", encoding="utf-8")

    report = hook_admission_report(
        root=repo,
        layer="post-write",
        paths=[repo / "README.md"],
        editor_root=repo,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "fused"
    assert report["role"] == "accepted_root"
    assert report["decision"] == {
        "action": "fuse",
        "reason": "post_write_protected_root_dirty",
    }
    assert report["changed_paths"] == ["README.md"]
    assert "post_write_protected_root_dirty" in report["required_gaps"]


def test_post_write_hook_fuses_work_lane_dirty_state_without_expected_paths(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# changed\n", encoding="utf-8")

    report = hook_admission_report(
        root=worktree,
        layer="post-write",
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["state"] == "fused"
    assert report["role"] == "work_lane"
    assert report["decision"] == {
        "action": "fuse",
        "reason": "post_write_unexpected_path",
    }
    assert report["changed_paths"] == ["README.md"]
    assert report["unexpected_paths"] == ["README.md"]
    assert "post_write_unexpected_path" in report["required_gaps"]

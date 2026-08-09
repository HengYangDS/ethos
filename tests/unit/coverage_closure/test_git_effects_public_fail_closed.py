"""Public Git workspace-effect failure boundaries."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effects as effects

if TYPE_CHECKING:
    from pathlib import Path


def _completed(code: int, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), code, "", stderr)


def test_stage_paths_rejects_empty_and_preserves_runner_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="git_effect_stage_paths_missing"):
        effects.stage_git_paths(tmp_path, ())
    with pytest.raises(ValueError, match="explicit add failure"):
        effects.stage_git_paths(
            tmp_path,
            ("tracked.txt",),
            runner=lambda *_args, **_kwargs: _completed(1, "explicit add failure"),
        )
    with pytest.raises(ValueError, match="git_effect_stage_failed"):
        effects.stage_git_paths(
            tmp_path,
            ("tracked.txt",),
            runner=lambda *_args, **_kwargs: _completed(1),
        )


def test_stage_and_commit_worktree_reject_stale_head_and_git_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(effects, "current_tracked_head", lambda _root: "observed")
    with pytest.raises(ValueError, match="git_effect_head_stale"):
        effects.stage_git_worktree(tmp_path, previous="expected")
    with pytest.raises(ValueError, match="git_effect_head_stale"):
        effects.commit_git_worktree(tmp_path, previous="expected", message="change")

    monkeypatch.setattr(effects, "run_git", lambda *_args, **_kwargs: _completed(1))
    with pytest.raises(ValueError, match="git_effect_stage_failed"):
        effects.stage_git_worktree(tmp_path, previous="observed")


def test_move_tracked_tree_rejects_escape_missing_and_existing_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="git_effect_move_path_outside_root"):
        effects.move_tracked_tree(tmp_path, "source", "../outside")

    with pytest.raises(ValueError, match="git_effect_move_binding_stale"):
        effects.move_tracked_tree(tmp_path, "missing", "target")

    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(ValueError, match="git_effect_move_binding_stale"):
        effects.move_tracked_tree(tmp_path, "source", "target")


def test_compensation_rejects_git_failure_and_unsafe_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(effects, "run_git", lambda *_args, **_kwargs: _completed(1))
    with pytest.raises(ValueError, match="git_effect_compensation_failed"):
        effects.compensate_git_worktree(tmp_path, head="a" * 40)
    with pytest.raises(ValueError, match="git_effect_compensation_failed"):
        effects.compensate_created_paths(
            tmp_path,
            head="a" * 40,
            paths=("created/file",),
            untracked_root="created",
        )

    unsafe = tmp_path / "unsafe"
    unsafe.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="git_effect_compensation_path_unsafe"):
        effects.remove_untracked_tree(tmp_path, "unsafe")
    with pytest.raises(ValueError, match="git_effect_compensation_path_outside_root"):
        effects.remove_untracked_tree(tmp_path, "../outside")


def test_compensate_created_paths_removes_exact_untracked_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    created = tmp_path / "created"
    created.mkdir()
    (created / "file").write_text("created", encoding="utf-8")
    monkeypatch.setattr(effects, "run_git", lambda *_args, **_kwargs: _completed(0))

    effects.compensate_created_paths(
        tmp_path,
        head="a" * 40,
        paths=("created/file",),
        untracked_root="created",
    )

    assert not created.exists()

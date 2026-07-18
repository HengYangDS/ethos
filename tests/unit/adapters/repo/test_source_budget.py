from __future__ import annotations

import subprocess

import ethos.adapters.repo.source_budget.core as source_budget
from ethos.adapters.repo.source_budget.core import present_worktree_paths


def _git(root, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_present_worktree_paths_includes_untracked_and_excludes_missing_index_path(
    tmp_path,
):
    _git(tmp_path, "init", "--quiet")
    tracked = tmp_path / "tools" / "tracked.sh"
    deleted = tmp_path / "tools" / "deleted.sh"
    untracked = tmp_path / "tools" / "untracked.sh"
    ignored = tmp_path / "tools" / "ignored.sh"
    for path in (tracked, deleted, untracked, ignored):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("echo source\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("tools/ignored.sh\n", encoding="utf-8")
    _git(
        tmp_path,
        "add",
        ".gitignore",
        tracked.relative_to(tmp_path).as_posix(),
        deleted.relative_to(tmp_path).as_posix(),
    )
    deleted.unlink()

    assert present_worktree_paths(tmp_path) == (
        ".gitignore",
        "tools/tracked.sh",
        "tools/untracked.sh",
    )


def test_present_worktree_paths_returns_empty_when_git_is_unavailable(tmp_path, monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(source_budget.subprocess, "run", unavailable)

    assert present_worktree_paths(tmp_path) == ()

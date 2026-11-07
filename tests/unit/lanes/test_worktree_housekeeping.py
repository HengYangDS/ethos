"""Remove only authorized disposable worktrees after fresh ownership checks."""

from __future__ import annotations

import shutil
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.worktree.detached_cleanup as detached_cleanup
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


def _detached(repo: Path, path: Path) -> None:
    git(repo, "worktree", "add", "--detach", path.as_posix(), "dev")


def _ignore(repo: Path, worktree: Path, relative: str) -> None:
    """Write one file that the shared exclude list ignores, inside a worktree."""
    if relative:
        (repo / ".git/info").mkdir(exist_ok=True)
        with (repo / ".git/info/exclude").open("a", encoding="utf-8") as exclude:
            exclude.write(relative.partition("/")[0] + "/\n")
        (worktree / relative).parent.mkdir(parents=True, exist_ok=True)
        (worktree / relative).write_text("ignored\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("reason", "ignored"),
    [
        ("worktree_dirty", ""),
        ("worktree_locked", ""),
        ("worktree_missing", ""),
        ("worktree_head_unreachable", ""),
        ("worktree_ignored_content", "build/evidence/record.json"),
        ("worktree_ignored_content", "__pycache__/gone.cpython-314.pyc"),
    ],
)
def test_housekeeping_preserves_protected_detached_worktrees(
    tmp_path: Path, reason: str, ignored: str
) -> None:
    """Housekeeping never removes the only copy of a commit or of ignored content."""
    repo, _candidate = init_repo_with_candidate(tmp_path)
    protected = tmp_path / f"protected-{reason}-{len(ignored)}"
    _detached(repo, protected)
    _ignore(repo, protected, ignored)
    if reason == "worktree_dirty":
        (protected / "README.md").write_text("dirty\n")
    elif reason == "worktree_locked":
        git(repo, "worktree", "lock", protected.as_posix())
    elif reason == "worktree_head_unreachable":
        tree = git(protected, "rev-parse", "HEAD^{tree}")
        unique = git(protected, "commit-tree", tree, "-p", "HEAD", "-m", "unique")
        git(protected, "checkout", "--quiet", "--detach", unique)
    elif reason == "worktree_missing":
        shutil.rmtree(protected)

    report = detached_cleanup.housekeeping_worktrees(
        root=repo, temporary_roots=(tmp_path,), authorized=True, apply=True
    )

    entry = next(item for item in report["entries"] if item["path"] == protected.as_posix())
    assert entry["reasons"] == [reason]
    assert report["summary"]["removed_count"] == 0


def test_housekeeping_requires_authorization_then_removes_rechecked_candidate(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    clean = tmp_path / "clean-detached"
    _detached(repo, clean)
    # A regenerable root, such as a root `.venv`, leaves the worktree removable.
    _ignore(repo, clean, ".venv/lib/module.py")

    blocked = detached_cleanup.housekeeping_worktrees(
        root=repo, temporary_roots=(tmp_path,), apply=True
    )
    applied = detached_cleanup.housekeeping_worktrees(
        root=repo, temporary_roots=(tmp_path,), authorized=True, apply=True
    )

    assert blocked["required_gaps"] == ["authorization_required"]
    assert applied["state"] == "cleaned"
    assert applied["summary"]["removed_count"] == 1
    assert not clean.exists()


def test_housekeeping_fails_closed_on_inventory_and_recheck_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    detached = tmp_path / "changing-detached"
    _detached(repo, detached)
    original = detached_cleanup.run_git
    inventories = 0

    def fail_second_inventory(root: Path, *args: str, check: bool = True):
        nonlocal inventories
        if args == ("worktree", "list", "--porcelain"):
            inventories += 1
            if inventories == 2:
                return CompletedProcess(args, 1, stdout="", stderr="unavailable")
        return original(root, *args, check=check)

    monkeypatch.setattr(detached_cleanup, "run_git", fail_second_inventory)
    stale = detached_cleanup.housekeeping_worktrees(
        root=repo, temporary_roots=(tmp_path,), authorized=True, apply=True
    )
    monkeypatch.setattr(
        detached_cleanup,
        "run_git",
        lambda root, *args, check=True: (
            CompletedProcess(args, 1, stdout="", stderr="bad")
            if args[0] == "for-each-ref"
            else original(root, *args, check=check)
        ),
    )
    # A Git that cannot say whether a ref reaches the HEAD protects the worktree.
    unreachable = detached_cleanup.housekeeping_worktrees(root=repo, temporary_roots=(tmp_path,))
    monkeypatch.setattr(
        detached_cleanup,
        "run_git",
        lambda _root, *_args, **_kwargs: CompletedProcess(_args, 1, stdout="", stderr="bad"),
    )
    unavailable = detached_cleanup.housekeeping_worktrees(root=repo)

    assert stale["required_gaps"] == [
        f"housekeeping_candidate_stale:{detached.resolve().as_posix()}"
    ]
    assert unavailable["required_gaps"] == ["housekeeping_inventory_failed"]
    assert [entry["reasons"] for entry in unreachable["entries"] if entry["detached"]] == [
        ["worktree_reachability_unavailable"]
    ]

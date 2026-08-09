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


@pytest.mark.parametrize("reason", ["worktree_dirty", "worktree_locked", "worktree_missing"])
def test_housekeeping_preserves_protected_detached_worktrees(tmp_path: Path, reason: str) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    protected = tmp_path / f"protected-{reason}"
    _detached(repo, protected)
    if reason == "worktree_dirty":
        (protected / "README.md").write_text("dirty\n")
    elif reason == "worktree_locked":
        git(repo, "worktree", "lock", protected.as_posix())
    else:
        shutil.rmtree(protected)

    report = detached_cleanup.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
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

    blocked = detached_cleanup.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        apply=True,
    )
    applied = detached_cleanup.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )

    assert blocked["required_gaps"] == ["authorization_required"]
    assert applied["state"] == "cleaned"
    assert applied["summary"]["removed_count"] == 1
    assert not clean.exists()


def test_housekeeping_fails_closed_on_inventory_and_recheck_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )
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

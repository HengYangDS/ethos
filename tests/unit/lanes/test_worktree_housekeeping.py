from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import ethos.adapters.mutation.worktree_housekeeping as worktree_housekeeping
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_repo_with_candidate


def _add_detached(repo: Path, path: Path) -> None:
    git(repo, "worktree", "add", "--detach", path.as_posix(), "dev")


def test_housekeeping_classifies_only_clean_detached_temporary_worktrees(
    tmp_path: Path,
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    clean = tmp_path / "clean-detached"
    dirty = tmp_path / "dirty-detached"
    outside = repo.parent.parent / "outside-detached"
    _add_detached(repo, clean)
    _add_detached(repo, dirty)
    _add_detached(repo, outside)
    (dirty / "README.md").write_text("dirty\n", encoding="utf-8")

    report = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=False,
        apply=False,
    )

    entries = {entry["path"]: entry for entry in report["entries"]}
    assert entries[clean.resolve().as_posix()]["removable"] is True
    assert entries[dirty.resolve().as_posix()]["reasons"] == ["worktree_dirty"]
    assert entries[outside.resolve().as_posix()]["reasons"] == ["worktree_outside_temporary_roots"]
    assert entries[candidate.resolve().as_posix()]["reasons"] == ["worktree_branch_bound"]


def test_housekeeping_requires_authorization_and_removes_only_rechecked_candidates(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    clean = tmp_path / "clean-detached"
    dirty = tmp_path / "dirty-detached"
    _add_detached(repo, clean)
    _add_detached(repo, dirty)
    (dirty / "README.md").write_text("dirty\n", encoding="utf-8")

    blocked = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=False,
        apply=True,
    )
    assert blocked["required_gaps"] == ["housekeeping_authorization_required"]
    assert clean.exists()

    applied = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )
    assert applied["ok"] is True
    assert applied["state"] == "cleaned"
    assert applied["summary"]["removed_count"] == 1
    assert not clean.exists()
    assert dirty.exists()


def test_housekeeping_protects_git_locked_detached_worktrees(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    locked = tmp_path / "locked-detached"
    _add_detached(repo, locked)
    git(repo, "worktree", "lock", locked.as_posix())

    report = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )

    entry = next(item for item in report["entries"] if item["path"] == locked.as_posix())
    assert entry["reasons"] == ["worktree_locked"]
    assert locked.exists()


def test_housekeeping_preserves_candidate_that_changes_before_removal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    changing = tmp_path / "changing-detached"
    _add_detached(repo, changing)

    def changed_entry(
        _repo: Path,
        path: Path,
        _roots: tuple[Path, ...],
    ) -> dict[str, object]:
        return {
            "path": path.resolve().as_posix(),
            "head": "changed",
            "branch": "detached",
            "detached": True,
            "removable": False,
            "reasons": ["worktree_dirty"],
        }

    monkeypatch.setattr(worktree_housekeeping, "_entry", changed_entry)
    report = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == [
        f"housekeeping_candidate_stale:{changing.resolve().as_posix()}"
    ]
    assert changing.exists()


def test_housekeeping_default_roots_cover_system_and_session_temp() -> None:
    roots = worktree_housekeeping._temporary_roots(None)

    assert Path("/tmp").resolve() in roots
    assert Path(worktree_housekeeping.tempfile.gettempdir()).resolve() in roots


def test_housekeeping_protects_worktree_when_status_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    unavailable = tmp_path / "unavailable-detached"
    _add_detached(repo, unavailable)
    original_run_git = worktree_housekeeping.run_git

    def fail_target_status(root: Path, *args: str, check: bool = True):
        if Path(root).resolve() == unavailable.resolve() and args[:2] == (
            "status",
            "--porcelain",
        ):
            return CompletedProcess(args, 1, stdout="", stderr="unavailable")
        return original_run_git(root, *args, check=check)

    monkeypatch.setattr(worktree_housekeeping, "run_git", fail_target_status)
    report = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
        authorized=True,
        apply=True,
    )

    entry = next(item for item in report["entries"] if item["path"] == unavailable.as_posix())
    assert entry["reasons"] == ["worktree_status_unavailable"]
    assert unavailable.exists()


def test_housekeeping_blocks_when_git_inventory_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)

    def fail_inventory(_root: Path, *args: str, check: bool = True):
        del check
        assert args == ("worktree", "list", "--porcelain")
        return CompletedProcess(args, 1, stdout="", stderr="unavailable")

    monkeypatch.setattr(worktree_housekeeping, "run_git", fail_inventory)
    report = worktree_housekeeping.housekeeping_worktrees(
        root=repo,
        temporary_roots=(tmp_path,),
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["housekeeping_inventory_failed"]

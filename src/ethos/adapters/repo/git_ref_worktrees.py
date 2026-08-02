"""Admission and synchronization of worktrees bound to mutated Git refs."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git


def ref_worktree_paths(worktrees: list[dict[str, object]], branch: str) -> tuple[Path, ...]:
    """Return every present worktree bound to one ref."""
    return tuple(
        Path(str(item["path"]))
        for item in worktrees
        if item.get("branch") == branch and item.get("worktree_binding") in {"current", "linked"}
    )


def worktree_sync_gap(
    root: Path,
    paths: tuple[Path, ...],
    branch: str,
    ref_head: str,
    previous: str,
    head: str,
) -> str:
    """Return the first stale, dirty, or overwrite-risk worktree gap."""
    changed = run_git(
        root,
        "diff",
        "--no-ext-diff",
        "--name-only",
        "-z",
        previous,
        head,
        check=False,
        text=False,
        observation=True,
    )
    if changed.returncode:
        return "worktree_diff_unreadable"
    changed_paths = set(changed.stdout.split(b"\0")) - {b""}
    common_dir = git_common_dir(root)
    for path in paths:
        if path.is_symlink() or not path.is_dir():
            return "worktree_binding_stale"
        if (
            git_common_dir(path) != common_dir
            or run_git(path, "branch", "--show-current", observation=True).stdout.strip() != branch
            or current_tracked_head(path) != ref_head
        ):
            return "worktree_binding_stale"
        commands = (
            run_git(path, "diff-index", "--cached", "--quiet", previous, "--", check=False),
            run_git(path, "diff-files", "--quiet", "--ignore-submodules", "--", check=False),
            run_git(
                path,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                check=False,
                text=False,
            ),
        )
        if any(command.returncode for command in commands):
            return "worktree_status_unreadable"
        if commands[2].stdout:
            return "worktree_dirty"
        indexed = run_git(path, "ls-files", "-v", "-z", check=False, text=False)
        ignored = run_git(
            path,
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "-z",
            check=False,
            text=False,
        )
        if indexed.returncode or ignored.returncode:
            return "worktree_status_unreadable"
        masked = {
            record[2:]
            for record in indexed.stdout.split(b"\0")
            if len(record) > 2 and (record.startswith(b"S ") or record[:1].islower())
        }
        ignored_paths = set(ignored.stdout.split(b"\0")) - {b""}
        if changed_paths & masked or any(
            changed_path == ignored_path
            or changed_path.startswith(ignored_path.rstrip(b"/") + b"/")
            for changed_path in changed_paths
            for ignored_path in ignored_paths
        ):
            return "worktree_ignored_path_conflict"
    return ""


def sync_ref_worktrees(
    root: Path,
    paths: tuple[Path, ...],
    branch: str,
    head: str,
    previous: str,
) -> dict[str, object]:
    """Synchronize every pre-admitted clean worktree after one ref CAS."""
    outcomes: list[dict[str, str]] = []
    for path in paths:
        gap = worktree_sync_gap(root, (path,), branch, head, previous, head)
        update = (
            run_git(path, "read-tree", "-u", "-m", previous, head, check=False) if not gap else None
        )
        post_gap = worktree_sync_gap(root, (path,), branch, head, head, head) if update else gap
        state = "failed" if update is None or update.returncode or post_gap else "synced"
        outcomes.append(
            {
                "path": path.as_posix(),
                "state": state,
                "status": post_gap,
                "stderr": gap or (update.stderr.strip() if update else ""),
            }
        )
    return {
        "worktree_sync": "failed"
        if any(item["state"] == "failed" for item in outcomes)
        else "synced",
        "worktrees": outcomes,
    }


def sync_linked_ref_worktree(
    root: Path,
    worktrees: list[dict[str, object]],
    branch: str,
    head: str,
    previous: str,
) -> dict[str, object]:
    """Synchronize all linked worktrees after their ref transaction."""
    if not branch:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    paths = ref_worktree_paths(worktrees, branch)
    result = {
        "mode": "accepted_ff",
        "branch": branch,
        "previous_head": previous,
        "head": head,
        "worktree_sync": "not_linked" if not paths else "synced",
        "worktrees": [],
    }
    return (
        result
        if not paths
        else {**result, **sync_ref_worktrees(root, paths, branch, head, previous)}
    )

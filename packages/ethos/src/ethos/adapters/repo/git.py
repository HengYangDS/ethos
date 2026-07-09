"""Git IO adapter — subprocess primitives for reading Git facts and wiring hooks.

The impure IO shell for Git: every function shells out to `git`. Product domain
code stays pure and is fed these facts by the surface/orchestration layer. Reads
dominate; the one sanctioned write is hook-path wiring (set_hooks_path), which
installs the local admission entrance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def current_head(root: Path) -> str:
    """Return the current HEAD sha, or 'untracked' if not a resolvable ref."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        # root does not exist (e.g. a stale or foreign target path): treat as untracked
        # rather than crashing — the caller reports a gap, not an exception.
        return "untracked"
    if completed.returncode != 0:
        return "untracked"
    return completed.stdout.strip()


def current_tracked_head(root: Path) -> str:
    """Return the current HEAD sha, or '' when untracked."""
    head = current_head(root)
    return "" if head == "untracked" else head


def git_stdout(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stripped stdout, or '' on failure."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        # root does not exist: no git facts to read, same as a failed command.
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def remote_tracking_sync(root: Path, branch: str, remote: str = "origin") -> dict[str, object]:
    """Project local HEAD versus the local remote-tracking ref without network IO."""
    branch_name = branch.strip()
    remote_name = remote.strip() or "origin"
    remote_ref = f"{remote_name}/{branch_name}" if branch_name else remote_name
    local_head = current_tracked_head(root)
    if not branch_name:
        return {
            "kind": "git_remote_tracking_sync",
            "remote": remote_name,
            "branch": branch_name,
            "remote_ref": remote_ref,
            "state": "branch_unknown",
            "local_head": local_head,
            "remote_head": "",
            "ahead": 0,
            "behind": 0,
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": ["remote_tracking_branch_unknown"],
        }
    remote_head = git_stdout(root, "rev-parse", "--verify", remote_ref)
    if not remote_head:
        return {
            "kind": "git_remote_tracking_sync",
            "remote": remote_name,
            "branch": branch_name,
            "remote_ref": remote_ref,
            "state": "remote_tracking_missing",
            "local_head": local_head,
            "remote_head": "",
            "ahead": 0,
            "behind": 0,
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [f"remote_tracking_missing:{remote_ref}"],
        }
    counts = git_stdout(root, "rev-list", "--left-right", "--count", f"{remote_ref}...HEAD")
    try:
        behind_text, ahead_text = counts.split()[:2]
        behind = int(behind_text)
        ahead = int(ahead_text)
    except (IndexError, ValueError):
        behind = 0
        ahead = 0
    if ahead and behind:
        state = "diverged"
    elif ahead:
        state = "local_ahead"
    elif behind:
        state = "local_behind"
    else:
        state = "synchronized"
    advisory = (
        []
        if state == "synchronized"
        else [f"remote_tracking_{state}:{remote_ref}:{ahead}:{behind}"]
    )
    return {
        "kind": "git_remote_tracking_sync",
        "remote": remote_name,
        "branch": branch_name,
        "remote_ref": remote_ref,
        "state": state,
        "local_head": local_head,
        "remote_head": remote_head,
        "ahead": ahead,
        "behind": behind,
        "available": True,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": advisory,
    }


def set_hooks_path(root: Path, hooks_path: str) -> bool:
    """Wire git core.hooksPath to hooks_path (the sanctioned local-entrance write)."""
    completed = subprocess.run(
        ["git", "config", "core.hooksPath", hooks_path],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def set_config(root: Path, key: str, value: str) -> bool:
    """Set a local git config key (used to record ethos.acceptedBranch for the hooks)."""
    completed = subprocess.run(
        ["git", "config", key, value],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def git_common_dir(root: Path) -> str:
    """Return the resolved git common dir (shared across worktrees), or ''."""
    common_dir = git_stdout(root, "rev-parse", "--git-common-dir")
    if not common_dir:
        return ""
    path = Path(common_dir)
    if not path.is_absolute():
        path = root / path
    return path.resolve().as_posix()


def same_git_repository(left: Path, right: Path) -> bool:
    """True when both paths resolve to the same underlying git repository."""
    left_common = git_common_dir(left)
    right_common = git_common_dir(right)
    return bool(left_common and right_common and left_common == right_common)


def git_files(root: Path, *patterns: str) -> list[str]:
    """Return tracked files matching the given pathspec patterns."""
    command = ["git", "ls-files", *patterns]
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


def commits_equivalent_over_paths(
    root: Path,
    head: str,
    *,
    relevant_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the commits parity-equivalent to head over a set of relevant pathspecs.

    A commit is "equivalent" to head when nothing under relevant_paths changed between
    it and head — so head's parity/shadow verdict is unchanged from that commit. Git
    cannot express "commits that did NOT touch a pathspec", so we find the boundary
    (the most recent commit at-or-before head that DID touch a relevant path) and
    return everything from that boundary (exclusive) up to head, plus head itself.

    When no relevant path was ever touched in head's history the boundary is empty; we
    then return just (head,) — the caller keeps its own parent handling for that case.
    """
    if not head:
        return ()
    boundary = git_stdout(root, "rev-list", "-1", head, "--", *relevant_paths)
    if not boundary:
        # No relevant path exists anywhere in head's history — nothing that could
        # change the parity verdict was ever committed, so every reachable commit is
        # parity-equivalent to head.
        span = git_stdout(root, "rev-list", head)
        return tuple(dict.fromkeys(line for line in span.splitlines() if line)) or (head,)
    if boundary == head:
        # head itself changed a relevant path — only head is current.
        return (head,)
    # boundary is the most recent commit that changed a relevant path; nothing relevant
    # changed after it, so boundary's source state equals head's. Every commit from
    # boundary (inclusive) up to head is therefore parity-equivalent to head.
    span = git_stdout(root, "rev-list", f"{boundary}..{head}")
    commits = [line for line in span.splitlines() if line]
    return tuple(dict.fromkeys([head, *commits, boundary]))


def remote_availability(
    root: Path, remote: str = "origin", *, timeout_seconds: float = 3.0
) -> dict[str, object]:
    """Probe whether a configured Git remote is reachable without mutating state."""
    url = git_stdout(root, "remote", "get-url", remote)
    if not url:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "state": "unconfigured",
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [f"remote_unconfigured:{remote}"],
        }
    try:
        completed = subprocess.run(
            ["git", "ls-remote", "--exit-code", remote],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "url": url,
            "state": "unavailable",
            "available": False,
            "blocking": False,
            "reason": "timeout",
            "stderr": str(exc),
            "required_gaps": [],
            "advisory_gaps": [f"remote_unavailable:{remote}"],
        }
    if completed.returncode == 0:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "url": url,
            "state": "available",
            "available": True,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        }
    return {
        "kind": "git_remote_availability",
        "remote": remote,
        "url": url,
        "state": "unavailable",
        "available": False,
        "blocking": False,
        "reason": "ls_remote_failed",
        "exit_code": completed.returncode,
        "stderr": completed.stderr.strip(),
        "required_gaps": [],
        "advisory_gaps": [f"remote_unavailable:{remote}"],
    }

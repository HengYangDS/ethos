"""Git IO adapter — subprocess primitives for reading Git facts.

The impure IO shell for Git: every function shells out to `git`. Product domain
code stays pure and is fed these facts by the surface/orchestration layer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import overload

if TYPE_CHECKING:
    from collections.abc import Mapping

_GIT = shutil.which("git") or "git"


@overload
def run_git(
    root: Path,
    *args: str,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    stdin: str | None = None,
    text: Literal[True] = True,
    observation: bool = False,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_git(
    root: Path,
    *args: str,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    stdin: bytes | None = None,
    text: Literal[False],
    observation: bool = False,
) -> subprocess.CompletedProcess[bytes]: ...


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
    env: Mapping[str, str] | None = None,
    stdin: str | bytes | None = None,
    text: bool = True,
    observation: bool = False,
) -> subprocess.CompletedProcess[Any]:
    """Run one Git command and preserve the complete subprocess result."""
    if observation and env:
        message = "git_observation_environment_override_forbidden"
        raise ValueError(message)
    effective_env = (
        {"PATH": os.environ.get("PATH", os.defpath)}
        if observation
        else {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    )
    effective_env.update(
        {
            "LC_ALL": "C",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            **(env or {}),
        }
    )
    return subprocess.run(
        [_GIT, *args],
        cwd=root,
        check=check,
        text=text,
        capture_output=True,
        env=effective_env,
        input=stdin,
        shell=False,
    )


def repository_root(root: Path) -> Path:
    """Return the resolved Git worktree root for ``root``."""
    return Path(run_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` reaches ``descendant`` in Git history."""
    completed = run_git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return completed.returncode == 0


def current_head(root: Path) -> str:
    """Return the current HEAD sha, or 'untracked' if not a resolvable ref."""
    try:
        completed = run_git(root, "rev-parse", "HEAD", check=False)
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


def ref_head(
    root: Path,
    ref: str,
    expected: str = "",
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Resolve one ref, preserving the width of an expected null object ID."""
    completed = run_git(root, "rev-parse", "--verify", ref, check=False, env=environment)
    if completed.returncode == 0:
        return completed.stdout.strip()
    return expected if expected and not set(expected) - {"0"} else "0" * len(expected)


def current_tree(
    root: Path,
    head: str = "HEAD",
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Return the exact tree for a Git revision, or an empty string on failure."""
    completed = run_git(
        root,
        "rev-parse",
        f"{head}^{{tree}}",
        check=False,
        env=environment,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def git_stdout_checked(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stdout, raising on failure."""
    completed = run_git(root, *args)
    return completed.stdout.rstrip("\n")


def git_stdout(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stripped stdout, or '' on failure."""
    try:
        completed = run_git(root, *args, check=False)
    except (FileNotFoundError, NotADirectoryError):
        # root does not exist: no git facts to read, same as a failed command.
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def committed_file_text(root: Path, ref: str, path: str) -> str:
    """Return a tracked file's text from a committed tree, or '' when unavailable."""
    return git_stdout(root, "show", f"{ref}:{path}") if ref else ""


def committed_file_bytes(
    root: Path,
    ref: str,
    path: str,
    *,
    environment: dict[str, str] | None = None,
) -> bytes:
    """Return exact tracked bytes from one committed tree, or ``b''`` on failure."""
    if not ref:
        return b""
    try:
        completed = run_git(
            root,
            "show",
            f"{ref}:{path}",
            check=False,
            env=environment,
            text=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return b""
    return completed.stdout if completed.returncode == 0 else b""


def exact_rename_target(root: Path, old_ref: str, new_ref: str, source: str) -> str:
    """Return the sole target of one exact Git rename from ``source``."""
    completed = run_git(
        root,
        "diff",
        "--no-ext-diff",
        "--name-status",
        "-z",
        "--find-renames=100%",
        "--find-copies=100%",
        old_ref,
        new_ref,
        check=False,
        text=False,
        observation=True,
    )
    if completed.returncode != 0:
        return ""
    fields = completed.stdout.split(b"\0")
    renames: list[str] = []
    exact_targets = 0
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        has_target = status.startswith((b"R", b"C"))
        width = 2 if has_target else 1
        if index + width > len(fields):
            return ""
        paths = fields[index : index + width]
        index += width
        try:
            old_path = paths[0].decode()
            new_path = paths[1].decode() if has_target else ""
        except UnicodeDecodeError:
            return ""
        if status in {b"R100", b"C100"} and old_path == source:
            exact_targets += 1
            if status == b"R100":
                renames.append(new_path)
    return renames[0] if exact_targets == len(renames) == 1 else ""


def remote_tracking_sync(root: Path, branch: str, remote: str = "origin") -> dict[str, object]:
    """Project local HEAD versus the local remote-tracking ref without network IO."""
    branch_name = branch.strip()
    remote_name = remote.strip() or "origin"
    remote_ref = f"{remote_name}/{branch_name}" if branch_name else remote_name
    result: dict[str, object] = {
        "kind": "git_remote_tracking_sync",
        "remote": remote_name,
        "branch": branch_name,
        "remote_ref": remote_ref,
        "local_head": current_tracked_head(root),
        "remote_head": "",
        "ahead": 0,
        "behind": 0,
        "available": False,
        "blocking": False,
        "required_gaps": [],
    }
    if not branch_name:
        return {
            **result,
            "state": "branch_unknown",
            "advisory_gaps": ["remote_tracking_branch_unknown"],
        }
    remote_head = git_stdout(root, "rev-parse", "--verify", remote_ref)
    if not remote_head:
        return {
            **result,
            "state": "remote_tracking_missing",
            "advisory_gaps": [f"remote_tracking_missing:{remote_ref}"],
        }
    counts = git_stdout(root, "rev-list", "--left-right", "--count", f"{remote_ref}...HEAD")
    try:
        behind_text, ahead_text = counts.split()[:2]
        behind, ahead = int(behind_text), int(ahead_text)
    except (IndexError, ValueError):
        behind = ahead = 0
    state = (
        "diverged"
        if ahead and behind
        else "local_ahead"
        if ahead
        else "local_behind"
        if behind
        else "synchronized"
    )
    result.update(
        state=state,
        remote_head=remote_head,
        ahead=ahead,
        behind=behind,
        available=True,
        advisory_gaps=[]
        if state == "synchronized"
        else [f"remote_tracking_{state}:{remote_ref}:{ahead}:{behind}"],
    )
    return result


def publication_remote_syncs(root: Path, branch: str) -> dict[str, object]:
    """Project configured GitLab/GitHub branches without granting either authority."""
    records: dict[str, dict[str, object]] = {}
    configured = set(git_stdout(root, "remote").splitlines())
    for remote in ("origin", "github"):
        if remote not in configured:
            continue
        records[remote] = remote_tracking_sync(root, branch, remote)
    states = {str(record.get("state") or "not_checked") for record in records.values()}
    synchronized = bool(records) and states == {"synchronized"}
    reconciliation_required = any(
        state in {"diverged", "local_behind", "remote_tracking_missing"} for state in states
    )
    return {
        "remotes": records,
        "state": "synchronized"
        if synchronized
        else "reconciliation_required"
        if reconciliation_required
        else "pending",
        "advisory_gaps": [
            f"remote_reconciliation_required:{name}:{record.get('state')}"
            for name, record in records.items()
            if record.get("state") != "synchronized"
        ],
    }


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
    completed = run_git(root, "ls-files", *patterns, check=False)
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


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
            [_GIT, "ls-remote", "--exit-code", remote],
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


def remote_availability_not_probed(root: Path, remote: str = "origin") -> dict[str, object]:
    """Describe a configured remote without performing a network reachability probe."""
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
    return {
        "kind": "git_remote_availability",
        "remote": remote,
        "url": url,
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }

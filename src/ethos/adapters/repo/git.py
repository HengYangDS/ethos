"""Git IO adapter — subprocess primitives for reading Git facts.

The impure IO shell for Git: every function shells out to `git`. Product domain
code stays pure and is fed these facts by the surface/orchestration layer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import overload

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

_GIT_CONFIG_SOURCE_ENV = ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM")
GIT_EXECUTABLE_UNAVAILABLE = "git_executable_unavailable"
GIT_PROCESS_SPAWN_FAILED = "git_process_spawn_failed"


class GitExecutionError(ValueError):
    """Stable failure boundary for resolving or spawning the Git executable."""

    def __init__(self, code: str, *, reason: str) -> None:
        super().__init__(code)
        self.code = code
        self.reason = reason


def git_executable(environment: Mapping[str, str]) -> str:
    """Resolve one absolute Git executable from the exact execution environment."""
    executable = shutil.which("git", path=environment.get("PATH"))
    if executable is None:
        raise GitExecutionError(
            GIT_EXECUTABLE_UNAVAILABLE,
            reason="not_found_on_effective_path",
        )
    resolved = Path(executable).resolve()
    if not resolved.is_file():
        raise GitExecutionError(
            GIT_EXECUTABLE_UNAVAILABLE,
            reason="resolved_executable_invalid",
        )
    return resolved.as_posix()


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
        else {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
            and not (key.startswith("ETHOS_") and key.endswith("_TRANSITION"))
        }
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
    return _execute(
        root,
        (git_executable(effective_env), *args),
        text=text,
        check=check,
        env=effective_env,
        stdin=stdin,
    )


def _execute(
    root: Path,
    command: tuple[str, ...],
    *,
    text: bool,
    check: bool,
    env: Mapping[str, str],
    stdin: str | bytes | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[Any]:
    if not root.is_dir():
        raise GitExecutionError(
            GIT_PROCESS_SPAWN_FAILED,
            reason="working_directory_unavailable",
        )
    try:
        return subprocess.run(
            command,
            cwd=root,
            check=check,
            text=text,
            capture_output=True,
            env=env,
            input=stdin,
            timeout=timeout,
            shell=False,
        )
    except OSError as error:
        raise GitExecutionError(
            GIT_PROCESS_SPAWN_FAILED,
            reason="process_creation_failed",
        ) from error


def run_command(
    root: Path,
    command: tuple[str, ...],
    *,
    text: bool = True,
    capture_output: bool = True,
    check: bool = False,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[Any]:
    """Run one exact argv command without a shell or inherited Git overrides."""
    if not capture_output:
        message = "command_capture_output_required"
        raise ValueError(message)
    effective_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    effective_env.update({"PATH": os.environ.get("PATH", os.defpath), **(env or {})})
    return _execute(
        root,
        command,
        text=text,
        check=check,
        timeout=timeout,
        env=effective_env,
    )


def run_network_git(
    root: Path,
    *args: str,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run network Git with effective credential configuration but no ref overlays.

    Remote publication needs the user's effective credential helpers, SSH
    transport, and explicitly selected global/system config.  It must not inherit
    repository/ref/index overrides or command-line ``GIT_CONFIG_COUNT`` entries
    that could redirect the exact effect away from ``root``.
    """
    effective_env = dict(os.environ)
    for key in tuple(effective_env):
        if key in {
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_NAMESPACE",
            "GIT_CONFIG_COUNT",
        } or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            effective_env.pop(key, None)
    effective_env.update(
        {
            "LC_ALL": "C",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return _execute(
        root,
        (git_executable(effective_env), *args),
        text=True,
        check=check,
        env=effective_env,
        timeout=timeout,
    )


def effective_git_config_value(root: Path, name: str) -> str:
    """Read one effective Git config value without inheriting command overlays."""
    effective_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    effective_env.update(
        {key: os.environ[key] for key in _GIT_CONFIG_SOURCE_ENV if key in os.environ}
    )
    effective_env.update({"LC_ALL": "C", "GIT_NO_REPLACE_OBJECTS": "1"})
    completed = _execute(
        root,
        (git_executable(effective_env), "config", "--get", name),
        text=True,
        check=False,
        env=effective_env,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def repository_root(root: Path) -> Path:
    """Return the resolved Git worktree root for ``root``."""
    return Path(git_stdout_checked(root, "rev-parse", "--show-toplevel")).resolve()


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` reaches ``descendant`` in Git history."""
    return (
        run_git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode
        == 0
    )


def current_branch(root: Path) -> str:
    """Return the current branch, or an empty string when HEAD is detached."""
    return git_stdout(root, "branch", "--show-current")


def branch_ref_is_valid(root: Path, branch: str) -> bool:
    """Return whether Git recognizes ``branch`` as a complete branch name."""
    return git_stdout(root, "check-ref-format", "--branch", branch) == branch


def current_head(root: Path) -> str:
    """Return the current HEAD sha, or 'untracked' if not a resolvable ref."""
    return current_tracked_head(root) or "untracked"


def current_tracked_head(root: Path) -> str:
    """Return the current HEAD sha, or '' when untracked."""
    return git_stdout(root, "rev-parse", "HEAD")


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


def object_format(root: Path) -> str:
    """Return the repository object format reported by Git."""
    completed = run_git(root, "rev-parse", "--show-object-format", check=False)
    value = completed.stdout.strip() if completed.returncode == 0 else ""
    return value if value in {"sha1", "sha256"} else ""


def zero_oid(root: Path) -> str:
    """Return the null object ID at the repository's native hash width."""
    widths = {"sha1": 40, "sha256": 64}
    width = widths.get(object_format(root))
    if width is None:
        message = "git_object_format_unavailable"
        raise ValueError(message)
    return "0" * width


def git_stdout_checked(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stdout, raising on failure."""
    completed = run_git(root, *args)
    return completed.stdout.rstrip("\n")


def git_stdout(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stripped stdout, or '' on failure."""
    completed = run_git(root, *args, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def ref_progress(root: Path, ref: str, *, observed_at: datetime) -> dict[str, object]:
    """Project recent ref progress from Git's native reflog."""
    output = git_stdout(root, "reflog", "show", "--date=unix", "--format=%H%x00%gD", ref)
    entries: list[tuple[str, int]] = []
    for line in output.splitlines():
        head, _, selector = line.partition("\0")
        timestamp = selector.removeprefix(f"{ref}@{{").removesuffix("}")
        if head and timestamp.isdigit():
            entries.append((head, int(timestamp)))
    timestamps = [
        timestamp for (new, timestamp), (old, _) in pairwise(entries) if is_ancestor(root, old, new)
    ]
    if not timestamps:
        return {
            "observation": "git_reflog",
            "ref": ref,
            "advance_count": 0,
            "interval_seconds": None,
            "latest_interval_seconds": None,
            "latest_advance_age_seconds": None,
            "advances_per_hour": None,
        }
    interval = max(timestamps) - min(timestamps)
    latest_interval = timestamps[0] - timestamps[1] if len(timestamps) > 1 else None
    return {
        "observation": "git_reflog",
        "ref": ref,
        "advance_count": len(timestamps),
        "interval_seconds": interval,
        "latest_interval_seconds": latest_interval,
        "latest_advance_age_seconds": max(0, int(observed_at.timestamp()) - max(timestamps)),
        "advances_per_hour": len(timestamps) * 3600 / interval if interval else 0.0,
    }


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
    completed = run_git(
        root,
        "show",
        f"{ref}:{path}",
        check=False,
        env=environment,
        text=False,
    )
    return completed.stdout if completed.returncode == 0 else b""


def _exact_rename_pairs(root: Path, old_ref: str, new_ref: str) -> tuple[tuple[str, str], ...]:
    """Return every exact rename pair on one Git edge, or no pairs if malformed."""
    completed = run_git(
        root,
        "diff",
        "--no-ext-diff",
        "--name-status",
        "-z",
        "--find-renames=100%",
        "--find-copies=100%",
        "--find-copies-harder",
        "--diff-filter=RC",
        old_ref,
        new_ref,
        check=False,
        text=False,
        observation=True,
    )
    if completed.returncode != 0:
        return ()
    fields = completed.stdout.split(b"\0")
    pairs: list[tuple[str, str]] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        if status not in {b"R100", b"C100"} or index + 2 > len(fields):
            return ()
        paths = fields[index : index + 2]
        index += 2
        try:
            pairs.append((paths[0].decode(), paths[1].decode()))
        except UnicodeDecodeError:
            return ()
    return tuple(pairs)


def exact_rename_target(root: Path, old_ref: str, new_ref: str, source: str) -> str:
    """Return the sole target of one exact Git rename from ``source``."""
    targets = tuple(
        target
        for previous, target in _exact_rename_pairs(root, old_ref, new_ref)
        if previous == source
    )
    return targets[0] if len(targets) == 1 else ""


def exact_rename_source(root: Path, old_ref: str, new_ref: str, target: str) -> str:
    """Return the sole source of one exact Git rename to ``target``."""
    sources = tuple(
        previous
        for previous, current in _exact_rename_pairs(root, old_ref, new_ref)
        if current == target
    )
    return sources[0] if len(sources) == 1 else ""


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


def publication_remote_syncs(root: Path, branch: str, remotes: dict[str, str]) -> dict[str, object]:
    """Project declared peer branches without granting any peer authority."""
    records: dict[str, dict[str, object]] = {}
    configured = set(git_stdout(root, "remote").splitlines())
    for peer_id, remote in remotes.items():
        if remote not in configured:
            continue
        records[peer_id] = remote_tracking_sync(root, branch, remote)
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
    return bool(common := git_common_dir(left)) and common == git_common_dir(right)


def git_files(root: Path, *patterns: str) -> list[str]:
    """Return tracked files matching the given pathspec patterns."""
    completed = run_git(root, "ls-files", *patterns, check=False)
    return (
        [line for line in completed.stdout.splitlines() if line]
        if completed.returncode == 0
        else []
    )


def remote_availability(
    root: Path, remote: str = "origin", *, timeout_seconds: float = 3.0
) -> dict[str, object]:
    """Probe whether a configured Git remote is reachable without mutating state."""
    result = remote_availability_not_probed(root, remote)
    if result["state"] == "unconfigured":
        return result
    try:
        completed = run_network_git(
            root,
            "ls-remote",
            "--exit-code",
            remote,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return result | {
            "state": "unavailable",
            "reason": "timeout",
            "stderr": str(exc),
            "advisory_gaps": [f"remote_unavailable:{remote}"],
        }
    if completed.returncode == 0:
        return result | {
            "state": "available",
            "available": True,
            "advisory_gaps": [],
        }
    return result | {
        "state": "unavailable",
        "reason": "ls_remote_failed",
        "exit_code": completed.returncode,
        "stderr": completed.stderr.strip(),
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

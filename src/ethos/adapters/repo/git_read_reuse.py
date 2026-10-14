"""Reuse Git reads whose answers are fixed by object names or checkout identity.

A commit, tree or blob name is a content address, so a successful read of a
named object cannot change. The Git directory, common directory, object format
and Git paths other than hooks are fixed by the checkout's Git entry; the hooks
path follows core.hooksPath and the top level follows core.worktree, so both
always run. Each answer is keyed by that entry's identity, the exact argv, the
output mode and the configuration overlay. A linked checkout's Git file is
identified by its inode, size and modification time. A Git directory is
identified by its inode and by its object directory's info entry, which a new
repository creates afresh, so a repository recreated at the same path is not
answered from the former one even where the file system recycles inode
numbers. Reads with an environment override or input always run, and failures
are never reused: a missing object is observed again.
"""

from __future__ import annotations

import re
import stat
import subprocess
import threading
from collections import OrderedDict
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

_OBJECT_NAME = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_CAPACITY = 4096
_LOCK = threading.Lock()
_ANSWERS: OrderedDict[tuple[object, ...], subprocess.CompletedProcess[Any]] = OrderedDict()


def _named(value: str) -> bool:
    return _OBJECT_NAME.fullmatch(value) is not None


def fixed_answer(args: tuple[str, ...]) -> bool:
    """Return whether one read-only Git query has a single answer for its stated names."""
    match args:
        case ("version",) | (
            "rev-parse",
            "--git-common-dir" | "--absolute-git-dir" | "--show-object-format",
        ):
            fixed = True
        case ("rev-parse", "--git-path", path) | (
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            path,
        ):
            fixed = path.split("/", 1)[0] != "hooks"
        case ("show", spec):
            name, separator, _path = spec.partition(":")
            fixed = bool(separator) and _named(name)
        case ("rev-parse", spec):
            fixed = spec.endswith("^{tree}") and _named(spec.removesuffix("^{tree}"))
        case ("cat-file", "commit" | "tree" | "blob" | "tag", name):
            fixed = _named(name)
        case ("merge-base", "--is-ancestor", ancestor, descendant):
            fixed = _named(ancestor) and _named(descendant)
        case ("ls-tree", *options, name):
            fixed = all(option.startswith("-") for option in options) and _named(name)
        case _:
            fixed = False
    return fixed


def answer_key(
    root: Path,
    command: tuple[str, ...],
    *,
    text: bool,
    observation: bool,
    overlay: tuple[tuple[str, str], ...],
) -> tuple[object, ...] | None:
    """Key one fixed-answer read by its checkout identity, or None when it must run."""
    if not fixed_answer(command[1:]):
        return None
    identity = _checkout_identity(root / ".git")
    if identity is None:
        return None
    return (root.resolve().as_posix(), identity, command, text, observation, overlay)


def _checkout_identity(git: Path) -> tuple[int, ...] | None:
    """Identify one checkout's Git file or directory; links and incomplete entries have none."""
    try:
        entry = git.lstat()
        info = (git / "objects" / "info").lstat() if stat.S_ISDIR(entry.st_mode) else None
    except OSError:
        return None
    if info is not None:
        return (entry.st_dev, entry.st_ino, info.st_ino, info.st_mtime_ns)
    if stat.S_ISREG(entry.st_mode):
        return (entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns)
    return None


def reused_answer(key: tuple[object, ...]) -> subprocess.CompletedProcess[Any] | None:
    """Return an earlier successful answer for the same fixed read, or None."""
    with _LOCK:
        answer = _ANSWERS.get(key)
        if answer is None:
            return None
        _ANSWERS.move_to_end(key)
    return subprocess.CompletedProcess(answer.args, answer.returncode, answer.stdout, answer.stderr)


def remember_answer(key: tuple[object, ...], completed: subprocess.CompletedProcess[Any]) -> None:
    """Keep one successful answer, evicting the least recently used beyond capacity."""
    if completed.returncode != 0:
        return
    with _LOCK:
        _ANSWERS[key] = completed
        _ANSWERS.move_to_end(key)
        while len(_ANSWERS) > _CAPACITY:
            _ANSWERS.popitem(last=False)

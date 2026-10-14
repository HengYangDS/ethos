"""Reuse Git reads whose answers are fixed by object names or checkout identity.

A commit, tree or blob name is a content address, so a successful read of a
named object cannot change. The common directory is fixed by the checkout's Git
entry. Each answer is keyed by that entry's identity, the exact argv, the output
mode and the configuration overlay, so a repository recreated at the same path
is never answered from the former one. Reads with an environment override or
input always run, and failures are never reused: a missing object is observed
again.
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
        case ("version",) | ("rev-parse", "--git-common-dir"):
            fixed = True
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
    try:
        entry = (root / ".git").lstat()
    except OSError:
        return None
    # A Git directory keeps its inode; a linked checkout's Git file may be rewritten in place.
    identity = (
        (entry.st_dev, entry.st_ino)
        if stat.S_ISDIR(entry.st_mode)
        else (entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns)
    )
    return (root.resolve().as_posix(), identity, command, text, observation, overlay)


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

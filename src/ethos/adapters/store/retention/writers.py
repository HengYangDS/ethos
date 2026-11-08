"""Find the running processes that execute one of this repository's other ETHOS interpreters.

A batch of the record retirement apply defers while such a process runs, since a writer without the
mtime refresh can adopt a record the apply is about to delete. Only the path that begins a command
counts, and the path after it only when that first path is a shell or a Python interpreter, so a
shell or editor that merely names an environment does not defer.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.contracts.digest import is_sha256_hex

if TYPE_CHECKING:
    from collections.abc import Iterable

_LAUNCHERS = re.compile(r"(?:ba|z|da|k|fi)?sh|python[0-9.]*(?:\.exe)?", re.IGNORECASE)
_ENTRIES = re.compile(r"ethos(?:\.exe)?|python[0-9.]*(?:\.exe)?", re.IGNORECASE)


def _leading_path(text: str) -> tuple[Path, str] | None:
    """Return the existing absolute path that begins `text` and the rest; names may hold spaces."""
    text = text.replace("\\", "/")
    match = re.match(r"(?:[A-Za-z]:)?/", text)
    if match is None:
        return None
    found: tuple[Path, str] | None = None
    for end in [m.start() for m in re.finditer(r" ", text)] + [len(text)]:
        candidate = Path(text[:end])
        if candidate.is_file() or candidate.is_symlink():
            found = (candidate, text[end:].lstrip(" "))
    return found


def _owner(path: Path, roots: Iterable[Path]) -> Path | None:
    """Return the writer root that holds an entry point, resolving only its directory."""
    if not _ENTRIES.fullmatch(path.name):
        return None
    try:
        directory = path.parent.resolve(strict=True)
    except OSError:
        return None
    return next((root for root in roots if directory.is_relative_to(root)), None)


def running_writers(commands: str, roots: Iterable[Path]) -> tuple[Path, ...]:
    """Return each writer root that a running command starts from, in order of first sight."""
    roots = tuple(roots)
    found: dict[Path, None] = {}
    for line in commands.splitlines():
        first = _leading_path(line.strip())
        if first is None:
            continue
        executable, rest = first
        owner = _owner(executable, roots)
        if owner is None and _LAUNCHERS.fullmatch(executable.name):
            second = _leading_path(rest)
            owner = _owner(second[0], roots) if second else None
        if owner is not None:
            found.setdefault(owner)
    return tuple(found)


def writer_roots(repo: Path, *, selected: Path | None) -> tuple[Path, ...]:
    """Return the directories of this repository's ETHOS interpreters other than the selected one.

    They are its other runtime generations, the host installations whose consumers name its Git
    common directory or cannot be read, and the environments of its worktrees that install `ethos`.
    """
    common = Path(git_common_dir(repo)).resolve()
    roots: list[Path] = []
    generations = common / "ethos" / "runtime"
    if generations.is_dir():
        roots.extend(
            path.resolve()
            for path in sorted(generations.iterdir())
            if is_sha256_hex(path.name) and path.is_dir()
        )
    host = host_store_root()
    installations = host / "installations" if host is not None else None
    if installations is not None and installations.is_dir():
        for path in sorted(installations.iterdir()):
            consumers = installation_consumers(path) if path.is_dir() else {}
            if consumers is None or any(item in {None, common} for item in consumers.values()):
                roots.append(path.resolve())
    roots.extend(
        environment.resolve()
        for worktree in _worktrees(repo)
        for environment in (worktree / ".venv",)
        if (environment / "bin/ethos").is_file() or (environment / "Scripts/ethos.exe").is_file()
    )
    excluded = selected.resolve() if selected is not None else None
    return tuple(root for root in dict.fromkeys(roots) if root != excluded)


def _worktrees(repo: Path) -> tuple[Path, ...]:
    listed = run_git(repo, "worktree", "list", "--porcelain", "-z", check=False)
    if listed.returncode:
        message = "record_retirement_worktrees_unreadable"
        raise ValueError(message)
    return tuple(
        Path(field.removeprefix("worktree "))
        for field in listed.stdout.split("\0")
        if field.startswith("worktree ")
    )

"""Reclaim immutable generations from fresh operational dependencies."""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path
from typing import Literal
from typing import NotRequired
from typing import TypedDict

from filelock import Timeout

from ethos.adapters.process import process_listing_command
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.runtime.selection import runtime_selection_transaction


class GenerationCleanup(TypedDict):
    """Observed reclamation effects, separate from successful runtime activation."""

    state: Literal["complete", "deferred"]
    checked: list[str]
    removed: list[str]
    retained: list[str]
    deferred: NotRequired[list[str]]
    error: NotRequired[str]


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _directory_identity(path: Path) -> tuple[int, int, int, int]:
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or is_junction(path):
        _fail("hook_runtime_generation_root_invalid")
    return metadata.st_dev, metadata.st_ino, metadata.st_mtime_ns, metadata.st_ctime_ns


def _generations(common: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for root in (common / "ethos/hooks", common / "ethos/runtime"):
        if not root.exists() and not root.is_symlink():
            continue
        _directory_identity(root)
        candidates.extend(path for path in root.iterdir() if _digest(path.name))
    candidates.extend(
        path
        for path in common.iterdir()
        if path.name == "ethos-hooks"
        or (path.name.startswith("ethos-hooks-") and _digest(path.name[len("ethos-hooks-") :]))
    )
    return tuple(sorted(candidates))


def _digest(value: str) -> bool:
    return len(value) == 64 and not set(value) - set("0123456789abcdef")


def process_commands(root: Path, *, platform_name: str | None = None) -> str:
    """Observe native running commands within a bounded, fail-closed boundary."""
    command = process_listing_command(platform_name=platform_name)
    completed = run_command(
        root, command, timeout=10, remove_env=("PSModulePath",), remove_env_prefixes=("GIT_",)
    )
    if completed.returncode or completed.stderr:
        _fail("hook_runtime_consumers_unknown")
    return completed.stdout


def _interpreter_bindings(worktree: Path) -> tuple[str, ...]:
    environment = worktree / ".venv"
    if not environment.exists() and not environment.is_symlink():
        return ()
    if not environment.is_dir() or is_junction(environment):
        _fail("hook_runtime_consumers_unknown")
    references = [environment.resolve(strict=True).as_posix()]
    metadata = environment / "pyvenv.cfg"
    if metadata.exists() or metadata.is_symlink():
        if metadata.is_symlink() or not metadata.is_file():
            _fail("hook_runtime_consumers_unknown")
        references.extend(
            value.strip()
            for line in metadata.read_text(encoding="utf-8").splitlines()
            if (parts := line.partition("="))[1]
            and parts[0].strip().casefold() in {"home", "executable"}
            for value in (parts[2],)
        )
    for relative in ("bin/python", "Scripts/python.exe"):
        executable = environment / relative
        if executable.exists() or executable.is_symlink():
            references.append(executable.resolve(strict=True).as_posix())
    return tuple(references)


def _operational_references(root: Path) -> str:
    references = [process_commands(root)]
    result = run_git(root, "worktree", "list", "--porcelain", "-z", check=False)
    if result.returncode:
        _fail("hook_runtime_worktrees_unreadable")
    worktrees = tuple(
        Path(field[len("worktree ") :])
        for field in result.stdout.split("\0")
        if field.startswith("worktree ")
    )
    if not worktrees or any(not path.is_dir() for path in worktrees):
        _fail("hook_runtime_worktrees_unreadable")
    for worktree in worktrees:
        config = run_git(worktree, "config", "--null", "--get-regexp", ".*", check=False)
        if config.returncode not in {0, 1}:
            _fail("hook_runtime_consumers_unknown")
        references.append(config.stdout)
        references.extend(_interpreter_bindings(worktree))
    return "\n".join(references).replace("\\", "/")


def _reference_paths(references: str) -> frozenset[Path]:
    """Resolve observable absolute paths before comparing resource ancestry.

    Native command listings may omit quoting around spaces. Preserve each
    possible path boundary conservatively; digest spelling is not identity.
    """
    paths: set[Path] = set()
    for field in re.split(r"[\n\x00]", references):
        for start in re.finditer(r"(?<![\w./:-])(?:[A-Za-z]:)?/", field):
            paths.update(_native_path_prefixes(Path(start.group()), field[start.end() :]))
    return frozenset(paths)


def _native_path_prefixes(anchor: Path, tail: str) -> set[Path]:
    """Stop a possible path at its first absent directory, not arbitrary punctuation."""
    paths: set[Path] = set()
    current = anchor
    while tail:
        component, separator, rest = tail.partition("/")
        for end in re.finditer(r"[\s'\";|&)]|$", component):
            part = component[: end.start()]
            candidate = current / part
            if part and (candidate.exists() or candidate.is_symlink()):
                paths.add(candidate.resolve(strict=True))
        full = current / component
        if not separator or not full.is_dir():
            break
        current = full.resolve(strict=True)
        paths.add(current)
        tail = rest
    return paths


def _require_identity(path: Path, expected: tuple[int, int, int, int]) -> None:
    """Reject a vanished or replaced directory without admitting its new occupant."""
    try:
        current = _directory_identity(path)
    except FileNotFoundError as failure:
        message = "hook_runtime_generation_identity_stale"
        raise ValueError(message) from failure
    if current != expected:
        _fail("hook_runtime_generation_identity_stale")


def _require_identities(
    paths: set[Path], identities: dict[Path, tuple[int, int, int, int]]
) -> None:
    """Require every retained or selected resource to match its observed identity."""
    for path in paths:
        expected = identities.get(path)
        if expected is None:
            _fail("hook_runtime_generation_identity_stale")
        else:
            _require_identity(path, expected)


def retire_generations(root: Path, *, hooks: Path, runtime: Path) -> GenerationCleanup:
    """Retire only currently unused generations, conserving partial outcomes."""
    selected = {hooks, runtime}
    identities: dict[Path, tuple[int, int, int, int]] = {}
    candidates: tuple[Path, ...] = ()
    removed: list[Path] = []
    retained = set(selected)
    error = ""
    try:
        common = Path(git_common_dir(root)).resolve()
        expected = runtime_selection_bytes(common, runtime)
        with runtime_selection_transaction(common, expected_current=expected):
            candidates = _generations(common)
            identities = {
                path: _directory_identity(path) for path in sorted({*candidates, *selected})
            }
            _require_identities(selected, identities)
        for path, identity in identities.items():
            if path in selected:
                continue
            with runtime_selection_transaction(common, expected_current=expected):
                _require_identities(selected, identities)
                references = _reference_paths(_operational_references(root))
                used = {
                    candidate
                    for candidate in identities
                    if any(reference.is_relative_to(candidate) for reference in references)
                }
                retained.update(candidate for candidate in used if candidate not in removed)
                retained.discard(path)
                _require_identity(path, identity)
                if path in used:
                    retained.add(path)
                    continue
                try:
                    remove_generated_tree(path)
                finally:
                    if not path.exists() and not path.is_symlink():
                        removed.append(path)
                if path not in removed:
                    _fail("hook_runtime_generation_cleanup_failed")
        with runtime_selection_transaction(common, expected_current=expected):
            _require_identities(retained, identities)
    except Timeout:
        error = "hook_runtime_selection_busy"
    except (OSError, RuntimeError, UnicodeError, ValueError, subprocess.TimeoutExpired) as failure:
        error = str(failure) or type(failure).__name__
    deferred = set(candidates) - set(removed) - retained
    result: GenerationCleanup = {
        "state": "deferred" if error else "complete",
        "checked": [str(path) for path in candidates],
        "removed": [str(path) for path in removed],
        "retained": [str(path) for path in sorted(retained)],
    }
    if error:
        result.update(deferred=[str(path) for path in sorted(deferred)], error=error)
    return result

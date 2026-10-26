"""Reclaim immutable generations from fresh operational dependencies."""

from __future__ import annotations

import errno
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
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.binding import load_hook_contract
from ethos.adapters.repo.hook.binding import require_hook_projection
from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.adapters.repo.runtime.manifest import load_runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.runtime.selection import runtime_selection_transaction
from ethos.repository.release.admission import accepted_release_identities


class GenerationCleanup(TypedDict):
    """Observed reclamation effects, separate from successful runtime activation."""

    state: Literal["complete", "deferred"]
    checked: list[str]
    removed: list[str]
    retained: list[str]
    unproven_removals: list[str]
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


def operational_reference_paths(root: Path) -> frozenset[Path]:
    """Return the paths that running commands and this repository's bindings refer to."""
    return _reference_paths(_operational_references(root))


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
    """Preserve every real prefix, ignoring suffixes the native filesystem rejects."""
    paths: set[Path] = set()
    current = anchor
    while tail:
        component, separator, rest = tail.partition("/")
        for end in re.finditer(r"[\s'\";|&)]|$", component):
            part = component[: end.start()]
            if part and (resolved := _native_path(current / part)):
                paths.add(resolved)
        if not separator or not (resolved := _native_path(current / component, directory=True)):
            break
        current = resolved
        paths.add(current)
        tail = rest
    return paths


def _native_path(path: Path, *, directory: bool = False) -> Path | None:
    """Resolve an observed path; an invalid suffix or one deleted since its check is absent."""
    try:
        if path.is_dir() if directory else path.exists() or path.is_symlink():
            return path.resolve(strict=True)
    except OSError as failure:
        # A path deleted after its check is an observed absence; a dangling link stays unknown.
        vanished = isinstance(failure, FileNotFoundError) and not path.is_symlink()
        if not vanished and failure.errno not in {errno.ENAMETOOLONG, errno.EINVAL}:
            raise
    return None


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


def _reclamation_unproven(path: Path, common: Path) -> bool:
    """A digest-shaped local directory alone proves neither ownership nor non-use."""
    if path.parent == common / "ethos/hooks":
        contract = load_hook_contract()
        if path.name != contract["generation_digest"]:
            return True
        try:
            require_hook_projection(path, contract)
        except ValueError:
            return True
        return False
    if path.parent == common / "ethos/runtime":
        try:
            manifest = load_runtime_manifest_bytes((path / "manifest.json").read_bytes())
            if manifest.repository_private:
                return not require_selected_runtime(path).repository_private
        except (OSError, TypeError, UnicodeError, ValueError):
            pass
    return True


def _generation_wheels(common: Path, generations: set[Path]) -> frozenset[str] | None:
    """Name supply wheels still bound by retained runtime generation manifests."""
    wheels: set[str] = set()
    for path in generations:
        if path.parent != common / "ethos/runtime":
            continue
        try:
            manifest = load_runtime_manifest_bytes((path / "manifest.json").read_bytes())
        except (OSError, TypeError, UnicodeError, ValueError):
            return None
        wheels.add(manifest.wheel_sha256)
    return frozenset(wheels)


def _retire_packages(
    root: Path,
    common: Path,
    *,
    checked: list[Path],
    retained: set[Path],
    removed: list[Path],
    unproven: set[Path],
) -> None:
    """Reclaim wheels that no retained generation, accepted release or live reference names."""
    store = common / "ethos/packages"
    if not store.exists() and not store.is_symlink():
        return
    _directory_identity(store)
    candidates = tuple(sorted(path for path in store.iterdir() if _digest(path.name)))
    checked.extend(candidates)
    identities = {path: _directory_identity(path) for path in candidates}
    wheels = _generation_wheels(common, retained)
    if wheels is None:
        retained.update(candidates)
        unproven.update(candidates)
        return
    unnamed = [path for path in candidates if path.name not in wheels]
    if unnamed:
        _selected, attestations = read_attestation_set(root)
        released = {release.wheel_sha256 for release in accepted_release_identities(attestations)}
        unnamed = [path for path in unnamed if path.name not in released]
    retained.update(path for path in candidates if path not in unnamed)
    if not unnamed:
        return
    references = _reference_paths(_operational_references(root))
    for path in unnamed:
        if any(reference.is_relative_to(path) for reference in references):
            retained.add(path)
            continue
        _require_identity(path, identities[path])
        try:
            remove_generated_tree(path)
        finally:
            if not path.exists() and not path.is_symlink():
                removed.append(path)
        if path not in removed:
            _fail("hook_runtime_package_cleanup_failed")


def retire_generations(
    root: Path, *, hooks: Path, runtime: Path, unnamed_predecessor: bool = False
) -> GenerationCleanup:
    """Retire only currently unused generations, conserving partial outcomes.

    An unnamed predecessor keeps every runtime generation: one of them may be the only rollback.
    """
    selected = {hooks, runtime}
    identities: dict[Path, tuple[int, int, int, int]] = {}
    candidates: tuple[Path, ...] = ()
    packages: list[Path] = []
    removed: list[Path] = []
    retained = set(selected)
    unproven = set[Path]()
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
                if (
                    unnamed_predecessor and path.parent == common / "ethos/runtime"
                ) or _reclamation_unproven(path, common):
                    # A repository-local runtime may be selected by another Git common-dir.
                    retained.add(path)
                    unproven.add(path)
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
            _retire_packages(
                root,
                common,
                checked=packages,
                retained=retained,
                removed=removed,
                unproven=unproven,
            )
    except Timeout:
        error = "hook_runtime_selection_busy"
    except (OSError, RuntimeError, UnicodeError, ValueError, subprocess.TimeoutExpired) as failure:
        error = str(failure) or type(failure).__name__
    return _cleanup_result(
        (*candidates, *packages), removed=removed, retained=retained, unproven=unproven, error=error
    )


def _cleanup_result(
    checked: tuple[Path, ...],
    *,
    removed: list[Path],
    retained: set[Path],
    unproven: set[Path],
    error: str,
) -> GenerationCleanup:
    """Project observed reclamation effects, keeping deferred work explicit."""
    result: GenerationCleanup = {
        "state": "deferred" if error else "complete",
        "checked": [str(path) for path in checked],
        "removed": [str(path) for path in removed],
        "retained": [str(path) for path in sorted(retained)],
        "unproven_removals": [str(path) for path in sorted(unproven)],
    }
    if error:
        deferred = set(checked) - set(removed) - retained
        result.update(deferred=[str(path) for path in sorted(deferred)], error=error)
    return result

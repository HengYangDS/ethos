"""Derive the Python version a repository's code must be judged against.

The product's isolated Ruff ignores a repository's own Ruff policy so that a candidate cannot
weaken the common rule floor, yet the Python version the repository supports remains its own
accepted fact rather than the checker's default or ETHOS's interpreter. The target is read from
the exact committed tree in Ruff's own order: the target-version of the accepted Ruff
configuration, either the paradigm carrier or Ruff's root discovery, following extend inside
the repository; otherwise the lower bound of requires-python. Missing, malformed or conflicting
declarations, and nested declarations that give checked code another target, are gaps.
"""

from __future__ import annotations

import posixpath
import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import NoReturn

from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet

from ethos.adapters.repo.git import run_git
from ethos.contracts.paradigm.declaration import load_repository_paradigm

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import ToolCarrier

UNDECLARED = "python_target_undeclared"
INVALID = "python_target_invalid"
CONFLICT = "python_target_conflict"
DIVERGENT = "python_target_divergent"
_MANIFEST = "pyproject.toml"
_TARGET = re.compile(r"py3([0-9]{1,2})")


@dataclass(frozen=True)
class PythonTarget:
    """The declared Ruff target and the committed files that declare it."""

    version: str
    basis: str
    files: tuple[str, ...]

    def evidence(self) -> dict[str, object]:
        """Return the JSON form recorded beside the same-attempt checker evidence."""
        return {"version": self.version, "basis": self.basis, "files": list(self.files)}


class _Tree:
    """Read tracked TOML declarations once from one exact committed tree."""

    def __init__(self, root: Path, tree: str) -> None:
        self.root = root
        self.tree = tree
        listing = run_git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            tree,
            check=False,
            text=False,
            observation=True,
        )
        if listing.returncode:
            _invalid()
        # A path that is not UTF-8 cannot name a declaration, so it is kept only as listed.
        names = listing.stdout.decode(errors="surrogateescape").split("\0")
        self.paths = frozenset(path for path in names if path)
        self._documents: dict[str, dict[str, object]] = {}

    def document(self, path: str) -> dict[str, object]:
        if path not in self._documents:
            blob = run_git(
                self.root,
                "cat-file",
                "blob",
                f"{self.tree}:{path}",
                check=False,
                text=False,
                observation=True,
            )
            if blob.returncode:
                _invalid()
            try:
                self._documents[path] = tomllib.loads(blob.stdout.decode())
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
                _invalid(error)
        return self._documents[path]


def compatibility_target(root: Path, tree: str, paths: tuple[str, ...]) -> PythonTarget:
    """Resolve the one declared target that governs every checked path."""
    committed = _Tree(root, tree)
    ruff = next(tool for tool in load_repository_paradigm().tool if tool.id == "ruff")
    target = _directory_target(committed, ruff, "")
    if target is None:
        raise ValueError(UNDECLARED)
    for directory in _governing_directories(committed, ruff, paths):
        nested = _directory_target(committed, ruff, directory)
        if nested is None or nested.version != target.version:
            raise ValueError(DIVERGENT)
    return target


def _directory_target(committed: _Tree, ruff: ToolCarrier, directory: str) -> PythonTarget | None:
    """Return the target one directory declares, or None when it declares none."""
    manifest = posixpath.join(directory, _MANIFEST)
    floor = _floor(committed.document(manifest)) if manifest in committed.paths else None
    explicit = [
        declared
        for path, settings in _configurations(committed, ruff, directory)
        if (declared := _chain(committed, ruff, path, settings)) is not None
    ]
    minors = {declared[0] for declared in explicit}
    if len(minors) > 1 or (floor is not None and any(minor > floor for minor in minors)):
        raise ValueError(CONFLICT)
    if explicit:
        minor, files = explicit[0]
        return PythonTarget(f"py3{minor}", "ruff-target-version", files)
    if floor is not None:
        return PythonTarget(f"py3{floor}", "requires-python", (manifest,))
    return None


def _configurations(
    committed: _Tree, ruff: ToolCarrier, directory: str
) -> list[tuple[str, dict[str, object]]]:
    """List the paradigm carrier at the root and the Ruff configuration Ruff itself discovers."""
    found = (
        [(ruff.carrier, committed.document(ruff.carrier))]
        if not directory and ruff.carrier in committed.paths
        else []
    )
    for name in ruff.root_names:
        path = posixpath.join(directory, name)
        if path in committed.paths:
            return [*found, (path, committed.document(path))]
    manifest = posixpath.join(directory, _MANIFEST)
    if manifest in committed.paths:
        settings = _manifest_settings(committed.document(manifest), ruff)
        if settings is not None:
            found.append((manifest, settings))
    return found


def _chain(
    committed: _Tree, ruff: ToolCarrier, path: str, settings: dict[str, object]
) -> tuple[int, tuple[str, ...]] | None:
    """Follow extend inside the repository to the first declared target-version."""
    files = [path]
    while (value := settings.get("target-version")) is None:
        extend = settings.get("extend")
        if extend is None:
            return None
        if not isinstance(extend, str) or extend.startswith(("/", "~")) or "$" in extend:
            _invalid()
        path = posixpath.normpath(posixpath.join(posixpath.dirname(path), extend))
        if path not in committed.paths or path in files:
            _invalid()
        files.append(path)
        document = committed.document(path)
        settings = (
            _manifest_settings(document, ruff) or {}
            if posixpath.basename(path) == _MANIFEST
            else document
        )
    match = _TARGET.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        _invalid()
    return int(match.group(1)), tuple(files)


def _manifest_settings(document: dict[str, object], ruff: ToolCarrier) -> dict[str, object] | None:
    """Return the Ruff table a manifest embeds, or None when it embeds none."""
    tool = document.get("tool", {})
    if not isinstance(tool, dict):
        _invalid()
    settings = next((tool[table] for table in ruff.manifest_tables if table in tool), None)
    if settings is not None and not isinstance(settings, dict):
        _invalid()
    return settings


def _floor(document: dict[str, object]) -> int | None:
    """Return the lowest Python 3 minor version requires-python admits, if it is bounded."""
    project = document.get("project", {})
    if not isinstance(project, dict):
        _invalid()
    declared = project.get("requires-python")
    if declared is None:
        return None
    if not isinstance(declared, str):
        _invalid()
    try:
        specifier = SpecifierSet(declared)
    except InvalidSpecifier as error:
        _invalid(error)
    if specifier.contains("0"):
        return None
    floor = next(
        (
            minor
            for minor in range(100)
            if any(specifier.contains(f"3.{minor}.{patch}") for patch in range(100))
        ),
        None,
    )
    if floor is None:
        _invalid()
    return floor


def _invalid(error: Exception | None = None) -> NoReturn:
    """End target resolution at a malformed or unresolvable declaration."""
    raise ValueError(INVALID) from error


def _governing_directories(
    committed: _Tree, ruff: ToolCarrier, paths: tuple[str, ...]
) -> list[str]:
    """Return nested directories whose own declarations govern a checked path."""
    ancestors = sorted(
        {
            "/".join(parts[:depth])
            for parts in (path.split("/") for path in paths)
            for depth in range(1, len(parts))
        }
    )
    return [
        directory
        for directory in ancestors
        if any(posixpath.join(directory, name) in committed.paths for name in ruff.root_names)
        or (
            posixpath.join(directory, _MANIFEST) in committed.paths
            and _declares(committed.document(posixpath.join(directory, _MANIFEST)), ruff)
        )
    ]


def _declares(document: dict[str, object], ruff: ToolCarrier) -> bool:
    """Report whether a nested manifest declares a Ruff policy or a supported version."""
    project = document.get("project", {})
    return _manifest_settings(document, ruff) is not None or (
        isinstance(project, dict) and "requires-python" in project
    )

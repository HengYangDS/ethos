"""Hold each declared repository path to the content it names at the current head."""

from __future__ import annotations

import posixpath
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.policy.references.carriers import REPOSITORY_PATH_FIELDS
from ethos.repository.policy.references.carriers import declaration_files
from ethos.repository.policy.rules.config import path_matches

if TYPE_CHECKING:
    from collections.abc import Iterable

_README = "README.md"
_GLOB = frozenset("*?[")


def content_directories(tracked: Iterable[str]) -> frozenset[str]:
    """Return every directory that holds a tracked file other than a README."""
    directories: set[str] = set()
    for path in tracked:
        if posixpath.basename(path) == _README:
            continue
        parent = posixpath.dirname(path)
        while parent and parent not in directories:
            directories.add(parent)
            parent = posixpath.dirname(parent)
    return frozenset(directories)


def dead_declared_paths(files: dict[str, str], tracked: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return each declared repository path, with its declaration, that names no content.

    A value names content when it is a tracked file, a directory that holds a tracked file
    other than a README, or a glob that matches such a file. An unobserved index names none.
    """
    if not tracked:
        return []
    names = frozenset(tracked)
    directories = content_directories(tracked)
    content = tuple(path for path in tracked if posixpath.basename(path) != _README)
    dead: set[tuple[str, str]] = set()
    for kind, fields in REPOSITORY_PATH_FIELDS.items():
        for source, text in declaration_files(files, kind).items():
            try:
                payload = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                continue
            for field in fields:
                for value in _field_values(payload, field.split(".")):
                    path = value.removeprefix("./")
                    if not _repository_relative(path):
                        continue
                    stripped = path.rstrip("/")
                    if _GLOB.isdisjoint(stripped):
                        held = stripped in names or stripped in directories
                    else:
                        held = any(path_matches(item, (path,)) for item in content)
                    if not held:
                        dead.add((value, source))
    return sorted(dead)


def _field_values(node: object, parts: list[str]) -> list[str]:
    """Read one dotted field through tables and arrays; `*` selects every key of a table."""
    if isinstance(node, list):
        return [value for item in node for value in _field_values(item, parts)]
    if not parts:
        return [node] if isinstance(node, str) else []
    if not isinstance(node, dict):
        return []
    head, rest = parts[0], parts[1:]
    children = list(node.values()) if head == "*" else [node[head]] if head in node else []
    return [value for child in children for value in _field_values(child, rest)]


def _repository_relative(path: str) -> bool:
    return bool(path.strip("/")) and not (
        path.startswith(("/", "../", "~", "$")) or "://" in path or "{" in path
    )

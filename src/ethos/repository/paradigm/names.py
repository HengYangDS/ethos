"""Repository-authored names of the repository paradigm.

Every tracked name is lowercase kebab-case unless an ecosystem or tool fixes it. A
dot-separated segment may be a BCP 47 language tag in its canonical case. Paths that the
repository's Git attributes mark vendored or generated are received, not authored, and
keep their names. A name that another obligation judges, through the root catalog, the
binding file set, the configuration plane or the decision record grammar, keeps that
obligation's single gap, so each name has one owner.
"""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING

from ethos.repository.paradigm.documents import is_decision_record
from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_WORDS = r"[a-z0-9]+(?:-[a-z0-9]+)*"
# A language, an optional script and an optional region, in the case RFC 5646 recommends.
_LANGUAGE_TAG = r"[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|[0-9]{3}))?"
_SEGMENT = rf"(?:{_WORDS}|{_LANGUAGE_TAG})"
_NAME = re.compile(rf"[._]?{_SEGMENT}(?:\.{_SEGMENT})*")
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[^a-z0-9]+")


def authored_name_gaps(
    paradigm: RepositoryParadigm,
    tracked: frozenset[str],
    received: frozenset[str] = frozenset(),
) -> Iterator[ParadigmGap]:
    """Report each authored file or directory name outside kebab-case once."""
    paths = sorted(
        path
        for path in tracked
        if not path.startswith(paradigm.immutable_roots) and path not in received
    )
    holders = _module_directories(paradigm, paths)
    admitted = _fixed_names(paradigm)
    judged: set[str] = set()
    for path in paths:
        parts = path.split("/")
        for depth, name in enumerate(parts):
            carrier = "/".join(parts[: depth + 1])
            if carrier in judged:
                continue
            judged.add(carrier)
            is_file = depth == len(parts) - 1
            if _owned_elsewhere(paradigm, parts, depth, is_file=is_file):
                continue
            if _conforms(
                paradigm, name, admitted, is_file=is_file, holds_modules=carrier in holders
            ):
                continue
            yield _gap(carrier)


def name_path_gaps(
    paradigm: RepositoryParadigm, path: str, *, received: bool = False
) -> Iterator[ParadigmGap]:
    """Judge a new file's own name; whether its directories hold modules is the report's."""
    parts = path.split("/")
    if (
        received
        or path.startswith(paradigm.immutable_roots)
        or _owned_elsewhere(paradigm, parts, len(parts) - 1, is_file=True)
    ):
        return
    if not _conforms(
        paradigm, parts[-1], _fixed_names(paradigm), is_file=True, holds_modules=False
    ):
        yield _gap(path)


def kebab_name(name: str) -> str:
    """Return a name's kebab-case form, keeping its leading marker and dotted suffixes."""
    marker = name[0] if name[0] in "._" and len(name) > 1 else ""
    segments = name.removeprefix(marker).split(".")
    return marker + ".".join(
        "-".join(
            word for word in _SEPARATORS.split(_WORD_BOUNDARY.sub("-", segment).lower()) if word
        )
        for segment in segments
    )


def _gap(carrier: str) -> ParadigmGap:
    directory, name = posixpath.split(carrier)
    renamed = posixpath.join(directory, kebab_name(name))
    return ParadigmGap(
        "authored-name",
        carrier,
        f"rename {carrier} to {renamed} and update its references, or mark it linguist-vendored "
        "or linguist-generated in .gitattributes if it is third-party or generated",
    )


def _fixed_names(paradigm: RepositoryParadigm) -> frozenset[str]:
    """Return the entry documents, catalogued tool names and tool-required basenames."""
    return frozenset(
        {
            *paradigm.root.entry_documents,
            *paradigm.names.tool_basenames,
            *(name for tool in paradigm.tool for name in tool.root_names),
            *(posixpath.basename(tool.carrier) for tool in paradigm.tool),
        }
    )


def _module_directories(paradigm: RepositoryParadigm, paths: Iterable[str]) -> frozenset[str]:
    """Return every directory that holds a module file, whose language fixes its name."""
    directories: set[str] = set()
    for path in paths:
        directory = posixpath.dirname(path) if path.endswith(paradigm.module_suffixes) else ""
        while directory and directory not in directories:
            directories.add(directory)
            directory = posixpath.dirname(directory)
    return frozenset(directories)


def _conforms(
    paradigm: RepositoryParadigm,
    name: str,
    admitted: frozenset[str],
    *,
    is_file: bool,
    holds_modules: bool,
) -> bool:
    if _NAME.fullmatch(name) or name in admitted:
        return True
    return name.endswith(paradigm.module_suffixes) if is_file else holds_modules


def _owned_elsewhere(
    paradigm: RepositoryParadigm, parts: list[str], depth: int, *, is_file: bool
) -> bool:
    """Return whether another obligation's grammar or catalog judges this name."""
    if is_file and is_decision_record(parts[depth]):
        return True
    if depth == 0:
        return is_file or parts[0].startswith(".")
    if parts[0] == paradigm.binding.root:
        return True
    plane = paradigm.configuration
    if parts[0] != plane.root:
        return False
    return depth == 1 or (
        parts[1] in plane.owner_groups and (depth == 2 or (depth == 3 and is_file))
    )

"""Repository-authored names of the repository paradigm.

Every tracked name is lowercase kebab-case unless an ecosystem or tool fixes it. A
dot-separated segment may be a BCP 47 language tag in its canonical case. Paths that the
repository's Git attributes mark vendored or generated are received, not authored, and
keep their names. A name that another obligation judges, through the root catalog, the
binding file set, the configuration plane or the decision record grammar, keeps that
obligation's single gap, so each name has one owner.

An upstream data contract can also fix an identifier that the repository must spell as a name
and that its own manifest repeats as a value. The profile's `identifier_sources` declare which
keys of which tracked manifests hold such identifiers and how their values are read. A name
outside kebab-case is admitted only when some declared manifest repeats it, wherever that
manifest lies, and each admission is recorded with it. A declared key that no matched manifest
carries, and a matched manifest that does not parse, are gaps.
"""

from __future__ import annotations

import json
import posixpath
import re
import tomllib
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.contracts.paradigm.declaration import binding_path
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.paradigm.documents import is_decision_record
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.policy.references.declared_paths import field_values
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterable
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm
    from ethos.repository.profile import IdentifierSource

_WORDS = r"[a-z0-9]+(?:-[a-z0-9]+)*"
# A language, an optional script and an optional region, in the case RFC 5646 recommends.
_LANGUAGE_TAG = r"[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|[0-9]{3}))?"
_SEGMENT = rf"(?:{_WORDS}|{_LANGUAGE_TAG})"
_NAME = re.compile(rf"[._]?{_SEGMENT}(?:\.{_SEGMENT})*")
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[^a-z0-9]+")
_SOURCE = "identifier-source"


class IdentifierNames(NamedTuple):
    """Each evidenced identifier's manifest, the declaration's gaps and the names admitted."""

    manifests: dict[str, str]
    gaps: list[ParadigmGap]
    admissions: list[dict[str, str]]

    def admits(self, carrier: str, *, is_file: bool) -> bool:
        """Admit and record a name, or a file's stem before its first dot, that a manifest holds."""
        name = posixpath.basename(carrier)
        manifest = self.manifests.get(name) or (is_file and self.manifests.get(name.split(".")[0]))
        if manifest:
            self.admissions.append({"name": name, "carrier": carrier, "manifest": manifest})
        return bool(manifest)


def identifier_names(root: Path, tracked: Iterable[str]) -> IdentifierNames:
    """Read the identifiers that the profile's sources declare from the tracked manifests.

    A declared key that no readable tracked manifest of its source carries, which includes a
    source that matches no tracked file, and a manifest that does not parse are gaps: a
    declaration without evidence admits nothing.
    """
    declaration = load_repository_profile(root).declaration
    names = IdentifierNames({}, [], [])
    for source in declaration.identifier_sources if declaration else ():
        absent = set(source.keys)
        for manifest in sorted(tracked):
            if repository_path_matches(manifest, source.manifests):
                _read(names, absent, root, manifest, source)
        place = f"{binding_path('profile')}:identifier_sources.{source.manifests}"
        repair = f"in a tracked manifest that {source.manifests} matches, or remove the key"
        names.gaps.extend(
            ParadigmGap(_SOURCE, f"{place}:{key}", f"declare {key} {repair}")
            for key in sorted(absent)
        )
    return names


def authored_name_gaps(
    paradigm: RepositoryParadigm,
    tracked: frozenset[str],
    received: frozenset[str] = frozenset(),
    identifiers: IdentifierNames | None = None,
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
            if not (
                _owned_elsewhere(paradigm, parts, depth, is_file=is_file)
                or _conforms(
                    paradigm, name, admitted, is_file=is_file, holds_modules=carrier in holders
                )
                or (identifiers and identifiers.admits(carrier, is_file=is_file))
            ):
                yield _gap(carrier)


def name_path_gaps(
    paradigm: RepositoryParadigm,
    path: str,
    *,
    received: bool = False,
    identifiers: Callable[[], IdentifierNames] | None = None,
) -> Iterator[ParadigmGap]:
    """Judge a new file's own name; whether its directories hold modules is the report's.

    The identifier evidence is read only for a name that would otherwise be refused.
    """
    parts = path.split("/")
    if (
        received
        or path.startswith(paradigm.immutable_roots)
        or _owned_elsewhere(paradigm, parts, len(parts) - 1, is_file=True)
    ):
        return
    if not _conforms(
        paradigm, parts[-1], _fixed_names(paradigm), is_file=True, holds_modules=False
    ) and not (identifiers and identifiers().admits(path, is_file=True)):
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
        "or linguist-generated in .gitattributes if it is third-party or generated, or, if an "
        "upstream contract fixes the name, declare the tracked manifest and the key whose value "
        f"repeats it under identifier_sources in {binding_path('profile')}",
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


def _read(
    names: IdentifierNames, absent: set[str], root: Path, manifest: str, source: IdentifierSource
) -> None:
    """Record one manifest's identifiers and the declared keys that carry one; else its gap."""
    try:
        text = (root / manifest).read_text(encoding="utf-8")
        document = (json if manifest.endswith(".json") else tomllib).loads(text)
    except (OSError, ValueError):
        repair = f"restore {manifest} as readable TOML or JSON"
        names.gaps.append(ParadigmGap(_SOURCE, manifest, repair))
        return
    for key in source.keys:
        for value in field_values(document, key.split(".")):
            for name in _identifiers(value, source.values):
                absent.discard(key)
                names.manifests.setdefault(name, manifest)


def _identifiers(value: str, reading: str) -> list[str]:
    """Read a value whole, as dotted parts, or as a path's segments and its file's stem.

    An identifier is not empty and holds no `/`.
    """
    if reading == "path":
        names = [*value.split("/"), posixpath.basename(value).split(".")[0]]
    else:
        names = value.split(".") if reading == "dotted" else [value]
    return [name for name in names if name and "/" not in name]


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

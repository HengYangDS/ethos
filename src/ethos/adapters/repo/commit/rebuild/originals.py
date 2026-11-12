"""Walk a history rebuild's originals once: every message and every blob that they reach.

Commits come oldest first, each followed by the blobs that it reaches first, in tree order, so a
blob held at two paths or kept across a rename is read once, at the first commit and path that
reach it, and a merge adds only what its own tree first holds. An annotated tag, and each tag that
it targets, adds its own message without its signature. Each message also carries the trailers
that `git interpret-trailers --parse` finds in it and its closing paragraph, the last one before
those trailers. A gitlink has no bytes to read, and text keeps every byte through
`surrogateescape`. The same walk keeps how the objects link and what readiness judges beside the
scanned bytes: each commit's and tag's header and each tree's entry names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import object_types
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.git_object import tag_message
from ethos.contracts.outcome import require
from ethos.repository.paradigm.peer_identity import Sighting

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.adapters.repo.git_object import ObjectType

# Paragraphs are separated by a line that holds nothing but blanks.
_PARAGRAPH = re.compile(r"\n[ \t]*\n")
_GITLINK = b"160000"
# The header fields that name a commit's tree and parents, or a tag's target, in that order.
_LINKS = frozenset({"tree", "parent", "object"})


@dataclass(frozen=True, slots=True)
class History:
    """What one walk of the originals reached, and how its objects link.

    `links` maps a commit to its tree and then its parents, a tree to its entries' objects without
    gitlinks, and a tag to its target; `commits` lists the commits oldest first; `headers` holds
    each commit's and tag's header, and `names` each tree's entry names.
    """

    sightings: list[Sighting]
    commits: list[str]
    links: dict[str, tuple[str, ...]]
    headers: dict[str, str]
    names: dict[str, tuple[str, ...]]


def original_sightings(root: Path, revisions: tuple[str, ...]) -> list[Sighting]:
    """Return each message and blob that the revisions reach, once each, in walk order."""
    return original_history(root, revisions).sightings


def original_history(root: Path, revisions: tuple[str, ...]) -> History:
    """Walk every object that the revisions reach once, in walk order.

    Every revision must peel to a commit: a tag of a tree or a blob has no commit and path that a
    witness could name.
    """
    peeled = object_types(root, tuple(f"{revision}^{{}}" for revision in revisions))
    require(set(peeled.values()) <= {"commit"}, "rebuild_original_unplaced")
    listed = run_git(
        root,
        "rev-list",
        "--objects",
        "--in-commit-order",
        "--reverse",
        "--topo-order",
        "--stdin",
        stdin="".join(f"{revision}\n" for revision in revisions).encode(),
        text=False,
    ).stdout
    rows = [row.decode("utf-8", "surrogateescape").partition(" ") for row in listed.split(b"\n")]
    named = [(oid, name) for oid, _space, name in rows if oid]
    wanted = list(_placed(named, object_types(root, tuple(oid for oid, _name in named))))
    payloads = read_objects(
        root, tuple(row[0] for row in wanted), kind=tuple(row[1] for row in wanted)
    )
    history = History([], [], {}, {}, {})
    for row, payload in zip(wanted, payloads, strict=True):
        _keep(root, history, row, payload)
    return history


def _keep(
    root: Path, history: History, row: tuple[str, ObjectType, str, str], payload: bytes
) -> None:
    """Keep a tree's links and names, a header and its links, and every scanned text."""
    oid, kind = row[:2]
    if kind == "tree":
        entries = list(_entries(payload, len(oid) // 2))
        history.links[oid] = tuple(item for mode, _name, item in entries if mode != _GITLINK)
        history.names[oid] = tuple(name for _mode, name, _item in entries)
        return
    if kind != "blob":
        header = payload.partition(b"\n\n")[0].decode("utf-8", "surrogateescape")
        history.headers[oid] = header
        fields = (line.partition(" ") for line in header.split("\n"))
        history.links[oid] = tuple(value for name, _, value in fields if name in _LINKS)
        history.commits.extend((oid,) if kind == "commit" else ())
    history.sightings.append(_sighting(root, row, payload))


def _entries(payload: bytes, width: int) -> Iterator[tuple[bytes, str, str]]:
    """Each tree entry's mode, name and object, read from Git's binary tree format."""
    offset = 0
    while offset < len(payload):
        space = payload.index(b" ", offset)
        end = payload.index(b"\0", space)
        name = payload[space + 1 : end].decode("utf-8", "surrogateescape")
        yield payload[offset:space], name, payload[end + 1 : end + 1 + width].hex()
        offset = end + 1 + width


def _sighting(root: Path, row: tuple[str, ObjectType, str, str], payload: bytes) -> Sighting:
    """Read a blob whole; a message also with Git's own trailers and its closing paragraph."""
    oid, kind, holder, path = row
    if kind == "blob":
        return Sighting(oid, holder, path, payload.decode("utf-8", "surrogateescape"))
    message = payload.partition(b"\n\n")[2] if kind == "commit" else tag_message(payload)
    parsed = run_git(
        root, "interpret-trailers", "--parse", "--no-divider", stdin=message, text=False
    ).stdout.decode("utf-8", "surrogateescape")
    trailers = tuple(line for line in parsed.splitlines() if line)
    text = message.decode("utf-8", "surrogateescape")
    paragraphs = [part.strip("\n") for part in _PARAGRAPH.split(text) if part.strip()]
    closing = paragraphs[-1 - bool(trailers)] if len(paragraphs) > bool(trailers) else ""
    return Sighting(oid, holder, path, text, trailers, closing)


def _placed(
    named: list[tuple[str, str]], types: dict[str, str]
) -> Iterator[tuple[str, ObjectType, str, str]]:
    """Place each object: a message names its own object, a blob its first commit and path.

    A tree is read for its links and names, never scanned; a blob that no commit reaches first
    cannot be placed.
    """
    holder = ""
    for oid, name in named:
        kind = types[oid]
        if kind == "blob":
            require(holder, "rebuild_original_unplaced")
            yield oid, "blob", holder, name
        elif kind == "commit":
            holder = oid
            yield oid, "commit", oid, ""
        elif kind == "tag":
            yield oid, "tag", oid, ""
        elif kind == "tree":
            yield oid, "tree", oid, ""


def reaching(history: History, holders: Collection[str]) -> frozenset[str]:
    """Every walked commit and tag that reaches an object in `holders`, its own message included.

    A tree reaches what its entries reach, a commit what its tree and its parents reach, and a tag
    what its target reaches.
    """
    trees: dict[str, bool] = {}

    def tree(oid: str) -> bool:
        if oid not in trees:
            trees[oid] = any(
                item in holders or (item in history.names and tree(item))
                for item in history.links.get(oid, ())
            )
        return trees[oid]

    reached: set[str] = set()
    for commit in history.commits:
        top, *parents = history.links[commit]
        if commit in holders or tree(top) or any(parent in reached for parent in parents):
            reached.add(commit)
    commits = set(history.commits)

    def tag(oid: str) -> bool:
        target = history.links[oid][0]
        return oid in holders or target in reached or (target not in commits and tag(target))

    return frozenset(reached | {oid for oid in history.headers if oid not in commits and tag(oid)})

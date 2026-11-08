"""The store records that retention owns, each recognized by its one writer's exact form.

Every writer names its file by the SHA-256 of its bytes, so a file whose name is not its digest
or whose form matches no writer is another producer's and stays.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from zipfile import BadZipFile
from zipfile import ZipFile

from ethos.contracts.semantic import canonical_json_bytes

if TYPE_CHECKING:
    from pathlib import Path

_MERGE_KEYS = frozenset({"observation", "files", "stage_blobs", "metadata"})
_NATIVE_MEMBERS = frozenset({"execution.json", "stdout.txt", "stderr.txt"})
_MANIFEST_REFERENCE = re.compile(rb'"manifest":\{"sha256":"([0-9a-f]{64})"')


@dataclass(frozen=True)
class StoreItem:
    """One retirable record: its kind, state, every file it owns and the digests that name it."""

    kind: str
    state: str
    paths: tuple[Path, ...]
    tokens: frozenset[str]


def classify_store(store: Path) -> tuple[tuple[StoreItem, ...], tuple[Path, ...]]:
    """Return the owned items and the files in an owned directory that no writer produced."""
    items: list[StoreItem] = []
    unowned: list[Path] = []
    for path in _files(store / "artifacts"):
        data = path.read_bytes()
        kind = _artifact_kind(path, data) if _digest(data) == path.stem else None
        if kind is None:
            unowned.append(path)
        else:
            items.append(StoreItem(kind, "artifact", (path,), frozenset({path.stem})))
    units, foreign = _lane_units(store)
    return (*items, *units), tuple(sorted((*unowned, *foreign)))


def _artifact_kind(path: Path, data: bytes) -> str | None:
    if path.suffix == ".zip":
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
        except BadZipFile:
            return None
        if names >= _NATIVE_MEMBERS:
            return "native-attempt"
        return "javascript-attempt" if "observation.json" in names else None
    document = _decoded(data) if path.suffix == ".json" else None
    if not isinstance(document, dict):
        return None
    if document.get("schema_version") == 1 and {"head", "checks"} <= set(document):
        return "proof-check"
    return "merge-preimage" if set(document) == _MERGE_KEYS else None


def _lane_units(store: Path) -> tuple[list[StoreItem], list[Path]]:
    """Group lane retirement records by request digest, reading each file once.

    Units without a terminal receipt stay unclassified and kept until the apply decides them.
    """
    manifests = store / "requests" / "lane-retirement-manifest"
    foreign: list[Path] = []
    requests: dict[str, Path] = {}
    bound: set[str] = set()
    for path in _files(store / "requests" / "lane-retirement"):
        data = path.read_bytes()
        if _digest(data) != path.stem:
            foreign.append(path)
            continue
        requests[path.stem] = path
        bound |= _manifest_references(data)
    receipts: dict[str, tuple[Path, set[str]]] = {}
    for path in _files(store / "receipts" / "lane-retirement"):
        data = path.read_bytes()
        document = _decoded(data) if _digest(data) == path.stem else None
        if not isinstance(document, dict) or document.get("kind") != "lane-retirement-receipt":
            foreign.append(path)
            continue
        request = document.get("request")
        if not isinstance(request, dict):
            foreign.append(path)
            continue
        references = _manifest_references(data)
        bound |= references
        receipts[hashlib.sha256(canonical_json_bytes(request)).hexdigest()] = (path, references)
    units: list[StoreItem] = []
    for digest, (receipt, references) in receipts.items():
        request = requests.get(digest)
        files = (
            receipt,
            *((request,) if request is not None else ()),
            *_files(store / "operations" / "lane-retirement" / digest),
            *(path for name in references if (path := manifests / f"{name}.json").is_file()),
        )
        state = "terminal" if request is not None else "receipt-only"
        tokens = frozenset({digest, *(path.stem for path in files)})
        units.append(StoreItem("lane-retirement", state, tuple(sorted(files)), tokens))
    units.extend(
        StoreItem("lane-retirement", "manifest-only", (path,), frozenset({path.stem}))
        for path in _files(manifests)
        if path.stem not in bound
    )
    return units, foreign


def _manifest_references(data: bytes) -> set[str]:
    return {match.decode() for match in _MANIFEST_REFERENCE.findall(data)}


def _files(directory: Path) -> tuple[Path, ...]:
    """Return the regular files directly in a directory, without writers' temporaries."""
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and not path.is_symlink() and not path.name.startswith(".")
        )
    )


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decoded(data: bytes) -> object:
    try:
        return json.loads(data)
    except ValueError:
        return None

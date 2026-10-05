"""Resolve native source relationships once for policy binding and byte observation."""

from __future__ import annotations

import json
import posixpath
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations

if TYPE_CHECKING:
    from ethos.repository.policy.projections import Projection
    from ethos.repository.profile import SourceContract


@dataclass(frozen=True, slots=True)
class LockedArchive:
    """A native npm content identity, not evidence that cached archive bytes match."""

    integrity: str
    archive_path: str | None


def locked_archive(reference: str, source: bytes) -> LockedArchive:
    """Interpret an exact lock member without observing cache state or executing code."""
    lock, _separator, key = reference.partition("#packages/")
    payload = json.loads(source)
    packages = payload.get("packages") if isinstance(payload, Mapping) else None
    metadata = packages.get(key) if isinstance(packages, Mapping) else None
    if (
        not isinstance(payload, Mapping)
        or payload.get("lockfileVersion") != 3
        or not isinstance(metadata, Mapping)
        or metadata.get("link")
        or not isinstance(metadata.get("integrity"), str)
        or not isinstance(metadata.get("resolved"), str)
    ):
        message = f"source_upstream_lock_unqualified:{reference}"
        raise ValueError(message)
    resolved = metadata["resolved"]
    if resolved.startswith("file:"):
        relative = resolved.removeprefix("file:")
        path = PurePosixPath(posixpath.normpath(str(PurePosixPath(lock).parent / relative)))
        if (
            not relative
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() == "."
            or "\\" in relative
            or "\0" in relative
        ):
            message = f"source_upstream_archive_outside_root:{reference}"
            raise ValueError(message)
        return LockedArchive(metadata["integrity"], path.as_posix())
    url = urlsplit(resolved)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
        message = f"source_upstream_archive_unsupported:{reference}"
        raise ValueError(message)
    return LockedArchive(metadata["integrity"], None)


def generated_relations(
    contracts: tuple[SourceContract, ...], declarations: Mapping[str, bytes]
) -> tuple[Projection, ...]:
    """Require each declared output group to preserve its original native owner."""
    generated = tuple(contract for contract in contracts if contract.kind == "generated")
    references = {reference for contract in generated for reference in contract.input_refs}
    if not references <= PROJECTION_DECLARATIONS.keys():
        message = "source_producer_native_contract_unsupported"
        raise ValueError(message)
    relations = projection_relations(
        {reference: declarations[reference].decode("utf-8") for reference in references}
    )
    claimed = {
        artifact: member for contract in generated for artifact, member in contract.members.items()
    }
    for reference in sorted(references):
        outputs = {relation.output for relation in relations if relation.declaration == reference}
        selected = {artifact for artifact, member in claimed.items() if member[0] == reference}
        if not outputs or selected != outputs:
            message = f"source_producer_group_incomplete:{reference}"
            raise ValueError(message)
    return relations


def source_contract_paths(
    contracts: tuple[SourceContract, ...], materials: Mapping[str, bytes | None]
) -> tuple[str, ...]:
    """Expand existing declarations and locks; missing seeds remain explicit source obligations."""
    paths = [artifact for contract in contracts for artifact in contract.members]
    generated = tuple(contract for contract in contracts if contract.kind == "generated")
    references = {reference for contract in generated for reference in contract.input_refs}
    paths.extend(sorted(references))
    declarations = {
        reference: raw for reference in references if (raw := materials.get(reference)) is not None
    }
    if len(declarations) == len(references):
        paths.extend(
            relative
            for relation in generated_relations(generated, declarations)
            for relative in relation.materials
        )
    for reference in sorted(
        {
            reference
            for contract in contracts
            if contract.kind == "upstream"
            for reference in contract.input_refs
        }
    ):
        lock = reference.partition("#packages/")[0]
        paths.append(lock)
        if (raw := materials.get(lock)) is not None:
            archive = locked_archive(reference, raw)
            if archive.archive_path is not None:
                paths.append(archive.archive_path)
    return tuple(dict.fromkeys(paths))

"""Resolve native source relationships once for policy binding and byte observation."""

from __future__ import annotations

import json
import posixpath
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.quality.gate_composition import canonical_gate_command
from ethos.repository.policy.quality.obligations import INTEGRITY_PROVIDER
from ethos.repository.policy.quality.tool_configuration import native_tool_configurations
from ethos.repository.policy.references.commands import python_module
from ethos.repository.policy.references.python_syntax import module_source_paths
from ethos.repository.profile import received_archive

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate
    from ethos.repository.policy.projections import Projection
    from ethos.repository.profile import SourceContract


PRODUCT_PROVIDER_SOURCE = "@ethos/"


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
        if received := received_archive(reference):
            paths.append(received[0])
            continue
        lock = reference.partition("#packages/")[0]
        paths.append(lock)
        if (raw := materials.get(lock)) is not None:
            archive = locked_archive(reference, raw)
            if archive.archive_path is not None:
                paths.append(archive.archive_path)
    return tuple(dict.fromkeys(paths))


def provider_module_sources(gate: Gate) -> tuple[tuple[str, str], ...]:
    """Pair each invoked provider with its implementation source, not all gate materials."""
    provider_root = (
        PRODUCT_PROVIDER_SOURCE
        if gate.profile == "repository" and gate.tool_adapter == "ethos"
        else "src/ethos/"
    )
    return tuple(
        (
            reference,
            provider_root
            + reference.partition(":")[0].removeprefix("ethos.").replace(".", "/")
            + ".py",
        )
        for reference in (*gate.providers, *gate.verification_providers)
    )


def source_paths_for_gate(
    gate: Gate,
    *,
    repository_paths: tuple[str, ...] = (),
    source_contracts: tuple[SourceContract, ...] = (),
    source_materials: Mapping[str, bytes | None] | None = None,
) -> tuple[str, ...]:
    providers = provider_module_sources(gate)
    artifacts: tuple[str, ...] = ()
    for reference, source in providers:
        if reference == INTEGRITY_PROVIDER:
            prefix = source.removesuffix("adapters/gates/provenance/observation.py")
            artifacts = (
                prefix + "adapters/gates/provenance/archive.mjs",
                prefix + "adapters/repo/content/observation.py",
                prefix + "repository/policy/quality/sources.py",
                *source_contract_paths(source_contracts, source_materials or {}),
                *_projection_product_sources(source_contracts, source_materials or {}),
            )
    command = canonical_gate_command(gate.command)
    module = python_module(command)
    noxfile = ("noxfile.py", "pyproject.toml", "uv.lock") if module == "nox" else ()
    script = (
        (command[0],)
        if command
        and not noxfile
        and command[0] not in {"python", "ethos"}
        and "/" in command[0]
        and not Path(command[0]).is_absolute()
        and ".." not in Path(command[0]).parts
        else ()
    )
    module_sources = module_source_paths(module, repository_paths) if module and not noxfile else ()
    return tuple(
        dict.fromkeys(
            (
                *[path for _reference, path in providers],
                *(
                    path
                    for tool in gate.tools
                    for path in native_tool_configurations(repository_paths, tool)
                ),
                *artifacts,
                *noxfile,
                *(output.configuration for output in gate.native_outputs if output.configuration),
                *module_sources,
                *script,
            )
        )
    )


def _projection_product_sources(
    contracts: tuple[SourceContract, ...], materials: Mapping[str, bytes | None]
) -> tuple[str, ...]:
    """Bind the actual native compiler and product inputs without claiming repository bytes."""
    references = {
        reference
        for contract in contracts
        if contract.kind == "generated"
        for reference in contract.input_refs
    }
    declarations = {
        reference: raw for reference in references if (raw := materials.get(reference)) is not None
    }
    if len(declarations) != len(references):
        return ()
    sources: list[str] = []
    for relation in generated_relations(contracts, declarations):
        if relation.kind != "cue":
            continue
        sources.extend(
            PRODUCT_PROVIDER_SOURCE + path
            for path in (
                "adapters/projections/compiler.py",
                "adapters/projections/cue.py",
                "adapters/toolchain/mise.py",
                "adapters/repo/runtime/materialization/native_supply.py",
                "repository/policy/projections.py",
                "repository/release/resources.py",
            )
        )
        compiler = tomllib.loads(declarations[relation.declaration].decode("utf-8"))["compiler"]
        if common := compiler.get("common"):
            sources.append(PRODUCT_PROVIDER_SOURCE + "resources/" + common)
            if not compiler.get("supply"):
                sources.extend(
                    PRODUCT_PROVIDER_SOURCE + "resources/.config/mise/" + name
                    for name in ("config.toml", "mise.lock")
                )
    return tuple(dict.fromkeys(sources))


def source_paths_for_gates(
    gates: tuple[Gate, ...],
    *,
    repository_paths: tuple[str, ...] = (),
    source_contracts: tuple[SourceContract, ...] = (),
    source_materials: Mapping[str, bytes | None] | None = None,
) -> tuple[str, ...]:
    """Return the unique repository materials needed by a gate closure."""
    return tuple(
        dict.fromkeys(
            path
            for gate in gates
            for path in source_paths_for_gate(
                gate,
                repository_paths=repository_paths,
                source_contracts=source_contracts,
                source_materials=source_materials,
            )
        )
    )

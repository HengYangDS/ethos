"""Observe exact native producer and locked upstream bytes without accepting labels."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING

import nodejs_wheel

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.process import run_command
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable
from ethos.repository.policy.quality.sources import generated_relations
from ethos.repository.policy.quality.sources import locked_archive
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import repository_profile_from_text

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.repository.profile import SourceContract

_MAX_MEMBER_BYTES = 64 * 1024 * 1024
_MAX_OBSERVATION_BYTES = 128 * 1024 * 1024
_ARCHIVE_LIMITS = {
    "archive_bytes": _MAX_MEMBER_BYTES,
    "raw_bytes": _MAX_OBSERVATION_BYTES,
    "input_bytes": 192 * 1024 * 1024,
    "expanded_bytes": 256 * 1024 * 1024,
    "metadata_bytes": 1024 * 1024,
    "entries": 20000,
    "digests": 64,
}


@dataclass(frozen=True, slots=True)
class _SourceTree:
    root: Path
    head: str
    tree: str
    entries: Mapping[str, tuple[str, int]]
    observed: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def observe(cls, root: Path) -> _SourceTree:
        head = current_tracked_head(root)
        if not head:
            message = "source_head_missing"
            raise ValueError(message)
        raw = run_git(root, "ls-tree", "-rlz", head, text=False, check=True).stdout
        entries = {}
        for record in raw.split(b"\0"):
            if not record:
                continue
            metadata, path = record.split(b"\t", 1)
            mode, kind, _oid, size = metadata.split()
            if kind == b"blob":
                entries[path.decode("utf-8")] = (mode.decode("ascii"), int(size))
        return cls(root.resolve(), head, current_tree(root, head), entries)

    def read(self, relative: str) -> bytes:
        """Reuse exact Git bytes within this observation and reject changed live inputs."""
        metadata = self.entries.get(relative)
        if metadata is None or metadata[0] not in {"100644", "100755"}:
            message = f"source_member_unavailable:{relative}"
            raise ValueError(message)
        if metadata[1] > _MAX_MEMBER_BYTES:
            message = f"source_member_size_exceeded:{relative}"
            raise ValueError(message)
        if relative not in self.observed:
            if (
                sum(map(len, self.observed.values())) + metadata[1] > _MAX_OBSERVATION_BYTES
                or len(self.observed) >= _ARCHIVE_LIMITS["entries"]
            ):
                message = "source_observation_size_exceeded"
                raise ValueError(message)
            self.observed[relative] = run_git(
                self.root, "show", f"{self.head}:{relative}", text=False, check=True
            ).stdout
        expected = self.observed[relative]
        actual = read_regular_bytes(
            self.root,
            relative,
            max_bytes=metadata[1],
            unsafe_gap=f"source_member_link_or_type_forbidden:{relative}",
            unstable_gap=f"source_member_changed:{relative}",
            size_gap=f"source_member_size_exceeded:{relative}",
        )
        if actual != expected:
            message = f"source_member_changed:{relative}"
            raise ValueError(message)
        return expected

    def recheck(self) -> None:
        if current_tracked_head(self.root) != self.head:
            message = "source_tree_changed"
            raise ValueError(message)
        for relative in tuple(self.observed):
            self.read(relative)


def _generated(snapshot: _SourceTree, contracts: tuple[SourceContract, ...]) -> None:
    if not contracts:
        return
    references = {reference for contract in contracts for reference in contract.input_refs}
    declarations = {reference: snapshot.read(reference) for reference in references}
    relations = generated_relations(contracts, declarations)
    for reference in sorted(references):
        group = tuple(relation for relation in relations if relation.declaration == reference)
        compiled: dict[str, str] = {}
        if any(relation.kind == "cue" for relation in group):
            files = {
                relative: snapshot.read(relative).decode("utf-8")
                for relation in group
                for relative in relation.materials
                if relative != relation.output
            }
            compiled = compile_projections(snapshot.root, reference, files)
        for relation in group:
            original = snapshot.read(relation.source)
            expected = (
                compiled[relation.provider].encode("utf-8")
                if relation.kind == "cue"
                else original
                if relation.kind == "copy"
                else relation.render(original.decode("utf-8")).encode("utf-8")
            )
            if snapshot.read(relation.output) != expected:
                message = f"source_generated_bytes_mismatch:{relation.output}"
                raise ValueError(message)


@dataclass(frozen=True, slots=True)
class _ArchiveMember:
    member: str
    expected: bytes


@dataclass(slots=True)
class _ArchiveInput:
    reference: str
    integrity: str
    data: bytes | None
    members: dict[str, _ArchiveMember] = field(default_factory=dict)
    selected_integrity: str | None = None

    @property
    def raw_size(self) -> int:
        return (len(self.data) if self.data is not None else 0) + sum(
            len(member.expected) for member in self.members.values()
        )

    def payload(self) -> dict[str, object]:
        if self.data is None:
            message = "source_upstream_archive_missing"
            raise ValueError(message)
        return {
            "reference": self.reference,
            "integrity": self.integrity,
            "selected_integrity": self.selected_integrity,
            "data": base64.b64encode(self.data).decode("ascii"),
            "members": {
                artifact: {
                    "member": relation.member,
                    "expected": base64.b64encode(relation.expected).decode("ascii"),
                }
                for artifact, relation in self.members.items()
            },
        }


def _native_archives(
    snapshot: _SourceTree, node: Path, npm: Path, request: dict[str, object]
) -> Mapping[str, object]:
    """Invoke only the selected product helper and bounded native input protocol."""
    request["limits"] = _ARCHIVE_LIMITS
    payload = json.dumps(request, separators=(",", ":"))
    if len(payload.encode("utf-8")) > _ARCHIVE_LIMITS["input_bytes"]:
        message = "source_upstream_request_size_exceeded"
        raise ValueError(message)
    result = run_command(
        snapshot.root,
        (str(node), str(Path(__file__).with_name("archive.mjs")), str(npm)),
        stdin=payload,
        timeout=60,
        remove_env=("NODE_OPTIONS", "NODE_PATH"),
    )
    if result.returncode:
        message = f"source_upstream_archive_unqualified:{result.stderr.strip()}"
        raise ValueError(message)
    observed = json.loads(result.stdout)
    if not isinstance(observed, dict):
        message = "source_upstream_native_result_invalid"
        raise TypeError(message)
    return observed


def _read_archive_cache(
    snapshot: _SourceTree, node: Path, npm: Path, archives: dict[str, _ArchiveInput]
) -> None:
    """Native availability selects a digest; one safe reader verifies its fresh bytes."""
    cached = [entry for entry in archives.values() if entry.data is None]
    if not cached:
        return
    selected = _native_archives(
        snapshot,
        node,
        npm,
        {
            "select_cache": True,
            "archives": [
                {"reference": entry.reference, "integrity": entry.integrity} for entry in cached
            ],
        },
    ).get("selected")
    if not isinstance(selected, list) or len(selected) != len(cached):
        message = "source_upstream_native_selection_invalid"
        raise ValueError(message)
    raw_size = sum(entry.raw_size for entry in archives.values())
    for entry, identity in zip(cached, selected, strict=True):
        if (
            not isinstance(identity, dict)
            or identity.get("reference") != entry.reference
            or not isinstance(identity.get("path"), str)
            or not isinstance(identity.get("root"), str)
            or not isinstance(identity.get("integrity"), str)
            or type(identity.get("size")) is not int
            or not 0 <= identity["size"] <= _ARCHIVE_LIMITS["archive_bytes"]
        ):
            message = "source_upstream_native_selection_invalid"
            raise ValueError(message)
        store = Path(identity["root"])
        relative = Path(identity["path"]).relative_to(store)
        if raw_size + identity["size"] > _ARCHIVE_LIMITS["raw_bytes"]:
            message = "source_upstream_request_size_exceeded"
            raise ValueError(message)
        entry.data = read_regular_bytes(
            store,
            relative.as_posix(),
            max_bytes=min(identity["size"], _ARCHIVE_LIMITS["raw_bytes"] - raw_size),
            unsafe_gap="archive_path_link_or_type_forbidden",
            unstable_gap="archive_content_changed",
            size_gap="archive_size_exceeded",
        )
        if len(entry.data) != identity["size"]:
            message = "archive_content_changed"
            raise ValueError(message)
        raw_size += len(entry.data)
        entry.selected_integrity = identity["integrity"]


def _upstream(snapshot: _SourceTree, contracts: tuple[SourceContract, ...]) -> None:
    """Read once, then conjoin native SRI and bounded framing/member observations."""
    archives: dict[str, _ArchiveInput] = {}
    for contract in contracts:
        for artifact, (reference, member) in contract.members.items():
            if reference not in archives:
                lock = reference.partition("#packages/")[0]
                archive = locked_archive(reference, snapshot.read(lock))
                data = snapshot.read(archive.archive_path) if archive.archive_path else None
                archives[reference] = _ArchiveInput(reference, archive.integrity, data)
            archives[reference].members[artifact] = _ArchiveMember(member, snapshot.read(artifact))
    if not archives:
        return
    package = Path(str(nodejs_wheel.__file__)).resolve().parent
    npm = package / "lib/node_modules/npm/bin/npm-cli.js"
    if not npm.is_file():
        message = "source_upstream_native_npm_unavailable"
        raise ValueError(message)
    node = resolve_node_executable()
    _read_archive_cache(snapshot, node, npm, archives)
    if (
        sum(entry.raw_size for entry in archives.values()) > _ARCHIVE_LIMITS["raw_bytes"]
        or sum(len(entry.members) for entry in archives.values()) > _ARCHIVE_LIMITS["entries"]
    ):
        message = "source_upstream_request_size_exceeded"
        raise ValueError(message)
    payload = _native_archives(
        snapshot, node, npm, {"archives": [entry.payload() for entry in archives.values()]}
    )
    if payload != {
        "matched": sorted(artifact for entry in archives.values() for artifact in entry.members)
    }:
        message = "source_upstream_native_result_invalid"
        raise ValueError(message)


def _contracts(snapshot: _SourceTree) -> tuple[SourceContract, ...]:
    """Read obligations only from the same unchanged committed native profile."""
    relative = ".ethos/profile.toml"
    if relative not in snapshot.entries:
        return ()
    profile = repository_profile_from_text(
        snapshot.root, exists=True, text=snapshot.read(relative).decode("utf-8")
    )
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return profile.declaration.proof.source_contracts if profile.declaration else ()


def integrity_report(root: Path, *, timeout_seconds: float | None = None) -> dict[str, object]:
    """Conjoin native raw-byte observations; neither a label nor a producer certifies them."""
    snapshot = None
    contracts = ()
    try:
        with command_scope(timeout_seconds=timeout_seconds):
            snapshot = _SourceTree.observe(root)
            contracts = _contracts(snapshot)
            _generated(
                snapshot, tuple(contract for contract in contracts if contract.kind == "generated")
            )
            _upstream(
                snapshot, tuple(contract for contract in contracts if contract.kind == "upstream")
            )
            snapshot.recheck()
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, ProcessExecutionError) as error:
        paths = [artifact for contract in contracts for artifact in contract.members]
        return {
            "verdict": "unknown",
            "state": "unproven",
            "required_gaps": [f"source_integrity_unproven:{path}" for path in paths]
            or ["source_integrity_observation_unproven"],
            "diagnostics": [{"reason": str(error)}],
        }
    return {
        "verdict": "pass",
        "state": "verified" if contracts else "not_applicable",
        "required_gaps": [],
        "source_integrity": {
            "source_tree": snapshot.tree,
            "members": {
                artifact: {"kind": contract.kind, "input_ref": reference, "member": member}
                for contract in contracts
                for artifact, (reference, member) in contract.members.items()
            },
        },
    }

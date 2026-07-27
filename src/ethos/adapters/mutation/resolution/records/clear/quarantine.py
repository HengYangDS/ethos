"""Identity-bound quarantine validation and clear path safety."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import display_record_path
from ethos.adapters.mutation.resolution.records.roots import record_path_is_safe
from ethos.contracts.resolution.closeout import LaneResolutionClearReceipt
from ethos.contracts.resolution.lane import is_lane_decision_id

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.resolution.records.current.snapshot import CurrentFileIdentity


_PRESERVATION_PACKAGE_NAMES = {
    "manifest.json",
    "repository.bundle",
    "tracked.patch",
    "index.patch",
    "untracked.tar",
}
_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_RECORD_CATEGORIES = {"decisions", "receipts", "clears", "reservations"}
_SHA256_LENGTH = 64
_FILE_IDENTITY_FIELD_COUNT = 6
_QUARANTINE_NAME_PART_COUNT = 3
_CLEAR_QUARANTINE_IDENTITY_FIELD_COUNT = 3
_MANIFEST_FIELDS = {
    "decision_id",
    "lane_ref",
    "head",
    "observation_digest",
    "bundle_sha256",
    "patch_sha256",
    "untracked_archive_sha256",
    "source_lease_transferred",
}
_V2_MANIFEST_FIELDS = {
    *_MANIFEST_FIELDS,
    "package_format_version",
    "index_patch_sha256",
}


@dataclass(frozen=True, slots=True)
class ClearQuarantineCandidate:
    """Concrete descriptor-bound package facts consumed by clear validation."""

    path: Path
    payload_sha256: dict[str, str | None] | None
    package_names: set[str] | None
    payload_identities: dict[str, CurrentFileIdentity | None] | None
    entry_identity: tuple[int, int, int] | None


def clear_quarantine_name(decision_id: str, identity: tuple[int, int, int]) -> str:
    """Bind one clear quarantine name to its decision and filesystem identity."""
    device, inode, mode = identity
    digest = hashlib.sha256(decision_id.encode()).hexdigest()
    return f".{digest}.{device:x}-{inode:x}-{mode:x}.clear-quarantine"


def clear_quarantine_identity(name: str, decision_id: str) -> tuple[int, int, int] | None:
    """Parse the identity only from the exact quarantine namespace for one decision."""
    digest = hashlib.sha256(decision_id.encode()).hexdigest()
    prefix, suffix = f".{digest}.", ".clear-quarantine"
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    encoded = name.removeprefix(prefix).removesuffix(suffix)
    try:
        values = tuple(int(part, 16) for part in encoded.split("-"))
    except ValueError:
        return None
    if len(values) != _CLEAR_QUARANTINE_IDENTITY_FIELD_COUNT:
        return None
    identity = values[0], values[1], values[2]
    return identity if clear_quarantine_name(decision_id, identity) == name else None


def quarantined_payloads_match(
    manifest: dict[str, object],
    payload_sha256: dict[str, str | None],
    present_names: set[str],
) -> bool:
    """Allow only intact remaining payloads from the reviewed manifest."""
    expected = {
        "repository.bundle": str(manifest.get("bundle_sha256") or ""),
        "tracked.patch": str(manifest.get("patch_sha256") or ""),
    }
    if manifest.get("package_format_version") == "v2":
        expected["index.patch"] = str(manifest.get("index_patch_sha256") or "")
    archive_digest = str(manifest.get("untracked_archive_sha256") or "")
    if archive_digest:
        expected["untracked.tar"] = archive_digest
    allowed = {"manifest.json", *expected}
    return present_names <= allowed and all(
        payload_sha256.get(name) == digest
        for name, digest in expected.items()
        if name in present_names
    )


def validated_manifest(payload: dict[str, object]) -> dict[str, object]:
    """Validate the exact current preservation-manifest contract."""
    package_format = payload.get("package_format_version")
    expected_fields = _V2_MANIFEST_FIELDS if package_format == "v2" else _MANIFEST_FIELDS
    if set(payload) != expected_fields or package_format not in (None, "v2"):
        raise ValueError(_CURRENT_RECORD_INVALID)
    digest_fields = [
        payload["observation_digest"],
        payload["bundle_sha256"],
        payload["patch_sha256"],
    ]
    if package_format == "v2":
        digest_fields.append(payload["index_patch_sha256"])
    archive_digest = payload["untracked_archive_sha256"]
    if (
        not is_lane_decision_id(str(payload["decision_id"]))
        or not isinstance(payload["lane_ref"], str)
        or not payload["lane_ref"]
        or not _git_oid(payload["head"])
        or not all(_sha256(value) for value in digest_fields)
        or not (archive_digest == "" or _sha256(archive_digest))
        or payload["source_lease_transferred"] is not False
    ):
        raise ValueError(_CURRENT_RECORD_INVALID)
    return payload


def exact_package_binding(
    record: dict[str, object],
) -> tuple[set[str], dict[str, str], dict[str, CurrentFileIdentity]] | None:
    """Return one complete child-name, digest, and identity binding."""
    names = record.get("package_names")
    digests = record.get("payload_sha256")
    identities = record.get("payload_identities")
    if (
        not isinstance(names, set)
        or not isinstance(digests, dict)
        or not isinstance(identities, dict)
    ):
        return None
    if not all(isinstance(name, str) for name in names):
        return None
    bound_names = cast("set[str]", names)
    if any(not isinstance(digests.get(name), str) for name in bound_names):
        return None
    if any(
        not isinstance(identities.get(name), tuple)
        or len(cast("tuple[object, ...]", identities.get(name))) != _FILE_IDENTITY_FIELD_COUNT
        or not all(
            isinstance(value, int) for value in cast("tuple[object, ...]", identities.get(name))
        )
        for name in bound_names
    ):
        return None
    return (
        bound_names,
        {name: cast("str", digests.get(name)) for name in bound_names},
        {name: cast("CurrentFileIdentity", identities.get(name)) for name in bound_names},
    )


def clear_quarantines(
    root: Path,
    sources: tuple[ClearQuarantineCandidate, ...],
    clears: dict[str, dict[str, object]],
    manifests: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], list[Path]]:
    """Admit exactly one identity-bound manifest-less quarantine per clear."""
    records: dict[str, dict[str, object]] = {}
    invalid_paths: list[Path] = []
    by_digest = {
        hashlib.sha256(decision_id.encode()).hexdigest(): decision_id for decision_id in clears
    }
    admitted: dict[str, list[tuple[ClearQuarantineCandidate, tuple[int, int, int]]]] = {}
    for source in sources:
        parts = source.path.name.split(".", 2)
        digest = parts[1] if len(parts) == _QUARANTINE_NAME_PART_COUNT and not parts[0] else ""
        decision_id = by_digest.get(digest, "")
        identity = clear_quarantine_identity(source.path.name, decision_id) if decision_id else None
        names = source.package_names
        digests = source.payload_sha256
        identities = source.payload_identities
        if (
            identity is None
            or source.entry_identity != identity
            or names is None
            or digests is None
            or identities is None
            or bool(names)
        ):
            invalid_paths.append(source.path)
            continue
        admitted.setdefault(decision_id, []).append((source, identity))
    for decision_id, candidates in admitted.items():
        manifest = manifests.get(decision_id)
        if len(candidates) != 1 or manifest:
            invalid_paths.extend(source.path for source, _identity in candidates)
            if manifest:
                invalid_paths.append(cast("Path", manifest["physical_path"]))
            continue
        source, identity = candidates[0]
        names = source.package_names
        digests = source.payload_sha256
        identities = source.payload_identities
        records[decision_id] = {
            "decision_id": decision_id,
            "physical_path": source.path,
            "package_path": display_record_path(root, source.path),
            "quarantine_name": source.path.name,
            "package_identity": identity,
            "manifest_sha256": clears[decision_id]["manifest_sha256"],
            "quarantined": True,
            "package_names": names,
            "payload_sha256": digests,
            "payload_identities": identities,
        }
    return records, invalid_paths


def exact_clear_receipt(record: dict[str, object], expected: dict[str, object]) -> bool:
    """Match the exact canonical clear payload and immutable content digest."""
    try:
        payload = {field: record[field] for field in LaneResolutionClearReceipt.model_fields}
    except KeyError:
        return False
    canonical = (json.dumps(expected, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    content_sha256 = hashlib.sha256(canonical).hexdigest()
    return payload == expected and record.get("content_sha256") == content_sha256


def unsafe_package_path_present(root: Path) -> bool:
    """Return whether current package topology contains an unsafe path."""
    record_root = current_record_root(root)
    if not record_path_is_safe(record_root, record_root):
        return True
    if not record_root.exists():
        return False
    try:
        entries = tuple(record_root.iterdir())
    except OSError:
        return True
    return any(
        entry.name not in _RECORD_CATEGORIES
        and (entry.is_symlink() or (entry / "manifest.json").is_symlink())
        for entry in entries
    )


def unsafe_record_path_present(root: Path) -> bool:
    """Return whether a current record category path is a symlink."""
    record_root = current_record_root(root)
    return any((record_root / category).is_symlink() for category in _RECORD_CATEGORIES)


def package_path_safe(root: Path, package_path: Path) -> bool:
    """Return whether a package and its manifest remain under the current root."""
    record_root = current_record_root(root)
    return record_path_is_safe(record_root, package_path) and record_path_is_safe(
        record_root, package_path / "manifest.json"
    )


def _git_oid(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )

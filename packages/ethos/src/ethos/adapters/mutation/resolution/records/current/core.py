"""Strict readers for canonical current lane-resolution records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.resolution._shared import cross_record_invalid_paths
from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import preservation_payloads_match
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.clear.quarantine import clear_quarantines
from ethos.adapters.mutation.resolution.records.clear.quarantine import quarantined_payloads_match
from ethos.adapters.mutation.resolution.records.clear.quarantine import validated_manifest
from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.core import clear_quarantine_identity
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.current.snapshot import CurrentRecordSnapshot
from ethos.adapters.mutation.resolution.records.current.snapshot import open_current_record_snapshot
from ethos.adapters.mutation.resolution.records.current.validation.core import canonical_record_name
from ethos.adapters.mutation.resolution.records.current.validation.core import (
    validate_clear_receipt,
)
from ethos.adapters.mutation.resolution.records.current.validation.core import validate_decision
from ethos.adapters.mutation.resolution.records.current.validation.core import validate_receipt
from ethos.adapters.mutation.resolution.records.current.validation.core import validate_reservation

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos.adapters.mutation.resolution.records.current.snapshot import CurrentFileIdentity

_DECISIONS = "decisions"
_RECEIPTS = "receipts"
_CLEARS = "clears"
_RESERVATIONS = "reservations"
_RECORD_CATEGORIES = {_DECISIONS, _RECEIPTS, _CLEARS, _RESERVATIONS}
_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_DECISION_RECORD_CONFLICT = "lane_resolution_decision_record_conflict"


@dataclass(frozen=True, slots=True)
class CurrentLaneResolutionRecords:
    """Validated current records and physical-integrity accounting."""

    decisions: dict[str, dict[str, object]]
    manifests: dict[str, dict[str, object]]
    receipts: dict[str, dict[str, object]]
    clears: dict[str, dict[str, object]]
    reservations: dict[str, dict[str, object]]
    receipt_reservations: dict[str, dict[str, object]]
    clear_quarantines: dict[str, dict[str, object]]
    conflicts: set[str]
    invalid_count: int
    invalid_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class _CurrentPayload:
    path: Path
    content: bytes | None
    payload_sha256: dict[str, str | None] | None = None
    package_names: set[str] | None = None
    payload_identities: dict[str, CurrentFileIdentity | None] | None = None
    entry_identity: tuple[int, int, int] | None = None


@dataclass(frozen=True, slots=True)
class _CurrentRecordTopology:
    records: dict[str, tuple[_CurrentPayload, ...]]
    manifests: tuple[_CurrentPayload, ...]
    receipt_reservations: tuple[_CurrentPayload, ...]
    quarantine_candidates: tuple[_CurrentPayload, ...]
    invalid_paths: tuple[Path, ...]


def current_record_integrity_gap(*, inventory: dict[str, object]) -> str:
    """Return the stable effect-admission blocker for any invalid current payload."""
    summary = inventory.get("summary")
    invalid_count = (
        summary.get("invalid_current_record_count", 0) if isinstance(summary, dict) else 0
    )
    required_gaps = inventory.get("required_gaps")
    if bool(invalid_count) or (
        isinstance(required_gaps, list) and _CURRENT_RECORD_INVALID in required_gaps
    ):
        return _CURRENT_RECORD_INVALID
    if isinstance(required_gaps, list) and _DECISION_RECORD_CONFLICT in required_gaps:
        return _DECISION_RECORD_CONFLICT
    return ""


def read_current_lane_resolution_records(
    *, root: Path, record_root: Path
) -> CurrentLaneResolutionRecords:
    """Validate every physical payload under one descriptor-bound current snapshot."""
    topology = _current_record_topology(record_root)
    decisions, decision_conflicts, invalid_decisions = _records_with_conflicts(
        root,
        record_root,
        _DECISIONS,
        topology.records[_DECISIONS],
        lambda payload: validate_decision(root, payload),
    )
    receipts, receipt_conflicts, invalid_receipts = _records_with_conflicts(
        root,
        record_root,
        _RECEIPTS,
        topology.records[_RECEIPTS],
        lambda payload: validate_receipt(root, record_root, payload),
    )
    clears, clear_conflicts, invalid_clears = _records_with_conflicts(
        root,
        record_root,
        _CLEARS,
        topology.records[_CLEARS],
        lambda payload: validate_clear_receipt(root, payload),
    )
    manifests, manifest_conflicts, invalid_manifests = _manifests_with_conflicts(
        root, topology.manifests, clears
    )
    reservations, reservation_conflicts, invalid_reservations = _records_with_conflicts(
        root,
        record_root,
        _RESERVATIONS,
        topology.records[_RESERVATIONS],
        validate_reservation,
    )
    receipt_reservations, invalid_sidecars = _receipt_reservations(
        root, record_root, topology.receipt_reservations
    )
    clear_quarantine_records, invalid_quarantines = clear_quarantines(
        root, topology.quarantine_candidates, clears, manifests
    )
    cross_record_invalid = cross_record_invalid_paths(
        decisions=decisions,
        manifests=manifests,
        receipts=receipts,
        clears=clears,
        reservations=reservations,
    )
    invalid_paths = tuple(
        dict.fromkeys(
            path
            for paths in (
                invalid_decisions,
                invalid_manifests,
                invalid_receipts,
                invalid_clears,
                invalid_reservations,
                invalid_sidecars,
                invalid_quarantines,
                topology.invalid_paths,
                cross_record_invalid,
            )
            for path in paths
        )
    )
    return CurrentLaneResolutionRecords(
        decisions=decisions,
        manifests=manifests,
        receipts=receipts,
        clears=clears,
        reservations=reservations,
        receipt_reservations=receipt_reservations,
        clear_quarantines=clear_quarantine_records,
        conflicts=(
            decision_conflicts
            | manifest_conflicts
            | receipt_conflicts
            | clear_conflicts
            | reservation_conflicts
        ),
        invalid_count=len(invalid_paths),
        invalid_paths=invalid_paths,
    )


def _current_record_topology(record_root: Path) -> _CurrentRecordTopology:
    records: dict[str, tuple[_CurrentPayload, ...]] = dict.fromkeys(_RECORD_CATEGORIES, ())
    snapshot, state = open_current_record_snapshot(record_root)
    if state == "missing":
        return _CurrentRecordTopology(records, (), (), (), ())
    if snapshot is None:
        return _CurrentRecordTopology(records, (), (), (), (record_root,))
    manifests: list[_CurrentPayload] = []
    receipt_reservations: list[_CurrentPayload] = []
    quarantine_candidates: list[_CurrentPayload] = []
    invalid_paths: list[Path] = []
    with snapshot:
        for name in snapshot.names:
            if name in _RECORD_CATEGORIES:
                admitted, sidecars, invalid = _category_topology(snapshot, record_root, name)
                records[name] = admitted
                receipt_reservations.extend(sidecars)
                invalid_paths.extend(invalid)
                continue
            manifest, quarantine, invalid = _package_topology(snapshot, record_root, name)
            if manifest is not None:
                manifests.append(manifest)
            if quarantine is not None:
                quarantine_candidates.append(quarantine)
            if invalid is not None:
                invalid_paths.append(invalid)
    return _CurrentRecordTopology(
        records=records,
        manifests=tuple(manifests),
        receipt_reservations=tuple(receipt_reservations),
        quarantine_candidates=tuple(quarantine_candidates),
        invalid_paths=tuple(invalid_paths),
    )


def _category_topology(
    snapshot: CurrentRecordSnapshot,
    record_root: Path,
    category: str,
) -> tuple[tuple[_CurrentPayload, ...], tuple[_CurrentPayload, ...], tuple[Path, ...]]:
    names, state = snapshot.open_directory(category)
    category_root = record_root / category
    if state != "valid":
        return (), (), (category_root,)
    admitted: list[_CurrentPayload] = []
    sidecars: list[_CurrentPayload] = []
    invalid: list[Path] = []
    for name in names:
        source = _CurrentPayload(category_root / name, snapshot.read_file(category, name))
        if name.endswith(".json"):
            admitted.append(source)
        elif category == _RECEIPTS and _receipt_reservation_name(name):
            sidecars.append(source)
        else:
            invalid.append(source.path)
    return tuple(admitted), tuple(sidecars), tuple(invalid)


def _package_topology(
    snapshot: CurrentRecordSnapshot,
    record_root: Path,
    package: str,
) -> tuple[_CurrentPayload | None, _CurrentPayload | None, Path | None]:
    names, state = snapshot.open_directory(package)
    package_root = record_root / package
    if state != "valid":
        return None, None, package_root
    if "manifest.json" not in names:
        if package.endswith(".clear-quarantine"):
            return (
                None,
                _CurrentPayload(
                    path=package_root,
                    content=None,
                    payload_sha256={name: snapshot.digest_file(package, name) for name in names},
                    package_names=set(names),
                    payload_identities={
                        name: snapshot.file_identity(package, name) for name in names
                    },
                    entry_identity=snapshot.root_entry_identity(package),
                ),
                None,
            )
        return None, None, package_root
    return (
        _CurrentPayload(
            path=package_root / "manifest.json",
            content=snapshot.read_file(package, "manifest.json"),
            payload_sha256={name: snapshot.digest_file(package, name) for name in names},
            package_names=set(names),
            payload_identities={name: snapshot.file_identity(package, name) for name in names},
            entry_identity=snapshot.root_entry_identity(package),
        ),
        None,
        None,
    )


def _receipt_reservation_name(name: str) -> bool:
    return name.startswith(".") and name.endswith(".receipt-reservation")


def _records_with_conflicts(
    root: Path,
    record_root: Path,
    category: str,
    sources: tuple[_CurrentPayload, ...],
    validator: Callable[[dict[str, object]], dict[str, object]],
) -> tuple[dict[str, dict[str, object]], set[str], list[Path]]:
    records: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    invalid_paths: list[Path] = []
    for source in sources:
        current = _read_current_payload(source, validator)
        if current is None:
            invalid_paths.append(source.path)
            continue
        payload, content_sha256 = current
        decision_id = str(payload["decision_id"])
        if not canonical_record_name(
            root=root,
            record_root=record_root,
            category=category,
            path=source.path,
            payload=payload,
        ):
            invalid_paths.append(source.path)
            continue
        projected = {
            **payload,
            "physical_path": source.path,
            "record_path": display_path(root, source.path),
            "content_sha256": content_sha256,
        }
        existing = records.get(decision_id)
        if existing and existing["content_sha256"] != content_sha256:
            conflicts.add(decision_id)
            continue
        records.setdefault(decision_id, projected)
    return records, conflicts, invalid_paths


def _manifests_with_conflicts(
    root: Path,
    sources: tuple[_CurrentPayload, ...],
    clears: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], set[str], list[Path]]:
    records: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    invalid_paths: list[Path] = []
    rejected: set[str] = set()
    for source in sources:
        current = _read_current_payload(source, validated_manifest)
        if current is None:
            invalid_paths.append(source.path)
            continue
        payload, content_sha256 = current
        decision_id = str(payload["decision_id"])
        package_name = source.path.parent.name
        quarantine_identity = clear_quarantine_identity(package_name, decision_id)
        quarantined = quarantine_identity is not None
        complete = (
            source.payload_sha256 is not None
            and source.package_names is not None
            and preservation_payloads_match(payload, source.payload_sha256, source.package_names)
        )
        resumable = (
            quarantined
            and source.entry_identity == quarantine_identity
            and clears.get(decision_id, {}).get("manifest_sha256") == content_sha256
            and source.payload_sha256 is not None
            and source.package_names is not None
            and quarantined_payloads_match(payload, source.payload_sha256, source.package_names)
        )
        if package_name != decision_id and not quarantined:
            invalid_paths.append(source.path)
            continue
        if (quarantined and not resumable) or (not quarantined and not complete):
            invalid_paths.append(source.path)
            continue
        if decision_id in rejected:
            invalid_paths.append(source.path)
            continue
        existing = records.get(decision_id)
        if existing:
            if existing["manifest_sha256"] != content_sha256:
                conflicts.add(decision_id)
            invalid_paths.extend([cast("Path", existing["physical_path"]), source.path])
            records.pop(decision_id)
            rejected.add(decision_id)
            continue
        records[decision_id] = {
            "physical_path": source.path,
            "package_path": display_path(root, source.path.parent),
            "record_path": display_path(root, source.path),
            "copy_count": 1,
            "manifest_sha256": content_sha256,
            "lane_ref": payload["lane_ref"],
            "head": payload["head"],
            "observation_digest": payload["observation_digest"],
            "quarantined": quarantined,
            "quarantine_name": package_name if quarantined else "",
            "package_identity": source.entry_identity,
            "package_names": source.package_names,
            "payload_sha256": source.payload_sha256,
            "payload_identities": source.payload_identities,
        }
    return records, conflicts, invalid_paths


def _read_current_payload(
    source: _CurrentPayload,
    validator: Callable[[dict[str, object]], dict[str, object]],
) -> tuple[dict[str, object], str] | None:
    content = source.content
    if content is None:
        return None
    try:
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return None
        canonical = validator(payload)
        if canonical != payload or content != canonical_current_record_bytes(canonical):
            return None
    except (KeyError, OverflowError, RecursionError, TypeError, UnicodeDecodeError, ValueError):
        return None
    return canonical, hashlib.sha256(content).hexdigest()


def _receipt_reservations(
    root: Path,
    record_root: Path,
    sources: tuple[_CurrentPayload, ...],
) -> tuple[dict[str, dict[str, object]], list[Path]]:
    records: dict[str, dict[str, object]] = {}
    invalid_paths: list[Path] = []
    for source in sources:
        content = source.content
        try:
            decision_id = content.decode().removesuffix("\n") if content is not None else ""
        except UnicodeDecodeError:
            decision_id = ""
        completion = receipt_path(root, decision_id, artifact_root=record_root)
        expected = completion.with_name(f".{completion.stem}.receipt-reservation")
        if (
            not valid_decision_id(decision_id)
            or content != f"{decision_id}\n".encode()
            or source.path.name != expected.name
        ):
            invalid_paths.append(source.path)
            continue
        records.setdefault(
            decision_id,
            {
                "decision_id": decision_id,
                "reservation_path": display_path(root, source.path),
                "phase": "unknown",
                "recovery_state": "transition_unknown",
            },
        )
    return records, invalid_paths

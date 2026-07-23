"""Durable local receipts and retention operations for lane resolution."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

import ethos.adapters.mutation.resolution.records.inventory as records_inventory
from ethos.adapters.mutation.resolution._shared import artifact_roots
from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.core import clear_receipt_path
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.core import target_digest
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt

_DECISIONS, _RECEIPTS, _CLEARS, _RESERVATIONS = (
    "decisions",
    "receipts",
    "clears",
    "reservations",
)
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_PRESERVATION_MANIFEST_INVALID = "lane_resolution_preservation_manifest_invalid"
_PRESERVATION_PACKAGE_INVALID = "lane_resolution_preservation_package_invalid"
_PRESERVATION_PACKAGE_OUTSIDE_ROOT = "lane_resolution_preservation_package_outside_root"


def canonical_resolution_decision_snapshot(
    *, decision_bytes: bytes, decision: dict[str, object]
) -> tuple[dict[str, object], str]:
    """Return one strict canonical decision snapshot and its validation gap."""
    try:
        payload = json.loads(decision_bytes)
        source = payload if isinstance(payload, dict) else {}
        model = LaneResolutionDecision.model_validate_json(
            json.dumps(
                {field: source[field] for field in LaneResolutionDecision.model_fields},
                allow_nan=False,
            )
        )
    except (KeyError, TypeError, ValueError, UnicodeDecodeError):
        return {}, "lane_resolution_ownerless_decision_invalid"
    snapshot = model.to_payload()
    if not _same_canonical_payload(payload, snapshot) or not _same_canonical_payload(
        decision, snapshot
    ):
        return {}, "lane_resolution_ownerless_decision_stale"
    return snapshot, ""


def exact_ownerless_resolution_receipt(
    *,
    receipt: dict[str, object] | None,
    decision: dict[str, object],
    observation: object,
    expected_binding: dict[str, object],
) -> bool:
    """Match one immutable ownerless receipt to its complete decision binding."""
    if receipt is None:
        return False
    try:
        canonical_receipt = LaneResolutionReceipt.model_validate(receipt).to_payload()
    except ValueError:
        return False
    if not _same_canonical_payload(receipt, canonical_receipt):
        return False
    lane_ref = str(getattr(observation, "lane_ref", ""))
    head = str(getattr(observation, "head", ""))
    digest = getattr(observation, "digest", None)
    return (
        callable(digest)
        and canonical_receipt.get("decision_id") == decision.get("decision_id")
        and canonical_receipt.get("lane_ref") == lane_ref
        and canonical_receipt.get("head") == head
        and canonical_receipt.get("observation_digest") == digest()
        and canonical_receipt.get("state") == "retired"
        and canonical_receipt.get("preservation_package") == ""
        and canonical_receipt.get("preservation_manifest_sha256") == ""
        and canonical_receipt.get("reconciliation_required") is bool(decision.get("break_glass"))
        and canonical_receipt.get("ownerless_closeout_binding") == expected_binding
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _same_canonical_payload(left: object, right: object) -> bool:
    try:
        return _canonical_json(left) == _canonical_json(right)
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True, slots=True)
class LaneResolutionClearRequest:
    """Exact request envelope for one irreversible package-clear operation."""

    decision_id: str
    expect_manifest_sha256: str
    chronicle_ref: str
    reason: str
    break_glass: bool
    confirm_irreversible: bool
    apply: bool


def write_resolution_receipt(
    *,
    root: Path,
    receipt: dict[str, object],
    artifact_root: Path | None = None,
    require_ownerless_closeout_binding: bool = False,
) -> str:
    """Validate and atomically materialize one immutable completion receipt."""
    payload = _validated_resolution_receipt(
        root=root,
        receipt=receipt,
        require_ownerless_closeout_binding=require_ownerless_closeout_binding,
    )
    destination = receipt_path(
        root,
        str(payload["decision_id"]),
        artifact_root=artifact_root,
    )
    record_root = artifact_root or records_artifact_root(root)
    write_json_atomic(destination, payload, record_root=record_root)
    return display_path(root, destination)


def read_resolution_receipt(
    *,
    root: Path,
    decision_id: str,
    artifact_root: Path | None = None,
    require_ownerless_closeout_binding: bool = False,
) -> tuple[dict[str, object], str] | None:
    """Read one deterministic immutable receipt without weakening write validation."""
    record_root = artifact_root or records_artifact_root(root)
    destination = receipt_path(root, decision_id, artifact_root=record_root)
    if not destination.exists() and not destination.is_symlink():
        return None
    if not record_destination_safe(record_root, destination) or destination.is_symlink():
        raise OSError(_RECORD_PATH_UNSAFE)
    try:
        receipt = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(_RECEIPT_INVALID) from error
    if not isinstance(receipt, dict):
        raise TypeError(_RECEIPT_INVALID)
    payload = _validated_resolution_receipt(
        root=root,
        receipt=receipt,
        require_ownerless_closeout_binding=require_ownerless_closeout_binding,
    )
    if payload["decision_id"] != decision_id:
        raise ValueError(_RECEIPT_INVALID)
    return payload, display_path(root, destination)


def _validated_resolution_receipt(
    *,
    root: Path,
    receipt: dict[str, object],
    require_ownerless_closeout_binding: bool,
) -> dict[str, object]:
    try:
        payload = LaneResolutionReceipt.model_validate(receipt).to_payload()
    except ValueError as error:
        raise ValueError(_RECEIPT_INVALID) from error
    if require_ownerless_closeout_binding and not _same_canonical_payload(receipt, payload):
        raise ValueError(_RECEIPT_INVALID)
    if require_ownerless_closeout_binding and "ownerless_closeout_binding" not in payload:
        raise ValueError(_RECEIPT_INVALID)
    binding = payload.get("ownerless_closeout_binding")
    if isinstance(binding, dict) and binding.get("target_digest") != target_digest(
        str(payload["lane_ref"]), str(payload["head"])
    ):
        raise ValueError(_RECEIPT_INVALID)
    if not valid_decision_id(str(payload["decision_id"])):
        raise ValueError(_RECEIPT_INVALID)
    _validate_schema(root, "lane-resolution-receipt.schema.json", payload)
    return payload


def verify_preservation_package(
    *,
    root: Path,
    package: dict[str, object],
    artifact_root: Path | None = None,
) -> None:
    """Fail closed unless the preservation package is complete and digest-bound."""
    raw_path = Path(str(package.get("path") or ""))
    destination = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    allowed_roots = (
        (artifact_root.resolve(),) if artifact_root is not None else artifact_roots(root)
    )
    allowed = any(destination.is_relative_to(candidate) for candidate in allowed_roots)
    if not allowed:
        raise ValueError(_PRESERVATION_PACKAGE_OUTSIDE_ROOT)
    manifest = _preservation_manifest(destination, package)
    checks = (("repository.bundle", "bundle_sha256"), ("tracked.patch", "patch_sha256"))
    invalid = any(
        (path := destination / name).is_symlink()
        or not path.is_file()
        or sha256_digest(path) != str(manifest.get(key) or "")
        for name, key in checks
    )
    archive, archive_digest = (
        destination / "untracked.tar",
        str(manifest.get("untracked_archive_sha256") or ""),
    )
    if invalid or (
        archive_digest
        and (
            archive.is_symlink()
            or not archive.is_file()
            or sha256_digest(archive) != archive_digest
        )
    ):
        raise ValueError(_PRESERVATION_PACKAGE_INVALID)


def _preservation_manifest(destination: Path, package: dict[str, object]) -> dict[str, object]:
    supplied_manifest = package.get("manifest")
    manifest_path = destination / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        if not isinstance(supplied_manifest, dict):
            raise TypeError(_PRESERVATION_MANIFEST_INVALID)
        raise ValueError(_PRESERVATION_PACKAGE_INVALID)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TypeError(_PRESERVATION_MANIFEST_INVALID) from error
    if not isinstance(manifest, dict) or not valid_decision_id(
        str(manifest.get("decision_id") or "")
    ):
        raise TypeError(_PRESERVATION_MANIFEST_INVALID)
    expected_manifest = str(package.get("manifest_sha256") or "")
    actual_manifest = sha256_digest(manifest_path)
    if expected_manifest and expected_manifest != actual_manifest:
        raise ValueError(_PRESERVATION_PACKAGE_INVALID)
    if supplied_manifest is not None:
        if not isinstance(supplied_manifest, dict):
            raise TypeError(_PRESERVATION_MANIFEST_INVALID)
        if supplied_manifest != manifest:
            raise ValueError(_PRESERVATION_PACKAGE_INVALID)
    return manifest


def lane_resolution_inventory(*, root: Path) -> dict[str, object]:
    """Return a read-only reconciliation view over local resolution artifacts."""
    try:
        return records_inventory.lane_resolution_inventory(
            root=root,
            readers=records_inventory.LaneResolutionInventoryReaders(
                artifact_roots=artifact_roots,
                manifests_with_conflicts=_manifests_with_conflicts,
                records_with_conflicts=_records_with_conflicts,
                unsafe_package_path_present=_unsafe_package_path_present,
                unsafe_record_path_present=_unsafe_record_path_present,
            ),
        )
    except ValueError as error:
        gap = _records_owner_gap(error)
        return {
            "ok": False,
            "state": "blocked",
            "summary": {
                "package_count": 0,
                "receipt_count": 0,
                "clear_count": 0,
                "inflight_count": 0,
                "partial_count": 0,
            },
            "entries": [],
            "conflicting_decision_ids": [],
            "integrity_decision_ids": [],
            "required_gaps": [gap],
        }


def clear_lane_resolution_package(
    *, root: Path, request: LaneResolutionClearRequest
) -> dict[str, object]:
    """Clear exactly one retained package after its bounded evidence review."""
    try:
        return _clear_lane_resolution_package(root=root, request=request)
    except ValueError as error:
        return {
            "ok": False,
            "state": "blocked",
            "decision_id": request.decision_id,
            "clear_receipt_path": "",
            "required_gaps": [_records_owner_gap(error)],
        }


def _clear_lane_resolution_package(
    *, root: Path, request: LaneResolutionClearRequest
) -> dict[str, object]:
    manifests, manifest_conflicts = _manifests_with_conflicts(root)
    unsafe_package_path = _unsafe_package_path_present(root)
    unsafe_record_path = _unsafe_record_path_present(root)
    conflicts = set(manifest_conflicts)
    receipts: dict[str, dict[str, str]] = {}
    for category, schema in (
        (_DECISIONS, "lane-resolution-decision.schema.json"),
        (_RECEIPTS, "lane-resolution-receipt.schema.json"),
        (_CLEARS, "lane-resolution-clear-receipt.schema.json"),
    ):
        category_records, category_conflicts = _records_with_conflicts(root, category, schema)
        if category == _RECEIPTS:
            receipts = category_records
        conflicts.update(category_conflicts)
    manifest = manifests.get(request.decision_id, {})
    actual = str(manifest.get("manifest_sha256") or "")
    receipt_present = request.decision_id in receipts
    receipt_manifest = str(
        receipts.get(request.decision_id, {}).get("preservation_manifest_sha256") or ""
    )
    copy_count = manifest.get("copy_count")
    ambiguous = (
        request.decision_id not in conflicts and isinstance(copy_count, int) and copy_count > 1
    )
    receipt_mismatch = bool(manifest and receipt_present and actual != receipt_manifest)
    chronicle, digest, chronicle_gaps = _clear_chronicle(root, request.chronicle_ref)
    gaps = [
        *(
            ["lane_resolution_decision_invalid"]
            if not valid_decision_id(request.decision_id)
            else []
        ),
        *(["lane_resolution_decision_record_conflict"] if request.decision_id in conflicts else []),
        *(["lane_resolution_package_path_unsafe"] if unsafe_package_path else []),
        *(["lane_resolution_record_path_unsafe"] if unsafe_record_path else []),
        *(["lane_resolution_clear_package_ambiguous"] if ambiguous else []),
        *(["lane_resolution_manifest_receipt_mismatch"] if receipt_mismatch else []),
        *(["lane_resolution_clear_package_missing"] if not manifest else []),
        *(["lane_resolution_clear_reason_required"] if not request.reason.strip() else []),
        *(["lane_resolution_clear_requires_break_glass"] if not request.break_glass else []),
        *(["irreversible_confirmation_required"] if not request.confirm_irreversible else []),
        *(
            ["lane_resolution_clear_manifest_mismatch"]
            if actual != request.expect_manifest_sha256
            else []
        ),
        *chronicle_gaps,
    ]
    report: dict[str, object] = {
        "ok": not gaps,
        "state": "blocked" if gaps else "clearing" if request.apply else "planned",
        "decision_id": request.decision_id,
        "clear_receipt_path": "",
        "required_gaps": list(dict.fromkeys(gaps)),
    }
    if not request.apply or gaps:
        return report
    receipt = LaneResolutionClearReceipt(
        clear_receipt_id=f"lane-resolution-clear-receipt:{uuid.uuid4()}",
        decision_id=request.decision_id,
        manifest_sha256=actual,
        chronicle_ref=chronicle,
        chronicle_digest=digest,
        reason=request.reason.strip(),
        completed=True,
        mints_authority=False,
    ).to_payload()
    _validate_schema(root, "lane-resolution-clear-receipt.schema.json", receipt)
    record_root = records_artifact_root(root)
    receipt_path = clear_receipt_path(root, request.decision_id)
    if not record_destination_safe(record_root, receipt_path):
        report.update(
            ok=False,
            state="blocked",
            required_gaps=["lane_resolution_clear_receipt_path_unsafe"],
        )
        return report
    write_json_atomic(receipt_path, receipt, record_root=record_root)
    package_path = Path(str(manifest["package_path"]))
    if not package_path.is_absolute():
        package_path = root / package_path
    if not _package_path_safe(root, package_path):
        receipt_path.unlink(missing_ok=True)
        report.update(
            ok=False,
            state="blocked",
            required_gaps=["lane_resolution_package_path_unsafe"],
        )
        return report
    manifest_path = package_path / "manifest.json"
    if sha256_digest(manifest_path) != actual:
        receipt_path.unlink(missing_ok=True)
        report.update(
            ok=False,
            state="blocked",
            required_gaps=["lane_resolution_clear_manifest_mismatch"],
        )
        return report
    try:
        shutil.rmtree(package_path)
    except OSError:
        receipt_path.unlink(missing_ok=True)
        report.update(
            ok=False, state="blocked", required_gaps=["lane_resolution_clear_remove_failed"]
        )
        return report
    report.update(state="cleared", clear_receipt_path=display_path(root, receipt_path))
    return report


def _records_owner_gap(error: ValueError) -> str:
    gap = str(error).strip()
    if gap == "lane_resolution_accepted_control_root_unavailable":
        return gap
    raise error


def _unsafe_package_path_present(root: Path) -> bool:
    for artifact_root in artifact_roots(root):
        if not record_destination_safe(artifact_root, artifact_root):
            return True
        if not artifact_root.exists():
            continue
        try:
            entries = tuple(artifact_root.iterdir())
        except OSError:
            return True
        for entry in entries:
            if entry.name in {_DECISIONS, _RECEIPTS, _CLEARS}:
                continue
            if entry.is_symlink() or (entry / "manifest.json").is_symlink():
                return True
    return False


def _unsafe_record_path_present(root: Path) -> bool:
    return any(
        (artifact_root / category).is_symlink()
        for artifact_root in artifact_roots(root)
        for category in (_DECISIONS, _RECEIPTS, _CLEARS, _RESERVATIONS)
    )


def _package_path_safe(root: Path, package_path: Path) -> bool:
    return any(
        record_destination_safe(artifact_root, package_path)
        and record_destination_safe(artifact_root, package_path / "manifest.json")
        for artifact_root in artifact_roots(root)
    )


def _manifests_with_conflicts(
    root: Path,
) -> tuple[dict[str, dict[str, object]], set[str]]:
    records: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    for artifact_root in artifact_roots(root):
        for path in sorted(artifact_root.glob("*/manifest.json")):
            if not _package_path_safe(root, path.parent):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                decision_id = str(payload["decision_id"])
                if not valid_decision_id(decision_id):
                    continue
                content_sha256 = sha256_digest(path)
            except (OSError, TypeError, ValueError, KeyError):
                continue
            existing = records.get(decision_id)
            package_path = display_path(root, path.parent)
            if existing:
                copy_count = existing.get("copy_count")
                existing["copy_count"] = copy_count + 1 if isinstance(copy_count, int) else 2
                if existing["manifest_sha256"] != content_sha256:
                    conflicts.add(decision_id)
                continue
            records.setdefault(
                decision_id,
                {
                    "package_path": package_path,
                    "copy_count": 1,
                    "manifest_sha256": content_sha256,
                    "lane_ref": str(payload.get("lane_ref") or ""),
                    "head": str(payload.get("head") or ""),
                },
            )
    return records, conflicts


def _records_with_conflicts(
    root: Path, category: str, schema: str
) -> tuple[dict[str, dict[str, str]], set[str]]:
    records: dict[str, dict[str, str]] = {}
    conflicts: set[str] = set()
    for artifact_root in artifact_roots(root):
        category_root = artifact_root / category
        if category_root.is_symlink():
            continue
        for path in sorted(category_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not validate_schema_instance(schema, payload, root=root)["ok"]:
                    continue
                decision_id = str(payload["decision_id"])
                if not valid_decision_id(decision_id):
                    continue
                content_sha256 = sha256_digest(path)
            except (OSError, TypeError, ValueError, KeyError):
                continue
            existing = records.get(decision_id)
            if existing and existing["content_sha256"] != content_sha256:
                conflicts.add(decision_id)
                continue
            records.setdefault(
                decision_id,
                {
                    **{key: value for key, value in payload.items() if isinstance(value, str)},
                    "record_path": display_path(root, path),
                    "content_sha256": content_sha256,
                },
            )
    return records, conflicts


def _clear_chronicle(root: Path, chronicle_ref: str) -> tuple[str, str, list[str]]:
    candidate = (root / chronicle_ref).resolve()
    try:
        relative = candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return "", "", ["lane_resolution_clear_chronicle_outside_repository"]
    if not relative.startswith("evidence/chronicle/") or not candidate.is_file():
        return relative, "", ["lane_resolution_clear_chronicle_missing"]
    if "lane_resolution/clear-preservation" not in candidate.read_text(encoding="utf-8"):
        return relative, "", ["lane_resolution_clear_chronicle_disposition_mismatch"]
    return relative, sha256_digest(candidate), []


def _validate_schema(root: Path, schema: str, payload: dict[str, object]) -> None:
    if not validate_schema_instance(schema, payload, root=root)["ok"]:
        raise ValueError(_RECEIPT_INVALID)

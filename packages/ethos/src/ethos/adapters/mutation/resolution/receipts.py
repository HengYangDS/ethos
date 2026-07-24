"""Durable local receipts and retention operations for lane resolution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import preservation_payloads_match
from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

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
    except (KeyError, OverflowError, RecursionError, TypeError, ValueError, UnicodeDecodeError):
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


def canonical_resolution_payload_digest(value: object) -> str:
    """Return the SHA-256 digest of one canonical resolution payload."""
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _same_canonical_payload(left: object, right: object) -> bool:
    try:
        return _canonical_json(left) == _canonical_json(right)
    except (TypeError, ValueError):
        return False


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
    record_root = artifact_root or current_record_root(root)
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
    record_root = artifact_root or current_record_root(root)
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
    allowed_root = (artifact_root or current_record_root(root)).resolve()
    allowed = destination.is_relative_to(allowed_root)
    if not allowed:
        raise ValueError(_PRESERVATION_PACKAGE_OUTSIDE_ROOT)
    manifest = _preservation_manifest(destination, package)
    payload_sha256 = {
        name: None if path.is_symlink() or not path.is_file() else sha256_digest(path)
        for name in ("repository.bundle", "tracked.patch", "index.patch", "untracked.tar")
        for path in (destination / name,)
    }
    present_names = {entry.name for entry in destination.iterdir()}
    if not preservation_payloads_match(manifest, payload_sha256, present_names):
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
    except (OSError, OverflowError, RecursionError, json.JSONDecodeError) as error:
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


def _validate_schema(root: Path, schema: str, payload: dict[str, object]) -> None:
    if not validate_schema_instance(schema, payload, root=root)["ok"]:
        raise ValueError(_RECEIPT_INVALID)

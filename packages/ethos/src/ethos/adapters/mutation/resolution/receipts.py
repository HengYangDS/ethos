"""Durable local receipts and retention operations for lane resolution."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt

_ARTIFACT_ROOT = Path("build/artifacts/lane-resolution")
_RECEIPTS, _CLEARS = "receipts", "clears"
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_PRESERVATION_MANIFEST_INVALID = "lane_resolution_preservation_manifest_invalid"
_PRESERVATION_PACKAGE_INVALID = "lane_resolution_preservation_package_invalid"
_PRESERVATION_PACKAGE_OUTSIDE_ROOT = "lane_resolution_preservation_package_outside_root"


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


def write_resolution_receipt(*, root: Path, receipt: dict[str, object]) -> str:
    """Validate and atomically materialize one immutable completion receipt."""
    payload = LaneResolutionReceipt.model_validate(receipt).to_payload()
    _validate_schema(root, "lane-resolution-receipt.schema.json", payload)
    destination = _receipt_path(root, str(payload["decision_id"]))
    _write_json_atomic(destination, payload)
    return destination.relative_to(root).as_posix()


def verify_preservation_package(*, root: Path, package: dict[str, object]) -> None:
    """Fail closed unless the preservation package is complete and digest-bound."""
    destination = (root / str(package.get("path") or "")).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(_PRESERVATION_PACKAGE_OUTSIDE_ROOT) from exc
    manifest = package.get("manifest")
    if not isinstance(manifest, dict):
        raise TypeError(_PRESERVATION_MANIFEST_INVALID)
    checks = (("repository.bundle", "bundle_sha256"), ("tracked.patch", "patch_sha256"))
    invalid = any(
        not (path := destination / name).is_file()
        or sha256_digest(path) != str(manifest.get(key) or "")
        for name, key in checks
    )
    archive, archive_digest = (
        destination / "untracked.tar",
        str(manifest.get("untracked_archive_sha256") or ""),
    )
    if invalid or (
        archive_digest and (not archive.is_file() or sha256_digest(archive) != archive_digest)
    ):
        raise ValueError(_PRESERVATION_PACKAGE_INVALID)


def lane_resolution_inventory(*, root: Path) -> dict[str, object]:
    """Return a read-only reconciliation view over local resolution artifacts."""
    manifests = _manifests(root)
    receipts = _records(root, _RECEIPTS, "lane-resolution-receipt.schema.json")
    clears = _records(root, _CLEARS, "lane-resolution-clear-receipt.schema.json")
    entries = []
    for decision_id in sorted(set(manifests) | set(receipts) | set(clears)):
        manifest, receipt, clear = (
            manifests.get(decision_id, {}),
            receipts.get(decision_id, {}),
            clears.get(decision_id, {}),
        )
        state = (
            "cleared"
            if clear
            else "retained"
            if manifest and receipt
            else "receipt_only"
            if receipt
            else "unindexed"
        )
        entries.append(
            {
                "decision_id": decision_id,
                "lane_ref": str(manifest.get("lane_ref") or receipt.get("lane_ref") or ""),
                "head": str(manifest.get("head") or receipt.get("head") or ""),
                "state": state,
                "receipt_path": str(receipt.get("record_path") or ""),
                "package_path": str(
                    manifest.get("package_path") or receipt.get("preservation_package") or ""
                ),
                "manifest_sha256": str(
                    manifest.get("manifest_sha256")
                    or receipt.get("preservation_manifest_sha256")
                    or ""
                ),
            }
        )
    return {
        "ok": True,
        "state": "ready",
        "summary": {
            "package_count": len(manifests),
            "receipt_count": len(receipts),
            "clear_count": len(clears),
        },
        "entries": entries,
        "required_gaps": [],
    }


def clear_lane_resolution_package(
    *, root: Path, request: LaneResolutionClearRequest
) -> dict[str, object]:
    """Clear exactly one retained package after its bounded evidence review."""
    manifest = _manifests(root).get(request.decision_id, {})
    actual = str(manifest.get("manifest_sha256") or "")
    chronicle, digest, chronicle_gaps = _clear_chronicle(root, request.chronicle_ref)
    gaps = [
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
    receipt_path = _clear_receipt_path(root, request.decision_id)
    _write_json_atomic(receipt_path, receipt)
    try:
        shutil.rmtree(root / str(manifest["package_path"]))
    except OSError:
        receipt_path.unlink(missing_ok=True)
        report.update(
            ok=False, state="blocked", required_gaps=["lane_resolution_clear_remove_failed"]
        )
        return report
    report.update(state="cleared", clear_receipt_path=receipt_path.relative_to(root).as_posix())
    return report


def _manifests(root: Path) -> dict[str, dict[str, str]]:
    records = {}
    for path in sorted((root / _ARTIFACT_ROOT).glob("*/manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            decision_id = str(payload["decision_id"])
        except (OSError, TypeError, ValueError, KeyError):
            continue
        records[decision_id] = {
            "package_path": path.parent.relative_to(root).as_posix(),
            "manifest_sha256": sha256_digest(path),
            "lane_ref": str(payload.get("lane_ref") or ""),
            "head": str(payload.get("head") or ""),
        }
    return records


def _records(root: Path, category: str, schema: str) -> dict[str, dict[str, str]]:
    records = {}
    for path in sorted((root / _ARTIFACT_ROOT / category).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not validate_schema_instance(schema, payload, root=root)["ok"]:
                continue
            decision_id = str(payload["decision_id"])
        except (OSError, TypeError, ValueError, KeyError):
            continue
        records[decision_id] = {
            **{key: value for key, value in payload.items() if isinstance(value, str)},
            "record_path": path.relative_to(root).as_posix(),
        }
    return records


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


def _receipt_path(root: Path, decision_id: str) -> Path:
    return _record_path(root, _RECEIPTS, decision_id)


def _clear_receipt_path(root: Path, decision_id: str) -> Path:
    return _record_path(root, _CLEARS, decision_id)


def _record_path(root: Path, category: str, decision_id: str) -> Path:
    return (
        root
        / _ARTIFACT_ROOT
        / category
        / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"
    )


def _write_json_atomic(destination: Path, payload: dict[str, object]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise FileExistsError(destination) from error
    finally:
        temporary.unlink(missing_ok=True)


def _validate_schema(root: Path, schema: str, payload: dict[str, object]) -> None:
    if not validate_schema_instance(schema, payload, root=root)["ok"]:
        raise ValueError(_RECEIPT_INVALID)

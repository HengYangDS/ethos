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

from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.lane import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.lane import LaneResolutionReceipt

_ARTIFACT_ROOT = Path("build") / "artifacts" / "lane-resolution"
_RECEIPTS = "receipts"
_CLEARS = "clears"
_RECEIPT_INVALID = "lane_resolution_receipt_invalid"


@dataclass(frozen=True)
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
    validated = LaneResolutionReceipt.model_validate(receipt).to_payload()
    _validate_schema(root, "lane-resolution-receipt.schema.json", validated)
    destination = _receipt_path(root, str(validated["decision_id"]))
    _write_json_atomic(destination, validated)
    return destination.relative_to(root).as_posix()


def lane_resolution_inventory(*, root: Path) -> dict[str, object]:
    """Return a read-only reconciliation view over local resolution artifacts."""
    manifests = _manifests(root)
    receipts = _records(root, _RECEIPTS, "lane-resolution-receipt.schema.json")
    clears = _records(root, _CLEARS, "lane-resolution-clear-receipt.schema.json")
    decision_ids = sorted(set(manifests) | set(receipts) | set(clears))
    entries: list[dict[str, str]] = []
    for decision_id in decision_ids:
        manifest = manifests.get(decision_id, {})
        receipt = receipts.get(decision_id, {})
        clear = clears.get(decision_id, {})
        package_path = str(
            manifest.get("package_path") or receipt.get("preservation_package") or ""
        )
        manifest_sha256 = str(
            manifest.get("manifest_sha256") or receipt.get("preservation_manifest_sha256") or ""
        )
        state = "cleared" if clear else "retained" if manifest and receipt else "unindexed"
        if not manifest and receipt and not clear:
            state = "receipt_only"
        entries.append(
            {
                "decision_id": decision_id,
                "lane_ref": str(manifest.get("lane_ref") or receipt.get("lane_ref") or ""),
                "head": str(manifest.get("head") or receipt.get("head") or ""),
                "state": state,
                "receipt_path": str(receipt.get("record_path") or ""),
                "package_path": package_path,
                "manifest_sha256": manifest_sha256,
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
    *,
    root: Path,
    request: LaneResolutionClearRequest,
) -> dict[str, object]:
    """Clear exactly one retained package after its bounded evidence review."""
    manifests = _manifests(root)
    manifest = manifests.get(request.decision_id, {})
    gaps: list[str] = []
    if not manifest:
        gaps.append("lane_resolution_clear_package_missing")
    if not request.reason.strip():
        gaps.append("lane_resolution_clear_reason_required")
    if not request.break_glass:
        gaps.append("lane_resolution_clear_requires_break_glass")
    if not request.confirm_irreversible:
        gaps.append("irreversible_confirmation_required")
    actual_manifest = str(manifest.get("manifest_sha256") or "")
    if actual_manifest != request.expect_manifest_sha256:
        gaps.append("lane_resolution_clear_manifest_mismatch")
    chronicle_path, chronicle_digest, chronicle_gaps = _clear_chronicle(root, request.chronicle_ref)
    gaps.extend(chronicle_gaps)
    report: dict[str, object] = {
        "ok": not gaps,
        "state": "planned" if not gaps and not request.apply else "blocked" if gaps else "clearing",
        "decision_id": request.decision_id,
        "clear_receipt_path": "",
        "required_gaps": list(dict.fromkeys(gaps)),
    }
    if not request.apply or report["required_gaps"]:
        return report
    clear_receipt = LaneResolutionClearReceipt(
        clear_receipt_id=f"lane-resolution-clear-receipt:{uuid.uuid4()}",
        decision_id=request.decision_id,
        manifest_sha256=actual_manifest,
        chronicle_ref=chronicle_path,
        chronicle_digest=chronicle_digest,
        reason=request.reason.strip(),
        completed=True,
        mints_authority=False,
    ).to_payload()
    _validate_schema(root, "lane-resolution-clear-receipt.schema.json", clear_receipt)
    receipt_path = _clear_receipt_path(root, request.decision_id)
    _write_json_atomic(receipt_path, clear_receipt)
    package = root / str(manifest["package_path"])
    try:
        shutil.rmtree(package)
    except OSError:
        receipt_path.unlink(missing_ok=True)
        report.update(
            ok=False,
            state="blocked",
            required_gaps=["lane_resolution_clear_remove_failed"],
        )
        return report
    report.update(
        state="cleared",
        clear_receipt_path=receipt_path.relative_to(root).as_posix(),
    )
    return report


def _manifests(root: Path) -> dict[str, dict[str, str]]:
    base = root / _ARTIFACT_ROOT
    records: dict[str, dict[str, str]] = {}
    for path in sorted(base.glob("*/manifest.json")) if base.exists() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            decision_id = str(payload["decision_id"])
        except (OSError, TypeError, ValueError, KeyError):
            continue
        records[decision_id] = {
            "package_path": path.parent.relative_to(root).as_posix(),
            "manifest_sha256": _sha256(path),
            "lane_ref": str(payload.get("lane_ref") or ""),
            "head": str(payload.get("head") or ""),
        }
    return records


def _records(root: Path, category: str, schema: str) -> dict[str, dict[str, str]]:
    directory = root / _ARTIFACT_ROOT / category
    records: dict[str, dict[str, str]] = {}
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not validate_schema_instance(schema, payload, root=root)["ok"]:
                continue
            decision_id = str(payload["decision_id"])
        except (OSError, TypeError, ValueError, KeyError):
            continue
        records[decision_id] = {
            **{key: str(value) for key, value in payload.items() if isinstance(value, str)},
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
    return relative, _sha256(candidate), []


def _receipt_path(root: Path, decision_id: str) -> Path:
    return root / _ARTIFACT_ROOT / _RECEIPTS / f"{_decision_digest(decision_id)}.json"


def _clear_receipt_path(root: Path, decision_id: str) -> Path:
    return root / _ARTIFACT_ROOT / _CLEARS / f"{_decision_digest(decision_id)}.json"


def _decision_digest(decision_id: str) -> str:
    return hashlib.sha256(decision_id.encode()).hexdigest()


def _write_json_atomic(destination: Path, payload: dict[str, object]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

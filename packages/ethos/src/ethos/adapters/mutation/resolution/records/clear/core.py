"""Irreversible identity-bound clearing of current preservation packages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos.adapters.mutation.resolution._shared import sha256_digest
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.clear.quarantine import exact_clear_receipt
from ethos.adapters.mutation.resolution.records.clear.quarantine import exact_package_binding
from ethos.adapters.mutation.resolution.records.clear.quarantine import package_path_safe
from ethos.adapters.mutation.resolution.records.clear.quarantine import unsafe_package_path_present
from ethos.adapters.mutation.resolution.records.clear.quarantine import unsafe_record_path_present
from ethos.adapters.mutation.resolution.records.core import clear_quarantine_path
from ethos.adapters.mutation.resolution.records.core import clear_receipt_path
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.adapters.mutation.resolution.records.current.core import (
    read_current_lane_resolution_records,
)
from ethos.adapters.mutation.resolution.records.current.snapshot import QuarantinedPackageBinding
from ethos.adapters.mutation.resolution.records.current.snapshot import (
    move_current_package_to_quarantine,
)
from ethos.adapters.mutation.resolution.records.current.snapshot import remove_quarantined_package
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionClearReceipt

_RECEIPT_INVALID = "lane_resolution_receipt_invalid"
_PACKAGE_IDENTITY_FIELD_COUNT = 3


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


@dataclass(frozen=True, slots=True)
class _ClearObservation:
    record_root: Path
    manifest: dict[str, object]
    quarantine: dict[str, object]
    existing_clear: dict[str, object]
    terminal: bool
    actual_manifest_sha256: str
    current_invalid: bool
    current_conflict: bool
    ambiguous: bool
    receipt_mismatch: bool
    canonical_retry_unsafe: bool


@dataclass(frozen=True, slots=True)
class _ClearPlan:
    observation: _ClearObservation
    clear_receipt: dict[str, object]
    gaps: tuple[str, ...]


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
    plan = _plan_clear(root, request)
    report = _clear_report(request, plan.gaps)
    if not request.apply or plan.gaps:
        return report
    return _apply_clear_plan(root, request, plan, report)


def _plan_clear(root: Path, request: LaneResolutionClearRequest) -> _ClearPlan:
    observation = _observe_clear(root, request.decision_id)
    chronicle, digest, chronicle_gaps = _clear_chronicle(root, request.chronicle_ref)
    clear_receipt = _clear_receipt_payload(request, observation, chronicle, digest)
    gaps = [
        *_record_state_gaps(root, observation, clear_receipt),
        *_request_gaps(request, observation.actual_manifest_sha256),
        *chronicle_gaps,
    ]
    return _ClearPlan(observation, clear_receipt, tuple(dict.fromkeys(gaps)))


def _observe_clear(root: Path, decision_id: str) -> _ClearObservation:
    record_root = current_record_root(root)
    current = read_current_lane_resolution_records(root=root, record_root=record_root)
    manifest = current.manifests.get(decision_id, {})
    quarantine = current.clear_quarantines.get(decision_id, {})
    existing_clear = current.clears.get(decision_id, {})
    terminal = bool(existing_clear and not manifest and not quarantine)
    actual = str(
        manifest.get("manifest_sha256")
        or quarantine.get("manifest_sha256")
        or existing_clear.get("manifest_sha256")
        or ""
    )
    receipt = current.receipts.get(decision_id, {})
    receipt_manifest = str(receipt.get("preservation_manifest_sha256") or "")
    copy_count = manifest.get("copy_count")
    ambiguous = decision_id not in current.conflicts and (
        (isinstance(copy_count, int) and copy_count > 1) or bool(manifest and quarantine)
    )
    return _ClearObservation(
        record_root=record_root,
        manifest=manifest,
        quarantine=quarantine,
        existing_clear=existing_clear,
        terminal=terminal,
        actual_manifest_sha256=actual,
        current_invalid=bool(current.invalid_count),
        current_conflict=bool(current.conflicts),
        ambiguous=ambiguous,
        receipt_mismatch=bool(receipt and actual != receipt_manifest),
        canonical_retry_unsafe=bool(
            existing_clear and manifest and manifest.get("quarantined") is not True
        ),
    )


def _clear_receipt_payload(
    request: LaneResolutionClearRequest,
    observation: _ClearObservation,
    chronicle: str,
    digest: str,
) -> dict[str, object]:
    clear_receipt_id = str(
        observation.existing_clear.get("clear_receipt_id")
        or f"lane-resolution-clear-receipt:{uuid.uuid4()}"
    )
    try:
        return LaneResolutionClearReceipt(
            schema_version=1,
            clear_receipt_id=clear_receipt_id,
            decision_id=request.decision_id,
            manifest_sha256=observation.actual_manifest_sha256,
            chronicle_ref=chronicle,
            chronicle_digest=digest,
            reason=request.reason.strip(),
            completed=True,
            mints_authority=False,
        ).to_payload()
    except ValueError:
        return {}


def _record_state_gaps(
    root: Path,
    observation: _ClearObservation,
    clear_receipt: dict[str, object],
) -> list[str]:
    missing = not observation.manifest and not observation.quarantine and not observation.terminal
    clear_receipt_mismatch = bool(
        observation.existing_clear
        and not exact_clear_receipt(observation.existing_clear, clear_receipt)
    )
    return [
        *(["lane_resolution_current_record_invalid"] if observation.current_invalid else []),
        *(["lane_resolution_decision_record_conflict"] if observation.current_conflict else []),
        *(["lane_resolution_package_path_unsafe"] if unsafe_package_path_present(root) else []),
        *(["lane_resolution_record_path_unsafe"] if unsafe_record_path_present(root) else []),
        *(["lane_resolution_clear_package_ambiguous"] if observation.ambiguous else []),
        *(["lane_resolution_manifest_receipt_mismatch"] if observation.receipt_mismatch else []),
        *(["lane_resolution_clear_receipt_mismatch"] if clear_receipt_mismatch else []),
        *(
            ["lane_resolution_clear_canonical_retry_unsafe"]
            if observation.canonical_retry_unsafe
            else []
        ),
        *(["lane_resolution_clear_package_missing"] if missing else []),
    ]


def _request_gaps(request: LaneResolutionClearRequest, actual_manifest_sha256: str) -> list[str]:
    return [
        *(
            ["lane_resolution_decision_invalid"]
            if not valid_decision_id(request.decision_id)
            else []
        ),
        *(["lane_resolution_clear_reason_required"] if not request.reason.strip() else []),
        *(["lane_resolution_clear_requires_break_glass"] if not request.break_glass else []),
        *(["irreversible_confirmation_required"] if not request.confirm_irreversible else []),
        *(
            ["lane_resolution_clear_manifest_mismatch"]
            if actual_manifest_sha256 != request.expect_manifest_sha256
            else []
        ),
    ]


def _clear_report(request: LaneResolutionClearRequest, gaps: tuple[str, ...]) -> dict[str, object]:
    return {
        "ok": not gaps,
        "state": "blocked" if gaps else "clearing" if request.apply else "planned",
        "decision_id": request.decision_id,
        "clear_receipt_path": "",
        "required_gaps": list(gaps),
    }


def _apply_clear_plan(
    root: Path,
    request: LaneResolutionClearRequest,
    plan: _ClearPlan,
    report: dict[str, object],
) -> dict[str, object]:
    observation = plan.observation
    clear_path = clear_receipt_path(root, request.decision_id)
    if not record_destination_safe(observation.record_root, clear_path):
        return _failed(report, "blocked", "lane_resolution_clear_receipt_path_unsafe")
    if observation.terminal:
        report.update(state="cleared", clear_receipt_path=display_path(root, clear_path))
        return report
    _validate_clear_schema(root, plan.clear_receipt)
    package = observation.manifest or observation.quarantine
    package_path = _package_path(root, package)
    if not package_path_safe(root, package_path):
        return _failed(report, "blocked", "lane_resolution_package_path_unsafe")
    if not observation.existing_clear:
        write_json_atomic(clear_path, plan.clear_receipt, record_root=observation.record_root)
    report["clear_receipt_path"] = display_path(root, clear_path)
    identity, quarantine_path, preparation_gap = _prepare_quarantine(
        root, request.decision_id, observation, package, package_path
    )
    if preparation_gap:
        return _failed(report, "partial_transition", preparation_gap)
    removal_gap = _remove_current_quarantine(
        root,
        request.decision_id,
        plan,
        cast("tuple[int, int, int]", identity),
        cast("Path", quarantine_path),
    )
    if removal_gap:
        return _failed(report, "partial_transition", removal_gap)
    report.update(state="cleared")
    return report


def _package_path(root: Path, package: dict[str, object]) -> Path:
    path = Path(str(package["package_path"]))
    return path if path.is_absolute() else root / path


def _prepare_quarantine(
    root: Path,
    decision_id: str,
    observation: _ClearObservation,
    package: dict[str, object],
    package_path: Path,
) -> tuple[tuple[int, int, int] | None, Path | None, str]:
    identity = package.get("package_identity")
    if not _package_identity_valid(identity):
        return None, None, "lane_resolution_clear_package_identity_mismatch"
    package_identity = cast("tuple[int, int, int]", identity)
    quarantine_path = clear_quarantine_path(
        root,
        decision_id,
        package_identity,
        artifact_root=observation.record_root,
    )
    if not record_destination_safe(observation.record_root, quarantine_path):
        return None, None, "lane_resolution_clear_quarantine_path_unsafe"
    if package.get("quarantined") is True:
        return package_identity, quarantine_path, ""
    move_state = move_current_package_to_quarantine(
        root=observation.record_root,
        source_name=package_path.name,
        quarantine_name=quarantine_path.name,
        expected_identity=package_identity,
    )
    return package_identity, quarantine_path, _move_gap(move_state)


def _package_identity_valid(identity: object) -> bool:
    return (
        isinstance(identity, tuple)
        and len(identity) == _PACKAGE_IDENTITY_FIELD_COUNT
        and all(isinstance(value, int) for value in identity)
    )


def _move_gap(state: str) -> str:
    if state == "moved":
        return ""
    if state == "collision":
        return "lane_resolution_clear_quarantine_collision"
    if state == "identity_mismatch":
        return "lane_resolution_clear_package_identity_mismatch"
    return "lane_resolution_clear_quarantine_failed"


def _remove_current_quarantine(
    root: Path,
    decision_id: str,
    plan: _ClearPlan,
    package_identity: tuple[int, int, int],
    quarantine_path: Path,
) -> str:
    observation = plan.observation
    final_current = read_current_lane_resolution_records(
        root=root, record_root=observation.record_root
    )
    final_clear = final_current.clears.get(decision_id, {})
    if not exact_clear_receipt(final_clear, plan.clear_receipt):
        return "lane_resolution_clear_receipt_mismatch"
    final_manifest = final_current.manifests.get(decision_id, {})
    final_quarantine = final_current.clear_quarantines.get(decision_id, {})
    final_package = final_manifest or final_quarantine
    binding = exact_package_binding(final_package)
    final_copy_count = final_manifest.get("copy_count")
    if (
        final_current.invalid_count
        or final_current.conflicts
        or not final_package
        or final_package.get("quarantined") is not True
        or final_package.get("manifest_sha256") != observation.actual_manifest_sha256
        or final_package.get("package_identity") != package_identity
        or binding is None
        or (final_manifest and final_copy_count != 1)
    ):
        return "lane_resolution_current_record_invalid"
    final_names, final_sha256, final_file_identities = binding
    if not remove_quarantined_package(
        root=observation.record_root,
        quarantine_name=quarantine_path.name,
        binding=QuarantinedPackageBinding(
            identity=package_identity,
            names=final_names,
            sha256=final_sha256,
            file_identities=final_file_identities,
        ),
    ):
        return "lane_resolution_clear_remove_failed"
    return _postcondition_gap(root, decision_id, plan)


def _postcondition_gap(root: Path, decision_id: str, plan: _ClearPlan) -> str:
    postcondition = read_current_lane_resolution_records(
        root=root, record_root=plan.observation.record_root
    )
    postcondition_clear = postcondition.clears.get(decision_id, {})
    if not exact_clear_receipt(postcondition_clear, plan.clear_receipt):
        return "lane_resolution_clear_receipt_mismatch"
    if (
        postcondition.invalid_count
        or postcondition.conflicts
        or decision_id in postcondition.manifests
        or decision_id in postcondition.clear_quarantines
    ):
        return "lane_resolution_clear_remove_failed"
    return ""


def _failed(report: dict[str, object], state: str, gap: str) -> dict[str, object]:
    report.update(ok=False, state=state, required_gaps=[gap])
    return report


def _records_owner_gap(error: ValueError) -> str:
    gap = str(error).strip()
    if gap == "lane_resolution_accepted_control_root_unavailable":
        return gap
    raise error


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


def _validate_clear_schema(root: Path, payload: dict[str, object]) -> None:
    validation = validate_schema_instance(
        "lane-resolution-clear-receipt.schema.json", payload, root=root
    )
    if not validation["ok"]:
        raise ValueError(_RECEIPT_INVALID)

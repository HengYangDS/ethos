"""Canonical validators for current lane-resolution record payloads."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import cast

from ethos.adapters.mutation.resolution.records.current.snapshot import read_current_record_path
from ethos.adapters.mutation.resolution.records.json_store import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.reservations import (
    validate_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.roots import display_record_path
from ethos.adapters.mutation.resolution.records.roots import record_path
from ethos.contracts.resolution.closeout import LaneResolutionClearReceipt
from ethos.contracts.resolution.closeout import LaneResolutionReceipt
from ethos.contracts.resolution.lane import LaneObservation
from ethos.contracts.resolution.lane import LaneResolutionDecision
from ethos.contracts.resolution.lane import is_lane_decision_id
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_RECEIPT_STATE_BY_DISPOSITION = {
    "block": "blocked_by_decision",
    "preserve": "preserved",
    "retire": "retired",
    "preserve-retire": "preserved_and_retired",
}


def canonical_record_name(
    *,
    root: Path,
    record_root: Path,
    category: str,
    path: Path,
    payload: dict[str, object],
) -> bool:
    """Return whether one current record uses its canonical physical name."""
    if category == "decisions":
        return True
    if category == "reservations":
        return path.name == f"{payload.get('target_digest', '')}.json"
    expected = record_path(
        root,
        category,
        str(payload.get("decision_id") or ""),
        artifact_root=record_root,
    )
    return path.name == expected.name


def validate_decision(root: Path, payload: dict[str, object]) -> dict[str, object]:
    """Return one canonical current decision or raise the stable invalid gap."""
    _require_schema(root, "lane-resolution-decision.schema.json", payload)
    selected = {field: payload[field] for field in LaneResolutionDecision.model_fields}
    canonical = LaneResolutionDecision.model_validate_json(
        json.dumps(selected, allow_nan=False)
    ).to_payload()
    if not is_lane_decision_id(str(canonical["decision_id"])) or canonical != payload:
        raise ValueError(_CURRENT_RECORD_INVALID)
    return canonical


def validate_receipt(
    root: Path, record_root: Path, payload: dict[str, object]
) -> dict[str, object]:
    """Return one canonical current receipt or raise the stable invalid gap."""
    _require_schema(root, "lane-resolution-receipt.schema.json", payload)
    canonical = LaneResolutionReceipt.model_validate(payload).to_payload()
    state = str(canonical["state"])
    package_present = bool(canonical["preservation_package"])
    manifest_present = bool(canonical["preservation_manifest_sha256"])
    preserved = state in {"preserved", "preserved_retirement_blocked", "preserved_and_retired"}
    expected_package = display_record_path(root, record_root / str(canonical["decision_id"]))
    binding = canonical.get("ownerless_closeout_binding")
    binding_valid = not isinstance(binding, dict) or (
        state == "retired"
        and not package_present
        and binding.get("target_digest")
        == target_digest(str(canonical["lane_ref"]), str(canonical["head"]))
    )
    if (
        canonical != payload
        or not is_lane_decision_id(str(canonical["decision_id"]))
        or package_present != manifest_present
        or preserved != package_present
        or (preserved and canonical["preservation_package"] != expected_package)
        or not binding_valid
    ):
        raise ValueError(_CURRENT_RECORD_INVALID)
    return canonical


def validate_clear_receipt(root: Path, payload: dict[str, object]) -> dict[str, object]:
    """Return one canonical current clear receipt or raise the stable invalid gap."""
    _require_schema(root, "lane-resolution-clear-receipt.schema.json", payload)
    canonical = LaneResolutionClearReceipt.model_validate(payload).to_payload()
    if canonical != payload or not is_lane_decision_id(str(canonical["decision_id"])):
        raise ValueError(_CURRENT_RECORD_INVALID)
    return canonical


def validate_reservation(payload: dict[str, object]) -> dict[str, object]:
    """Return one canonical current reservation or raise the stable invalid gap."""
    try:
        return validate_ownerless_closeout_reservation(payload)
    except (TypeError, ValueError) as error:
        raise ValueError(_CURRENT_RECORD_INVALID) from error


def cross_record_invalid_paths(
    *,
    decisions: dict[str, dict[str, object]],
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    clears: dict[str, dict[str, object]],
    reservations: dict[str, dict[str, object]],
) -> list[Path]:
    """Return physical records whose bindings disagree within one held snapshot."""
    return [
        *_decision_binding_invalid_paths(
            decisions=decisions,
            manifests=manifests,
            receipts=receipts,
            reservations=reservations,
        ),
        *_artifact_binding_invalid_paths(
            manifests=manifests,
            receipts=receipts,
            clears=clears,
        ),
    ]


def _decision_binding_invalid_paths(
    *,
    decisions: dict[str, dict[str, object]],
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    reservations: dict[str, dict[str, object]],
) -> list[Path]:
    invalid: list[Path] = []
    for decision_id, decision in decisions.items():
        observation = decision.get("observation")
        expected = (
            cast("Mapping[str, object]", observation) if isinstance(observation, dict) else {}
        )
        manifest = manifests.get(decision_id)
        receipt = receipts.get(decision_id)
        reservation = reservations.get(decision_id)
        if manifest and not _same_binding(manifest, expected, decision):
            invalid.append(cast("Path", manifest["physical_path"]))
        if receipt and not _same_binding(receipt, expected, decision, receipt=True):
            invalid.append(cast("Path", receipt["physical_path"]))
        if reservation and not _reservation_binding(reservation, expected, decision):
            invalid.append(cast("Path", reservation["physical_path"]))
    return invalid


def _artifact_binding_invalid_paths(
    *,
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    clears: dict[str, dict[str, object]],
) -> list[Path]:
    invalid: list[Path] = []
    for decision_id, receipt in receipts.items():
        preserved = str(receipt.get("state") or "") in {
            "preserved",
            "preserved_retirement_blocked",
            "preserved_and_retired",
        }
        manifest = manifests.get(decision_id)
        clear = clears.get(decision_id)
        if preserved and manifest is None and clear is None:
            invalid.append(cast("Path", receipt["physical_path"]))
        if manifest and receipt.get("preservation_manifest_sha256") != manifest.get(
            "manifest_sha256"
        ):
            invalid.append(cast("Path", receipt["physical_path"]))
        if clear and clear.get("manifest_sha256") != receipt.get("preservation_manifest_sha256"):
            invalid.append(cast("Path", clear["physical_path"]))
    for decision_id, manifest in manifests.items():
        if decision_id not in receipts:
            invalid.append(cast("Path", manifest["physical_path"]))
        if manifest.get("quarantined") is True and decision_id not in clears:
            invalid.append(cast("Path", manifest["physical_path"]))
    for decision_id, clear in clears.items():
        if decision_id not in receipts:
            invalid.append(cast("Path", clear["physical_path"]))
    return invalid


def _same_binding(
    record: Mapping[str, object],
    observation: Mapping[str, object],
    decision: Mapping[str, object],
    *,
    receipt: bool = False,
) -> bool:
    common = (
        record.get("lane_ref") == observation.get("lane_ref")
        and record.get("head") == observation.get("head")
        and record.get("observation_digest") == decision.get("observation_digest")
    )
    if not receipt:
        return common
    binding = record.get("ownerless_closeout_binding")
    ownerless_binding_valid = not _ownerless_retire_candidate(decision, observation) or (
        isinstance(binding, dict)
        and binding.get("decision_sha256") == decision.get("content_sha256")
    )
    return (
        common
        and _receipt_state_matches_disposition(record, decision)
        and record.get("reconciliation_required") is bool(decision.get("break_glass"))
        and ownerless_binding_valid
    )


def _receipt_state_matches_disposition(
    record: Mapping[str, object], decision: Mapping[str, object]
) -> bool:
    disposition = str(decision.get("disposition") or "")
    expected = _RECEIPT_STATE_BY_DISPOSITION.get(disposition)
    if disposition == "preserve-retire":
        return record.get("state") in {"preserved_retirement_blocked", expected}
    return record.get("state") == expected


def _ownerless_retire_candidate(
    decision: Mapping[str, object], observation: Mapping[str, object]
) -> bool:
    return (
        decision.get("disposition") == "retire"
        and observation.get("dirty") is False
        and observation.get("orphan") is True
        and not observation.get("holder_ref")
    )


def _reservation_binding(
    record: Mapping[str, object],
    observation: Mapping[str, object],
    decision: Mapping[str, object],
) -> bool:
    return (
        record.get("lane_ref") == observation.get("lane_ref")
        and record.get("head") == observation.get("head")
        and record.get("decision_sha256") == decision.get("content_sha256")
    )


def _require_schema(root: Path, schema: str, payload: dict[str, object]) -> None:
    if not validate_schema_instance(schema, payload, root=root)["ok"]:
        raise ValueError(_CURRENT_RECORD_INVALID)


class OwnerlessDecisionAdmissionError(ValueError):
    """Classified exact-current-decision failure for native admission."""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}:{detail}")
        self.kind = kind
        self.detail = detail


def admit_ownerless_decision_snapshot(
    *,
    root: Path,
    record_root: Path,
    decision_path: Path,
    supplied: dict[str, object],
) -> tuple[LaneResolutionDecision, bytes]:
    """Return one exact canonical retire decision and its descriptor-read bytes."""
    candidate = decision_path.absolute()
    if candidate.parent != (record_root / "decisions").absolute() or candidate.suffix != ".json":
        _decision_error("decision_invalid", "path")
    raw, state = read_current_record_path(record_root, candidate)
    if raw is None:
        _decision_error("decision_invalid", f"descriptor_{state}")
    _payload, canonical, model = _typed_ownerless_decision(root, raw)
    if raw != canonical_current_record_bytes(canonical):
        _decision_error("decision_invalid", "canonical_bytes")
    if supplied != canonical:
        _decision_error("decision_stale", "decision")
    if model.disposition != "retire":
        _decision_error("decision_invalid", "disposition")
    return model, raw


def _typed_ownerless_decision(
    root: Path, raw: bytes
) -> tuple[dict[str, object], dict[str, object], LaneResolutionDecision]:
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            _decision_error("decision_invalid", "payload")
        observation = payload.get("observation")
        if not isinstance(observation, dict):
            _decision_error("decision_invalid", "observation_digest")
        observed = LaneObservation.model_validate(observation, strict=True)
        if observed.digest() != payload.get("observation_digest"):
            _decision_error("decision_invalid", "observation_digest")
        canonical = validate_decision(root, payload)
        selected = {field: canonical[field] for field in LaneResolutionDecision.model_fields}
        model = LaneResolutionDecision.model_validate_json(json.dumps(selected, allow_nan=False))
    except OwnerlessDecisionAdmissionError:
        raise
    except (KeyError, OverflowError, RecursionError, TypeError, ValueError) as error:
        _decision_error("decision_invalid", "model", error)
    return payload, canonical, model


def _decision_error(kind: str, detail: str, cause: Exception | None = None) -> NoReturn:
    error = OwnerlessDecisionAdmissionError(kind, detail)
    if cause is None:
        raise error
    raise error from cause

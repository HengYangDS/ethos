"""Canonical validators for current lane-resolution record payloads."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.core import record_path
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.reservations import (
    validate_ownerless_closeout_reservation,
)
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.resolution.closeout import LaneResolutionClearReceipt
from ethos_core.contracts.resolution.closeout import LaneResolutionReceipt
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

if TYPE_CHECKING:
    from pathlib import Path

_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"


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
    if not valid_decision_id(str(canonical["decision_id"])) or canonical != payload:
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
    preserved = state in {"preserved", "preserved_and_retired"}
    expected_package = display_path(root, record_root / str(canonical["decision_id"]))
    binding = canonical.get("ownerless_closeout_binding")
    binding_valid = not isinstance(binding, dict) or (
        state == "retired"
        and not package_present
        and binding.get("target_digest")
        == target_digest(str(canonical["lane_ref"]), str(canonical["head"]))
    )
    if (
        canonical != payload
        or not valid_decision_id(str(canonical["decision_id"]))
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
    if canonical != payload or not valid_decision_id(str(canonical["decision_id"])):
        raise ValueError(_CURRENT_RECORD_INVALID)
    return canonical


def validate_reservation(payload: dict[str, object]) -> dict[str, object]:
    """Return one canonical current reservation or raise the stable invalid gap."""
    try:
        return validate_ownerless_closeout_reservation(payload)
    except (TypeError, ValueError) as error:
        raise ValueError(_CURRENT_RECORD_INVALID) from error


def _require_schema(root: Path, schema: str, payload: dict[str, object]) -> None:
    if not validate_schema_instance(schema, payload, root=root)["ok"]:
        raise ValueError(_CURRENT_RECORD_INVALID)

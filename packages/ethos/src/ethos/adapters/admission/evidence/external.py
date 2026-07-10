"""File-based adapters for optional external identity and enforcement receipts."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import ValidationError

from ethos_core.contracts.evidence.external import EnforcementReceipt
from ethos_core.contracts.evidence.external import IdentityAssertion

if TYPE_CHECKING:
    from pathlib import Path


def external_evidence_report(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    identity_path: Path | None,
    enforcement_path: Path | None,
    expected_action: str,
    expected_resource: str,
    expected_old: str,
    expected_new: str,
    require_identity: bool,
    require_hosted_enforcement: bool,
) -> dict[str, object]:
    """Verify only the exact evidence dimensions required by current policy."""
    identity, identity_gaps = _identity_report(identity_path, required=require_identity)
    enforcement, enforcement_gaps = _enforcement_report(
        enforcement_path,
        required=require_hosted_enforcement,
        expected_action=expected_action,
        expected_resource=expected_resource,
        expected_old=expected_old,
        expected_new=expected_new,
    )
    gaps = [*identity_gaps, *enforcement_gaps]
    return {
        "ok": not gaps,
        "root": root.resolve().as_posix(),
        "identity": identity,
        "enforcement": enforcement,
        "identity_basis": "verified_external_assertion" if identity else "not_evaluated",
        "enforcement_boundary": str(
            enforcement.get("enforcement_boundary") or "local_process_guard"
        ),
        "hosted_prevention_claimed": bool(enforcement.get("hosted_enforcement_proven")),
        "mints_authority": False,
        "required_gaps": gaps,
    }


def _identity_report(path: Path | None, *, required: bool) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["identity_assertion_required"] if required else []
    payload, gap = _read_mapping(path, "identity_assertion_invalid")
    if gap:
        return {}, [gap]
    try:
        assertion = IdentityAssertion.model_validate(payload)
    except ValidationError:
        return {}, ["identity_assertion_invalid"]
    now = datetime.now(UTC)
    if now < assertion.valid_from:
        return {}, ["identity_assertion_not_yet_valid"]
    if now > assertion.valid_until:
        return {}, ["identity_assertion_expired"]
    return assertion.to_payload(), []


def _enforcement_report(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    path: Path | None,
    *,
    required: bool,
    expected_action: str,
    expected_resource: str,
    expected_old: str,
    expected_new: str,
) -> tuple[dict[str, object], list[str]]:
    if path is None:
        return {}, ["hosted_enforcement_receipt_required"] if required else []
    payload, gap = _read_mapping(path, "hosted_enforcement_receipt_invalid")
    if gap:
        return {}, [gap]
    try:
        receipt = EnforcementReceipt.model_validate(payload)
    except ValidationError:
        return {}, ["hosted_enforcement_receipt_invalid"]
    expected = (expected_action, expected_resource, expected_old, expected_new)
    actual = (receipt.action, receipt.resource, receipt.old_value, receipt.new_value)
    if actual != expected:
        return {}, ["hosted_enforcement_receipt_binding_mismatch"]
    return receipt.to_payload(), []


def _read_mapping(path: Path, gap: str) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, gap
    if not isinstance(payload, dict):
        return {}, gap
    return cast("dict[str, Any]", payload), ""

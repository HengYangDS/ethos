from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.adapters.admission.evidence.external import external_evidence_report
from ethos_core.contracts.evidence.external import IdentityAssertion

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _identity(now: datetime, start: int = -1, end: int = 5) -> dict[str, str]:
    return {
        "identity_ref": "workload:issuer:subject:build-1",
        "issuer": "https://issuer.example",
        "audience": "ethos:accepted-closeout",
        "verification_method": "oidc-signature",
        "valid_from": (now + timedelta(minutes=start)).isoformat(),
        "valid_until": (now + timedelta(minutes=end)).isoformat(),
        "attestation_digest": "a" * 64,
    }


def _enforcement(now: datetime, resource: str = "refs/heads/dev") -> dict[str, str]:
    return {
        "provider": "gitlab",
        "enforcement_boundary": "protected_ref_transition",
        "action": "accepted.advance",
        "resource": resource,
        "old_value": "a" * 40,
        "new_value": "b" * 40,
        "observed_at": now.isoformat(),
        "receipt_digest": "c" * 64,
        "prevention_coverage": "provider_mediated_ref_update",
    }


def _report(
    root: Path,
    identity: Path | None = None,
    enforcement: Path | None = None,
    *,
    required: bool,
) -> dict[str, object]:
    return external_evidence_report(
        root=root,
        identity_path=identity,
        enforcement_path=enforcement,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=required,
        require_hosted_enforcement=required,
    )


def test_external_evidence_is_optional_when_policy_does_not_require_it(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, required=False)
    assert (
        report["ok"],
        report["identity_basis"],
        report["enforcement_boundary"],
        report["hosted_prevention_claimed"],
    ) == (True, "not_evaluated", "local_process_guard", False)


def test_required_external_evidence_fails_closed_on_missing_or_stale_receipts(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    identity = _write(tmp_path / "identity.json", _identity(now, -10, -5))
    assert _report(tmp_path, identity, required=True)["required_gaps"] == [
        "identity_assertion_expired",
        "hosted_enforcement_receipt_required",
    ]


def test_valid_receipts_upgrade_only_their_exact_decision_axes(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    report = _report(
        tmp_path,
        _write(tmp_path / "identity.json", _identity(now)),
        _write(tmp_path / "enforcement.json", _enforcement(now)),
        required=True,
    )
    assert (
        report["ok"],
        report["identity_basis"],
        report["enforcement_boundary"],
        report["hosted_prevention_claimed"],
    ) == (True, "verified_external_assertion", "protected_ref_transition", True)


def test_invalid_future_and_misbound_external_receipts_fail_closed(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json", encoding="utf-8")
    assert _report(tmp_path, invalid, invalid, required=True)["required_gaps"] == [
        "identity_assertion_invalid",
        "hosted_enforcement_receipt_invalid",
    ]
    now = datetime.now(UTC)
    with pytest.raises(ValidationError, match="valid_until must be later"):
        IdentityAssertion.model_validate(_identity(now, 0, 0))
    report = _report(
        tmp_path,
        _write(tmp_path / "future.json", _identity(now, 5, 10)),
        _write(tmp_path / "misbound.json", _enforcement(now, "refs/heads/main")),
        required=True,
    )
    assert report["required_gaps"] == [
        "identity_assertion_not_yet_valid",
        "hosted_enforcement_receipt_binding_mismatch",
    ]

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.admission.evidence.external import external_evidence_report

if TYPE_CHECKING:
    from pathlib import Path


def test_external_evidence_is_optional_when_policy_does_not_require_it(tmp_path: Path) -> None:
    report = external_evidence_report(
        root=tmp_path,
        identity_path=None,
        enforcement_path=None,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=False,
        require_hosted_enforcement=False,
    )

    assert report["ok"] is True
    assert report["identity_basis"] == "not_evaluated"
    assert report["enforcement_boundary"] == "local_process_guard"
    assert report["hosted_prevention_claimed"] is False


def test_required_external_evidence_fails_closed_on_missing_or_stale_receipts(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    identity = tmp_path / "identity.json"
    identity.write_text(
        json.dumps(
            {
                "identity_ref": "workload:issuer:subject:build-1",
                "issuer": "https://issuer.example",
                "audience": "ethos:accepted-closeout",
                "verification_method": "oidc-signature",
                "valid_from": (now - timedelta(minutes=10)).isoformat(),
                "valid_until": (now - timedelta(minutes=5)).isoformat(),
                "attestation_digest": "a" * 64,
            }
        ),
        encoding="utf-8",
    )

    report = external_evidence_report(
        root=tmp_path,
        identity_path=identity,
        enforcement_path=None,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=True,
        require_hosted_enforcement=True,
    )

    assert report["ok"] is False
    assert "identity_assertion_expired" in report["required_gaps"]
    assert "hosted_enforcement_receipt_required" in report["required_gaps"]


def test_valid_receipts_upgrade_only_their_exact_decision_axes(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    identity = tmp_path / "identity.json"
    enforcement = tmp_path / "enforcement.json"
    identity.write_text(
        json.dumps(
            {
                "identity_ref": "workload:issuer:subject:build-1",
                "issuer": "https://issuer.example",
                "audience": "ethos:accepted-closeout",
                "verification_method": "oidc-signature",
                "valid_from": (now - timedelta(minutes=1)).isoformat(),
                "valid_until": (now + timedelta(minutes=5)).isoformat(),
                "attestation_digest": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    enforcement.write_text(
        json.dumps(
            {
                "provider": "gitlab",
                "enforcement_boundary": "protected_ref_transition",
                "action": "accepted.advance",
                "resource": "refs/heads/dev",
                "old_value": "a" * 40,
                "new_value": "b" * 40,
                "observed_at": now.isoformat(),
                "receipt_digest": "c" * 64,
                "prevention_coverage": "provider_mediated_ref_update",
            }
        ),
        encoding="utf-8",
    )

    report = external_evidence_report(
        root=tmp_path,
        identity_path=identity,
        enforcement_path=enforcement,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=True,
        require_hosted_enforcement=True,
    )

    assert report["ok"] is True
    assert report["identity_basis"] == "verified_external_assertion"
    assert report["enforcement_boundary"] == "protected_ref_transition"
    assert report["hosted_prevention_claimed"] is True


def test_invalid_future_and_misbound_external_receipts_fail_closed(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json", encoding="utf-8")
    invalid_report = external_evidence_report(
        root=tmp_path,
        identity_path=invalid,
        enforcement_path=invalid,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=True,
        require_hosted_enforcement=True,
    )
    assert invalid_report["required_gaps"] == [
        "identity_assertion_invalid",
        "hosted_enforcement_receipt_invalid",
    ]

    now = datetime.now(UTC)
    identity = tmp_path / "future-identity.json"
    enforcement = tmp_path / "misbound-enforcement.json"
    identity.write_text(
        json.dumps(
            {
                "identity_ref": "workload:issuer:subject:future",
                "issuer": "https://issuer.example",
                "audience": "ethos:accepted-closeout",
                "verification_method": "oidc-signature",
                "valid_from": (now + timedelta(minutes=5)).isoformat(),
                "valid_until": (now + timedelta(minutes=10)).isoformat(),
                "attestation_digest": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    enforcement.write_text(
        json.dumps(
            {
                "provider": "gitlab",
                "enforcement_boundary": "protected_ref_transition",
                "action": "accepted.advance",
                "resource": "refs/heads/main",
                "old_value": "a" * 40,
                "new_value": "b" * 40,
                "observed_at": now.isoformat(),
                "receipt_digest": "c" * 64,
                "prevention_coverage": "provider_mediated_ref_update",
            }
        ),
        encoding="utf-8",
    )
    report = external_evidence_report(
        root=tmp_path,
        identity_path=identity,
        enforcement_path=enforcement,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
        require_identity=True,
        require_hosted_enforcement=True,
    )
    assert report["required_gaps"] == [
        "identity_assertion_not_yet_valid",
        "hosted_enforcement_receipt_binding_mismatch",
    ]

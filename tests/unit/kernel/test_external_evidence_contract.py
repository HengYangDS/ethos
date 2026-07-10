from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

from ethos_core.contracts.external_evidence import EnforcementReceipt
from ethos_core.contracts.external_evidence import IdentityAssertion


def test_identity_assertion_is_bounded_evidence_not_authority() -> None:
    now = datetime.now(UTC)
    assertion = IdentityAssertion(
        identity_ref="workload:issuer:subject:build-1",
        issuer="https://issuer.example",
        audience="ethos:accepted-closeout",
        verification_method="oidc-signature",
        valid_from=now - timedelta(minutes=1),
        valid_until=now + timedelta(minutes=5),
        attestation_digest="a" * 64,
    )

    payload = assertion.to_payload()
    assert payload["mints_authority"] is False
    assert payload["stores_credentials"] is False
    assert payload["evidence_boundary"] == "verified_external_identity_assertion"


def test_enforcement_receipt_binds_exact_transition_and_coverage() -> None:
    now = datetime.now(UTC)
    receipt = EnforcementReceipt(
        provider="gitlab",
        enforcement_boundary="protected_ref_transition",
        action="remote.publish",
        resource="refs/heads/dev",
        old_value="a" * 40,
        new_value="b" * 40,
        observed_at=now,
        receipt_digest="c" * 64,
        prevention_coverage="provider_mediated_ref_update",
    )

    payload = receipt.to_payload()
    assert payload["hosted_enforcement_proven"] is True
    assert payload["mints_authority"] is False
    assert payload["recheck_required"] is True

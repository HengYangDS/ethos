from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from ethos_core.contracts.evidence.external import IndependentVerificationReceipt


def _receipt(**overrides: object) -> IndependentVerificationReceipt:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "remote": "https://example.invalid/org/repo.git",
        "commit": "a" * 40,
        "tree": "b" * 40,
        "action": "publish",
        "proof_floor_id": "proof-floor:default",
        "proof_floor_digest": "c" * 64,
        "policy_digest": "d" * 64,
        "implementation_digest": "e" * 64,
        "result": "pass",
        "issuer": "provider:example",
        "key_id": "key:example",
        "signature_algorithm": "ssh-ed25519",
        "signature": "signed-payload",
        "issued_at": now,
        "valid_until": now + timedelta(minutes=5),
        "payload_digest": "",
    }
    payload.update(overrides)
    receipt = IndependentVerificationReceipt(**payload)
    return receipt.model_copy(update={"payload_digest": receipt.canonical_payload_digest()})


def test_receipt_canonical_payload_binds_exact_proof_dimensions() -> None:
    receipt = _receipt()

    assert receipt.payload_digest == receipt.canonical_payload_digest()
    assert receipt.to_payload()["mints_authority"] is False
    assert receipt.to_payload()["evidence_boundary"] == "independent_exact_proof_floor_reexecution"


def test_receipt_rejects_invalid_validity_interval() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="valid_until must be later"):
        _receipt(issued_at=now, valid_until=now)


def test_receipt_rejects_a_noncanonical_payload_digest() -> None:
    with pytest.raises(ValueError, match="payload_digest does not match"):
        _receipt(payload_digest="f" * 64)

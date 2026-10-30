"""Bind every control replacement test to one configured verification provider."""

from __future__ import annotations

import pytest

import ethos.adapters.admission.evidence.external as evidence


@pytest.fixture(autouse=True)
def configured_provider(tmp_path, monkeypatch):
    provider = evidence.IndependentVerificationProvider(
        receipt_store=tmp_path / "receipts",
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
        issuer="provider:example",
        key_id="provider:example",
    )
    provider.receipt_store.mkdir()
    monkeypatch.setattr(
        evidence, "load_independent_verification_provider", lambda _path: (provider, [])
    )
    monkeypatch.setattr(
        evidence, "default_provider_config_path", lambda: tmp_path / "provider.toml"
    )
    monkeypatch.setattr(
        evidence,
        "verify_independent_receipt_signature",
        lambda receipt, configured: receipt.signature == "signed" and configured == provider,
    )

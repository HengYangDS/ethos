from __future__ import annotations

from pathlib import Path

from ethos_governance.claims import claims_report


def test_claim_evidence_digests_are_verified() -> None:
    report = claims_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert "ethos-product-canonization" in report["claims"]
    assert "ethos-framework-hardening" in report["claims"]

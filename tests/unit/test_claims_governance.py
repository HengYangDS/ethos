from __future__ import annotations

import hashlib
from pathlib import Path

from ethos_repository.claims import claims_report


def test_claim_evidence_digests_are_verified() -> None:
    report = claims_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert "ethos-product-canonization" in report["claims"]
    assert "ethos-framework-hardening" in report["claims"]


def test_empty_claims_directory_is_a_gap(tmp_path: Path) -> None:
    (tmp_path / "claims").mkdir()

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "claims_missing" in report["required_gaps"]


def test_active_claims_reject_retired_product_family_subjects(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    evidence = tmp_path / "docs" / "evidence"
    claims.mkdir()
    evidence.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "ethos-governance-platform.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "ethos-governance-platform"',
                'subject = "ethos:governance-platform"',
                'state = "active"',
                'summary = "old family"',
                "",
                "[evidence]",
                'dated = "docs/evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert (
        "ethos-governance-platform:retired_product_family:ethos-governance"
        in report["required_gaps"]
    )


def test_active_trust_claim_requires_boundary_carriers_and_promotion(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    evidence = tmp_path / "docs" / "evidence"
    claims.mkdir()
    evidence.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "sample-trust.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample-trust"',
                'subject = "ethos:trust"',
                'state = "active"',
                'summary = "missing trust carriers"',
                "",
                "[evidence]",
                'dated = "docs/evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "sample-trust:boundary.owner_missing" in report["required_gaps"]
    assert "sample-trust:boundary.scope_missing" in report["required_gaps"]
    assert "sample-trust:carriers.openspec_missing" in report["required_gaps"]
    assert "sample-trust:fallback_missing" in report["required_gaps"]
    assert "sample-trust:kill_signal_missing" in report["required_gaps"]
    assert "sample-trust:promotion.targets_missing" in report["required_gaps"]
    envelope = report["claims"]["sample-trust"]["trust_envelope"]
    assert envelope["claim_id"] == "sample-trust"
    assert envelope["required_gaps"] == [
        "boundary.owner_missing",
        "boundary.scope_missing",
        "carriers.openspec_missing",
        "fallback_missing",
        "kill_signal_missing",
        "promotion.targets_missing",
    ]

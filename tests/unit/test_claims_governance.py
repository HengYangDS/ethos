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


def test_active_claims_require_typed_evidence_claim_binding(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    evidence = tmp_path / "docs" / "evidence"
    claims.mkdir()
    evidence.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "sample claim"',
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
    assert "sample:evidence_ids_missing" in report["required_gaps"]
    assert "sample:binding_missing" in report["required_gaps"]
    assert "sample:verifier_missing" in report["required_gaps"]


def test_digest_only_claim_rejects_operational_overclaim(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    evidence = tmp_path / "docs" / "evidence"
    claims.mkdir()
    evidence.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "hosted CI verified and dmgr raw/cache parity passed"',
                "",
                "[evidence]",
                'dated = "docs/evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
                'binding = "hosted CI verified and dmgr raw/cache parity passed"',
                'verifier = "digest_only"',
                'evidence_ids = ["evidence:sample"]',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "sample:semantic_overclaim_requires_semantic_verifier" in report["required_gaps"]


def test_digest_only_claim_rejects_summary_overclaim(tmp_path: Path) -> None:
    claims = tmp_path / "claims"
    evidence = tmp_path / "docs" / "evidence"
    claims.mkdir()
    evidence.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "hosted CI verified and remote publication completed"',
                "",
                "[evidence]",
                'dated = "docs/evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
                'binding = "digest-bound sample evidence binding"',
                'verifier = "digest_only"',
                'evidence_ids = ["evidence:sample"]',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "sample:semantic_overclaim_requires_semantic_verifier" in report["required_gaps"]

from __future__ import annotations

from pathlib import Path

from ethos.domain.report import scorecard_report

ROOT = Path(__file__).resolve().parents[3]


def test_report_projects_local_and_independent_verification_evidence_classes() -> None:
    report = scorecard_report(ROOT)

    readiness = report["data"]["proof_readiness"]
    assert readiness["evidence_class"] in {
        "local_readiness",
        "independently_reexecuted",
    }
    assert report["summary"]["proof_evidence_class"] == readiness["evidence_class"]
    assert "independent_verification" in readiness

from __future__ import annotations

from pathlib import Path

from ethos_governance.history import history_identity_report


def test_history_identity_report_exposes_rewrite_readiness() -> None:
    report = history_identity_report(Path.cwd())

    assert report["expected_author"] == "Yang HENG <heng.yang.ds@hotmail.com>"
    assert "commits" in report
    assert "raw_mismatches" in report
    assert "unsigned_commits" in report
    assert "subject_mismatches" in report

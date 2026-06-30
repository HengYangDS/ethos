from __future__ import annotations

from ethos_governance.commit_policy import commit_subject_ok, signature_policy_report


def test_conventional_commit_subjects_are_enforced() -> None:
    assert commit_subject_ok("feat: mature ETHOS product governance") is True
    assert commit_subject_ok("Harden ETHOS framework core") is False


def test_signature_policy_reports_expected_identity() -> None:
    report = signature_policy_report()

    assert report["expected_author"] == "Yang HENG <heng.yang.ds@hotmail.com>"
    assert report["signing_required"] is True
    assert report["gpg_format"] == "ssh"
    assert report["signing_key"]


def test_signature_policy_uses_machine_readable_head_signature_status() -> None:
    report = signature_policy_report()

    assert report["head_signature_status"] in {"G", "B", "U", "X", "Y", "R", "E", "N"}
    assert report["head_signature_ok"] is (report["head_signature_status"] == "G")

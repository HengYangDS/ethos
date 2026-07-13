from __future__ import annotations

import hashlib
from pathlib import Path  # noqa: TC003

from ethos.repository.evidence.claims import claims_report
from ethos.repository.release.core import release_config
from ethos.repository.release.core import release_policy_report
from ethos.repository.release.core import version_manifest


def test_claims_report_surfaces_active_claim_trust_envelope_and_head_gaps(tmp_path: Path):
    evidence = tmp_path / "evidence" / "proof.md"
    carrier = tmp_path / "openspec" / "changes" / "sample" / "proposal.md"
    target = tmp_path / "docs" / "guide.md"
    claims_dir = tmp_path / "evidence" / "claims"
    carrier.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    claims_dir.mkdir(parents=True)
    evidence.write_text("proof", encoding="utf-8")
    carrier.write_text("proposal", encoding="utf-8")
    target.write_text("doc", encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    (claims_dir / "sample.toml").write_text(
        f"""
[claim]
id = "sample"
state = "active"
subject = "repository"
change_id = "change-1"
summary = "verified hosted ci"

[evidence]
dated = "evidence/proof.md"
sha256 = "{digest}"
head = "old-head"
evidence_ids = ["proof-run"]
binding = "published result"
verifier = "digest"
tests = ["pytest"]

[boundary]
owner = "team"
scope = "repository"

[carriers]
openspec = "openspec/changes/sample/proposal.md"

[promotion]
targets = ["docs/guide.md", "missing.py"]
""".strip(),
        encoding="utf-8",
    )

    report = claims_report(tmp_path, current_head="new-head")

    assert report["ok"] is False
    gaps = report["required_gaps"]
    assert "sample:evidence.head_stale:old-head!=new-head" in gaps
    assert "sample:claim_assurance_invalid" in gaps
    assert "sample:fallback_missing" in gaps
    assert "sample:kill_signal_missing" in gaps
    assert "sample:promotion_target_missing:missing.py" in gaps
    envelope = report["claims"]["sample"]["trust_envelope"]
    assert envelope["promotion"]["targets"] == [
        {"kind": "docs", "path": "docs/guide.md"},
        {"kind": "source", "path": "missing.py"},
    ]
    assert envelope["promotion"]["ready"] is False


def test_claims_report_marks_missing_claims_and_digest_gap(tmp_path: Path):
    empty = claims_report(tmp_path)
    assert empty["required_gaps"] == ["claims_missing"]

    evidence = tmp_path / "evidence" / "proof.md"
    claims_dir = tmp_path / "evidence" / "claims"
    claims_dir.mkdir(parents=True)
    evidence.write_text("proof", encoding="utf-8")
    (claims_dir / "inactive.toml").write_text(
        """
[claim]
id = "inactive"
state = "superseded"

[evidence]
dated = "evidence/proof.md"
sha256 = "wrong"
""".strip(),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)
    assert "inactive:evidence.sha256_mismatch" in report["required_gaps"]
    assert (
        report["claims"]["inactive"]["actual_sha256"]
        == hashlib.sha256(evidence.read_bytes()).hexdigest()
    )


def test_release_policy_reports_missing_files_versions_refs_surfaces_and_attestation(
    tmp_path: Path,
):
    (tmp_path / "packages" / "ethos").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="ethos"\nversion="1.0.0"\n', encoding="utf-8"
    )
    (tmp_path / "packages" / "ethos" / "pyproject.toml").write_text(
        '[project]\nname="ethos"\nversion="2.0.0"\n', encoding="utf-8"
    )
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "release.toml").write_text(
        """
[protected_refs]
branches = ["dev"]
tags = []

[host_profile]
provider = "gitlab"

[host_profile.surfaces]
ci = ".gitlab-ci.yml"

[attestation]
formats = ["spdx-lite"]
signing = "local"
""".strip(),
        encoding="utf-8",
    )

    config = release_config(tmp_path)
    version = version_manifest(tmp_path)
    report = release_policy_report(tmp_path)

    assert config["host_profile"]["provider"] == "gitlab"
    assert version["mismatches"] == {"ethos": "2.0.0"}
    assert "package_version_mismatch" in report["required_gaps"]
    assert "protected_branches_policy_missing" in report["required_gaps"]
    assert "protected_tags_policy_missing" in report["required_gaps"]
    assert "host_surface_missing:gitlab:ci:.gitlab-ci.yml" in report["required_gaps"]
    assert "attestation_formats_incomplete" in report["required_gaps"]
    assert "release_file_missing:README.md" in report["required_gaps"]

"""Coverage-closure v3: evidence reachable branches (100% no-exemption).

Each test drives one uncovered gap-emitting branch in the evidence cluster:
- ethos.repository.evidence.claims: change-claim evidence-ref validation
  (111, 116-117, 121-122, 126, 130, 132, 145) and normal-claim digest/date
  gates (250-251, 294-295, 299-300).
- ethos.repository.evidence.parity_validation: the None-target command-identity
  branch 328->330.
All lines are reached through the real public/underscore-prefixed functions.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity_validation import command_matches_identity

if TYPE_CHECKING:
    from pathlib import Path


def _claims_dir(root: Path) -> Path:
    claims = root / "evidence" / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    return claims


def _write_evidence(root: Path, rel: str, text: str = "sample\n") -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# ethos.repository.evidence.claims :: _change_claim_record
# --------------------------------------------------------------------------- #


def test_change_claim_closed_lifecycle_without_refs_is_gap(tmp_path: Path) -> None:
    # Line 111: requires_evidence (lifecycle="closed") + no evidence_refs -> refs_missing.
    (_claims_dir(tmp_path) / "closed.toml").write_text(
        'id = "closed-change"\nkind = "change"\nlifecycle = "closed"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "closed-change:evidence_refs_missing" in report["required_gaps"]


def test_change_claim_non_dict_ref_is_invalid(tmp_path: Path) -> None:
    # Lines 116-117: an evidence_ref that is not a dict -> evidence_ref_invalid, continue.
    (_claims_dir(tmp_path) / "listref.toml").write_text(
        'id = "list-change"\nkind = "change"\nlifecycle = "active"\n'
        'evidence_refs = ["plain-string"]\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "list-change:evidence_ref_invalid:0" in report["required_gaps"]


def test_change_claim_ref_without_artifact_is_gap(tmp_path: Path) -> None:
    # Lines 121-122: a dict ref with no artifact -> evidence_ref_artifact_missing, continue.
    (_claims_dir(tmp_path) / "noart.toml").write_text(
        'id = "noart-change"\nkind = "change"\nlifecycle = "active"\n\n'
        '[[evidence_refs]]\ndigest = "sha256:abc"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "noart-change:evidence_ref_artifact_missing:0" in report["required_gaps"]


def test_change_claim_ref_artifact_file_missing_is_gap(tmp_path: Path) -> None:
    # Line 126: ref artifact path does not exist on disk -> evidence_file_missing.
    (_claims_dir(tmp_path) / "missfile.toml").write_text(
        'id = "missfile-change"\nkind = "change"\nlifecycle = "active"\n\n'
        '[[evidence_refs]]\nartifact = "evidence/missing.md"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "missfile-change:evidence_file_missing:evidence/missing.md" in report["required_gaps"]


def test_change_claim_ref_digest_mismatch_is_gap(tmp_path: Path) -> None:
    # Line 130: artifact exists but declared digest != actual -> evidence.sha256_mismatch.
    _write_evidence(tmp_path, "evidence/e.md")
    (_claims_dir(tmp_path) / "mismatch.toml").write_text(
        'id = "mismatch-change"\nkind = "change"\nlifecycle = "active"\n\n'
        '[[evidence_refs]]\nartifact = "evidence/e.md"\ndigest = "sha256:deadbeef"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "mismatch-change:evidence.sha256_mismatch:evidence/e.md" in report["required_gaps"]


def test_change_claim_ref_digest_missing_is_gap(tmp_path: Path) -> None:
    # Line 132: artifact exists but no digest declared -> evidence.sha256_missing.
    _write_evidence(tmp_path, "evidence/e.md")
    (_claims_dir(tmp_path) / "nodigest.toml").write_text(
        'id = "nodigest-change"\nkind = "change"\nlifecycle = "active"\n\n'
        '[[evidence_refs]]\nartifact = "evidence/e.md"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "nodigest-change:evidence.sha256_missing:evidence/e.md" in report["required_gaps"]


def test_change_claim_active_retired_family_token_is_gap(tmp_path: Path) -> None:
    # Line 145: lifecycle="active" and a retired product-family token in claim id.
    (_claims_dir(tmp_path) / "retired.toml").write_text(
        'id = "ethos-kernel"\nkind = "change"\nlifecycle = "active"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "ethos-kernel:retired_product_family:ethos-kernel" in report["required_gaps"]


# --------------------------------------------------------------------------- #
# ethos.repository.evidence.claims :: claims_report (normal [claim] records)
# --------------------------------------------------------------------------- #


def test_normal_claim_without_dated_is_gap(tmp_path: Path) -> None:
    # Lines 250-251: [evidence] table present but no `dated` -> dated_missing, continue.
    (_claims_dir(tmp_path) / "nodate.toml").write_text(
        '[claim]\nid = "nodate"\nstate = "historical"\n\n[evidence]\nsha256 = "abc"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "nodate:evidence.dated_missing" in report["required_gaps"]


def test_normal_claim_dated_file_missing_is_gap(tmp_path: Path) -> None:
    # Lines 294-295: dated points at a non-existent file -> evidence_file_missing, continue.
    (_claims_dir(tmp_path) / "missfile.toml").write_text(
        '[claim]\nid = "missing-file"\nstate = "historical"\n\n'
        '[evidence]\ndated = "evidence/nope.md"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "missing-file:evidence_file_missing:evidence/nope.md" in report["required_gaps"]


def test_normal_claim_dated_file_without_sha256_is_gap(tmp_path: Path) -> None:
    # Lines 299-300: dated file exists but no declared sha256 -> evidence.sha256_missing.
    _write_evidence(tmp_path, "evidence/e.md")
    (_claims_dir(tmp_path) / "nosha.toml").write_text(
        '[claim]\nid = "nosha"\nstate = "historical"\n\n[evidence]\ndated = "evidence/e.md"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert "nosha:evidence.sha256_missing" in report["required_gaps"]


# --------------------------------------------------------------------------- #
# ethos.repository.evidence.parity_validation :: command_matches_identity
# --------------------------------------------------------------------------- #


def test_command_identity_none_target_reaches_flag_check() -> None:
    # Branch 328->330: target is None (skips 322 block) and "--target " IS present,
    # so the elif is False and control falls through to the --execute/--json check.
    command = "ethos parity shadow --adopter demo --target . --execute --json"

    assert command_matches_identity(command, adopter="demo", target=None) is True

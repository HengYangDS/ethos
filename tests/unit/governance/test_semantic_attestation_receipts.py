from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING

import pytest

from ethos.repository.evidence.claims import claims_report
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def _sha256(path: Path) -> str:
    """Return the SHA-256 identity of one receipt or evidence carrier."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_digest(payload: dict[str, object]) -> str:
    """Derive the receipt digest excluding its self-describing digest field."""
    body = {key: value for key, value in payload.items() if key != "payload_digest"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _semantic_claim_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    variant: str = "valid",
    verifier: str = "semantic_attested",
) -> tuple[Path, str]:
    """Create one head-bound claim and optional candidate-external receipt."""
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "subject.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    head = "a" * 40

    evidence = root / "evidence" / "chronicle" / "sample" / "2026-07-14.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("# Sample evidence\n", encoding="utf-8")
    carrier = root / "openspec" / "archive"
    carrier.mkdir(parents=True)
    (carrier / "proposal.md").write_text("# Carrier\n", encoding="utf-8")
    scope_digest = "b" * 64
    receipt_root = tmp_path / "external-receipts"
    if variant == "inside_repository":
        receipt_root = root / "external-receipts"
    receipt_root.mkdir(parents=True)
    monkeypatch.setenv("ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR", receipt_root.as_posix())

    receipt_id = "sample-attestation"
    receipt_path = receipt_root / f"{receipt_id}.json"
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "semantic-attestation",
        "claim_id": "sample-claim",
        "evidence_sha256": _sha256(evidence),
        "scope_sha256": scope_digest,
        "head": head,
        "reviewer_role": "independent_reviewer",
        "reviewer_ref": "reviewer:sample",
        "basis": "Reviewed the bounded claim, evidence, and declared semantic scope.",
        "verdict": "allow",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "valid_until": "2099-01-01T00:00:00+00:00",
        "mints_authority": False,
        "payload_digest": "",
    }
    overrides = {
        "stale": ("valid_until", "2000-01-01T00:00:00+00:00"),
        "evidence_mismatch": ("evidence_sha256", "0" * 64),
        "scope_mismatch": ("scope_sha256", "1" * 64),
        "head_mismatch": ("head", "2" * 40),
        "claim_mismatch": ("claim_id", "other-claim"),
    }
    if override := overrides.get(variant):
        payload[override[0]] = override[1]
    payload["payload_digest"] = _receipt_digest(payload)
    if variant == "malformed":
        receipt_path.write_text("{}\n", encoding="utf-8")
    elif variant != "missing":
        receipt_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    claims = root / "evidence" / "claims"
    claims.mkdir(parents=True)
    receipt_sha = _sha256(receipt_path) if receipt_path.exists() else "f" * 64
    if variant == "receipt_mismatch":
        receipt_sha = "0" * 64
    attestation = ""
    if verifier == "semantic_attested":
        attestation = (
            "\n[evidence.semantic_attestation]\n"
            f'receipt_id = "{receipt_id}"\n'
            f'receipt_sha256 = "{receipt_sha}"\n'
            f'scope_sha256 = "{scope_digest}"\n'
            f'head = "{head}"\n'
        )
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample-claim"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "A bounded sample claim."',
                "",
                "[evidence]",
                f'dated = "{evidence.relative_to(root).as_posix()}"',
                f'sha256 = "{_sha256(evidence)}"',
                'evidence_ids = ["evidence:sample"]',
                'binding = "Digest-bound sample evidence and declared scope."',
                f'verifier = "{verifier}"',
                'tests = ["pytest -q tests/sample.py"]',
                attestation.rstrip(),
                "",
                "[evidence.freshness]",
                'mode = "semantic_scope"',
                f'head = "{head}"',
                f'semantic_sha256 = "{scope_digest}"',
                "",
                "[boundary]",
                'owner = "ethos"',
                'scope = "sample semantic claim"',
                "",
                "[carriers]",
                'openspec = "openspec/archive"',
                "",
                'fallback = "Use digest-only evidence until a fresh receipt is supplied."',
                'kill_signal = "Receipt binding, reviewer basis, or declared scope no longer matches."',
                "",
                "[promotion]",
                'targets = ["subject.py"]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root, head


@pytest.mark.parametrize(
    ("variant", "expected_gap"),
    [
        ("missing", "semantic_attestation_receipt_required"),
        ("malformed", "semantic_attestation_receipt_invalid"),
        ("stale", "semantic_attestation_receipt_stale"),
        ("evidence_mismatch", "semantic_attestation_evidence_digest_mismatch"),
        ("scope_mismatch", "semantic_attestation_scope_digest_mismatch"),
        ("head_mismatch", "semantic_attestation_head_mismatch"),
        ("claim_mismatch", "semantic_attestation_claim_id_mismatch"),
        ("receipt_mismatch", "semantic_attestation_receipt_digest_mismatch"),
        ("inside_repository", "semantic_attestation_receipt_inside_repository"),
    ],
)
def test_semantic_attestation_receipt_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
    expected_gap: str,
) -> None:
    """A semantic claim must reject every incomplete or mismatched receipt state."""
    root, head = _semantic_claim_fixture(tmp_path, monkeypatch, variant=variant)
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_a, **_k: "b" * 64,
    )
    report = claims_report(root, current_head=head)

    assert f"sample-claim:{expected_gap}" in report["required_gaps"]


def test_semantic_attestation_receipt_binds_claim_evidence_and_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid candidate-external receipt admits only its exact claim scope."""
    root, head = _semantic_claim_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_a, **_k: "b" * 64,
    )
    report = claims_report(root, current_head=head)

    assert report["ok"] is True
    attestation = report["claims"]["sample-claim"]["trust_envelope"]["semantic_attestation"]
    assert attestation["state"] == "attested"
    assert attestation["reviewer_role"] == "independent_reviewer"


def test_semantic_attestation_claim_schema_requires_semantic_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The receipt class cannot pair with historical or head-only freshness."""
    root, _ = _semantic_claim_fixture(tmp_path, monkeypatch)
    claim = tomllib.loads((root / "evidence/claims/sample.toml").read_text())
    claim["evidence"]["freshness"]["mode"] = "historical"

    report = validate_schema_instance("claim.schema.json", claim)

    assert report["ok"] is False


def test_semantic_attestation_receipt_model_rejects_tampered_payload_digest() -> None:
    """The typed receipt contract rejects a self-inconsistent canonical payload."""
    from ethos_core.contracts.evidence.semantic import SemanticAttestationReceipt

    payload = {
        "schema_version": 1,
        "kind": "semantic-attestation",
        "claim_id": "sample-claim",
        "evidence_sha256": "a" * 64,
        "scope_sha256": "b" * 64,
        "head": "c" * 40,
        "reviewer_role": "independent_reviewer",
        "reviewer_ref": "reviewer:sample",
        "basis": "Reviewed the declared semantic scope.",
        "verdict": "allow",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "valid_until": "2099-01-01T00:00:00+00:00",
        "mints_authority": False,
        "payload_digest": "0" * 64,
    }

    with pytest.raises(ValueError, match="payload_digest"):
        SemanticAttestationReceipt.model_validate(payload)
    with pytest.raises(ValueError, match="valid dictionary"):
        SemanticAttestationReceipt.model_validate([])


def test_semantic_attestation_receipt_rejects_nonabsolute_receipt_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative receipt root is invalid rather than an implicit local fallback."""
    root, head = _semantic_claim_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR", "relative-receipts")
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_a, **_k: "b" * 64,
    )

    report = claims_report(root, current_head=head)

    assert "sample-claim:semantic_attestation_receipt_invalid" in report["required_gaps"]


def test_digest_only_claim_does_not_require_semantic_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Historical digest-only claims remain portable without any receipt provider."""
    root, head = _semantic_claim_fixture(tmp_path, monkeypatch, verifier="digest_only")
    monkeypatch.delenv("ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR")
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_a, **_k: "b" * 64,
    )
    report = claims_report(root, current_head=head)

    assert report["ok"] is True

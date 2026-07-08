from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.evidence.parity import build_tracked_parity_evidence
from ethos.repository.evidence.parity_validation import command_matches_identity
from ethos.repository.evidence.parity_validation import parity_evidence
from ethos.repository.evidence.parity_validation import validate_parity_evidence
from tests.unit.product.parity.snapshots import complete_parity_evidence

if TYPE_CHECKING:
    from pathlib import Path


def test_tracked_parity_evidence_reports_absent_adopter_and_non_object_payload(
    tmp_path: Path,
) -> None:
    assert parity_evidence(tmp_path, None) == {}
    path = tmp_path / "evidence" / "parity" / "generic-shadow.json"
    path.parent.mkdir(parents=True)
    path.write_text("[]\n", encoding="utf-8")

    report = parity_evidence(tmp_path, "generic")

    assert report["path"] == "evidence/parity/generic-shadow.json"
    assert report["required_gaps"] == ["parity_evidence_not_object"]
    assert report["verified_capabilities"] == []


def test_parity_validation_boundary_gaps() -> None:
    payload = complete_parity_evidence("generic")
    payload["command"] = (
        "ethos parity shadow --adopter other --target /tmp/generic --execute --json"
    )
    payload["shadow"] = "not-shadow"
    payload["verified_capabilities"] = ["not-a-capability"]
    payload["capability_basis"] = "not-basis"
    freshness = payload["freshness"]
    assert isinstance(freshness, dict)
    freshness["product_head"] = "old-product"
    freshness["target_head"] = "old-target"
    freshness["command_sha256"] = "bad-digest"

    gaps = validate_parity_evidence(
        payload,
        "generic",
        current_product_head="new-product",
        current_target_head="new-target",
    )

    assert "parity_evidence_invalid:generic" in gaps
    assert "parity_evidence_invalid:generic:command_identity" in gaps
    assert "parity_evidence_invalid:generic:shadow" in gaps
    assert "parity_evidence_invalid:generic:unknown_capability" in gaps
    assert "parity_evidence_invalid:generic:capability_basis" in gaps
    assert "parity_evidence_invalid:generic:command_sha256" in gaps
    assert "parity_evidence_invalid:generic:product_head" in gaps
    assert "parity_evidence_invalid:generic:target_head" in gaps
    assert command_matches_identity("ethos status --json", adopter="generic", target=None) is False
    assert (
        command_matches_identity(
            "ethos parity shadow --adopter generic --execute --json",
            adopter="generic",
            target="/tmp/generic",
        )
        is False
    )


def test_parity_validation_accepts_repository_target_command_alias() -> None:
    assert (
        command_matches_identity(
            "uv run --package ethos ethos parity shadow --adopter generic "
            "--target . --execute --timeout-seconds 30 --json",
            adopter="generic",
            target="<repo>",
        )
        is True
    )
    assert (
        command_matches_identity(
            "uv run --package ethos ethos parity shadow --adopter generic "
            "--execute --timeout-seconds 30 --json",
            adopter="generic",
            target="<repo>",
        )
        is False
    )


def test_parity_validation_accepts_equivalent_heads_and_rejects_bad_capability_basis() -> None:
    payload = complete_parity_evidence("generic")
    capabilities = payload["verified_capabilities"]
    assert isinstance(capabilities, list)
    first = capabilities[0]
    basis = payload["capability_basis"]
    assert isinstance(basis, dict)
    basis[first] = []

    gaps = validate_parity_evidence(
        payload,
        "generic",
        current_product_head="new-product",
        current_target_head="new-target",
        acceptable_product_heads=("product-head",),
        acceptable_target_heads=("target-head",),
    )

    assert "parity_evidence_invalid:generic:product_head" not in gaps
    assert "parity_evidence_invalid:generic:target_head" not in gaps
    assert f"parity_evidence_invalid:generic:capability_basis:{first}" in gaps


def test_tracked_parity_evidence_records_numeric_false_negative_string(tmp_path: Path) -> None:
    payload = build_tracked_parity_evidence(
        adopter="generic",
        target=tmp_path,
        shadow={"ok": True, "required_gaps": [], "false_negative_count": "2"},
        current_product_head="product",
        current_target_head="target",
        timeout_seconds=30,
        root=tmp_path,
    )

    assert payload["shadow"]["false_negative_count"] == 2

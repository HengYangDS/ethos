from __future__ import annotations

import hashlib
from pathlib import Path

from ethos.repository.evidence.claims import claims_report


def test_claim_evidence_digests_are_verified() -> None:
    report = claims_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert "ethos-product-canonization" in report["claims"]
    assert "ethos-framework-hardening" in report["claims"]


def test_asset_quality_claim_promotion_targets_cover_semantic_change_surface() -> None:
    report = claims_report(Path.cwd())
    claim = report["claims"]["ethos-asset-quality-kernel"]
    envelope = claim["trust_envelope"]
    targets = {target["path"] for target in envelope["promotion"]["targets"]}

    assert {
        "packages/ethos/src/ethos/cli.py",
        "packages/ethos/src/ethos/repository/policy/gates.py",
        "packages/ethos/src/ethos/repository/evidence/core.py",
        "packages/ethos/src/ethos/repository/registry/docs",
        "packages/ethos/src/ethos/repository/policy/schema.py",
        "packages/ethos-core/src/ethos_core/action_graph.py",
        "tests/unit/kernel/test_quality.py",
        "tests/unit/lanes/test_runner_evidence.py",
        "tests/unit/cli/test_contracts.py",
        "tests/unit/governance/validation",
        "docs/reference/command-plane.md",
        "docs/reference/glossary.md",
        "openspec/changes/archive/2026-07-01-ethos-asset-quality-kernel/proposal.md",
    } <= targets


def test_active_claims_do_not_promote_transient_execution_plans() -> None:
    report = claims_report(Path.cwd())

    findings = []
    for claim_id, claim in report["claims"].items():
        if claim["state"] != "active":
            continue
        targets = claim["trust_envelope"]["promotion"]["targets"]
        findings.extend(
            f"{claim_id}:{target['path']}"
            for target in targets
            if str(target["path"]).startswith("docs/superpowers/")
        )

    assert findings == []


def test_active_claim_text_uses_historical_not_legacy_binding_language() -> None:
    report = claims_report(Path.cwd())

    findings = []
    for claim_id, claim in report["claims"].items():
        if claim["state"] != "active":
            continue
        text = Path(claim["path"]).read_text(encoding="utf-8").lower()
        if "legacy" in text:
            findings.append(claim_id)

    assert findings == []


def test_empty_claims_directory_is_a_gap(tmp_path: Path) -> None:
    (tmp_path / "evidence" / "claims").mkdir(parents=True)

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "claims_missing" in report["required_gaps"]


def test_profile_claims_root_accepts_recursive_change_claims(tmp_path: Path) -> None:
    evidence = tmp_path / "docs" / "evidence"
    claims = tmp_path / "claims" / "changes"
    profile = tmp_path / ".ethos" / "profile.toml"
    evidence.mkdir(parents=True)
    claims.mkdir(parents=True)
    profile.parent.mkdir()
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    profile.write_text(
        'schema_version = 1\n[roots]\nclaims = "claims"\ndurable_evidence = "docs/evidence"',
        encoding="utf-8",
    )
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                'id = "sample-change"',
                'kind = "change"',
                'lifecycle = "evidence_closed"',
                "",
                "[[evidence_refs]]",
                'artifact = "docs/evidence/sample.md"',
                f'digest = "sha256:{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
                'verdict = "pass"',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is True
    assert report["claims_root"] == "claims"
    assert "sample-change" in report["claims"]


def test_active_change_claim_without_evidence_refs_is_not_closed_claim_gap(tmp_path: Path) -> None:
    claims = tmp_path / "claims" / "changes"
    profile = tmp_path / ".ethos" / "profile.toml"
    claims.mkdir(parents=True)
    profile.parent.mkdir()
    profile.write_text('schema_version = 1\n[roots]\nclaims = "claims"\n', encoding="utf-8")
    (claims / "active.toml").write_text(
        'id = "active-change"\nkind = "change"\nlifecycle = "active"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is True
    assert report["claims"]["active-change"]["state"] == "active"


def test_active_claims_reject_retired_product_family_subjects(tmp_path: Path) -> None:
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
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
                'dated = "evidence/sample.md"',
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
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
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
                'dated = "evidence/sample.md"',
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


def test_active_claim_commands_do_not_use_retired_ci_runner_root() -> None:
    report = claims_report(Path.cwd())

    findings: list[str] = []
    for claim_id, claim in report["claims"].items():
        if claim["state"] != "active":
            continue
        envelope = claim.get("trust_envelope") or {}
        evidence = envelope.get("evidence") or {}
        commands = evidence.get("commands") or []
        for command in commands:
            if ".config/ci/scripts" in str(command):
                findings.append(f"{claim_id}:evidence.commands:{command}")
        fallback = envelope.get("fallback", "")
        if ".config/ci/scripts" in str(fallback):
            findings.append(f"{claim_id}:fallback:{fallback}")
        promotion = envelope.get("promotion") or {}
        for target in promotion.get("targets") or []:
            target_path = str(target.get("path") or "")
            if target_path.startswith(".config/ci/scripts"):
                findings.append(f"{claim_id}:promotion.targets:{target_path}")

    assert findings == []


def test_active_claims_require_typed_evidence_claim_binding(tmp_path: Path) -> None:
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
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
                'dated = "evidence/sample.md"',
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
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "hosted CI verified and reference cache parity passed"',
                "",
                "[evidence]",
                'dated = "evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
                'binding = "hosted CI verified and reference cache parity passed"',
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
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
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
                'dated = "evidence/sample.md"',
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


def _write_head_claim(tmp_path: Path, *, head: str | None) -> None:
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    claims.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    lines = [
        "[claim]",
        'id = "ethos-sample"',
        'subject = "ethos:sample"',
        'state = "active"',
        'summary = "sample claim"',
        "",
        "[evidence]",
        'dated = "evidence/sample.md"',
        'evidence_ids = ["evidence:sample"]',
        'binding = "digest-bound evidence binding"',
        'verifier = "digest_only"',
        f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
    ]
    if head is not None:
        lines.append(f'head = "{head}"')
    (claims / "ethos-sample.toml").write_text("\n".join(lines), encoding="utf-8")


def test_claim_with_stale_head_blocks(tmp_path: Path) -> None:
    _write_head_claim(tmp_path, head="oldhead")

    report = claims_report(tmp_path, current_head="newhead")

    assert report["ok"] is False
    assert any(
        gap.startswith("ethos-sample:evidence.head_stale") for gap in report["required_gaps"]
    )


def test_claim_without_head_is_advisory_not_blocking(tmp_path: Path) -> None:
    _write_head_claim(tmp_path, head=None)

    report = claims_report(tmp_path, current_head="newhead")

    # Legacy unbound claim surfaces as advisory (migration signal), does not block.
    assert "ethos-sample:evidence.head_unbound" in report["advisory_gaps"]
    assert not any("head" in gap for gap in report["required_gaps"])


def test_claim_with_matching_head_passes(tmp_path: Path) -> None:
    _write_head_claim(tmp_path, head="matchhead")

    report = claims_report(tmp_path, current_head="matchhead")

    assert not any("head" in gap for gap in report["required_gaps"])
    assert not any("head" in gap for gap in report["advisory_gaps"])

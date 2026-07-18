from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.repository.evidence.claims import claims_report

if TYPE_CHECKING:
    import pytest


def test_claim_evidence_digests_are_verified() -> None:
    report = claims_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert "ethos-product-canonization" in report["claims"]
    assert "ethos-framework-hardening" in report["claims"]


def test_tracked_claims_use_only_the_canonical_envelope() -> None:
    claim_paths = sorted((Path.cwd() / "evidence" / "claims").rglob("*.toml"))
    noncanonical = [
        path.relative_to(Path.cwd()).as_posix()
        for path in claim_paths
        if not isinstance(tomllib.loads(path.read_text(encoding="utf-8")).get("claim"), dict)
    ]

    assert noncanonical == []


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
        "packages/ethos-core/src/ethos_core/action_graph/core.py",
        "tests/unit/kernel/test_quality.py",
        "tests/unit/lanes/test_runner_evidence.py",
        "tests/unit/cli/test_contracts.py",
        "tests/unit/governance/validation",
        "docs/reference/command-plane.md",
        "docs/reference/glossary.md",
        "openspec/changes/archive/2026-07-01-ethos-asset-quality-kernel/proposal.md",
    } <= targets


def test_empty_claims_directory_is_a_gap(tmp_path: Path) -> None:
    (tmp_path / "evidence" / "claims").mkdir(parents=True)

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "claims_missing" in report["required_gaps"]


def test_profile_claims_root_accepts_recursive_canonical_claims(tmp_path: Path) -> None:
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
                "[claim]",
                'id = "sample-change"',
                'subject = "ethos:sample-change"',
                'state = "accepted"',
                'summary = "sample canonical claim"',
                "",
                "[evidence]",
                'dated = "docs/evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is True
    assert report["claims_root"] == "claims"
    assert "sample-change" in report["claims"]


def test_top_level_claim_shape_is_rejected_without_compatibility_parser(
    tmp_path: Path,
) -> None:
    claims = tmp_path / "claims" / "changes"
    profile = tmp_path / ".ethos" / "profile.toml"
    claims.mkdir(parents=True)
    profile.parent.mkdir()
    profile.write_text('schema_version = 1\n[roots]\nclaims = "claims"\n', encoding="utf-8")
    (claims / "active.toml").write_text(
        'id = "active-change"\n',
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["active:claim_envelope_missing"]


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


def test_active_trust_claim_requires_boundary_carriers_and_promotion(
    tmp_path: Path,
) -> None:
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
    assert "sample:claim_assurance_invalid" in report["required_gaps"]


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
    assert "sample:claim_assurance_invalid" in report["required_gaps"]


def test_active_product_claim_rejects_private_adopter_and_workstation_literals(
    tmp_path: Path,
) -> None:
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    carrier = tmp_path / "openspec" / "specs" / "quality"
    target = tmp_path / "docs" / "guide.md"
    claims.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
    carrier.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (carrier / "spec.md").write_text("spec\n", encoding="utf-8")
    target.write_text("guide\n", encoding="utf-8")
    workstation_path = "/" + "Users" + "/example/project"
    (claims / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                f'summary = "uses private project `domain-adopter` and {workstation_path} as authority"',
                "",
                "[evidence]",
                'dated = "evidence/sample.md"',
                f'sha256 = "{hashlib.sha256(evidence_file.read_bytes()).hexdigest()}"',
                'binding = "digest-bound evidence binding"',
                'verifier = "digest_only"',
                'evidence_ids = ["evidence:sample"]',
                "",
                "[boundary]",
                'owner = "ethos"',
                'scope = "sample"',
                "",
                "[carriers]",
                'openspec = "openspec/specs/quality/spec.md"',
                "",
                'fallback = "use generic profile evidence"',
                'kill_signal = "private repository names become product authority"',
                "",
                "[promotion]",
                'targets = ["docs/guide.md"]',
            ]
        ),
        encoding="utf-8",
    )

    report = claims_report(tmp_path)

    assert report["ok"] is False
    assert "sample:active_claim_private_coupling:private_adopter_literal" in report["required_gaps"]
    assert "sample:active_claim_private_coupling:local_workstation_path" in report["required_gaps"]


def _write_freshness_claim(
    tmp_path: Path,
    *,
    mode: str,
    head: str | None = None,
    semantic_sha256: str | None = None,
) -> None:
    claims = tmp_path / "evidence" / "claims"
    evidence = tmp_path / "evidence"
    openspec = tmp_path / "openspec" / "sample"
    claims.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    openspec.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence / "sample.md"
    evidence_file.write_text("sample\n", encoding="utf-8")
    (tmp_path / "source.py").write_text("value = 1\n", encoding="utf-8")
    (openspec / "proposal.md").write_text("# Sample\n", encoding="utf-8")
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
    lines.extend(["", "[evidence.freshness]", f'mode = "{mode}"'])
    if head is not None:
        lines.append(f'head = "{head}"')
    if semantic_sha256 is not None:
        lines.append(f'semantic_sha256 = "{semantic_sha256}"')
    lines.extend(
        [
            "",
            "[boundary]",
            'owner = "quality"',
            'scope = "sample claim"',
            "",
            "[carriers]",
            'openspec = "openspec/sample/proposal.md"',
            'fallback = "re-run the sample proof"',
            'kill_signal = "sample evidence no longer matches"',
            "",
            "[promotion]",
            'targets = ["source.py"]',
        ]
    )
    (claims / "ethos-sample.toml").write_text("\n".join(lines), encoding="utf-8")


def test_claim_with_stale_head_blocks(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="head_bound", head="oldhead")

    report = claims_report(tmp_path, current_head="newhead")

    assert report["ok"] is False
    assert any(
        gap.startswith("ethos-sample:evidence.head_stale") for gap in report["required_gaps"]
    )


def test_claim_without_freshness_is_blocking(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="historical")
    path = tmp_path / "evidence" / "claims" / "ethos-sample.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('\n[evidence.freshness]\nmode = "historical"', ""),
        encoding="utf-8",
    )

    report = claims_report(tmp_path, current_head="newhead")

    assert "ethos-sample:evidence.freshness_missing" in report["required_gaps"]


def test_claim_without_freshness_reports_declared_stale_head(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="historical")
    path = tmp_path / "evidence" / "claims" / "ethos-sample.toml"
    path.write_text(
        path.read_text(encoding="utf-8")
        .replace("\n\n[evidence.freshness]", '\nhead = "oldhead"\n\n[evidence.freshness]')
        .replace('\n[evidence.freshness]\nmode = "historical"', ""),
        encoding="utf-8",
    )

    report = claims_report(tmp_path, current_head="newhead")

    assert "ethos-sample:evidence.freshness_missing" in report["required_gaps"]
    assert "ethos-sample:evidence.head_stale:oldhead!=newhead" in report["required_gaps"]


def test_claim_with_matching_head_passes(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="head_bound", head="matchhead")

    report = claims_report(tmp_path, current_head="matchhead")

    assert not any("head" in gap for gap in report["required_gaps"])
    assert not any("head" in gap for gap in report["advisory_gaps"])


def test_head_bound_claim_requires_a_head(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="head_bound")

    report = claims_report(tmp_path, current_head="currenthead")

    assert "ethos-sample:evidence.head_missing" in report["required_gaps"]


def test_head_bound_claim_rejects_a_semantic_digest(tmp_path: Path) -> None:
    _write_freshness_claim(
        tmp_path,
        mode="head_bound",
        head="currenthead",
        semantic_sha256="a" * 64,
    )

    report = claims_report(tmp_path, current_head="currenthead")

    assert "ethos-sample:evidence.head_bound_semantic_digest_forbidden" in report["required_gaps"]


def test_historical_claim_is_durably_bound_without_current_head(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="historical")

    report = claims_report(tmp_path, current_head="newhead")

    assert report["required_gaps"] == []
    assert report["claims"]["ethos-sample"]["freshness"]["state"] == "durably_bound"


def test_semantic_scope_claim_requires_current_matching_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_freshness_claim(
        tmp_path,
        mode="semantic_scope",
        head="a" * 40,
        semantic_sha256="b" * 64,
    )
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_args, **_kwargs: "b" * 64,
    )

    report = claims_report(tmp_path, current_head="c" * 40)

    assert report["required_gaps"] == []
    assert report["claims"]["ethos-sample"]["freshness"]["state"] == "current"


def test_semantic_scope_claim_blocks_when_semantic_target_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_freshness_claim(
        tmp_path,
        mode="semantic_scope",
        head="a" * 40,
        semantic_sha256="b" * 64,
    )
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_args, **_kwargs: "c" * 64,
    )

    report = claims_report(tmp_path, current_head="d" * 40)

    assert "ethos-sample:evidence.semantic_scope_stale" in report["required_gaps"]


def test_semantic_scope_claim_requires_its_binding_fields(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="semantic_scope")

    report = claims_report(tmp_path, current_head="currenthead")

    assert "ethos-sample:evidence.head_missing" in report["required_gaps"]
    assert "ethos-sample:evidence.semantic_sha256_missing" in report["required_gaps"]


def test_semantic_scope_claim_blocks_when_semantic_digest_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_freshness_claim(
        tmp_path,
        mode="semantic_scope",
        head="a" * 40,
        semantic_sha256="b" * 64,
    )
    monkeypatch.setattr(
        "ethos.repository.evidence.claims.semantic_tree_digest",
        lambda *_args, **_kwargs: "",
    )

    report = claims_report(tmp_path, current_head="c" * 40)

    assert "ethos-sample:evidence.semantic_scope_unavailable" in report["required_gaps"]


def test_claim_with_unknown_freshness_mode_is_blocking(tmp_path: Path) -> None:
    _write_freshness_claim(tmp_path, mode="undeclared")

    report = claims_report(tmp_path, current_head="currenthead")

    assert "ethos-sample:evidence.freshness_mode_invalid" in report["required_gaps"]


def test_adopter_lifecycle_claim_uses_exact_behavioral_semantic_scope() -> None:
    report = claims_report(Path.cwd())
    claim = report["claims"]["adopter-openspec-lifecycle-20260714"]

    assert claim["freshness"]["paths"] == [
        "packages/ethos/src/ethos/surface/cli/root/planning.py",
        "packages/ethos/src/ethos/surface/cli/root/proof.py",
        "tests/unit/cli/test_adopter_openspec_lifecycle.py",
        "tests/unit/cli/test_contracts_proof.py",
    ]

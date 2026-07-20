from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ethos.repository.evidence.topology import evidence_topology_report
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from ethos_core import _resources
from ethos_core.contracts.evidence import layout as layout_contract
from ethos_core.contracts.evidence.layout import load_evidence_layout_declaration
from tests.support.ethos_cli_runner import run_ethos


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _profile(root: Path, *, durable_evidence: str, claims: str = "") -> None:
    payload = RepositoryProfileDeclaration.bootstrap(root.name).model_dump(mode="python")
    payload["roots"]["durable_evidence"] = durable_evidence
    if claims:
        payload["roots"]["claims"] = claims
    _write(
        root / ".ethos/profile.toml",
        render_repository_profile(RepositoryProfileDeclaration.model_validate(payload)),
    )


def _write_claim(root: Path, claims: str, evidence: Path) -> None:
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    _write(
        root / claims / "sample.toml",
        f'[claim]\nid = "sample"\nstate = "superseded"\n\n[evidence]\ndated = "{evidence.relative_to(root).as_posix()}"\nsha256 = "{digest}"\n',
    )


def _write_freshness_support(root: Path, claim: str) -> None:
    _write(root / "docs/decision.md", "# Decision\n")
    _write(root / "tests/proof.py", "def test_ok():\n    assert True\n")
    _write(
        root / "evolution/ledger.toml",
        f'''schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "sample"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "{claim}"
challenge = "Evidence layout must remain explicit."
transition = "shape -> canonize"
proof_refs = ["ethos quality evidence-freshness --json"]
review_refs = ["tests/proof.py"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["evidence layout is clean"]
''',
    )


def test_evidence_topology_accepts_kernel_layout(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    (evidence / "claims").mkdir(parents=True)
    (evidence / "chronicle" / "topic").mkdir(parents=True)
    (evidence / "parity").mkdir(parents=True)
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")
    (evidence / "claims" / "sample.toml").write_text("", encoding="utf-8")
    (evidence / "chronicle" / "topic" / "2026-07-08.md").write_text("proof", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    declaration = load_evidence_layout_declaration()

    assert report["layout"] == declaration.layout_payload("evidence")
    assert report["counts"]["claim_files"] == 1
    assert report["counts"]["chronicle_records"] == 1


def test_evidence_topology_reports_missing_root(tmp_path: Path) -> None:
    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["evidence_root_missing"]
    assert report["counts"] == {
        "claim_files": 0,
        "chronicle_records": 0,
        "parity_artifacts": 0,
    }


def test_evidence_topology_rejects_invalid_profile(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("[", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["adopter_profile_invalid:.ethos/profile.toml"]


def test_evidence_topology_blocks_unknown_root_directory(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    (evidence / "claims").mkdir(parents=True)
    (evidence / "chronicle" / "topic").mkdir(parents=True)
    (evidence / "parity").mkdir(parents=True)
    (evidence / "tmp").mkdir()
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert "evidence_root_dir_not_allowed:tmp" in report["required_gaps"]


def test_evidence_topology_blocks_root_clutter_flat_chronicle_and_nested_claims(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    (evidence / "claims" / "nested").mkdir(parents=True)
    (evidence / "chronicle").mkdir(parents=True)
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")
    (evidence / "proof.md").write_text("root clutter", encoding="utf-8")
    (evidence / "claims" / "nested" / "sample.toml").write_text("", encoding="utf-8")
    (evidence / "chronicle" / "2026-07-08.md").write_text("flat", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "evidence_root_file_not_allowed:proof.md",
        "evidence_claim_nested_file:nested/sample.toml",
        "evidence_chronicle_flat_markdown:2026-07-08.md",
        "evidence_parity_root_missing",
    ]


def test_quality_evidence_freshness_blocks_evidence_topology_gaps(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    chronicle = evidence / "chronicle" / "topic" / "2026-07-08.md"
    _write(chronicle, "proof")
    (evidence / "claims").mkdir()
    (evidence / "parity").mkdir()
    _write(evidence / "README.md", "# Evidence\n")
    _write(evidence / "root-proof.md", "root clutter")
    _write_claim(tmp_path, "evidence/claims", chronicle)
    _write_freshness_support(tmp_path, "Evidence topology gaps must block freshness.")

    payload = run_ethos(
        "quality",
        "evidence-freshness",
        "--root",
        tmp_path.as_posix(),
        "--json",
        cwd=tmp_path,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["summary"]["topology_issue_count"] == 1
    assert payload["required_gaps"] == ["evidence_root_file_not_allowed:root-proof.md"]
    assert payload["data"]["claims"]["ok"] is True
    assert payload["data"]["evolution"]["ok"] is True
    assert payload["data"]["topology"]["ok"] is False


def test_quality_evidence_freshness_uses_profile_durable_evidence_root(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, claims="claims", durable_evidence="docs/evidence")
    docs_evidence = tmp_path / "docs" / "evidence"
    (docs_evidence / "claims").mkdir(parents=True)
    chronicle = docs_evidence / "chronicle" / "topic" / "2026-07-08.md"
    _write(chronicle, "profile evidence root proof")
    (docs_evidence / "parity").mkdir(parents=True)
    _write(docs_evidence / "README.md", "# Evidence\n")
    _write_claim(tmp_path, "claims", chronicle)
    _write_freshness_support(tmp_path, "Profile evidence roots must be honored.")

    payload = run_ethos(
        "quality",
        "evidence-freshness",
        "--root",
        tmp_path.as_posix(),
        "--json",
        cwd=tmp_path,
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["summary"]["evidence_roots"] == ["docs/evidence"]
    assert payload["data"]["topology"]["layout"]["root"] == "docs/evidence"


def test_evidence_topology_keeps_custom_non_docs_root_in_kernel_mode(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, durable_evidence="records/evidence")
    evidence = tmp_path / "records" / "evidence"
    (evidence / "claims").mkdir(parents=True)
    (evidence / "chronicle" / "topic").mkdir(parents=True)
    (evidence / "parity").mkdir(parents=True)
    (evidence / "delivery").mkdir()
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert "evidence_root_dir_not_allowed:delivery" in report["required_gaps"]
    declaration = load_evidence_layout_declaration()

    assert report["layout"] == declaration.layout_payload("records/evidence")


def test_evidence_topology_reports_missing_profile_docs_evidence_root(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, durable_evidence="docs/evidence")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["evidence_root_missing"]
    assert report["layout"]["mode"] == "curated_profile_evidence"
    assert report["counts"]["curated_artifacts"] == 0


def test_evidence_topology_blocks_profile_docs_evidence_root_file_clutter(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, durable_evidence="docs/evidence")
    evidence = tmp_path / "docs" / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")
    (evidence / "loose.json").write_text("{}", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["evidence_root_file_not_allowed:loose.json"]
    assert report["counts"]["curated_artifacts"] == 1


def test_quality_evidence_freshness_accepts_profile_curated_docs_evidence_layout(
    tmp_path: Path,
) -> None:
    _profile(tmp_path, claims="claims", durable_evidence="docs/evidence")
    curated = tmp_path / "docs" / "evidence" / "delivery" / "2026-07-08.md"
    _write(curated, "curated adopter delivery evidence")
    _write(tmp_path / "docs/evidence/README.md", "# Evidence\n")
    _write_claim(tmp_path, "claims", curated)
    _write_freshness_support(tmp_path, "Profile evidence roots may hold curated delivery evidence.")

    payload = run_ethos(
        "quality",
        "evidence-freshness",
        "--root",
        tmp_path.as_posix(),
        "--json",
        cwd=tmp_path,
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["topology"]["layout"]["mode"] == "curated_profile_evidence"
    assert payload["data"]["topology"]["counts"]["curated_artifacts"] == 1


def test_evidence_layout_declaration_loads_source_refs_and_packaged_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    declaration = load_evidence_layout_declaration()

    assert declaration.id == "evidence-layout"
    assert declaration.source_refs == ("system/policies/evidence-layout.toml",)
    assert declaration.layout_payload("evidence")["allowed_root_dirs"] == [
        "claims",
        "chronicle",
        "parity",
    ]

    missing = tmp_path / "missing-evidence-layout.toml"
    fallback = load_evidence_layout_declaration(missing)

    assert fallback.id == "evidence-layout"

    monkeypatch.setattr(
        layout_contract,
        "DECLARATION_PATH",
        layout_contract.Path("missing/default-evidence-layout.toml"),
    )
    default_fallback = load_evidence_layout_declaration()

    assert default_fallback.id == "evidence-layout"


def test_evidence_layout_declaration_default_path_falls_back_to_packaged_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover installed-wheel fallback when no source declaration is discoverable."""
    missing_declaration = Path("missing/system/policies/evidence-layout.toml")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(layout_contract, "DECLARATION_PATH", missing_declaration)

    declaration = load_evidence_layout_declaration()

    assert declaration.id == "evidence-layout"
    assert declaration.source_refs == ("system/policies/evidence-layout.toml",)


def test_evidence_layout_declaration_fails_when_no_resource_or_source_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_resources, "_SOURCE_FILE", tmp_path / "source.py")
    monkeypatch.setattr(
        _resources.resources, "files", lambda _: (_ for _ in ()).throw(FileNotFoundError)
    )

    with pytest.raises(FileNotFoundError, match="declaration resource unavailable"):
        load_evidence_layout_declaration(tmp_path / "missing.toml")

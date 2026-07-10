from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from ethos.repository.evidence.topology import evidence_topology_report
from ethos_core.contracts.evidence import layout as layout_contract
from ethos_core.contracts.evidence.layout import load_evidence_layout_declaration
from tests.support.ethos_cli_runner import run_ethos


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
    chronicle.parent.mkdir(parents=True)
    chronicle.write_text("proof", encoding="utf-8")
    (evidence / "claims").mkdir()
    (evidence / "parity").mkdir()
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")
    (evidence / "root-proof.md").write_text("root clutter", encoding="utf-8")
    digest = hashlib.sha256(chronicle.read_bytes()).hexdigest()
    claim_text = f'''
[claim]
id = "sample"
state = "superseded"

[evidence]
dated = "evidence/chronicle/topic/2026-07-08.md"
sha256 = "{digest}"
'''.strip()
    (evidence / "claims" / "sample.toml").write_text(claim_text, encoding="utf-8")

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "proof.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir()
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "sample"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Evidence topology gaps must block freshness."
challenge = "Root clutter makes evidence ambiguous."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["tests/proof.py"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["topology is clean"]
""".strip(),
        encoding="utf-8",
    )

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
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """
[roots]
claims = "claims"
durable_evidence = "docs/evidence"
""".strip(),
        encoding="utf-8",
    )
    docs_evidence = tmp_path / "docs" / "evidence"
    (docs_evidence / "claims").mkdir(parents=True)
    chronicle = docs_evidence / "chronicle" / "topic" / "2026-07-08.md"
    chronicle.parent.mkdir(parents=True)
    chronicle.write_text("profile evidence root proof", encoding="utf-8")
    (docs_evidence / "parity").mkdir(parents=True)
    (docs_evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")

    claims = tmp_path / "claims"
    claims.mkdir()
    digest = hashlib.sha256(chronicle.read_bytes()).hexdigest()
    claims.joinpath("sample.toml").write_text(
        f'''
[claim]
id = "sample"
state = "superseded"

[evidence]
dated = "docs/evidence/chronicle/topic/2026-07-08.md"
sha256 = "{digest}"
'''.strip(),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "proof.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir()
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "sample"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Profile evidence roots must be honored."
challenge = "Adopter docs/evidence roots must not be reported as missing evidence/."
transition = "profile -> freshness"
proof_refs = ["ethos quality evidence-freshness --json"]
review_refs = ["tests/proof.py"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["profile root honored"]
""".strip(),
        encoding="utf-8",
    )

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
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """
[roots]
durable_evidence = "records/evidence"
""".strip(),
        encoding="utf-8",
    )
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
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """
[roots]
durable_evidence = "docs/evidence"
""".strip(),
        encoding="utf-8",
    )

    report = evidence_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["evidence_root_missing"]
    assert report["layout"]["mode"] == "curated_profile_evidence"
    assert report["counts"]["curated_artifacts"] == 0


def test_evidence_topology_blocks_profile_docs_evidence_root_file_clutter(
    tmp_path: Path,
) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """
[roots]
durable_evidence = "docs/evidence"
""".strip(),
        encoding="utf-8",
    )
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
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """
[roots]
claims = "claims"
durable_evidence = "docs/evidence"
""".strip(),
        encoding="utf-8",
    )
    curated = tmp_path / "docs" / "evidence" / "delivery" / "2026-07-08.md"
    curated.parent.mkdir(parents=True)
    curated.write_text("curated adopter delivery evidence", encoding="utf-8")
    (tmp_path / "docs" / "evidence" / "README.md").write_text("# Evidence\n", encoding="utf-8")

    claims = tmp_path / "claims"
    claims.mkdir()
    digest = hashlib.sha256(curated.read_bytes()).hexdigest()
    claims.joinpath("sample.toml").write_text(
        f'''
[claim]
id = "sample"
state = "superseded"

[evidence]
dated = "docs/evidence/delivery/2026-07-08.md"
sha256 = "{digest}"
'''.strip(),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "proof.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir()
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "sample"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Profile evidence roots may hold curated adopter delivery evidence."
challenge = "Adopter docs/evidence delivery trees are curated evidence, not product kernel clutter."
transition = "profile -> curated evidence"
proof_refs = ["ethos quality evidence-freshness --json"]
review_refs = ["tests/proof.py"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["curated docs evidence accepted"]
""".strip(),
        encoding="utf-8",
    )

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

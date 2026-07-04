from __future__ import annotations

import importlib
from pathlib import Path


def authority_graph_report(root: Path) -> dict[str, object]:
    module = importlib.import_module("ethos.repository.authority_graph")
    return module.authority_graph_report(root)


def test_authority_graph_declares_judgment_source_and_derived_views() -> None:
    report = authority_graph_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    entries = {entry["id"]: entry for entry in report["entries"]}

    judgment = entries["ethos:judgment-source"]
    assert judgment["owner"] == "ethos-maintainers"
    assert judgment["canonical_for"] == ["product judgment"]
    assert judgment["stable_path"] == "docs/governance/judgment-source.md"

    north_star = entries["ethos:north-star"]
    assert north_star["derived_from"] == ["ethos:judgment-source"]
    assert north_star["owner"] == "reader-view"


def test_authority_graph_projects_supersession_without_owning_truth() -> None:
    report = authority_graph_report(Path.cwd())
    entries = {entry["id"]: entry for entry in report["entries"]}

    product_contract = entries["ethos:product-design-contract"]
    assert "ethos:legacy-nine-term-chain" in product_contract["supersedes"]
    assert product_contract["evidence_refs"]
    assert product_contract["stable_path"] == "docs/governance/product-design-contract.md"

    legacy = entries["ethos:legacy-nine-term-chain"]
    assert legacy["superseded_by"] == ["ethos:product-design-contract"]


def test_authority_graph_rejects_non_evidence_refs(tmp_path: Path) -> None:
    (tmp_path / "docs" / "_meta").mkdir(parents=True)
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / "docs" / "governance" / "judgment-source.md").write_text(
        "# Judgment\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "_meta" / "authority_graph.toml").write_text(
        """
[meta]
version = 1

[[node]]
id = "ethos:judgment-source"
owner = "ethos-maintainers"
relation_type = "authority"
canonical_for = ["product judgment"]
derived_from = []
supersedes = []
doc_refs = ["docs/governance/judgment-source.md"]
evidence_refs = ["docs/governance/judgment-source.md"]
stable_path = "docs/governance/judgment-source.md"
""".lstrip(),
        encoding="utf-8",
    )

    report = authority_graph_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "ethos:judgment-source:evidence_ref_not_evidence:docs/governance/judgment-source.md"
    ]


def test_authority_graph_requires_derived_views_to_derive_from_authority(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs" / "_meta").mkdir(parents=True)
    (tmp_path / "docs" / "evidence").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# Reader\n", encoding="utf-8")
    (tmp_path / "docs" / "evidence" / "authority-2026-07-01.md").write_text(
        "# Evidence\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "_meta" / "authority_graph.toml").write_text(
        """
[meta]
version = 1

[[node]]
id = "ethos:north-star"
owner = "reader-view"
relation_type = "derived_view"
canonical_for = ["reader entry"]
derived_from = []
supersedes = []
doc_refs = ["README.md"]
evidence_refs = ["docs/evidence/authority-2026-07-01.md"]
stable_path = "README.md"
""".lstrip(),
        encoding="utf-8",
    )

    report = authority_graph_report(tmp_path)

    assert report["ok"] is False
    assert "ethos:north-star:derived_view_missing_authority_derivation" in (report["required_gaps"])

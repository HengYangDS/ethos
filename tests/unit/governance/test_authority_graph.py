from __future__ import annotations

import importlib
from pathlib import Path


def authority_graph_report(root: Path) -> dict[str, object]:
    module = importlib.import_module("ethos.repository.registry.authority")
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
    (tmp_path / "evidence").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# Reader\n", encoding="utf-8")
    (tmp_path / "evidence" / "chronicle" / "authority").mkdir(parents=True)
    (tmp_path / "evidence" / "chronicle" / "authority" / "2026-07-01.md").write_text(
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
evidence_refs = ["evidence/chronicle/authority/2026-07-01.md"]
stable_path = "README.md"
""".lstrip(),
        encoding="utf-8",
    )

    report = authority_graph_report(tmp_path)

    assert report["ok"] is False
    assert "ethos:north-star:derived_view_missing_authority_derivation" in (report["required_gaps"])


def test_authority_graph_reports_missing_or_invalid_graph(tmp_path: Path) -> None:
    missing = authority_graph_report(tmp_path)
    assert missing == {
        "ok": False,
        "path": "docs/_meta/authority_graph.toml",
        "entries": [],
        "required_gaps": ["authority_graph_missing"],
    }

    (tmp_path / "docs" / "_meta").mkdir(parents=True)
    (tmp_path / "docs" / "_meta" / "authority_graph.toml").write_text(
        "[[node]\n",
        encoding="utf-8",
    )

    invalid = authority_graph_report(tmp_path)
    assert invalid["ok"] is False
    assert invalid["path"] == "docs/_meta/authority_graph.toml"
    assert invalid["entries"] == []
    assert invalid["required_gaps"][0].startswith("authority_graph_invalid_toml:")


def test_authority_graph_reports_shape_and_reference_gaps(tmp_path: Path) -> None:
    (tmp_path / "docs" / "_meta").mkdir(parents=True)
    (tmp_path / "docs" / "_meta" / "authority_graph.toml").write_text(
        """
[meta]
version = 1

[[node]]
id = "dup"
owner = ""
relation_type = "surface"
canonical_for = "product judgment"
derived_from = ["missing-source"]
supersedes = ["missing-old"]
doc_refs = ["docs/missing.md"]
evidence_refs = ["evidence/missing.md"]
stable_path = "docs/missing.md"

[[node]]
id = "dup"
owner = "reader"
relation_type = "decision"
canonical_for = []
derived_from = []
supersedes = []
doc_refs = []
evidence_refs = []
stable_path = ""
""".lstrip(),
        encoding="utf-8",
    )

    report = authority_graph_report(tmp_path)

    assert report["ok"] is False
    assert report["entries"][0]["canonical_for"] == []
    assert report["required_gaps"] == [
        "authority_graph_duplicate_ids",
        "dup:canonical_for_not_list",
        "dup:owner_missing",
        "dup:relation_type_invalid:surface",
        "dup:stable_path_missing:docs/missing.md",
        "dup:doc_ref_missing:docs/missing.md",
        "dup:evidence_ref_missing:evidence/missing.md",
        "dup:derived_from_missing:missing-source",
        "dup:supersedes_missing:missing-old",
        "dup:stable_path_missing",
        "dup:evidence_refs_missing",
    ]


def test_authority_graph_uses_cwd_when_root_is_not_supplied(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "docs" / "_meta").mkdir(parents=True)
    (tmp_path / "docs" / "a.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "a.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "a.md").write_text("# E\n", encoding="utf-8")
    (tmp_path / "docs" / "_meta" / "authority_graph.toml").write_text(
        """
[[node]]
id = "a"
owner = "owner"
relation_type = "authority"
canonical_for = []
derived_from = []
supersedes = []
doc_refs = ["docs/a.md"]
evidence_refs = ["evidence/a.md"]
stable_path = "docs/a.md"
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    module = importlib.import_module("ethos.repository.registry.authority")
    report = module.authority_graph_report()

    assert report["ok"] is True
    assert report["path"] == "docs/_meta/authority_graph.toml"
    assert report["entries"] == [
        {
            "id": "a",
            "owner": "owner",
            "canonical_for": [],
            "derived_from": [],
            "supersedes": [],
            "superseded_by": [],
            "doc_refs": ["docs/a.md"],
            "evidence_refs": ["evidence/a.md"],
            "stable_path": "docs/a.md",
            "relation_type": "authority",
        }
    ]

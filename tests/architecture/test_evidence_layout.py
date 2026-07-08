from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_evidence_root_keeps_only_index_and_owned_subdirectories() -> None:
    """Ensure promoted evidence is organized by semantic owner, not root clutter."""
    allowed_files = {"README.md"}
    allowed_dirs = {"claims", "chronicle", "parity"}

    root_entries = {path.name: path for path in (ROOT / "evidence").iterdir()}
    files = {name for name, path in root_entries.items() if path.is_file()}
    dirs = {name for name, path in root_entries.items() if path.is_dir()}

    assert files == allowed_files
    assert allowed_dirs <= dirs
    assert not (files - allowed_files)


def test_dated_markdown_evidence_lives_in_topic_scoped_chronicle() -> None:
    """Keep dated proof Markdown under topic-scoped judged-history bundles."""
    root_markdown = [path for path in (ROOT / "evidence").glob("*.md") if path.name != "README.md"]
    flat_chronicle_markdown = list((ROOT / "evidence" / "chronicle").glob("*.md"))
    topic_records = list((ROOT / "evidence" / "chronicle").glob("*/*.md"))

    assert root_markdown == []
    assert flat_chronicle_markdown == []
    assert topic_records
    assert all(path.parent.parent == ROOT / "evidence" / "chronicle" for path in topic_records)


def test_evidence_layout_is_exposed_by_quality_read_model() -> None:
    """Keep static layout policy and the public quality gate in one contract."""
    from ethos.repository.evidence.topology import evidence_topology_report

    report = evidence_topology_report(ROOT)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["layout"]["allowed_root_dirs"] == ["claims", "chronicle", "parity"]
    assert report["counts"]["claim_files"] > 0
    assert report["counts"]["chronicle_records"] > 0

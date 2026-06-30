from __future__ import annotations

from pathlib import Path

from ethos_governance.docs_registry import build_docs_registry, docs_health_report


def test_docs_registry_indexes_subject_metadata() -> None:
    registry = build_docs_registry(Path.cwd())

    subjects = {entry["subject"] for entry in registry}

    assert "ethos:kernel" in subjects
    assert "ethos:command-plane" in subjects
    assert all(entry["path"].endswith(".md") for entry in registry)


def test_docs_health_report_has_no_missing_metadata() -> None:
    report = docs_health_report(Path.cwd())

    assert report["ok"] is True
    assert report["missing_metadata"] == []
    assert report["document_count"] >= 10

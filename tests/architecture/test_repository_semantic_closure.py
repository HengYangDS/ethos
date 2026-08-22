"""Repository-wide semantic closure acceptance tests."""

from __future__ import annotations

from pathlib import Path

import ethos.repository.audit as repository_audit_module
from ethos.domain.status import audit_for_root

ROOT = Path(__file__).resolve().parents[2]


def test_current_repository_audit_proves_complete_semantic_closure() -> None:
    """The accepted candidate tree has no unclassified semantic relation."""
    report = audit_for_root(ROOT)
    closure = report["semantic_closure"]

    assert report["verdict"] == "pass", report["required_gaps"]
    assert closure["verdict"] == "pass"
    assert closure["summary"] == {
        "missing": 0,
        "duplicate": 0,
        "orphan": 0,
        "superseded": 0,
        "conflict": 0,
        "unknown": 0,
    }


def test_repository_audit_cannot_pass_when_semantic_closure_is_unknown(
    monkeypatch,
) -> None:
    """All legacy component passes cannot conceal an unproved closure."""
    monkeypatch.setattr(
        repository_audit_module,
        "repository_semantic_closure",
        lambda _root, **_observations: {
            "verdict": "unknown",
            "coverage": "unknown",
            "summary": {
                "missing": 0,
                "duplicate": 0,
                "orphan": 0,
                "superseded": 0,
                "conflict": 0,
                "unknown": 1,
            },
            "missing": [],
            "duplicate": [],
            "orphan": [],
            "superseded": [],
            "conflict": [],
            "unknown": [
                {
                    "relation": "carrier",
                    "kind": "reference",
                    "identity": "current/unreadable.toml",
                    "sources": ["current/unreadable.toml"],
                }
            ],
            "required_gaps": [
                "semantic_carrier_unknown:reference:current/unreadable.toml:current/unreadable.toml"
            ],
        },
    )

    report = repository_audit_module.repository_audit(
        ROOT,
        openspec_mode="shape",
        openspec_shape={"verdict": "pass", "required_gaps": []},
        tracked_documents=tuple(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.md")),
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == [
        "semantic_carrier_unknown:reference:current/unreadable.toml:current/unreadable.toml"
    ]


def test_repository_audit_projects_one_copy_of_a_shared_semantic_gap(monkeypatch) -> None:
    """An owner fact and its aggregate projection do not duplicate one gap."""
    gap = "semantic_owner_duplicate:tool:lint:system/tools.toml"
    contracts = {
        "verdict": "block",
        "contracts": {},
        "declaration_issues": [],
        "required_gaps": [gap],
    }
    closure = {
        "verdict": "block",
        "coverage": "evaluated",
        "summary": {
            "missing": 0,
            "duplicate": 1,
            "orphan": 0,
            "superseded": 0,
            "conflict": 0,
            "unknown": 0,
        },
        "missing": [],
        "duplicate": [],
        "orphan": [],
        "superseded": [],
        "conflict": [],
        "unknown": [],
        "required_gaps": [gap],
    }
    monkeypatch.setattr(repository_audit_module, "system_contracts_report", lambda _root: contracts)
    monkeypatch.setattr(
        repository_audit_module,
        "repository_semantic_closure",
        lambda _root, **_observations: closure,
    )

    report = repository_audit_module.repository_audit(
        ROOT,
        openspec_mode="shape",
        openspec_shape={"verdict": "pass", "required_gaps": []},
        tracked_documents=tuple(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.md")),
    )

    assert report["required_gaps"].count(gap) == 1

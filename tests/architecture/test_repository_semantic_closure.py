"""Repository-wide semantic closure acceptance tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ethos.repository.audit as repository_audit_module
from ethos.domain.status import audit_for_root

if TYPE_CHECKING:
    from ethos.repository.policy.commit import CommitPolicy

ROOT = Path(__file__).resolve().parents[2]


def _passing_commit_observation(
    _root: Path,
    policy: CommitPolicy,
) -> dict[str, object]:
    return {
        "verdict": "pass",
        "state": "current",
        "head": {
            "object_oid": "a" * 40,
            "subject": "fix(policy): use one compiler",
            "author": {"name": "Author", "email": "author@example.invalid"},
            "committer": {"name": "Committer", "email": "committer@example.invalid"},
        },
        "signature": {
            "verdict": "pass",
            "required": policy.signing_required,
            "principal": "signer@example.invalid",
            "fingerprint": "SHA256:test",
        },
        "required_gaps": [],
    }


def test_current_repository_audit_proves_complete_semantic_closure() -> None:
    """The accepted candidate tree has no unclassified semantic relation."""
    report = audit_for_root(ROOT)
    closure = report["semantic_closure"]

    assert closure["verdict"] == "pass"
    assert closure["summary"] == {
        "missing": 0,
        "duplicate": 0,
        "orphan": 0,
        "superseded": 0,
        "conflict": 0,
        "unknown": 0,
    }
    assert report["commit_policy"]["state"] == "current"
    assert report["commit_policy"]["declaration"] == {
        "subject_pattern": (
            "^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)"
            r"(\([a-z0-9-]+\))?: .+"
        ),
        "signing_required": True,
        "signing_format": "ssh",
    }
    assert report["commit_policy"]["head"]["subject"].startswith("chore(openspec):")


def test_repository_audit_fails_closed_through_the_unique_commit_policy_compiler(
    monkeypatch,
) -> None:
    """Malformed tracked policy cannot be hidden by otherwise-green audit reports."""
    observed = False

    def reject_policy(_root: Path) -> CommitPolicy:
        message = "commit_policy_unknown_fields:identity_mode"
        raise ValueError(message)

    def observe(_root: Path, _policy: CommitPolicy) -> dict[str, object]:
        nonlocal observed
        observed = True
        return _passing_commit_observation(_root, _policy)

    monkeypatch.setattr(repository_audit_module, "load_commit_policy", reject_policy)

    report = repository_audit_module.repository_audit(
        ROOT,
        openspec_mode="shape",
        openspec_shape={"verdict": "pass", "required_gaps": []},
        tracked_documents=tuple(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.md")),
        commit_policy_observer=observe,
    )

    assert report["verdict"] == "block"
    assert report["commit_policy"] == {
        "verdict": "block",
        "state": "invalid",
        "declaration": {},
        "head": {},
        "signature": {},
        "required_gaps": ["commit_policy_unknown_fields:identity_mode"],
    }
    assert report["required_gaps"].count("commit_policy_unknown_fields:identity_mode") == 1
    assert observed is False


def test_repository_audit_adds_no_constraint_when_commit_policy_is_absent(monkeypatch) -> None:
    """An absent optional declaration remains an explicit non-blocking fact."""
    monkeypatch.setattr(repository_audit_module, "load_commit_policy", lambda _root: None)

    report = repository_audit_module.repository_audit(
        ROOT,
        openspec_mode="shape",
        openspec_shape={"verdict": "pass", "required_gaps": []},
        tracked_documents=tuple(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.md")),
        commit_policy_observer=_passing_commit_observation,
    )

    assert report["commit_policy"] == {
        "verdict": "pass",
        "state": "absent",
        "declaration": {},
        "head": {},
        "signature": {},
        "required_gaps": [],
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
        commit_policy_observer=_passing_commit_observation,
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
        commit_policy_observer=_passing_commit_observation,
    )

    assert report["required_gaps"].count(gap) == 1

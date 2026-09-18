"""Compose common governance and explicitly invoked product conformance."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.repository.audit as repository_audit_module
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.observation import openspec_shape_report
from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.git import git_files

if TYPE_CHECKING:
    from pathlib import Path


def audit_for_root(
    root: Path, *, openspec_mode: str = "shape", openspec: dict[str, object] | None = None
) -> dict[str, object]:
    """Evaluate common obligations independently of proof-gate representation."""
    if openspec is None:
        openspec = (
            (
                openspec_governance_report(root)
                if openspec_mode == "deep"
                else openspec_shape_report(root)
            )
            if openspec_profile_enabled(root)
            else {"verdict": "pass", "state": "not_applicable", "required_gaps": []}
        )
    return repository_audit_module.governance_audit(
        root,
        openspec=openspec,
        commit_policy_observer=commit_policy_report,
    )


def product_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
    """Execute explicitly selected ETHOS product conformance, never infer identity."""
    reporter = openspec_governance_report if openspec_mode == "deep" else None
    return repository_audit_module.repository_audit(
        root,
        openspec_mode=openspec_mode,
        openspec_reporter=reporter,
        tracked_documents=tuple(git_files(root, "*.md")),
        openspec_shape=openspec_shape_report(root),
        commit_policy_observer=commit_policy_report,
    )

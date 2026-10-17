"""Canonical documentation carriers shared by reader-quality regressions."""

from __future__ import annotations


def documentation_fixture(subject: str, role: str, state: str, title: str) -> str:
    """Build one canonical documentation carrier for health and navigation cases."""
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: {state}\nrelations: {{}}\n---\n\n"
        f"# {title}\n\nStatus: {state}.\n\nPurpose: exercise docs health.\n\nSee also: none.\n"
    )


def decision_fixture(identity: str = "DR-0001", *, subject: str = "sample:decision") -> str:
    """Build a complete accepted decision for shared identity and rationale checks."""
    return (
        f"---\nsubject: {subject}\nrole: decision\nstate: canonical\n"
        f"decision_id: {identity}\ndecision_status: accepted\nrelations: {{}}\n---\n\n"
        f"# {identity}: Shared rationale\n\n"
        "## Context\n\nA lasting choice needs an explicit reason.\n\n"
        "## Decision\n\nKeep rationale with its semantic owner.\n\n"
        "## Alternatives Rejected\n\nAn execution log cannot explain the trade-off.\n\n"
        "## Consequences and Boundary\n\nCurrent behavior stays with the contract.\n\n"
        "## Evidence and Revisit\n\nRevisit when the original assumptions change.\n"
    )

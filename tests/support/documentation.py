"""Canonical documentation carriers shared by reader-quality regressions."""

from __future__ import annotations


def documentation_fixture(subject: str, role: str, state: str, title: str) -> str:
    """Build one canonical documentation carrier for health and navigation cases."""
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: {state}\nrelations: {{}}\n---\n\n"
        f"# {title}\n\nStatus: {state}.\n\nPurpose: exercise docs health.\n\nSee also: none.\n"
    )

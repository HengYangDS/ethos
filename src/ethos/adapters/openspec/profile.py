"""Profile-conditioned OpenSpec lifecycle adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.openspec.commitment import load_lease_bound_openspec_commitment
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.metadata.completion import (
    completed_active_changes_report as _completed,
)
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.repository.openspec.audit import active_change_names as _active_names
from ethos.repository.openspec.audit import active_change_names_in_ref as _active_names_in_ref
from ethos.repository.openspec.audit import (
    protected_branch_active_change_required_gaps as _protected_gaps,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def load_profile_lease_bound_commitment(
    root: Path,
    *,
    expected_head: str,
    base_commitment_digest: str,
    change_id: str | None = None,
) -> Commitment:
    """Load a Lease carrier through the explicitly selected profile adapter."""
    if openspec_profile_enabled(root):
        return load_lease_bound_openspec_commitment(
            root,
            change_id=change_id,
            expected_head=expected_head,
            base_commitment_digest=base_commitment_digest,
        )
    return load_lease_bound_commitment(
        root,
        change_id=change_id,
        expected_head=expected_head,
        base_commitment_digest=base_commitment_digest,
    )


def completed_active_changes_report(root: Path) -> dict[str, object]:
    """Return completion facts only when the OpenSpec profile adapter is enabled."""
    if openspec_profile_enabled(root):
        return _completed(root)
    return {
        "ok": True,
        "state": "not_applicable",
        "root": root.resolve().as_posix(),
        "completed_changes": [],
        "required_gaps": [],
    }


def active_change_names(root: Path) -> list[str]:
    """Discover active changes only inside the selected OpenSpec profile."""
    repo = root.parent if root.name == "openspec" else root
    return _active_names(repo / "openspec") if openspec_profile_enabled(repo) else []


def active_change_names_in_ref(root: Path, ref: str) -> list[str]:
    """Discover tree-bound active changes only for the selected profile."""
    return _active_names_in_ref(root, ref) if openspec_profile_enabled(root) else []


def protected_branch_active_change_required_gaps(root: Path, *, current_branch: str) -> list[str]:
    """Return protected-branch residue only for the selected OpenSpec profile."""
    if not openspec_profile_enabled(root):
        return []
    return _protected_gaps(root, current_branch=current_branch)

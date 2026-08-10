"""Semantic validation for Commitment rebind ref transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import rebind_target_fields
from ethos.adapters.repo.git import run_git
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import GitRefUpdate


def commitment_rebind_operation(
    repo: Path,
    update: GitRefUpdate,
    lease: dict[str, object],
    target: dict[str, str],
) -> str:
    """Classify one rebind as semantic update or identity repair."""
    try:
        old = load_lease_bound_commitment(repo, lease=lease)
        target = rebind_target_fields(
            repo,
            old_head=update.expected,
            new_head=update.desired,
            commitment=old,
            target=target,
        )
        new = load_commitment(
            repo,
            carrier=target["base_commitment_path"],
            tree_ref=update.desired,
            expected_digest=target["base_commitment_digest"],
        )
    except (KeyError, ValueError):
        return "commitment.rebind"
    return "change.identity-repair" if old.id != new.id else "commitment.rebind"


def commitment_rebind_gap(
    root: Path,
    lease: dict[str, object],
    target: dict[str, str],
    *,
    old_value: str,
    new_value: str,
) -> str:
    """Validate one semantic Work Lane ref move against live immutable facts."""
    try:
        old_commitment = load_lease_bound_commitment(root, lease=lease)
        target = rebind_target_fields(
            root,
            old_head=old_value,
            new_head=new_value,
            commitment=old_commitment,
            target=target,
        )
        new_commitment = load_commitment(
            root,
            carrier=target["base_commitment_path"],
            tree_ref=new_value,
            expected_digest=target["base_commitment_digest"],
        )
        parents = run_git(root, "rev-list", "--parents", "-n", "1", new_value).stdout.split()
        checks = (
            (parents == [new_value, old_value], "commitment_rebind_target_parent_mismatch"),
            (
                run_git(root, "write-tree").stdout.strip() == target["expected_tree"],
                "commitment_rebind_index_tree_mismatch",
            ),
            (
                new_commitment.id == old_commitment.id
                or malformed_change_identity_repair_valid(
                    carrier=target["base_commitment_path"],
                    old_id=old_commitment.id,
                    old_digest=old_commitment.digest(),
                    new=new_commitment,
                ),
                "commitment_rebind_identity_mismatch",
            ),
            (
                new_commitment.digest() != old_commitment.digest(),
                "commitment_rebind_semantics_unchanged",
            ),
        )
    except (KeyError, ValueError) as error:
        return str(error)
    return next((gap for valid, gap in checks if not valid), "")

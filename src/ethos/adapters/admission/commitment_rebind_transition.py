"""Semantic validation for Commitment rebind ref transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import rebind_target_fields
from ethos.adapters.repo.commitment import terminal_v1_binding
from ethos.adapters.repo.git import run_git
from ethos.contracts.plan import GitRefUpdate
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid

if TYPE_CHECKING:
    from pathlib import Path

def commitment_rebind_operation(
    repo: Path,
    update: GitRefUpdate,
    lease: dict[str, object],
    target: dict[str, str],
) -> str:
    """Classify one rebind as semantic update or identity repair."""
    if not _bootstrap_transition_gap(repo, update, lease, target):
        return "v1-to-v2-bootstrap"
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
    operation: str = "commitment.rebind",
) -> str:
    """Validate one semantic Work Lane ref move against live immutable facts."""
    update = GitRefUpdate(expected=old_value, desired=new_value)
    if operation == "v1-to-v2-bootstrap":
        return _bootstrap_transition_gap(root, update, lease, target)
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


def _bootstrap_transition_gap(
    root: Path,
    update: GitRefUpdate,
    lease: dict[str, object],
    target: dict[str, str],
) -> str:
    """Validate one exact terminal-v1 to strict-v2 Work Lane transition."""
    try:
        observed_target = exact_commitment_fields(
            root,
            head=update.desired,
            carrier=str(lease.get("base_commitment_path") or ""),
        )
        old_lane = terminal_v1_binding(
            root,
            tree_ref=update.expected,
            carrier=str(lease.get("base_commitment_path") or ""),
            repository=False,
        )
        old_repository = terminal_v1_binding(
            root,
            tree_ref=update.expected,
            carrier=".ethos/commitment.toml",
            repository=True,
        )
        new_lane = load_commitment(
            root,
            carrier=str(lease.get("base_commitment_path") or ""),
            tree_ref=update.desired,
        )
        new_repository = load_repository_commitment(root, tree_ref=update.desired)
        parents = run_git(root, "rev-list", "--parents", "-n", "1", update.desired).stdout.split()
        checks = (
            (
                old_lane["bytes_sha256"]
                == str(lease.get("base_commitment_bytes_sha256") or ""),
                "lease_base_commitment_bytes_mismatch",
            ),
            (
                old_lane["subjects"] == (old_repository["id"],),
                "commitment_rebind_repository_identity_mismatch",
            ),
            (new_lane.id == old_lane["id"], "commitment_rebind_identity_mismatch"),
            (
                new_lane.subjects == (old_repository["id"],),
                "commitment_rebind_repository_identity_mismatch",
            ),
            (
                new_repository.id == old_repository["id"],
                "commitment_rebind_repository_identity_mismatch",
            ),
            (
                parents == [update.desired, update.expected],
                "commitment_rebind_target_parent_mismatch",
            ),
            (
                run_git(root, "write-tree").stdout.strip()
                == observed_target["expected_tree"],
                "commitment_rebind_index_tree_mismatch",
            ),
            (
                observed_target["base_commitment_path"]
                == str(lease.get("base_commitment_path") or ""),
                "commitment_rebind_target_binding_mismatch",
            ),
            (
                observed_target["base_commitment_digest"] == new_lane.digest(),
                "commitment_rebind_target_binding_mismatch",
            ),
            (
                not target
                or all(target.get(name) == observed_target[name] for name in observed_target),
                "commitment_rebind_target_binding_mismatch",
            ),
        )
    except (KeyError, ValueError) as error:
        return str(error)
    return next((gap for valid, gap in checks if not valid), "")

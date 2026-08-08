"""Resolve exact Lease-bound OpenSpec archive carrier transitions."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment

ARCHIVE_COMMITMENT = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
ACTIVE_COMMITMENT = re.compile(
    r"^openspec/changes/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)


def archive_context(root: Path) -> tuple[str, dict[str, object], Commitment] | None:
    """Return the current exact Work Lane archive context, if bound."""
    branch = git_stdout(root, "branch", "--show-current")
    if load_branch_role_policy(root).role_for_branch(branch) != ROLE_WORK_LANE:
        return None
    head = git_stdout(root, "rev-parse", "HEAD")
    lease = leases_by_branch(root).get(branch, {})
    if (
        lease.get("lease_state") != "valid"
        or lease.get("commitment_binding") != "bound"
        or lease.get("expected_head") != head
    ):
        return None
    try:
        return head, lease, load_lease_bound_commitment(root, lease=lease)
    except ValueError:
        return None


def archive_binding(
    root: Path,
    *,
    head: str,
    change: str,
    lease: dict[str, object],
    target_carrier: str = "",
) -> tuple[str, str, str] | None:
    """Resolve active, staged, or committed archive carrier authority."""
    carrier = str(lease.get("base_commitment_path") or "")
    if valid_archive_carrier(carrier, change):
        return bound_archive_binding(root, head=head, change=change, carrier=carrier)
    try:
        tree = run_git(root, "write-tree").stdout.strip()
        active = f"openspec/changes/{change}/commitment.toml"
        if (
            tree != current_tree(root, head)
            and carrier == active
            and carrier in active_commitments(root, tree)
        ):
            target = exact_commitment_fields(root, head=tree, carrier=carrier, change_id=change)
            expected = {
                name: str(lease.get(name) or "")
                for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
            }
            if all(target[name] == value for name, value in expected.items()):
                return "completion_transition", target["expected_tree"], carrier
        inferred = target_carrier or staged_archive_carrier(
            root, head=head, tree=tree, lease=lease, change=change
        )
        target = exact_commitment_fields(root, head=tree, carrier=inferred, change_id=change)
    except ValueError:
        return None
    expected = {
        name: str(lease.get(name) or "")
        for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
    }
    target_carrier = target["base_commitment_path"]
    if not valid_archive_carrier(target_carrier, change) or any(
        target[name] != value for name, value in expected.items()
    ):
        return None
    return "archive_transition", target["expected_tree"], target_carrier


def staged_archive_carrier(
    root: Path,
    *,
    head: str,
    tree: str,
    lease: dict[str, object],
    change: str,
) -> str:
    """Return the sole exact staged archive commitment carrier."""
    active = f"openspec/changes/{change}/commitment.toml"
    if git_stdout(root, "rev-parse", f"{tree}:{active}"):
        message = "openspec_active_commitment_not_relocated"
        raise ValueError(message)
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes/archive",
        check=False,
    )
    if listed.returncode:
        message = "openspec_archive_tree_unreadable"
        raise ValueError(message)
    expected = {
        name: str(lease.get(name) or "")
        for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
    }
    candidates = []
    for carrier in listed.stdout.splitlines():
        if not valid_archive_carrier(carrier, change):
            continue
        if git_stdout(root, "rev-parse", f"{head}:{carrier}") == git_stdout(
            root, "rev-parse", f"{tree}:{carrier}"
        ):
            continue
        try:
            target = exact_commitment_fields(root, head=tree, carrier=carrier, change_id=change)
        except ValueError:
            continue
        if all(target[name] == value for name, value in expected.items()):
            candidates.append(carrier)
    if len(candidates) != 1:
        message = "lease_base_commitment_path_mismatch"
        raise ValueError(message)
    return candidates[0]


def bound_archive_binding(
    root: Path, *, head: str, change: str, carrier: str
) -> tuple[str, str, str] | None:
    """Recognize an archive carrier already bound by the current Lease."""
    source = f"openspec/changes/{change}/commitment.toml"
    if not git_stdout(root, "rev-parse", f"{head}:{source}"):
        return "post_archive_closeout", current_tree(root, head), carrier
    for revision in git_stdout(root, "rev-list", head, "--", source, carrier).splitlines():
        parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
        if len(parents) == 2 and exact_carrier_relocation(
            root, parents[1], revision, source, carrier
        ):
            return "post_archive_closeout", current_tree(root, head), carrier
    return None


def exact_carrier_relocation(
    root: Path, parent: str, revision: str, source: str, carrier: str
) -> bool:
    """Recognize semantic carrier relocation without Git rename heuristics."""
    source_blob = git_stdout(root, "rev-parse", f"{parent}:{source}")
    target_blob = git_stdout(root, "rev-parse", f"{revision}:{carrier}")
    return bool(
        source_blob
        and source_blob == target_blob
        and not git_stdout(root, "rev-parse", f"{revision}:{source}")
    )


def valid_archive_carrier(carrier: str, change: str) -> bool:
    """Return whether a carrier has the exact dated archive identity."""
    match = ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None or match[2] != change:
        return False
    try:
        date.fromisoformat(match[1])
    except ValueError:
        return False
    return True


def active_commitments(root: Path, tree: str) -> tuple[str, ...]:
    """List active Commitment carriers in one tree, failing closed."""
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes",
        check=False,
    )
    if listed.returncode:
        return ("unreadable",)
    return tuple(path for path in listed.stdout.splitlines() if ACTIVE_COMMITMENT.fullmatch(path))


def collision_preservation_path(path: str, tree: str, head: str) -> str:
    """Return the deterministic immutable preservation path for a collision."""
    suffix = hashlib.sha256(f"{tree}\0{head}".encode()).hexdigest()[:12]
    return f"{path}-{suffix}"

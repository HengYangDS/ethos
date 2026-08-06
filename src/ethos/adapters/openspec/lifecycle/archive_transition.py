"""Recognize the sole Lease-bound transition from active Change to archive."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import relocated_commitment_fields
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import exact_rename_target
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment

_ARCHIVE_COMMITMENT = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
_ACTIVE_COMMITMENT = re.compile(
    r"^openspec/changes/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)


def _archive_context(root: Path) -> tuple[str, dict[str, object], Commitment] | None:
    branch = git_stdout(root, "branch", "--show-current")
    if load_branch_role_policy(root).role_for_branch(branch) != ROLE_WORK_LANE:
        return None
    head = current_tracked_head(root)
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


def lease_bound_archive_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    requested_change: str | None = None,
    official_change_complete: bool = False,
    completion_artifacts: tuple[str, ...] = (),
    preserved_archive: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    """Project the sole archive edge authorized by the current Work Lane Lease."""
    context = _archive_context(root)
    if context is None:
        return None
    head, lease, source_commitment = context
    change = source_commitment.id.removeprefix("change:")
    if source_commitment.id == change or requested_change not in {None, change}:
        return None
    resolved = _archive_binding(
        root,
        head=head,
        change=change,
        lease=lease,
        target_carrier=f"{preserved_archive[0]}/commitment.toml" if preserved_archive else "",
    )
    if resolved is None:
        return None
    state, tree, carrier = resolved
    try:
        archived = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=tree,
            expected_digest=str(lease.get("base_commitment_digest") or ""),
        )
    except ValueError:
        return None
    active = _active_commitments(root, tree)
    expected_active = (carrier,) if state == "completion_transition" else ()
    changed = tuple(dict.fromkeys(filter(None, changed_paths)))
    if preserved_archive is not None:
        preserved_source, preserved_target = preserved_archive
        if not _exact_preserved_archive(
            root,
            head=head,
            tree=tree,
            source=preserved_source,
            target=preserved_target,
        ):
            return None
    completion_invalid = state == "completion_transition" and (
        not official_change_complete or len(changed) != 1 or changed[0] not in completion_artifacts
    )
    if (
        archived.digest() != source_commitment.digest()
        or active != expected_active
        or completion_invalid
    ):
        return None
    return _scope_report(
        root,
        commitment=archived,
        change=change,
        carrier=carrier,
        state=state,
        changed_paths=changed_paths,
    )


def _exact_preserved_archive(
    root: Path,
    *,
    head: str,
    tree: str,
    source: str,
    target: str,
) -> bool:
    source_tree = git_stdout(root, "rev-parse", f"{head}:{source}")
    replacement_tree = git_stdout(root, "rev-parse", f"{tree}:{source}")
    target_tree = git_stdout(root, "rev-parse", f"{tree}:{target}")
    return bool(source_tree and replacement_tree and source_tree == target_tree)


def _archive_binding(
    root: Path,
    *,
    head: str,
    change: str,
    lease: dict[str, object],
    target_carrier: str = "",
) -> tuple[str, str, str] | None:
    carrier = str(lease.get("base_commitment_path") or "")
    if _valid_archive_carrier(carrier, change):
        source = f"openspec/changes/{change}/commitment.toml"
        if not git_stdout(root, "rev-parse", f"{head}:{source}"):
            return "post_archive_closeout", current_tree(root, head), carrier
        revisions = git_stdout(root, "rev-list", head, "--", source, carrier).splitlines()
        for revision in revisions:
            parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
            try:
                _commit, parent = parents
            except ValueError:
                continue
            if exact_rename_target(root, parent, revision, source) == carrier:
                return "post_archive_closeout", current_tree(root, head), carrier
        return None
    try:
        index_tree = run_git(root, "write-tree").stdout.strip()
        active_carrier = f"openspec/changes/{change}/commitment.toml"
        if carrier == active_carrier and carrier in _active_commitments(root, index_tree):
            target = exact_commitment_fields(
                root,
                head=index_tree,
                carrier=carrier,
                change_id=change,
            )
            expected = {
                name: str(lease.get(name) or "")
                for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
            }
            if all(target[name] == value for name, value in expected.items()):
                return "completion_transition", target["expected_tree"], carrier
        target = (
            exact_commitment_fields(
                root,
                head=index_tree,
                carrier=target_carrier,
                change_id=change,
            )
            if target_carrier
            else relocated_commitment_fields(root, old_head=head, new_head=index_tree, lease=lease)
        )
    except ValueError:
        return None
    target_carrier = target["base_commitment_path"]
    expected = {
        name: str(lease.get(name) or "")
        for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
    }
    if not _valid_archive_carrier(target_carrier, change) or any(
        target[name] != value for name, value in expected.items()
    ):
        return None
    return "archive_transition", target["expected_tree"], target_carrier


def _valid_archive_carrier(carrier: str, change: str) -> bool:
    match = _ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None or match[2] != change:
        return False
    try:
        date.fromisoformat(match[1])
    except ValueError:
        return False
    return True


def _active_commitments(root: Path, tree: str) -> tuple[str, ...]:
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
    if listed.returncode != 0:
        return ("unreadable",)
    return tuple(path for path in listed.stdout.splitlines() if _ACTIVE_COMMITMENT.fullmatch(path))


def _scope_report(
    root: Path,
    *,
    commitment: Commitment,
    change: str,
    carrier: str,
    state: str,
    changed_paths: tuple[str, ...],
) -> dict[str, Any]:
    profile = load_repository_profile(root)
    if (
        profile.state == "invalid"
        or profile.declaration is None
        or profile.declaration.openspec is None
    ):
        raise ValueError(INVALID_PROFILE_ERROR)
    patterns = profile.declaration.openspec.material_paths
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    material = tuple(
        path for path in paths if any(repository_path_matches(path, glob) for glob in patterns)
    )
    uncovered = [
        path
        for path in material
        if not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
    ]
    covered = [{"path": path, "changes": [change]} for path in material if path not in uncovered]
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "changed_paths": list(paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": [
            {
                "name": change,
                "path": carrier.removesuffix("/commitment.toml"),
                "scope": list(commitment.scope),
            }
        ],
        "covered_paths": covered,
        "uncovered_paths": uncovered,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }

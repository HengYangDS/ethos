from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import git_stdout_checked
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_CANDIDATE
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import BranchRolePolicy

# fmt: off


def has_changed_paths(root: Path) -> bool:
    """Return whether tracked, untracked, or unreadable state is present."""
    try:
        return bool(git_stdout_checked(root, "status", "--porcelain", "--untracked-files=all"))
    except (OSError, subprocess.CalledProcessError):
        return True


def branch_bindings(
    root: Path, worktrees: list[dict[str, str]], candidate: dict[str, object], *,
    policy: BranchRolePolicy, lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    """Return configured, linked, and unbound branch bindings."""
    by_branch = {
        item["branch"]: item for item in worktrees if item["branch"] != "detached"
    }
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()
    configured = (
        (policy.release_branch, policy.role_for_branch(policy.release_branch)),
        (policy.accepted_branch, policy.role_for_branch(policy.accepted_branch)),
        (policy.candidate_branch, ROLE_CANDIDATE),
    )
    for branch, role in configured:
        if branch in seen:
            continue
        bindings.append(_configured_branch_binding(
            root, branch=branch, role=role, worktree=by_branch.get(branch),
            candidate=candidate if branch == policy.candidate_branch else None,
            lease=lease_by_branch.get(branch, {}),
        ))
        seen.add(branch)
    remaining = [
        _worktree_branch_binding(item, lease=lease_by_branch.get(item["branch"], {}))
        for item in worktrees if item["branch"] != "detached" and item["branch"] not in seen
    ]
    remaining.extend(
        _unbound_work_lane_binding(
            root, branch=branch, head=head, lease=lease_by_branch.get(branch, {})
        )
        for branch, head in _work_lane_refs(root, policy=policy)
        if branch not in seen and branch not in by_branch
    )
    order = {record["role"]: index for index, record in enumerate(policy.semantic_order())}
    for binding in sorted(
        remaining, key=lambda item: (order.get(item["role"], len(order)), item["branch"])
    ):
        if binding["branch"] not in seen:
            bindings.append(binding)
            seen.add(binding["branch"])
    return bindings


def _work_lane_refs(root: Path, *, policy: BranchRolePolicy) -> list[tuple[str, str]]:
    try:
        output = git_stdout_checked(
            root, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"
        )
    except subprocess.CalledProcessError:
        return []
    refs = (line.partition(" ") for line in output.splitlines())
    return [
        (branch, head)
        for branch, _, head in refs if policy.role_for_branch(branch) == ROLE_WORK_LANE
    ]


def unbound_work_lane_refs(
    root: Path, branch_bindings: list[dict[str, str]], *, policy: BranchRolePolicy
) -> list[dict[str, object]]:
    """Return unbound Work Lane refs derived from branch bindings."""
    return [
        {
            **{name: binding[name] for name in ("branch", "head", "claim_id", "claim_binding")},
            "relation_to_accepted": ref_relation(root, binding["branch"], policy.accepted_branch),
            "next_action": unbound_ref_next_action(root, binding["branch"], policy.accepted_branch),
        }
        for binding in branch_bindings
        if binding["role"] == ROLE_WORK_LANE and binding["worktree_binding"] == "unbound"
    ]


def ref_relation(root: Path, branch: str, accepted_branch: str) -> str:
    """Classify a branch ref relative to the accepted branch."""
    if not ref_head(root, branch) or not ref_head(root, accepted_branch):
        return "unknown"
    if is_ancestor(root, branch, accepted_branch):
        return "ancestor_of_accepted"
    return (
        "descendant_of_accepted"
        if is_ancestor(root, accepted_branch, branch) else "diverged_from_accepted"
    )


def unbound_ref_next_action(root: Path, branch: str, accepted_branch: str) -> str:
    """Return the safe next action for an unbound Work Lane ref."""
    return {
        "ancestor_of_accepted": (
            "retire unbound Work Lane ref after confirming no external owner depends on it"
        ),
        "descendant_of_accepted": "bind a lease or land the unbound Work Lane ref before cleanup",
    }.get(
        ref_relation(root, branch, accepted_branch),
        "inspect diverged unbound Work Lane ref before merge, supersede, or deletion",
    )


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether one ref is an ancestor of another ref."""
    return _git(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def _binding(  # noqa: PLR0913, RUF100 - exact branch binding dimensions
    branch: str, role: str, head: str, path: str, worktree: str, claim_id: str,
    claim_binding: str,
) -> dict[str, str]:
    return {
        "branch": branch, "role": role, "head": head, "worktree_path": path,
        "worktree_binding": worktree, "claim_id": claim_id, "claim_binding": claim_binding,
    }


def _unbound_work_lane_binding(
    root: Path, *, branch: str, head: str, lease: dict[str, object]
) -> dict[str, str]:
    claim_id = lease_claim_id(lease)
    return _binding(
        branch, ROLE_WORK_LANE, head or ref_head(root, branch), "", "unbound", claim_id,
        "bound" if claim_id else "missing",
    )


def _configured_branch_binding(  # noqa: PLR0913, RUF100 - exact bound-state dimensions
    root: Path, *, branch: str, role: str, worktree: dict[str, str] | None,
    candidate: dict[str, object] | None, lease: dict[str, object],
) -> dict[str, str]:
    if worktree is not None:
        return _worktree_branch_binding(worktree, lease=lease)
    if candidate is not None:
        return _binding(
            branch, role, str(candidate["head"]), str(candidate["worktree_path"]),
            str(candidate["worktree_binding"]), "", "unbound",
        )
    head = ref_head(root, branch)
    return _binding(branch, role, head, "", "unbound" if head else "absent", "", "unbound")


def _worktree_branch_binding(
    worktree: dict[str, str], *, lease: dict[str, object]
) -> dict[str, str]:
    claim_id = lease_claim_id(lease)
    return _binding(
        worktree["branch"], worktree["role"], worktree["head"], worktree["path"],
        worktree["worktree_binding"], claim_id, "bound" if claim_id else "missing",
    )


def worktree_binding(path: str, *, current_path: Path) -> str:
    """Classify a registered worktree path against filesystem reality."""
    if not path:
        return "absent"
    resolved = Path(path).resolve()
    if resolved == current_path:
        return "current"
    return "linked" if resolved.exists() else "missing"


def leases_by_branch(
    worktrees: list[dict[str, str]], *, current_path: Path
) -> dict[str, dict[str, object]]:
    """Load active leases, preferring the accepted-root control store."""
    control_root = next(
        (
            Path(item["path"])
            for item in worktrees if item["role"] == ROLE_ACCEPTED_ROOT and item["path"]
        ),
        current_path,
    )
    leases = {str(lease["subject"]): lease for lease in _json_projection_leases(control_root)}
    leases.update({
        str(lease["subject"]): lease
        for lease in active_leases(control_root / ".ethos" / "state" / "state.sqlite")
    })
    return leases


def _json_projection_leases(control_root: Path) -> list[dict[str, object]]:
    path = control_root / ".cache" / "local-state" / "worktree" / "leases.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows = payload.get("leases") if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []
    now = datetime.now(UTC)
    return [lease for row in rows if (lease := _json_projection_lease(row, now=now))]


def _json_projection_lease(row: object, *, now: datetime) -> dict[str, object]:
    if not isinstance(row, dict):
        return {}
    branch = str(row.get("branch") or row.get("subject") or "")
    owner, expires_at = str(row.get("owner") or ""), str(row.get("expires_at") or "")
    if not branch or not owner or not _lease_expires_after(expires_at, now=now):
        return {}
    return {
        "id": str(row.get("id") or f"json:{branch}"), "subject": branch,
        "owner": owner, "expires_at": expires_at,
        "payload": {
            "branch": branch, "claim_id": str(row.get("claim_id") or ""),
            "path": str(row.get("worktree_path") or row.get("path") or ""),
            "session_id": str(row.get("session_id") or ""),
        },
    }


def _lease_expires_after(value: str, *, now: datetime) -> bool:
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now


def lease_claim_id(lease: dict[str, object]) -> str:
    """Extract a claim id from a Work Lane lease payload."""
    payload = lease.get("payload") if isinstance(lease, dict) else {}
    return str(payload.get("claim_id") or "") if isinstance(payload, dict) else ""


def closeout_support(  # noqa: PLR0913, RUF100 - exact bound-state dimensions
    *, branch: str, role: str, dirty: bool, candidate: dict[str, object],
    lease_by_branch: dict[str, dict[str, object]], coordination_required_gaps: list[str],
) -> dict[str, object]:
    """Return closeout support and required gaps for a branch role."""
    gaps: list[str] = []
    is_work_lane = role == ROLE_WORK_LANE
    lease = lease_by_branch.get(branch, {}) if is_work_lane else {}
    if not is_work_lane:
        gaps.append("protected_root_mutation")
    elif dirty:
        gaps.append("work_lane_dirty")
    elif not lease.get("holder_ref"):
        gaps.append(f"work_lane_missing_lease:{branch}")
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    elif has_changed_paths(Path(str(candidate["worktree_path"]))):
        gaps.append("candidate_worktree_dirty")
    if is_work_lane:
        gaps.extend(coordination_required_gaps)
    claim_id = lease_claim_id(lease)
    return {
        "supported": not gaps, "branch": branch if is_work_lane else "",
        "target_branch": str(candidate["branch"]), "target_path": str(candidate["worktree_path"]),
        "operation": "land_to_candidate" if is_work_lane else "",
        "holder_ref": str(lease.get("holder_ref") or ""),
        "lease_id": str(lease.get("lease_id") or ""),
        "lease_epoch": integer_value(lease.get("epoch")) if lease else 0,
        "claim_id": claim_id,
        "claim_binding": (
            "bound" if claim_id else "missing" if is_work_lane else "unbound"
        ),
        "required_gaps": gaps,
    }


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=False, text=True, capture_output=True)


def ref_head(root: Path, ref: str) -> str:
    """Resolve a ref to its head, or return an empty string when absent."""
    completed = _git(root, "rev-parse", "--verify", ref)
    return completed.stdout.strip() if completed.returncode == 0 else ""
# fmt: on

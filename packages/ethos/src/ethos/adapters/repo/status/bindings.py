from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.store.state import active_leases
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_CANDIDATE
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import BranchRolePolicy


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.rstrip("\n")


def has_changed_paths(root: Path) -> bool:
    """Return whether the target worktree has tracked or untracked changes."""
    try:
        return bool(_run_git(root, "status", "--porcelain", "--untracked-files=all"))
    except subprocess.CalledProcessError:
        return True


def branch_bindings(
    root: Path,
    worktrees: list[dict[str, str]],
    candidate: dict[str, object],
    *,
    policy: BranchRolePolicy,
    lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    """Return protected, candidate, linked, and unbound branch bindings."""
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()

    worktree_by_branch = {
        str(worktree["branch"]): worktree
        for worktree in worktrees
        if str(worktree["branch"]) != "detached"
    }

    for branch, role in (
        (policy.release_branch, policy.role_for_branch(policy.release_branch)),
        (policy.accepted_branch, policy.role_for_branch(policy.accepted_branch)),
        (policy.candidate_branch, ROLE_CANDIDATE),
    ):
        if branch in seen:
            continue
        binding = _configured_branch_binding(
            root,
            branch=branch,
            role=role,
            worktree=worktree_by_branch.get(branch),
            candidate=candidate if branch == policy.candidate_branch else None,
            lease=lease_by_branch.get(branch, {}),
        )
        bindings.append(binding)
        seen.add(branch)

    role_order = {
        str(record["role"]): index for index, record in enumerate(policy.semantic_order())
    }
    remaining: list[dict[str, str]] = [
        _worktree_branch_binding(worktree, lease=lease_by_branch.get(str(worktree["branch"]), {}))
        for worktree in worktrees
        if str(worktree["branch"]) != "detached" and str(worktree["branch"]) not in seen
    ]
    remaining.extend(
        _unbound_work_lane_binding(
            root, branch=branch, head=head, lease=lease_by_branch.get(branch, {})
        )
        for branch, head in _work_lane_refs(root, policy=policy)
        if branch not in seen and branch not in worktree_by_branch
    )
    for binding in sorted(
        remaining,
        key=lambda item: (
            role_order.get(str(item["role"]), len(role_order)),
            str(item["branch"]),
        ),
    ):
        branch = str(binding["branch"])
        if branch in seen:
            continue
        bindings.append(binding)
        seen.add(branch)
    return bindings


def _work_lane_refs(root: Path, *, policy: BranchRolePolicy) -> list[tuple[str, str]]:
    try:
        output = _run_git(
            root,
            "for-each-ref",
            "--format=%(refname:short) %(objectname)",
            "refs/heads",
        )
    except subprocess.CalledProcessError:
        return []
    refs: list[tuple[str, str]] = []
    for line in output.splitlines():
        branch, _, head = line.partition(" ")
        if policy.role_for_branch(branch) == ROLE_WORK_LANE:
            refs.append((branch, head))
    return refs


def unbound_work_lane_refs(
    root: Path,
    branch_bindings: list[dict[str, str]],
    *,
    policy: BranchRolePolicy,
) -> list[dict[str, object]]:
    """Return unbound Work Lane refs derived from branch bindings."""
    refs: list[dict[str, object]] = []
    for binding in branch_bindings:
        if binding["role"] != ROLE_WORK_LANE or binding["worktree_binding"] != "unbound":
            continue
        branch = str(binding["branch"])
        refs.append(
            {
                "branch": branch,
                "head": str(binding["head"]),
                "claim_id": str(binding["claim_id"]),
                "claim_binding": str(binding["claim_binding"]),
                "relation_to_accepted": ref_relation(root, branch, policy.accepted_branch),
                "next_action": unbound_ref_next_action(root, branch, policy.accepted_branch),
            }
        )
    return refs


def ref_relation(root: Path, branch: str, accepted_branch: str) -> str:
    """Classify a branch ref relative to the accepted branch."""
    if not ref_head(root, branch) or not ref_head(root, accepted_branch):
        return "unknown"
    if is_ancestor(root, branch, accepted_branch):
        return "ancestor_of_accepted"
    if is_ancestor(root, accepted_branch, branch):
        return "descendant_of_accepted"
    return "diverged_from_accepted"


def unbound_ref_next_action(root: Path, branch: str, accepted_branch: str) -> str:
    """Return the safe next action for an unbound Work Lane ref."""
    relation = ref_relation(root, branch, accepted_branch)
    if relation == "ancestor_of_accepted":
        return "retire unbound Work Lane ref after confirming no external owner depends on it"
    if relation == "descendant_of_accepted":
        return "bind a lease or land the unbound Work Lane ref before cleanup"
    return "inspect diverged unbound Work Lane ref before merge, supersede, or deletion"


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether one ref is an ancestor of another ref."""
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.returncode == 0


def _unbound_work_lane_binding(
    root: Path,
    *,
    branch: str,
    head: str,
    lease: dict[str, object],
) -> dict[str, str]:
    claim_id = lease_claim_id(lease)
    return {
        "branch": branch,
        "role": ROLE_WORK_LANE,
        "head": head or ref_head(root, branch),
        "worktree_path": "",
        "worktree_binding": "unbound",
        "claim_id": claim_id,
        "claim_binding": "bound" if claim_id else "missing",
    }


def _configured_branch_binding(
    root: Path,
    *,
    branch: str,
    role: str,
    worktree: dict[str, str] | None,
    candidate: dict[str, object] | None,
    lease: dict[str, object],
) -> dict[str, str]:
    if worktree is not None:
        return _worktree_branch_binding(worktree, lease=lease)
    if candidate is not None:
        return {
            "branch": branch,
            "role": role,
            "head": str(candidate["head"]),
            "worktree_path": str(candidate["worktree_path"]),
            "worktree_binding": str(candidate["worktree_binding"]),
            "claim_id": "",
            "claim_binding": "unbound",
        }
    head = ref_head(root, branch)
    return {
        "branch": branch,
        "role": role,
        "head": head,
        "worktree_path": "",
        "worktree_binding": "unbound" if head else "absent",
        "claim_id": "",
        "claim_binding": "unbound",
    }


def _worktree_branch_binding(
    worktree: dict[str, str],
    *,
    lease: dict[str, object],
) -> dict[str, str]:
    claim_id = lease_claim_id(lease)
    return {
        "branch": str(worktree["branch"]),
        "role": str(worktree["role"]),
        "head": str(worktree["head"]),
        "worktree_path": str(worktree["path"]),
        "worktree_binding": str(worktree["worktree_binding"]),
        "claim_id": claim_id,
        "claim_binding": "bound" if claim_id else "missing",
    }


def worktree_binding(path: str, *, current_path: Path) -> str:
    """Classify a worktree path as current or linked."""
    if path and Path(path).resolve() == current_path:
        return "current"
    return "linked"


def leases_by_branch(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
) -> dict[str, dict[str, object]]:
    """Load active leases keyed by branch, preferring the accepted-root control store."""
    control_root = current_path
    for worktree in worktrees:
        if worktree["role"] == ROLE_ACCEPTED_ROOT and worktree["path"]:
            control_root = Path(worktree["path"])
            break
    leases = {str(lease["subject"]): lease for lease in _json_projection_leases(control_root)}
    leases.update(
        {
            str(lease["subject"]): lease
            for lease in active_leases(control_root / ".ethos" / "state" / "state.sqlite")
        }
    )
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
    leases: list[dict[str, object]] = []
    for row in rows:
        lease = _json_projection_lease(row, now=now)
        if lease:
            leases.append(lease)
    return leases


def _json_projection_lease(row: object, *, now: datetime) -> dict[str, object]:
    if not isinstance(row, dict):
        return {}
    branch = str(row.get("branch") or row.get("subject") or "")
    owner = str(row.get("owner") or "")
    expires_at = str(row.get("expires_at") or "")
    if not branch or not owner or not _lease_expires_after(expires_at, now=now):
        return {}
    return {
        "id": str(row.get("id") or f"json:{branch}"),
        "subject": branch,
        "owner": owner,
        "expires_at": expires_at,
        "payload": {
            "branch": branch,
            "claim_id": str(row.get("claim_id") or ""),
            "path": str(row.get("worktree_path") or row.get("path") or ""),
            "session_id": str(row.get("session_id") or ""),
        },
    }


def _lease_expires_after(value: str, *, now: datetime) -> bool:
    try:
        normalized = value.replace("Z", "+00:00")
        expires_at = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now


def lease_claim_id(lease: dict[str, object]) -> str:
    """Extract a claim id from a Work Lane lease payload."""
    payload = lease.get("payload") if isinstance(lease, dict) else {}
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("claim_id") or "")


def closeout_support(
    *,
    branch: str,
    role: str,
    dirty: bool,
    candidate: dict[str, object],
    lease_by_branch: dict[str, dict[str, object]],
    coordination_required_gaps: list[str],
) -> dict[str, object]:
    """Return closeout support and required gaps for a branch role."""
    gaps: list[str] = []
    if role != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif dirty:
        gaps.append("work_lane_dirty")
    elif not lease_by_branch.get(branch, {}).get("owner"):
        gaps.append(f"work_lane_missing_lease:{branch}")
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    else:
        candidate_path = Path(str(candidate["worktree_path"]))
        if has_changed_paths(candidate_path):
            gaps.append("candidate_worktree_dirty")
    if role == ROLE_WORK_LANE:
        gaps.extend(coordination_required_gaps)

    is_work_lane = role == ROLE_WORK_LANE
    lease = lease_by_branch.get(branch, {}) if is_work_lane else {}
    claim_id = lease_claim_id(lease)
    return {
        "supported": not gaps,
        "branch": branch if is_work_lane else "",
        "target_branch": str(candidate["branch"]),
        "target_path": str(candidate["worktree_path"]),
        "operation": "land_to_candidate" if is_work_lane else "",
        "owner": str(lease.get("owner") or "") if is_work_lane else "",
        "claim_id": claim_id,
        "claim_binding": "bound" if claim_id else "missing" if is_work_lane else "unbound",
        "required_gaps": gaps,
    }


def ref_head(root: Path, ref: str) -> str:
    """Resolve a ref to its head, or return an empty string when absent."""
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()

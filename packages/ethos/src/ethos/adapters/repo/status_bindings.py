from __future__ import annotations

import subprocess
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


def _has_changed_paths(root: Path) -> bool:
    try:
        return bool(_run_git(root, "status", "--porcelain", "--untracked-files=all"))
    except subprocess.CalledProcessError:
        return True


def _branch_bindings(
    root: Path,
    worktrees: list[dict[str, str]],
    candidate: dict[str, object],
    *,
    policy: BranchRolePolicy,
    lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
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


def _unbound_work_lane_refs(
    root: Path,
    branch_bindings: list[dict[str, str]],
    *,
    policy: BranchRolePolicy,
) -> list[dict[str, object]]:
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
                "relation_to_accepted": _ref_relation(root, branch, policy.accepted_branch),
                "next_action": _unbound_ref_next_action(root, branch, policy.accepted_branch),
            }
        )
    return refs


def _ref_relation(root: Path, branch: str, accepted_branch: str) -> str:
    if _is_ancestor(root, branch, accepted_branch):
        return "ancestor_of_accepted"
    if _is_ancestor(root, accepted_branch, branch):
        return "descendant_of_accepted"
    return "diverged_from_accepted"


def _unbound_ref_next_action(root: Path, branch: str, accepted_branch: str) -> str:
    relation = _ref_relation(root, branch, accepted_branch)
    if relation == "ancestor_of_accepted":
        return "retire unbound Work Lane ref after confirming no external owner depends on it"
    if relation == "descendant_of_accepted":
        return "bind a lease or land the unbound Work Lane ref before cleanup"
    return "inspect diverged unbound Work Lane ref before merge, supersede, or deletion"


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
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
    claim_id = _lease_claim_id(lease)
    return {
        "branch": branch,
        "role": ROLE_WORK_LANE,
        "head": head or _ref_head(root, branch),
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
    head = _ref_head(root, branch)
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
    claim_id = _lease_claim_id(lease)
    return {
        "branch": str(worktree["branch"]),
        "role": str(worktree["role"]),
        "head": str(worktree["head"]),
        "worktree_path": str(worktree["path"]),
        "worktree_binding": str(worktree["worktree_binding"]),
        "claim_id": claim_id,
        "claim_binding": "bound" if claim_id else "missing",
    }


def _worktree_binding(path: str, *, current_path: Path) -> str:
    if path and Path(path).resolve() == current_path:
        return "current"
    return "linked"


def _leases_by_branch(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
) -> dict[str, dict[str, object]]:
    control_root = current_path
    for worktree in worktrees:
        if worktree["role"] == ROLE_ACCEPTED_ROOT and worktree["path"]:
            control_root = Path(worktree["path"])
            break
    leases = active_leases(control_root / ".ethos" / "state" / "state.sqlite")
    return {str(lease["subject"]): lease for lease in leases}


def _lease_claim_id(lease: dict[str, object]) -> str:
    payload = lease.get("payload") if isinstance(lease, dict) else {}
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("claim_id") or "")


def _closeout_support(
    *,
    branch: str,
    role: str,
    dirty: bool,
    candidate: dict[str, object],
    lease_by_branch: dict[str, dict[str, object]],
    coordination_required_gaps: list[str],
) -> dict[str, object]:
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
        if _has_changed_paths(candidate_path):
            gaps.append("candidate_worktree_dirty")
    if role == ROLE_WORK_LANE:
        gaps.extend(coordination_required_gaps)

    is_work_lane = role == ROLE_WORK_LANE
    lease = lease_by_branch.get(branch, {}) if is_work_lane else {}
    claim_id = _lease_claim_id(lease)
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


def _ref_head(root: Path, ref: str) -> str:
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

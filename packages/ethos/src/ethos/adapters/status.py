from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.state import active_leases
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_CANDIDATE
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import BranchRolePolicy
from ethos_core.contracts.branch_roles import load_branch_role_policy


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.rstrip("\n")


def current_branch(root: Path) -> str:
    return _run_git(root, "branch", "--show-current") or "detached"


def changed_paths(root: Path) -> tuple[str, ...]:
    output = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        paths.append(line[3:] if len(line) > 3 and line[2] == " " else line[2:].strip())
    return tuple(paths)


def workspace_status(root: Path) -> dict[str, object]:
    try:
        repo = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve()
    except subprocess.CalledProcessError:
        return _non_git_status(root)
    current_path = repo
    paths = changed_paths(root)
    branch = current_branch(root)
    policy = load_branch_role_policy(repo)
    role = policy.role_for_branch(branch)
    worktrees = _worktrees(root, current_path=current_path, policy=policy)
    candidate = _candidate_status(root, worktrees, policy=policy)
    lease_by_branch = _leases_by_branch(worktrees, current_path=current_path)
    branch_bindings = _branch_bindings(
        repo,
        worktrees,
        candidate,
        policy=policy,
        lease_by_branch=lease_by_branch,
    )
    closeout_support = _closeout_support(
        branch=branch,
        role=role,
        dirty=bool(paths),
        candidate=candidate,
        lease_by_branch=lease_by_branch,
    )
    foreign = _foreign_work_lanes(
        worktrees,
        current_path=current_path,
        lease_by_branch=lease_by_branch,
    )
    coordination_gaps = _coordination_gaps(foreign)
    coordination = _coordination_package(foreign, coordination_gaps)
    required_gaps = []
    missing_current_lease = f"work_lane_missing_lease:{branch}"
    if missing_current_lease in closeout_support["required_gaps"]:
        required_gaps.append(missing_current_lease)
    if not candidate["exists"]:
        required_gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        required_gaps.append("candidate_worktree_missing")
    return {
        "root": str(root),
        "branch": branch,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "role": role,
        "role_policy": policy.as_status_policy(),
        "candidate": candidate,
        "worktrees": worktrees,
        "branch_bindings": branch_bindings,
        "foreign_work_lanes": foreign,
        "coordination_gaps": coordination_gaps,
        "coordination": coordination,
        "closeout_support": closeout_support,
        "required_gaps": required_gaps,
    }


def _non_git_status(root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    candidate = {
        "branch": policy.candidate_branch,
        "exists": False,
        "head": "",
        "worktree_exists": False,
        "worktree_path": "",
        "worktree_binding": "absent",
    }
    return {
        "root": str(root),
        "branch": "untracked",
        "dirty": False,
        "changed_paths": [],
        "role": "other",
        "role_policy": policy.as_status_policy(),
        "candidate": candidate,
        "worktrees": [],
        "branch_bindings": _branch_bindings(
            root,
            [],
            candidate,
            policy=policy,
            lease_by_branch={},
        ),
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "coordination": _coordination_package([], []),
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": policy.candidate_branch,
            "target_path": "",
            "operation": "",
            "owner": "",
            "claim_id": "",
            "claim_binding": "unbound",
            "required_gaps": ["protected_root_mutation", "git_repository_missing"],
        },
        "required_gaps": ["git_repository_missing", "candidate_branch_missing"],
    }


def _worktrees(
    root: Path,
    *,
    current_path: Path,
    policy: BranchRolePolicy,
) -> list[dict[str, str]]:
    output = _run_git(root, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                entries.append(
                    _normalize_worktree(current, current_path=current_path, policy=policy)
                )
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        entries.append(_normalize_worktree(current, current_path=current_path, policy=policy))
    return entries


def _normalize_worktree(
    entry: dict[str, str],
    *,
    current_path: Path,
    policy: BranchRolePolicy,
) -> dict[str, str]:
    branch = entry.get("branch", "")
    if branch.startswith("refs/heads/"):
        branch = branch.removeprefix("refs/heads/")
    path = entry.get("worktree", "")
    return {
        "path": path,
        "head": entry.get("HEAD", ""),
        "branch": branch or "detached",
        "role": policy.role_for_branch(branch),
        "worktree_binding": _worktree_binding(path, current_path=current_path),
    }


def _foreign_work_lanes(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
    lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    foreign: list[dict[str, str]] = []
    for worktree in worktrees:
        if worktree["role"] != ROLE_WORK_LANE:
            continue
        if Path(str(worktree["path"])).resolve() == current_path:
            continue
        branch = str(worktree["branch"])
        lease = lease_by_branch.get(branch, {})
        owner = str(lease.get("owner") or "")
        claim_id = _lease_claim_id(lease)
        foreign.append(
            {
                "path": worktree["path"],
                "head": worktree["head"],
                "branch": branch,
                "role": worktree["role"],
                "worktree_binding": worktree["worktree_binding"],
                "lease_owner": owner,
                "lease_state": "leased" if owner else "missing",
                "claim_id": claim_id,
                "claim_binding": "bound" if claim_id else "missing",
            }
        )
    return foreign


def _coordination_gaps(foreign_work_lanes: list[dict[str, str]]) -> list[str]:
    gaps: list[str] = []
    if foreign_work_lanes:
        gaps.append("foreign_work_lane_present")
    for lane in foreign_work_lanes:
        if lane["lease_state"] == "missing":
            gaps.append(f"work_lane_missing_lease:{lane['branch']}")
    return gaps


def _coordination_package(
    foreign_work_lanes: list[dict[str, str]],
    coordination_gaps: list[str],
) -> dict[str, object]:
    return {
        "kind": "work_lane_coordination",
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": list(coordination_gaps),
        "foreign_work_lane_count": len(foreign_work_lanes),
        "missing_lease_count": sum(
            1 for lane in foreign_work_lanes if lane["lease_state"] == "missing"
        ),
        "next_action": "coordinate foreign work lanes before local closeout if they overlap scope",
    }


def _candidate_status(
    root: Path,
    worktrees: list[dict[str, str]],
    *,
    policy: BranchRolePolicy,
) -> dict[str, object]:
    head = _ref_head(root, policy.candidate_branch)
    worktree_path = ""
    worktree_binding = "absent"
    for worktree in worktrees:
        if worktree["branch"] == policy.candidate_branch:
            worktree_path = worktree["path"]
            worktree_binding = worktree["worktree_binding"]
            break
    if head and not worktree_path:
        worktree_binding = "unbound"
    # Candidate-train integrity: how many accepted-root commits the candidate has not
    # yet caught up to. In a healthy train the candidate tracks accepted closely
    # (promotions flow lane -> candidate -> accepted). A large lag means promotions
    # bypassed the candidate train (e.g. a raw merge straight to accepted).
    behind_accepted = 0
    if head:
        count = _run_git(
            root, "rev-list", "--count", f"{policy.candidate_branch}..{policy.accepted_branch}"
        ).strip()
        behind_accepted = int(count) if count.isdigit() else 0
    return {
        "branch": policy.candidate_branch,
        "exists": bool(head),
        "head": head,
        "worktree_exists": bool(worktree_path),
        "worktree_path": worktree_path,
        "worktree_binding": worktree_binding,
        "behind_accepted": behind_accepted,
    }


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
    remaining_worktrees = sorted(
        worktrees,
        key=lambda worktree: (
            role_order.get(str(worktree["role"]), len(role_order)),
            str(worktree["branch"]),
        ),
    )
    for worktree in remaining_worktrees:
        branch = str(worktree["branch"])
        if branch == "detached" or branch in seen:
            continue
        bindings.append(_worktree_branch_binding(worktree, lease=lease_by_branch.get(branch, {})))
        seen.add(branch)
    return bindings


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
        if changed_paths(candidate_path):
            gaps.append("candidate_worktree_dirty")

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

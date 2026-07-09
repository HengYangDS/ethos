from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

from ethos.adapters.repo.coordination import branch_path_scope
from ethos.adapters.repo.coordination import coordination_gaps
from ethos.adapters.repo.coordination import coordination_package
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.coordination import workspace_required_gaps
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.runtime.core import runtime_binding
from ethos.adapters.repo.status.bindings import branch_bindings
from ethos.adapters.repo.status.bindings import closeout_support
from ethos.adapters.repo.status.bindings import is_ancestor
from ethos.adapters.repo.status.bindings import lease_claim_id
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.bindings import ref_relation
from ethos.adapters.repo.status.bindings import unbound_work_lane_refs
from ethos.adapters.repo.status.bindings import worktree_binding
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import BranchRolePolicy
from ethos_core.contracts.branch_roles import load_branch_role_policy


def landing_readiness(
    root: Path,
    *,
    branch: str,
    role: str,
    candidate: dict[str, object],
) -> dict[str, object]:
    """Read-only view of whether this lane can fast-forward into candidate.

    This does not mutate candidate/dev and does not replace the land-time CAS check.
    It makes the common candidate_base_stale race visible before an agent spends a
    proof cycle and only discovers the race at `ethos land --apply`.
    """
    current_head = _safe_ref(root, "HEAD")
    candidate_branch = str(candidate.get("branch") or "")
    candidate_head = str(candidate.get("head") or "")
    refresh_command = (
        "ethos lane refresh-base --apply --authorize "
        f"--expect-head {current_head or '<head>'} --json"
    )
    if role != "work_lane":
        return {
            "kind": "landing_readiness",
            "state": "not_work_lane",
            "branch": branch,
            "head": current_head,
            "candidate_branch": candidate_branch,
            "candidate_head": candidate_head,
            "required_gaps": [],
            "next_action": "start or enter a Work Lane before landing",
        }
    if not candidate.get("exists"):
        return {
            "kind": "landing_readiness",
            "state": "blocked",
            "branch": branch,
            "head": current_head,
            "candidate_branch": candidate_branch,
            "candidate_head": candidate_head,
            "required_gaps": ["candidate_branch_missing"],
            "next_action": "create or repair the configured candidate branch",
        }
    if not candidate.get("worktree_exists"):
        return {
            "kind": "landing_readiness",
            "state": "blocked",
            "branch": branch,
            "head": current_head,
            "candidate_branch": candidate_branch,
            "candidate_head": candidate_head,
            "required_gaps": ["candidate_worktree_missing"],
            "next_action": "create or repair the configured candidate worktree",
        }
    if current_head and candidate_head and not is_ancestor(root, candidate_head, current_head):
        return {
            "kind": "landing_readiness",
            "state": "candidate_base_stale",
            "branch": branch,
            "head": current_head,
            "candidate_branch": candidate_branch,
            "candidate_head": candidate_head,
            "required_gaps": ["candidate_base_stale"],
            "next_action": refresh_command,
        }
    return {
        "kind": "landing_readiness",
        "state": "candidate_base_current",
        "branch": branch,
        "head": current_head,
        "candidate_branch": candidate_branch,
        "candidate_head": candidate_head,
        "required_gaps": [],
        "next_action": "ethos land --json",
    }


def _safe_ref(root: Path, ref: str) -> str:
    try:
        return _run_git(root, "rev-parse", ref)
    except subprocess.CalledProcessError:
        return ""


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


def workspace_status(root: Path) -> dict[str, object]:
    try:
        repo = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve()
    except subprocess.CalledProcessError:
        return _non_git_status(root)
    current_path = repo
    provenance = dirty_provenance(root)
    entries = cast("list[dict[str, str]]", provenance["entries"])
    paths = tuple(str(entry["path"]) for entry in entries)
    branch = current_branch(root)
    head = _safe_ref(root, "HEAD")
    policy = load_branch_role_policy(repo)
    role = policy.role_for_branch(branch)
    worktrees = _worktrees(root, current_path=current_path, policy=policy)
    candidate = _candidate_status(root, worktrees, policy=policy)
    lease_by_branch = leases_by_branch(worktrees, current_path=current_path)
    bindings = branch_bindings(
        repo,
        worktrees,
        candidate,
        policy=policy,
        lease_by_branch=lease_by_branch,
    )
    current_scope, current_scope_state = branch_path_scope(
        repo, branch=branch, candidate_branch=policy.candidate_branch
    )
    foreign = _foreign_work_lanes(
        worktrees,
        current_path=current_path,
        current_role=role,
        current_path_scope=current_scope,
        current_scope_state=current_scope_state,
        accepted_branch=policy.accepted_branch,
        candidate_branch=policy.candidate_branch,
        lease_by_branch=lease_by_branch,
        root=repo,
    )
    coordination_required_gaps, coordination_advisory_gaps = coordination_gaps(
        foreign, current_role=role, current_scope_state=current_scope_state
    )
    unbound_refs = unbound_work_lane_refs(repo, bindings, policy=policy)
    if unbound_refs:
        coordination_advisory_gaps.append("unbound_work_lane_ref_present")
    coordination_gap_list = coordination_required_gaps + coordination_advisory_gaps
    coordination = coordination_package(
        foreign,
        required_gaps=coordination_required_gaps,
        advisory_gaps=coordination_advisory_gaps,
        unbound_work_lane_refs=unbound_refs,
    )
    support = closeout_support(
        branch=branch,
        role=role,
        dirty=bool(paths),
        candidate=candidate,
        lease_by_branch=lease_by_branch,
        coordination_required_gaps=coordination_required_gaps,
    )
    closeout_gaps = cast("list[str]", support["required_gaps"])
    required_gaps = workspace_required_gaps(closeout_gaps, candidate=candidate)
    landing = landing_readiness(repo, branch=branch, role=role, candidate=candidate)
    stage_gates = _stage_gates(
        branch=branch,
        role=role,
        closeout_support=support,
        landing_readiness=landing,
    )
    return {
        "root": str(root),
        "branch": branch,
        "head": head,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "dirty_provenance": provenance,
        "role": role,
        "role_policy": policy.as_status_policy(),
        "runtime_binding": runtime_binding(repo),
        "landing_readiness": landing,
        "candidate": candidate,
        "worktrees": worktrees,
        "branch_bindings": bindings,
        "foreign_work_lanes": foreign,
        "coordination_gaps": coordination_gap_list,
        "coordination": coordination,
        "closeout_support": support,
        "stage_gates": stage_gates,
        "required_gaps": required_gaps,
    }


def _stage_gates(
    *,
    branch: str,
    role: str,
    closeout_support: dict[str, object],
    landing_readiness: dict[str, object],
) -> dict[str, object]:
    is_work_lane = role == "work_lane"
    raw_closeout_gaps = cast("list[object]", closeout_support.get("required_gaps", ()))
    closeout_gaps = tuple(str(gap) for gap in raw_closeout_gaps)
    authoring_allowed = is_work_lane and not any(
        gap.startswith("work_lane_missing_lease:") for gap in closeout_gaps
    )
    raw_landing_gaps = cast("list[object]", landing_readiness.get("required_gaps", []))
    landing_gaps = tuple(str(gap) for gap in raw_landing_gaps)
    landing_stale = "candidate_base_stale" in landing_gaps
    integration_allowed = bool(closeout_support.get("supported")) and not landing_stale
    accepted_closeout_allowed = False
    next_commands: list[str] = []
    if authoring_allowed:
        next_commands.append("ethos lane prewrite <path>")
    if landing_stale:
        refresh_command = str(
            landing_readiness.get("next_action") or "ethos lane refresh-base --json"
        )
        next_commands.append(refresh_command)
    elif integration_allowed:
        next_commands.append("ethos land --json")
    if not next_commands:
        next_commands.append("ethos lane start <name>")

    blocked_stage = ""
    blocker_owner = ""
    if not authoring_allowed:
        blocked_stage = "authoring"
        blocker_owner = branch if is_work_lane else ""
    elif not integration_allowed:
        blocked_stage = "candidate_integration"
        blocker_owner = (
            str(landing_readiness.get("candidate_branch") or branch) if landing_stale else branch
        )
    else:
        # accepted_closeout_allowed is a constant False the closeout command owns, so
        # reaching this final arm means accepted-closeout is the remaining blocked stage.
        blocked_stage = "accepted_closeout"
        blocker_owner = str(closeout_support.get("target_branch") or "")

    return {
        "authoring_allowed": authoring_allowed,
        "integration_allowed": integration_allowed,
        "accepted_closeout_allowed": accepted_closeout_allowed,
        "blocked_stage": blocked_stage,
        "blocker_owner": blocker_owner,
        "recommended_next_command": next_commands[-1],
        "next_commands": next_commands,
    }


def _non_git_status(root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    candidate: dict[str, object] = {
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
        "dirty_provenance": {"dirty": False, "state": "non_git", "entries": [], "summary": {}},
        "role": "other",
        "role_policy": policy.as_status_policy(),
        "runtime_binding": runtime_binding(root),
        "landing_readiness": {
            "kind": "landing_readiness",
            "state": "not_work_lane",
            "branch": "untracked",
            "head": "",
            "candidate_branch": policy.candidate_branch,
            "candidate_head": "",
            "required_gaps": ["git_repository_missing"],
            "next_action": "enter a Git-backed Work Lane before landing",
        },
        "candidate": candidate,
        "worktrees": [],
        "branch_bindings": branch_bindings(
            root,
            [],
            candidate,
            policy=policy,
            lease_by_branch={},
        ),
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "coordination": coordination_package([], required_gaps=[], advisory_gaps=[]),
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
        "stage_gates": {
            "authoring_allowed": False,
            "integration_allowed": False,
            "accepted_closeout_allowed": False,
            "blocked_stage": "authoring",
            "blocker_owner": "",
            "recommended_next_command": "ethos lane start <name>",
            "next_commands": ["ethos lane start <name>"],
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
        "worktree_binding": worktree_binding(path, current_path=current_path),
    }


def _foreign_work_lanes(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
    current_role: str,
    current_path_scope: tuple[str, ...],
    current_scope_state: str,
    accepted_branch: str,
    candidate_branch: str,
    lease_by_branch: dict[str, dict[str, object]],
    root: Path,
) -> list[dict[str, object]]:
    foreign: list[dict[str, object]] = []
    for worktree in worktrees:
        if worktree["role"] != ROLE_WORK_LANE:
            continue
        if Path(str(worktree["path"])).resolve() == current_path:
            continue
        branch = str(worktree["branch"])
        lease = lease_by_branch.get(branch, {})
        foreign.append(
            foreign_work_lane(
                worktree,
                current_role=current_role,
                current_path_scope=current_path_scope,
                current_scope_state=current_scope_state,
                candidate_branch=candidate_branch,
                lease=lease,
                root=root,
                claim_id=lease_claim_id(lease),
                relation_to_accepted=ref_relation(root, branch, accepted_branch),
                dirty_paths=_worktree_dirty_paths(worktree),
            )
        )
    return foreign


def _worktree_dirty_paths(worktree: dict[str, str]) -> tuple[str, ...]:
    if str(worktree.get("worktree_binding") or "") == "missing":
        return ()
    return changed_paths(Path(str(worktree["path"])))


def _candidate_status(
    root: Path,
    worktrees: list[dict[str, str]],
    *,
    policy: BranchRolePolicy,
) -> dict[str, object]:
    head = ref_head(root, policy.candidate_branch)
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
        "worktree_exists": worktree_binding in {"current", "linked"},
        "worktree_path": worktree_path,
        "worktree_binding": worktree_binding,
        "behind_accepted": behind_accepted,
    }

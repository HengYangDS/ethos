# ruff: noqa: E501 - source-budget closeout keeps equivalent status projections compact.
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.coordination import branch_path_scope
from ethos.adapters.repo.coordination import coordination_gaps
from ethos.adapters.repo.coordination import coordination_package
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.coordination import foreign_work_lane_deferred
from ethos.adapters.repo.coordination import workspace_required_gaps
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.git import git_stdout_checked
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
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Mapping

# fmt: off


def landing_readiness(
    root: Path, *, branch: str, role: str, candidate: dict[str, object]
) -> dict[str, object]:
    """Expose candidate-base readiness without replacing land-time CAS."""
    head, candidate_branch = _safe_ref(root, "HEAD"), str(candidate.get("branch") or "")
    candidate_head = str(candidate.get("head") or "")
    if role != ROLE_WORK_LANE:
        result = "not_work_lane", [], "start or enter a Work Lane before landing"
    elif not candidate.get("exists"):
        result = "blocked", ["candidate_branch_missing"], "create or repair the configured candidate branch"
    elif not candidate.get("worktree_exists"):
        result = "blocked", ["candidate_worktree_missing"], "create or repair the configured candidate worktree"
    elif head and candidate_head and not is_ancestor(root, candidate_head, head):
        result = "candidate_base_stale", ["candidate_base_stale"], f"ethos lane refresh-base --apply --authorize --expect-head {head or '<head>'} --json"
    else:
        result = "candidate_base_current", [], "ethos land --json"
    state, gaps, action = result
    return {"kind": "landing_readiness", "state": state, "branch": branch, "head": head, "candidate_branch": candidate_branch, "candidate_head": candidate_head, "required_gaps": gaps, "next_action": action}


def _safe_ref(root: Path, ref: str) -> str:
    try:
        return git_stdout_checked(root, "rev-parse", ref)
    except subprocess.CalledProcessError:
        return ""


def current_branch(root: Path) -> str:
    return git_stdout_checked(root, "branch", "--show-current") or "detached"


def workspace_status(root: Path, *, include_foreign_path_scope: bool = True) -> dict[str, object]:
    """Return workspace truth, optionally deferring foreign path-scope expansion."""
    try:
        repo = Path(git_stdout_checked(root, "rev-parse", "--show-toplevel")).resolve()
    except subprocess.CalledProcessError:
        return _non_git_status(root, defer_details=not include_foreign_path_scope)
    provenance = dirty_provenance(root)
    paths = tuple(str(item["path"]) for item in cast("list[dict[str, str]]", provenance["entries"]))
    branch, head, policy = current_branch(root), _safe_ref(root, "HEAD"), load_branch_role_policy(repo)
    role = policy.role_for_branch(branch)
    worktrees = worktree_records(root, current_path=repo, policy=policy)
    candidate = _candidate_status(root, worktrees, policy=policy)
    leases = leases_by_branch(repo)
    bindings = branch_bindings(repo, worktrees, candidate, policy=policy, lease_by_branch=leases)
    scope = branch_path_scope(repo, branch=branch, candidate_branch=policy.candidate_branch) if include_foreign_path_scope else ((), "deferred")
    foreign = _foreign_work_lanes(worktrees, current=(repo, role, *scope), policy=policy, leases=leases, include_path_scope=include_foreign_path_scope)
    required, advisory = coordination_gaps(foreign, current_role=role, current_scope_state=scope[1])
    unbound_refs = unbound_work_lane_refs(repo, bindings, policy=policy)
    if unbound_refs:
        advisory.append("unbound_work_lane_ref_present")
    coordination = coordination_package(foreign, required_gaps=required, advisory_gaps=advisory, defer_details=not include_foreign_path_scope, unbound_work_lane_refs=unbound_refs)
    support = closeout_support(branch=branch, role=role, dirty=bool(paths), candidate=candidate, lease_by_branch=leases, coordination_required_gaps=required)
    landing = landing_readiness(repo, branch=branch, role=role, candidate=candidate)
    return _status_payload(root=root, runtime_root=repo, branch=branch, head=head, paths=paths, provenance=provenance, role=role, policy=policy, candidate=candidate, landing=landing, support=support, worktrees=worktrees, bindings=bindings, foreign=foreign, required=required, advisory=advisory, coordination=coordination, workspace_gaps=workspace_required_gaps(cast("list[str]", support["required_gaps"]), candidate=candidate))


def _status_payload(
    *, root: Path, runtime_root: Path, branch: str, head: str | None, paths: tuple[str, ...], provenance: Mapping[str, object], role: str, policy: BranchRolePolicy, candidate: dict[str, object], landing: dict[str, object], support: dict[str, object], worktrees: list[dict[str, str]], bindings: list[dict[str, str]], foreign: list[dict[str, object]], required: list[str], advisory: list[str], coordination: dict[str, object], workspace_gaps: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {"root": str(root), "branch": branch}
    if head is not None:
        payload["head"] = head
    payload.update({"dirty": bool(paths), "changed_paths": list(paths), "dirty_provenance": provenance, "role": role, "role_policy": policy.as_status_policy(), "runtime_binding": runtime_binding(runtime_root), "landing_readiness": landing, "candidate": candidate, "worktrees": worktrees, "branch_bindings": bindings, "foreign_work_lanes": foreign, "coordination_gaps": [*required, *advisory], "coordination": coordination, "closeout_support": support, "stage_gates": _stage_gates(branch=branch, role=role, closeout_support=support, landing_readiness=landing), "required_gaps": workspace_gaps})
    return payload


def _stage_gates(
    *, branch: str, role: str, closeout_support: Mapping[str, object], landing_readiness: Mapping[str, object],
) -> dict[str, object]:
    is_work_lane = role == ROLE_WORK_LANE
    closeout_gaps = tuple(map(str, cast("list[object]", closeout_support.get("required_gaps", ()))))
    authoring = is_work_lane and not any(gap.startswith("work_lane_missing_lease:") for gap in closeout_gaps)
    landing_gaps = tuple(map(str, cast("list[object]", landing_readiness.get("required_gaps", []))))
    stale = "candidate_base_stale" in landing_gaps
    integration = bool(closeout_support.get("supported")) and not stale
    followup = [str(landing_readiness.get("next_action") or "ethos lane refresh-base --json")] if stale else ["ethos land --json"] if integration else []
    commands = (["ethos lane prewrite <path>"] if authoring else []) + followup or ["ethos lane start <name>"]
    if not authoring:
        blocked, owner = "authoring", branch if is_work_lane else ""
    elif not integration:
        blocked, owner = "candidate_integration", str(landing_readiness.get("candidate_branch") or branch) if stale else branch
    else:
        blocked, owner = "accepted_closeout", str(closeout_support.get("target_branch") or "")
    return {"authoring_allowed": authoring, "integration_allowed": integration, "accepted_closeout_allowed": False, "blocked_stage": blocked, "blocker_owner": owner, "recommended_next_command": commands[-1], "next_commands": commands}


def _non_git_status(root: Path, *, defer_details: bool) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    candidate: dict[str, object] = {"branch": policy.candidate_branch, "exists": False, "head": "", "worktree_exists": False, "worktree_path": "", "worktree_binding": "absent"}
    landing: dict[str, object] = {"kind": "landing_readiness", "state": "not_work_lane", "branch": "untracked", "head": "", "candidate_branch": policy.candidate_branch, "candidate_head": "", "required_gaps": ["git_repository_missing"], "next_action": "enter a Git-backed Work Lane before landing"}
    support: dict[str, object] = {"supported": False, "branch": "", "target_branch": policy.candidate_branch, "target_path": "", "operation": "", "holder_ref": "", "lease_id": "", "lease_epoch": 0, "lease_expected_head": "", "lease_expires_at": "", "lease_payload_sha256": "", "claim_id": "", "claim_binding": "unbound", "required_gaps": ["protected_root_mutation", "git_repository_missing"]}
    provenance = {"dirty": False, "state": "non_git", "entries": [], "summary": {}, "temporary_probes": {"count": 0, "paths": [], "truncated": False}}
    worktrees: list[dict[str, str]] = []
    bindings = branch_bindings(root, worktrees, candidate, policy=policy, lease_by_branch={})
    coordination = coordination_package([], required_gaps=[], advisory_gaps=[], defer_details=defer_details)
    return _status_payload(root=root, runtime_root=root, branch="untracked", head=None, paths=(), provenance=provenance, role="other", policy=policy, candidate=candidate, landing=landing, support=support, worktrees=worktrees, bindings=bindings, foreign=[], required=[], advisory=[], coordination=coordination, workspace_gaps=["git_repository_missing", "candidate_branch_missing"])


def worktree_records(
    root: Path, *, current_path: Path, policy: BranchRolePolicy
) -> list[dict[str, str]]:
    """Return normalized Git worktree records without probing their state."""
    blocks = (block for block in git_stdout_checked(root, "worktree", "list", "--porcelain").split("\n\n") if block.strip())
    return [_normalize_worktree(dict(line.partition(" ")[::2] for line in block.splitlines() if line), current_path=current_path, policy=policy) for block in blocks]


def _normalize_worktree(
    entry: dict[str, str], *, current_path: Path, policy: BranchRolePolicy
) -> dict[str, str]:
    branch = entry.get("branch", "").removeprefix("refs/heads/")
    path = entry.get("worktree", "")
    return {"path": path, "head": entry.get("HEAD", ""), "branch": branch or "detached", "role": policy.role_for_branch(branch), "worktree_binding": worktree_binding(path, current_path=current_path)}


def _foreign_work_lanes(
    worktrees: list[dict[str, str]], *, current: tuple[Path, str, tuple[str, ...], str], policy: BranchRolePolicy, leases: dict[str, dict[str, object]], include_path_scope: bool,
) -> list[dict[str, object]]:
    root, current_role, current_path_scope, current_scope_state = current
    foreign: list[dict[str, object]] = []
    for worktree in worktrees:
        if worktree["role"] != ROLE_WORK_LANE or Path(worktree["path"]).resolve() == root:
            continue
        branch, lease = worktree["branch"], leases.get(worktree["branch"], {})
        claim_id = lease_claim_id(lease)
        if not include_path_scope:
            foreign.append(foreign_work_lane_deferred(worktree, lease=lease, claim_id=claim_id))
            continue
        dirty_paths = () if worktree.get("worktree_binding") == "missing" else changed_paths(Path(worktree["path"]))
        foreign.append(foreign_work_lane(worktree, current_role=current_role, current_path_scope=current_path_scope, current_scope_state=current_scope_state, candidate_branch=policy.candidate_branch, root=root, lease=lease, claim_id=claim_id, relation_to_accepted=ref_relation(root, branch, policy.accepted_branch), dirty_paths=dirty_paths))
    return foreign


def _candidate_status(
    root: Path, worktrees: list[dict[str, str]], *, policy: BranchRolePolicy
) -> dict[str, object]:
    head = ref_head(root, policy.candidate_branch)
    worktree = next((item for item in worktrees if item["branch"] == policy.candidate_branch), {})
    path, binding = worktree.get("path", ""), worktree.get("worktree_binding", "absent")
    binding = "unbound" if head and not path else binding
    count = git_stdout_checked(root, "rev-list", "--count", f"{policy.candidate_branch}..{policy.accepted_branch}").strip() if head else ""
    return {"branch": policy.candidate_branch, "exists": bool(head), "head": head, "worktree_exists": binding in {"current", "linked"}, "worktree_path": path, "worktree_binding": binding, "behind_accepted": int(count) if count.isdigit() else 0}
# fmt: on

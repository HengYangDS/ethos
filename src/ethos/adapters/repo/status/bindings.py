"""Project live branch, worktree and lease bindings into repository status."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.git import git_stdout_checked
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.merge.observation import pending_merge_heads
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy


@dataclass(frozen=True, slots=True)
class _BindingFields:
    branch: str
    role: str
    head: str
    path: str
    worktree: str
    lease_state: str


def has_changed_paths(root: Path) -> bool:
    """Return whether tracked, untracked, or unreadable state is present."""
    try:
        return bool(git_stdout_checked(root, "status", "--porcelain", "--untracked-files=all"))
    except (OSError, subprocess.CalledProcessError):
        return True


def branch_bindings(
    root: Path,
    worktrees: list[dict[str, str]],
    candidate: dict[str, object],
    *,
    policy: BranchRolePolicy,
    lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Return configured, linked, and unbound branch bindings."""
    by_branch = {item["branch"]: item for item in worktrees if item["branch"] != "detached"}
    bindings: list[dict[str, object]] = []
    seen: set[str] = set()
    configured = (
        (policy.release_branch, policy.role_for_branch(policy.release_branch)),
        (policy.accepted_branch, policy.role_for_branch(policy.accepted_branch)),
        (policy.candidate_branch, ROLE_CANDIDATE),
    )
    for branch, role in configured:
        if branch in seen:
            continue
        bindings.append(
            _branch_binding(
                root,
                branch=branch,
                role=role,
                worktree=by_branch.get(branch),
                candidate=candidate if branch == policy.candidate_branch else None,
                lease=lease_by_branch.get(branch, {}),
            )
        )
        seen.add(branch)
    remaining = [
        _branch_binding(
            root,
            branch=item["branch"],
            role=item["role"],
            worktree=item,
            lease=lease_by_branch.get(item["branch"], {}),
        )
        for item in worktrees
        if item["branch"] != "detached" and item["branch"] not in seen
    ]
    remaining.extend(
        _branch_binding(
            root,
            branch=branch,
            role=ROLE_WORK_LANE,
            head=head,
            lease=lease_by_branch.get(branch, {}),
        )
        for branch, head in _work_lane_refs(root, policy=policy)
        if branch not in seen and branch not in by_branch
    )
    order = {record["role"]: index for index, record in enumerate(policy.semantic_order())}
    for binding in sorted(
        remaining, key=lambda item: (order.get(item["role"], len(order)), item["branch"])
    ):
        branch = str(binding["branch"])
        if branch not in seen:
            bindings.append(binding)
            seen.add(branch)
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
        for branch, _, head in refs
        if policy.role_for_branch(branch) == ROLE_WORK_LANE
    ]


def unbound_work_lane_refs(
    root: Path,
    branch_bindings: list[dict[str, object]],
    *,
    policy: BranchRolePolicy,
    lease_by_branch: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Return exact Lease observations for unbound Work Lane refs."""
    refs: list[dict[str, object]] = []
    for binding in branch_bindings:
        if binding["role"] != ROLE_WORK_LANE or binding["worktree_binding"] != "unbound":
            continue
        branch = str(binding["branch"])
        generation = lease_generation(lease_by_branch.get(branch, {}))
        generation.pop("lane_ref")
        relation = ref_relation(root, branch, policy.accepted_branch)
        refs.append(
            {
                "branch": branch,
                "head": binding["head"],
                **generation,
                "lease_state": binding["lease_state"],
                "relation_to_accepted": relation,
                "next_action": unbound_ref_next_action(relation),
            }
        )
    return refs


def ref_relation(root: Path, branch: str, accepted_branch: str) -> str:
    """Classify a branch ref relative to the accepted branch."""
    if not ref_head(root, branch) or not ref_head(root, accepted_branch):
        return "unknown"
    if is_ancestor(root, branch, accepted_branch):
        return "ancestor_of_accepted"
    return (
        "descendant_of_accepted"
        if is_ancestor(root, accepted_branch, branch)
        else "diverged_from_accepted"
    )


def landing_readiness(
    root: Path,
    *,
    head: str,
    branch: str,
    role: str,
    candidate: dict[str, object],
    accepted: dict[str, object],
) -> dict[str, object]:
    """Select the next integration boundary from exact Git containment."""
    candidate_branch = str(candidate.get("branch") or "")
    candidate_head = str(candidate.get("head") or "")
    accepted_head = str(accepted.get("head") or "")
    accepted_root = (
        str(accepted.get("worktree_path") or "")
        if accepted.get("worktree_binding") in {"current", "linked"}
        else ""
    )
    accepted_includes_head = bool(
        role == ROLE_WORK_LANE and head and accepted_head and is_ancestor(root, head, accepted_head)
    )
    if role != ROLE_WORK_LANE:
        result = "not_work_lane", [], "start or enter a Work Lane before landing"
    elif not accepted_includes_head and not candidate.get("exists"):
        result = (
            "blocked",
            ["candidate_branch_missing"],
            "create or repair the configured candidate branch",
        )
    elif not accepted_includes_head and not candidate.get("worktree_exists"):
        result = (
            "blocked",
            ["candidate_worktree_missing"],
            "create or repair the configured candidate worktree",
        )
    elif pending_merge_heads(root):
        result = (
            "blocked",
            ["merge_in_progress"],
            (
                "ethos lane refresh-base --strategy merge "
                f"--root {shlex.quote(str(root.resolve()))} --json"
            ),
        )
    elif accepted_includes_head:
        result = (
            "accepted_integrated" if accepted_root else "blocked",
            [] if accepted_root else ["accepted_worktree_missing"],
            (
                "ethos lane retire landed "
                f"--branch {shlex.quote(branch)} --root {shlex.quote(accepted_root)} --json"
                if accepted_root
                else "link the configured accepted checkout before lane retirement"
            ),
        )
    elif head and candidate_head and is_ancestor(root, head, candidate_head):
        result = (
            "candidate_integrated" if accepted_root else "blocked",
            [] if accepted_root else ["accepted_worktree_missing"],
            (
                f"ethos status --root {shlex.quote(accepted_root)} --json"
                if accepted_root
                else "link the configured accepted checkout before closeout"
            ),
        )
    elif head and candidate_head and not is_ancestor(root, candidate_head, head):
        result = (
            "candidate_base_stale",
            ["candidate_base_stale"],
            f"ethos lane refresh-base --apply --authorize --expect-head {head or '<head>'} --json",
        )
    else:
        result = "candidate_base_current", [], "ethos land --json"
    state, gaps, action = result
    return {
        "kind": "landing_readiness",
        "state": state,
        "branch": branch,
        "head": head,
        "candidate_branch": candidate_branch,
        "candidate_head": candidate_head,
        "required_gaps": gaps,
        "next_action": action,
    }


def unbound_ref_next_action(relation: str) -> str:
    """Return an observation-only action for an unbound Work Lane ref."""
    return {
        "ancestor_of_accepted": "preserve unbound Work Lane ref; no retirement effect is admitted",
        "descendant_of_accepted": (
            "preserve unbound Work Lane ref; bind a recovery contract before action"
        ),
    }.get(relation, "preserve and block on unbound Work Lane ref")


def _binding(fields: _BindingFields) -> dict[str, object]:
    return {
        "branch": fields.branch,
        "role": fields.role,
        "head": fields.head,
        "worktree_path": fields.path,
        "worktree_binding": fields.worktree,
        "lease_state": fields.lease_state,
    }


def _branch_binding(
    root: Path,
    *,
    branch: str,
    role: str,
    lease: dict[str, object],
    worktree: dict[str, str] | None = None,
    candidate: dict[str, object] | None = None,
    head: str = "",
) -> dict[str, object]:
    if worktree is not None:
        branch, role, head, path, binding = (
            worktree["branch"],
            worktree["role"],
            worktree["head"],
            worktree["path"],
            worktree["worktree_binding"],
        )
    elif candidate is not None:
        head, path, binding = (
            str(candidate["head"]),
            str(candidate["worktree_path"]),
            str(candidate["worktree_binding"]),
        )
    else:
        head, path = head or ref_head(root, branch), ""
        binding = "unbound" if head else "absent"
    lease_state = str(lease.get("lease_state") or "missing") if role == ROLE_WORK_LANE else "none"
    return _binding(
        _BindingFields(
            branch=branch,
            role=role,
            head=head,
            path=path,
            worktree=binding,
            lease_state=lease_state,
        )
    )


def worktree_binding(path: str, *, current_path: Path) -> str:
    """Classify a registered worktree path against filesystem reality."""
    if not path:
        return "absent"
    resolved = Path(path).resolve()
    if resolved == current_path:
        return "current"
    return "linked" if resolved.exists() else "missing"


def leases_by_branch(current_path: Path) -> dict[str, dict[str, object]]:
    """Load strict Lease observations without collapsing unknown to missing."""
    leases: dict[str, dict[str, object]] = {}
    for observation in lease_observations(state_database(current_path)):
        record = observation.record()
        leases[observation.subject] = record
    return leases


def lease_generation(lease: dict[str, object]) -> dict[str, object]:
    """Project the exact current Lease generation bound by transient Facts."""
    return {
        "lane_ref": str(lease.get("lane_ref") or ""),
        "generation": integer_value(lease.get("generation")),
        "holder_ref": str(lease.get("holder_ref") or ""),
        "expires_at": str(lease.get("expires_at") or ""),
    }


def accepted_worktree_root(worktrees: object, default: Path) -> Path:
    """Return the linked accepted checkout required for destructive closeout."""
    return next(
        (
            Path(str(item.get("path")))
            for item in (worktrees if isinstance(worktrees, list) else ())
            if isinstance(item, dict)
            and item.get("role") == ROLE_ACCEPTED_ROOT
            and item.get("path")
        ),
        default,
    )


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
    is_work_lane = role == ROLE_WORK_LANE
    lease = lease_by_branch.get(branch, {}) if is_work_lane else {}
    gaps = _closeout_lease_gaps(
        branch=branch,
        is_work_lane=is_work_lane,
        dirty=dirty,
        lease=lease,
    )
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    elif has_changed_paths(Path(str(candidate["worktree_path"]))):
        gaps.append("candidate_worktree_dirty")
    if is_work_lane:
        gaps.extend(coordination_required_gaps)
    return {
        "supported": not gaps,
        "branch": branch if is_work_lane else "",
        "target_branch": str(candidate["branch"]),
        "target_path": str(candidate["worktree_path"]),
        "operation": "land_to_candidate" if is_work_lane else "",
        "holder_ref": str(lease.get("holder_ref") or ""),
        "lease_generation": integer_value(lease.get("generation")) if lease else 0,
        "lease_expires_at": str(lease.get("expires_at") or ""),
        "lease_state": (str(lease.get("lease_state") or "missing") if is_work_lane else "none"),
        "required_gaps": gaps,
    }


def _closeout_lease_gaps(
    *,
    branch: str,
    is_work_lane: bool,
    dirty: bool,
    lease: dict[str, object],
) -> list[str]:
    state = str(lease.get("lease_state") or "missing")
    if not is_work_lane:
        gap = "protected_root_mutation"
    elif dirty:
        gap = "work_lane_dirty"
    elif state == "unknown":
        gap = f"work_lane_lease_unknown:{branch}"
    elif state == "expired":
        gap = f"work_lane_lease_expired:{branch}"
    elif state != "valid" or not lease.get("holder_ref"):
        gap = f"work_lane_missing_lease:{branch}"
    elif integer_value(lease.get("generation")) < 1:
        gap = f"work_lane_lease_generation_missing:{branch}"
    else:
        return []
    return [gap]

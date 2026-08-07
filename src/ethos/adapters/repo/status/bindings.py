from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import git_stdout_checked
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.schema import observed_state_database
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
    base_commitment_digest: str
    commitment_binding: str
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
        generation.pop("branch")
        generation["base_commitment_path"] = generation["base_commitment_path"] or None
        relation = ref_relation(root, branch, policy.accepted_branch)
        refs.append(
            {
                "branch": branch,
                "head": binding["head"],
                **generation,
                "commitment_binding": binding["commitment_binding"],
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


def unbound_ref_next_action(relation: str) -> str:
    """Return an observation-only action for an unbound Work Lane ref."""
    return {
        "ancestor_of_accepted": "preserve unbound Work Lane ref; no retirement effect is admitted",
        "descendant_of_accepted": (
            "preserve unbound Work Lane ref; bind a recovery contract before action"
        ),
    }.get(relation, "preserve and block on unbound Work Lane ref")


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether one ref is an ancestor of another ref."""
    return _git(root, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def _binding(fields: _BindingFields) -> dict[str, object]:
    return {
        "branch": fields.branch,
        "role": fields.role,
        "head": fields.head,
        "worktree_path": fields.path,
        "worktree_binding": fields.worktree,
        "base_commitment_digest": fields.base_commitment_digest,
        "commitment_binding": fields.commitment_binding,
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
    base_digest = (
        str(lease.get("base_commitment_digest") or "")
        if lease_state in {"valid", "expired"}
        else ""
    )
    observed_binding = str(lease.get("commitment_binding") or "")
    commitment_binding = (
        observed_binding
        if lease_state == "valid" and observed_binding
        else "unknown"
        if lease_state == "unknown"
        else "expired"
        if lease_state == "expired"
        else "missing"
        if role == ROLE_WORK_LANE
        else "not_applicable"
    )
    return _binding(
        _BindingFields(
            branch=branch,
            role=role,
            head=head,
            path=path,
            worktree=binding,
            base_commitment_digest=base_digest,
            commitment_binding=commitment_binding,
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


def leases_by_branch(
    current_path: Path,
    *,
    object_environment: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    """Load strict Lease observations without collapsing unknown to missing."""
    leases: dict[str, dict[str, object]] = {}
    for observation in lease_observations(observed_state_database(current_path)):
        record = observation.record()
        record["commitment_binding"] = _lease_commitment_binding(
            current_path,
            record,
            object_environment=object_environment,
        )
        leases[observation.subject] = record
    return leases


def lease_generation(lease: dict[str, object]) -> dict[str, object]:
    """Project the exact current Lease generation bound by transient Facts."""
    raw_scope = lease.get("path_scope")
    path_scope = [str(item) for item in raw_scope] if isinstance(raw_scope, list | tuple) else []
    return {
        "branch": str(lease.get("lane_ref") or ""),
        "lane_incarnation_id": str(lease.get("lane_incarnation_id") or ""),
        "lease_id": str(lease.get("lease_id") or ""),
        "epoch": integer_value(lease.get("epoch")),
        "holder_ref": str(lease.get("holder_ref") or ""),
        "expected_head": str(lease.get("expected_head") or ""),
        "expected_tree": str(lease.get("expected_tree") or ""),
        "base_commitment_path": (
            str(lease["base_commitment_path"]) if lease.get("base_commitment_path") else None
        ),
        "base_commitment_bytes_sha256": str(lease.get("base_commitment_bytes_sha256") or ""),
        "base_commitment_digest": str(lease.get("base_commitment_digest") or ""),
        "issued_at": str(lease.get("issued_at") or ""),
        "renewed_at": str(lease.get("renewed_at") or ""),
        "path_scope": path_scope,
        "expires_at": str(lease.get("expires_at") or ""),
        "payload_sha256": str(lease.get("payload_sha256") or ""),
    }


def _lease_commitment_binding(
    root: Path,
    lease: dict[str, object],
    *,
    object_environment: dict[str, str] | None = None,
) -> str:
    state = str(lease.get("lease_state") or "missing")
    if state != "valid":
        return state
    digest = str(lease.get("base_commitment_digest") or "")
    try:
        selected = load_lease_bound_commitment(
            root,
            lease=lease,
            environment=object_environment,
        ).digest()
    except ValueError:
        return "mismatch"
    return "bound" if digest and selected == digest else "mismatch"


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
    commitment_binding = str(lease.get("commitment_binding") or "missing")
    gaps = _closeout_lease_gaps(
        branch=branch,
        is_work_lane=is_work_lane,
        dirty=dirty,
        lease=lease,
        commitment_binding=commitment_binding,
    )
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    elif has_changed_paths(Path(str(candidate["worktree_path"]))):
        gaps.append("candidate_worktree_dirty")
    if is_work_lane:
        gaps.extend(coordination_required_gaps)
    base_digest = str(lease.get("base_commitment_digest") or "")
    return {
        "supported": not gaps,
        "branch": branch if is_work_lane else "",
        "target_branch": str(candidate["branch"]),
        "target_path": str(candidate["worktree_path"]),
        "operation": "land_to_candidate" if is_work_lane else "",
        "holder_ref": str(lease.get("holder_ref") or ""),
        "lease_id": str(lease.get("lease_id") or ""),
        "lease_epoch": integer_value(lease.get("epoch")) if lease else 0,
        "lease_expected_head": str(lease.get("expected_head") or ""),
        "lease_expected_tree": str(lease.get("expected_tree") or ""),
        "lease_base_commitment_path": (
            str(lease["base_commitment_path"]) if lease.get("base_commitment_path") else None
        ),
        "lease_base_commitment_bytes_sha256": str(lease.get("base_commitment_bytes_sha256") or ""),
        "lease_expires_at": str(lease.get("expires_at") or ""),
        "lease_payload_sha256": str(lease.get("payload_sha256") or ""),
        "lease_state": (str(lease.get("lease_state") or "missing") if is_work_lane else "none"),
        "base_commitment_digest": base_digest,
        "commitment_binding": (
            commitment_binding
            if is_work_lane and lease.get("lease_state") == "valid"
            else "unknown"
            if is_work_lane and lease.get("lease_state") == "unknown"
            else "expired"
            if is_work_lane and lease.get("lease_state") == "expired"
            else "missing"
            if is_work_lane
            else "not_applicable"
        ),
        "required_gaps": gaps,
    }


def _closeout_lease_gaps(
    *,
    branch: str,
    is_work_lane: bool,
    dirty: bool,
    lease: dict[str, object],
    commitment_binding: str,
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
    elif commitment_binding != "bound":
        gap = f"lease_base_commitment_digest_mismatch:{branch}"
    else:
        return []
    return [gap]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=False, text=True, capture_output=True)


def ref_head(root: Path, ref: str) -> str:
    """Resolve a ref to its head, or return an empty string when absent."""
    completed = _git(root, "rev-parse", "--verify", ref)
    return completed.stdout.strip() if completed.returncode == 0 else ""

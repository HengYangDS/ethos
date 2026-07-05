from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

from ethos.adapters.repo.coordination import branch_path_scope
from ethos.adapters.repo.coordination import coordination_gaps as _scope_coordination_gaps
from ethos.adapters.repo.coordination import coordination_package
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.coordination import workspace_required_gaps
from ethos.adapters.store.state import active_leases
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
    entries = cast("list[dict[str, str]]", dirty_provenance(root)["entries"])
    return tuple(item["path"] for item in entries)


def dirty_provenance(root: Path) -> dict[str, object]:
    """Structured local dirty-state provenance from Git porcelain v1.

    The old status payload only exposed path strings. Closeout repair needs the
    reason a path is dirty: tracked edit vs deletion vs untracked residue vs index
    conflict. Keep this Git-native and lightweight so it can run inside status,
    hooks, and failed-mutation diagnostics without a second state store.
    """
    try:
        output = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    except subprocess.CalledProcessError as exc:
        return {
            "dirty": True,
            "state": "unavailable",
            "entries": [],
            "summary": {
                "tracked": 0,
                "untracked": 0,
                "deleted": 0,
                "conflicted": 0,
                "unavailable": 1,
            },
            "error": (exc.stderr or str(exc)).strip(),
        }
    entries = [_dirty_entry(line) for line in output.splitlines() if line]
    summary = {
        "tracked": sum(1 for entry in entries if entry["kind"] == "tracked"),
        "untracked": sum(1 for entry in entries if entry["kind"] == "untracked"),
        "deleted": sum(1 for entry in entries if entry["kind"] == "deleted"),
        "conflicted": sum(1 for entry in entries if entry["kind"] == "conflicted"),
        "unavailable": 0,
    }
    return {
        "dirty": bool(entries),
        "state": "dirty" if entries else "clean",
        "entries": entries,
        "summary": summary,
    }


def _dirty_entry(line: str) -> dict[str, str]:
    index = line[0] if line else " "
    worktree = line[1] if len(line) > 1 else " "
    raw_path = line[3:] if len(line) > 3 and line[2] == " " else line[2:].strip()
    path = _porcelain_path(raw_path)
    return {
        "path": path,
        "index": index,
        "worktree": worktree,
        "kind": _dirty_kind(index, worktree),
    }


def _porcelain_path(raw: str) -> str:
    # Git rename/copy porcelain uses "old -> new". The new path is what closeout
    # commands need to clean or stage.
    if " -> " in raw:
        return raw.rsplit(" -> ", 1)[1].strip('"')
    return raw.strip('"')


def _dirty_kind(index: str, worktree: str) -> str:
    if index == "?" and worktree == "?":
        return "untracked"
    if "U" in {index, worktree} or (index, worktree) in {("A", "A"), ("D", "D")}:
        return "conflicted"
    if index == "D" or worktree == "D":
        return "deleted"
    return "tracked"


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
    current_scope, current_scope_state = branch_path_scope(
        repo, branch=branch, candidate_branch=policy.candidate_branch
    )
    foreign = _foreign_work_lanes(
        worktrees,
        current_path=current_path,
        current_role=role,
        current_path_scope=current_scope,
        current_scope_state=current_scope_state,
        candidate_branch=policy.candidate_branch,
        lease_by_branch=lease_by_branch,
        root=repo,
    )
    coordination_required_gaps, coordination_advisory_gaps = _scope_coordination_gaps(
        foreign, current_role=role, current_scope_state=current_scope_state
    )
    unbound_work_lane_count = _unbound_work_lane_count(branch_bindings)
    if unbound_work_lane_count:
        coordination_advisory_gaps.append("unbound_work_lane_ref_present")
    coordination_gaps = coordination_required_gaps + coordination_advisory_gaps
    coordination = coordination_package(
        foreign,
        required_gaps=coordination_required_gaps,
        advisory_gaps=coordination_advisory_gaps,
        unbound_work_lane_count=unbound_work_lane_count,
    )
    closeout_support = _closeout_support(
        branch=branch,
        role=role,
        dirty=bool(paths),
        candidate=candidate,
        lease_by_branch=lease_by_branch,
        coordination_required_gaps=coordination_required_gaps,
    )
    closeout_gaps = cast("list[str]", closeout_support["required_gaps"])
    required_gaps = workspace_required_gaps(closeout_gaps, candidate=candidate)
    return {
        "root": str(root),
        "branch": branch,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "dirty_provenance": provenance,
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
    current_role: str,
    current_path_scope: tuple[str, ...],
    current_scope_state: str,
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
                claim_id=_lease_claim_id(lease),
                dirty_paths=changed_paths(Path(str(worktree["path"]))),
            )
        )
    return foreign


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


def _unbound_work_lane_count(branch_bindings: list[dict[str, str]]) -> int:
    return sum(
        1
        for binding in branch_bindings
        if binding["role"] == ROLE_WORK_LANE and binding["worktree_binding"] == "unbound"
    )


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
        if changed_paths(candidate_path):
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

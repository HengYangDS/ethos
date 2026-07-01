from __future__ import annotations

import subprocess
from pathlib import Path

from ethos_adapters.state import active_leases

CANDIDATE_BRANCH = "candidate/dev"


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
    output = _run_git(root, "status", "--porcelain")
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
    role = _role_for_branch(branch)
    worktrees = _worktrees(root, current_path=current_path)
    candidate = _candidate_status(root, worktrees)
    branch_actions = _branch_actions(worktrees, candidate)
    owner_by_branch = _lease_owners(worktrees, current_path=current_path)
    closeout_support = _closeout_support(
        branch=branch,
        role=role,
        dirty=bool(paths),
        candidate=candidate,
        owner_by_branch=owner_by_branch,
    )
    foreign = _foreign_work_lanes(
        worktrees,
        current_path=current_path,
        owner_by_branch=owner_by_branch,
    )
    coordination_gaps = _coordination_gaps(foreign)
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
        "candidate": candidate,
        "worktrees": worktrees,
        "branch_actions": branch_actions,
        "foreign_work_lanes": foreign,
        "coordination_gaps": coordination_gaps,
        "closeout_support": closeout_support,
        "required_gaps": required_gaps,
    }


def _non_git_status(root: Path) -> dict[str, object]:
    candidate = {
        "branch": CANDIDATE_BRANCH,
        "exists": False,
        "head": "",
        "worktree_exists": False,
        "worktree_path": "",
        "open_action": "bootstrap_worktree",
        "open_label": "Bootstrap Worktree",
    }
    return {
        "root": str(root),
        "branch": "untracked",
        "dirty": False,
        "changed_paths": [],
        "role": "other",
        "candidate": candidate,
        "worktrees": [],
        "branch_actions": [
            {
                "branch": CANDIDATE_BRANCH,
                "role": "candidate",
                "head": "",
                "path": "",
                "action": "bootstrap_worktree",
                "label": "Bootstrap Worktree",
            }
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": CANDIDATE_BRANCH,
            "target_path": "",
            "action": "not_supported",
            "label": "Not Supported",
            "owner": "",
            "required_gaps": ["protected_root_mutation", "git_repository_missing"],
        },
        "required_gaps": ["git_repository_missing", "candidate_branch_missing"],
    }


def _worktrees(root: Path, *, current_path: Path) -> list[dict[str, str]]:
    output = _run_git(root, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                entries.append(_normalize_worktree(current, current_path=current_path))
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        entries.append(_normalize_worktree(current, current_path=current_path))
    return entries


def _normalize_worktree(entry: dict[str, str], *, current_path: Path) -> dict[str, str]:
    branch = entry.get("branch", "")
    if branch.startswith("refs/heads/"):
        branch = branch.removeprefix("refs/heads/")
    path = entry.get("worktree", "")
    action, label = _worktree_action(path, current_path=current_path)
    return {
        "path": path,
        "head": entry.get("HEAD", ""),
        "branch": branch or "detached",
        "role": _role_for_branch(branch),
        "open_action": action,
        "open_label": label,
    }


def _foreign_work_lanes(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
    owner_by_branch: dict[str, str],
) -> list[dict[str, str]]:
    foreign: list[dict[str, str]] = []
    for worktree in worktrees:
        if worktree["role"] != "work_lane":
            continue
        if Path(str(worktree["path"])).resolve() == current_path:
            continue
        branch = str(worktree["branch"])
        owner = owner_by_branch.get(branch, "")
        foreign.append(
            {
                "path": worktree["path"],
                "head": worktree["head"],
                "branch": branch,
                "role": worktree["role"],
                "open_action": worktree["open_action"],
                "open_label": worktree["open_label"],
                "lease_owner": owner,
                "lease_state": "leased" if owner else "missing",
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


def _candidate_status(
    root: Path,
    worktrees: list[dict[str, str]],
) -> dict[str, object]:
    head = _ref_head(root, CANDIDATE_BRANCH)
    worktree_path = ""
    open_action = "bootstrap_worktree"
    open_label = "Bootstrap Worktree"
    for worktree in worktrees:
        if worktree["branch"] == CANDIDATE_BRANCH:
            worktree_path = worktree["path"]
            open_action = worktree["open_action"]
            open_label = worktree["open_label"]
            break
    if head and not worktree_path:
        open_action = "create_worktree"
        open_label = "Create Worktree"
    return {
        "branch": CANDIDATE_BRANCH,
        "exists": bool(head),
        "head": head,
        "worktree_exists": bool(worktree_path),
        "worktree_path": worktree_path,
        "open_action": open_action,
        "open_label": open_label,
    }


def _branch_actions(
    worktrees: list[dict[str, str]],
    candidate: dict[str, object],
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    seen: set[str] = set()
    for worktree in worktrees:
        branch = str(worktree["branch"])
        if branch == "detached":
            continue
        actions.append(
            {
                "branch": branch,
                "role": str(worktree["role"]),
                "head": str(worktree["head"]),
                "path": str(worktree["path"]),
                "action": str(worktree["open_action"]),
                "label": str(worktree["open_label"]),
            }
        )
        seen.add(branch)
    if CANDIDATE_BRANCH not in seen:
        actions.append(
            {
                "branch": CANDIDATE_BRANCH,
                "role": "candidate",
                "head": str(candidate["head"]),
                "path": str(candidate["worktree_path"]),
                "action": str(candidate["open_action"]),
                "label": str(candidate["open_label"]),
            }
        )
    return actions


def _worktree_action(path: str, *, current_path: Path) -> tuple[str, str]:
    if path and Path(path).resolve() == current_path:
        return "current_worktree", "Current Worktree"
    return "open_worktree", "Open Worktree"


def _lease_owners(
    worktrees: list[dict[str, str]],
    *,
    current_path: Path,
) -> dict[str, str]:
    control_root = current_path
    for worktree in worktrees:
        if worktree["role"] == "accepted_root" and worktree["path"]:
            control_root = Path(worktree["path"])
            break
    leases = active_leases(control_root / ".ethos" / "state" / "state.sqlite")
    return {str(lease["subject"]): str(lease["owner"]) for lease in leases}


def _closeout_support(
    *,
    branch: str,
    role: str,
    dirty: bool,
    candidate: dict[str, object],
    owner_by_branch: dict[str, str],
) -> dict[str, object]:
    gaps: list[str] = []
    if role != "work_lane":
        gaps.append("protected_root_mutation")
    elif dirty:
        gaps.append("work_lane_dirty")
    elif not owner_by_branch.get(branch):
        gaps.append(f"work_lane_missing_lease:{branch}")
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    else:
        candidate_path = Path(str(candidate["worktree_path"]))
        if changed_paths(candidate_path):
            gaps.append("candidate_worktree_dirty")

    is_work_lane = role == "work_lane"
    return {
        "supported": not gaps,
        "branch": branch if is_work_lane else "",
        "target_branch": CANDIDATE_BRANCH,
        "target_path": str(candidate["worktree_path"]),
        "action": "land_to_candidate" if is_work_lane else "not_supported",
        "label": "Land to Candidate" if is_work_lane else "Not Supported",
        "owner": owner_by_branch.get(branch, "") if is_work_lane else "",
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


def _role_for_branch(branch: str) -> str:
    if branch.startswith("work/"):
        return "work_lane"
    if branch == CANDIDATE_BRANCH:
        return "candidate"
    if branch.startswith("submit/"):
        return "submit"
    if branch == "detached":
        return "detached"
    if branch in {"dev", "main"}:
        return "accepted_root"
    return "other"

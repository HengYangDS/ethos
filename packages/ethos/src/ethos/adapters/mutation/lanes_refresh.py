from __future__ import annotations

from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lanes_retire import _default_candidate_path
from ethos.adapters.mutation.lanes_retire import _git
from ethos.adapters.mutation.lanes_retire import _is_ancestor
from ethos.adapters.mutation.lanes_retire import _repo_root
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status import workspace_status
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or _default_candidate_path(repo, policy.candidate_branch)).resolve()
    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        gaps.append("candidate_bootstrap_requires_clean_accepted_root")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": gaps,
        }
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        return {
            "ok": True,
            "state": "present",
            "branch": policy.candidate_branch,
            "head": candidate["head"],
            "path": candidate["worktree_path"],
            "required_gaps": [],
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": [],
        }
    if target.exists():
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_path_exists"],
        }
    if not candidate["exists"]:
        completed = _git(repo, "branch", policy.candidate_branch, current_head, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "state": "blocked",
                "branch": policy.candidate_branch,
                "head": current_head,
                "path": target.as_posix(),
                "required_gaps": ["candidate_bootstrap_failed"],
                "stderr": completed.stderr.strip(),
            }
    completed = _git(
        repo,
        "worktree",
        "add",
        target.as_posix(),
        policy.candidate_branch,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_add_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "bootstrapped",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": target.as_posix(),
        "required_gaps": [],
    }


def _apply_gaps(
    *, apply: bool, authorized: bool, expect_head: str | None, current_head: str
) -> list[str]:
    gaps: list[str] = []
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and expect_head is None:
        gaps.append("expect_head_required")
    elif apply and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return gaps


def _candidate_worktree_gaps(candidate: dict[str, object], candidate_path: str) -> list[str]:
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    if changed_paths(Path(candidate_path)):
        return ["candidate_worktree_dirty"]
    return []


def _candidate_report(context: dict[str, object], *, stderr: str = "") -> dict[str, object]:
    report = {
        "ok": context["ok"],
        "state": context["state"],
        "branch": context["branch"],
        "head": context["head"],
        "previous_head": context["previous_head"],
        "path": context["path"],
        "required_gaps": context["required_gaps"],
    }
    if stderr:
        report["stderr"] = stderr
    return report


def _work_base_report(context: dict[str, object], *, stderr: str = "") -> dict[str, object]:
    report = {
        "ok": context["ok"],
        "state": context["state"],
        "branch": context["branch"],
        "head": context["head"],
        "candidate_branch": context["candidate_branch"],
        "candidate_head": context["candidate_head"],
        "candidate_path": context["candidate_path"],
        "required_gaps": context["required_gaps"],
    }
    previous_head = str(context.get("previous_head") or "")
    if previous_head:
        report["previous_head"] = previous_head
    if stderr:
        report["stderr"] = stderr
    return report


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path))
    gaps.extend(
        _apply_gaps(
            apply=apply, authorized=authorized, expect_head=expect_head, current_head=current_head
        )
    )
    if gaps:
        return _candidate_report(
            {
                "ok": False,
                "state": "blocked",
                "branch": policy.candidate_branch,
                "head": current_head,
                "previous_head": candidate_head,
                "path": candidate_path,
                "required_gaps": gaps,
            }
        )
    if candidate_head == current_head:
        return _candidate_report(
            {
                "ok": True,
                "state": "base_current",
                "branch": policy.candidate_branch,
                "head": current_head,
                "previous_head": candidate_head,
                "path": candidate_path,
                "required_gaps": [],
            }
        )
    if not apply:
        return _candidate_report(
            {
                "ok": True,
                "state": "ready_to_refresh_from_accepted",
                "branch": policy.candidate_branch,
                "head": current_head,
                "previous_head": candidate_head,
                "path": candidate_path,
                "required_gaps": [],
            }
        )
    completed = _git(Path(candidate_path), "reset", "--hard", current_head, check=False)
    if completed.returncode != 0:
        return _candidate_report(
            {
                "ok": False,
                "state": "blocked",
                "branch": policy.candidate_branch,
                "head": current_head,
                "previous_head": candidate_head,
                "path": candidate_path,
                "required_gaps": ["candidate_refresh_from_accepted_failed"],
            },
            stderr=completed.stderr.strip(),
        )
    return _candidate_report(
        {
            "ok": True,
            "state": "refreshed_from_accepted",
            "branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": candidate_head,
            "path": candidate_path,
            "required_gaps": [],
        }
    )


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    status = workspace_status(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path))
    gaps.extend(
        _apply_gaps(
            apply=apply, authorized=authorized, expect_head=expect_head, current_head=current_head
        )
    )
    if gaps:
        return _work_base_report(
            {
                "ok": False,
                "state": "blocked",
                "branch": branch,
                "head": current_head,
                "candidate_branch": policy.candidate_branch,
                "candidate_head": candidate_head,
                "candidate_path": candidate_path,
                "required_gaps": gaps,
            }
        )
    if _is_ancestor(root, candidate_head, current_head):
        return _work_base_report(
            {
                "ok": True,
                "state": "base_current",
                "branch": branch,
                "head": current_head,
                "candidate_branch": policy.candidate_branch,
                "candidate_head": candidate_head,
                "candidate_path": candidate_path,
                "required_gaps": [],
            }
        )
    if not apply:
        return _work_base_report(
            {
                "ok": True,
                "state": "ready_to_refresh_base",
                "branch": branch,
                "head": current_head,
                "candidate_branch": policy.candidate_branch,
                "candidate_head": candidate_head,
                "candidate_path": candidate_path,
                "required_gaps": [],
            }
        )
    completed = _git(root, "rebase", policy.candidate_branch, check=False)
    if completed.returncode != 0:
        _git(root, "rebase", "--abort", check=False)
        return _work_base_report(
            {
                "ok": False,
                "state": "blocked",
                "branch": branch,
                "head": current_head,
                "candidate_branch": policy.candidate_branch,
                "candidate_head": candidate_head,
                "candidate_path": candidate_path,
                "required_gaps": ["refresh_base_failed"],
            },
            stderr=completed.stderr.strip(),
        )
    refreshed_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    return _work_base_report(
        {
            "ok": True,
            "state": "base_refreshed",
            "branch": branch,
            "previous_head": current_head,
            "head": refreshed_head,
            "candidate_branch": policy.candidate_branch,
            "candidate_head": candidate_head,
            "candidate_path": candidate_path,
            "required_gaps": [],
        }
    )

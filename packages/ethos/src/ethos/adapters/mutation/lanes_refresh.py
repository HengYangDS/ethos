from __future__ import annotations

from pathlib import Path
from typing import TypedDict
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy

PARITY_EVIDENCE_ROOT = Path("evidence/parity")
PARITY_SHADOW_SUFFIX = "-shadow.json"


class _ProjectionResolution(TypedDict):
    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]


def _projection_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> _ProjectionResolution:
    return {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": next_actions or [],
    }


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or default_candidate_path(repo, policy.candidate_branch)).resolve()
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
        completed = run_git(repo, "branch", policy.candidate_branch, current_head, check=False)
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
    completed = run_git(
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
    for key in (
        "projection_refresh_required",
        "projection_refresh_gaps",
        "stale_projection_paths",
        "next_actions",
    ):
        if key in context:
            report[key] = context[key]
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
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
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
    completed = run_git(Path(candidate_path), "reset", "--hard", current_head, check=False)
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


def _resolve_projection_only_rebase_conflict(root: Path) -> _ProjectionResolution:
    paths = _unmerged_paths(root)
    adopters = [_parity_adopter(path) for path in paths]
    result = _projection_resolution(ok=False)
    if paths and all(adopters):
        checkout = run_git(root, "checkout", "--ours", "--", *paths, check=False)
        if checkout.returncode != 0:
            result = _projection_resolution(ok=False, paths=paths)
        else:
            added = run_git(root, "add", *paths, check=False)
            if added.returncode != 0:
                result = _projection_resolution(ok=False, paths=paths)
            else:
                result = _projection_resolution(
                    ok=True,
                    paths=paths,
                    gaps=[
                        f"projection_regeneration_required:parity:{adopter}" for adopter in adopters
                    ],
                    next_actions=[
                        (
                            "ethos parity shadow --adopter "
                            f"{adopter} --target . --execute --write-evidence --json"
                        )
                        for adopter in adopters
                    ],
                )
    return result


def _unmerged_paths(root: Path) -> list[str]:
    completed = run_git(root, "diff", "--name-only", "--diff-filter=U", check=False)
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _parity_adopter(path: str) -> str:
    candidate = Path(path)
    if candidate.parent != PARITY_EVIDENCE_ROOT or not candidate.name.endswith(
        PARITY_SHADOW_SUFFIX
    ):
        return ""
    adopter = candidate.name[: -len(PARITY_SHADOW_SUFFIX)]
    return adopter or ""


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    status = workspace_status(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
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
    if is_ancestor(root, candidate_head, current_head):
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
    completed = run_git(root, "rebase", policy.candidate_branch, check=False)
    projection_resolution = _resolve_projection_only_rebase_conflict(root)
    if completed.returncode != 0 and projection_resolution["ok"]:
        continued = run_git(root, "-c", "core.editor=true", "rebase", "--continue", check=False)
        if continued.returncode == 0:
            refreshed_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
            return _work_base_report(
                {
                    "ok": True,
                    "state": "base_refreshed_projection_stale",
                    "branch": branch,
                    "previous_head": current_head,
                    "head": refreshed_head,
                    "candidate_branch": policy.candidate_branch,
                    "candidate_head": candidate_head,
                    "candidate_path": candidate_path,
                    "required_gaps": [],
                    "projection_refresh_required": True,
                    "projection_refresh_gaps": projection_resolution["gaps"],
                    "stale_projection_paths": projection_resolution["paths"],
                    "next_actions": projection_resolution["next_actions"]
                    + ["ethos prove --execute --expect-head $(git rev-parse HEAD) --json"],
                }
            )
    if completed.returncode != 0:
        run_git(root, "rebase", "--abort", check=False)
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
    refreshed_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
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

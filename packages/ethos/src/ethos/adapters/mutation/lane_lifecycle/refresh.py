from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable

PARITY_EVIDENCE_ROOT = Path("evidence/parity")
PARITY_SHADOW_SUFFIX = "-shadow.json"
MAX_PROJECTION_REBASE_STEPS = 64


def _repo_root_adapter(root: Path) -> Path:
    return repo_root(root)


def _candidate_path_adapter(repo: Path, branch: str) -> Path:
    return default_candidate_path(repo, branch)


def _branch_role_policy_adapter(root: Path) -> Any:
    return load_branch_role_policy(root)


def _workspace_status_adapter(root: Path) -> dict[str, object]:
    return workspace_status(root)


def _changed_paths_adapter(root: Path) -> list[str]:
    return changed_paths(root)


def _is_ancestor_adapter(root: Path, ancestor: str, descendant: str) -> bool:
    return is_ancestor(root, ancestor, descendant)


def _run_git_adapter(root: Path, *args: str, check: bool = True) -> Any:
    return run_git(root, *args, check=check)


@dataclass(frozen=True)
class LaneRefreshRuntime:
    """Explicit dependencies used for candidate and Work Lane base refresh."""

    repo_root: Callable[[Path], Path] = _repo_root_adapter
    default_candidate_path: Callable[[Path, str], Path] = _candidate_path_adapter
    load_branch_role_policy: Callable[[Path], Any] = _branch_role_policy_adapter
    workspace_status: Callable[[Path], dict[str, object]] = _workspace_status_adapter
    changed_paths: Callable[[Path], list[str]] = _changed_paths_adapter
    is_ancestor: Callable[[Path, str, str], bool] = _is_ancestor_adapter
    run_git: Callable[..., Any] = _run_git_adapter


class _ProjectionResolution(TypedDict):
    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]


class _ProjectionRebaseResolution(TypedDict):
    ok: bool
    paths: list[str]
    gaps: list[str]
    next_actions: list[str]
    stderr: str


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


def _projection_rebase_resolution(
    *,
    ok: bool,
    paths: list[str] | None = None,
    gaps: list[str] | None = None,
    next_actions: list[str] | None = None,
    stderr: str = "",
) -> _ProjectionRebaseResolution:
    return {
        "ok": ok,
        "paths": paths or [],
        "gaps": gaps or [],
        "next_actions": next_actions or [],
        "stderr": stderr,
    }


def _append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime()
    repo = active_runtime.repo_root(root)
    policy = active_runtime.load_branch_role_policy(repo)
    status = active_runtime.workspace_status(repo)
    current_head = active_runtime.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (
        path or active_runtime.default_candidate_path(repo, policy.candidate_branch)
    ).resolve()
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
        completed = active_runtime.run_git(
            repo, "branch", policy.candidate_branch, current_head, check=False
        )
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
    completed = active_runtime.run_git(
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


def _candidate_worktree_gaps(
    candidate: dict[str, object],
    candidate_path: str,
    *,
    runtime: LaneRefreshRuntime | None = None,
) -> list[str]:
    active_runtime = runtime or LaneRefreshRuntime()
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    if active_runtime.changed_paths(Path(candidate_path)):
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
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime()
    repo = active_runtime.repo_root(root)
    policy = active_runtime.load_branch_role_policy(repo)
    status = active_runtime.workspace_status(repo)
    current_head = active_runtime.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path, runtime=active_runtime))
    gaps.extend(
        _apply_gaps(
            apply=apply,
            authorized=authorized,
            expect_head=expect_head,
            current_head=current_head,
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
    completed = active_runtime.run_git(
        Path(candidate_path), "reset", "--hard", current_head, check=False
    )
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


def _resolve_projection_only_rebase_conflict(
    root: Path,
    *,
    runtime: LaneRefreshRuntime | None = None,
) -> _ProjectionResolution:
    active_runtime = runtime or LaneRefreshRuntime()
    paths = _unmerged_paths(root, runtime=active_runtime)
    adopters = [_parity_adopter(path) for path in paths]
    result = _projection_resolution(ok=False)
    if paths and all(adopters):
        checkout = active_runtime.run_git(root, "checkout", "--ours", "--", *paths, check=False)
        if checkout.returncode != 0:
            result = _projection_resolution(ok=False, paths=paths)
        else:
            added = active_runtime.run_git(root, "add", *paths, check=False)
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


def _unmerged_paths(
    root: Path,
    *,
    runtime: LaneRefreshRuntime | None = None,
) -> list[str]:
    active_runtime = runtime or LaneRefreshRuntime()
    completed = active_runtime.run_git(root, "diff", "--name-only", "--diff-filter=U", check=False)
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


def _empty_projection_patch(stderr: str) -> bool:
    lowered = stderr.lower()
    return (
        "no changes" in lowered
        or "nothing to commit" in lowered
        or "patch is empty" in lowered
        or "previous cherry-pick is now empty" in lowered
    )


def _resolve_projection_rebase(
    root: Path,
    initial: object,
    *,
    runtime: LaneRefreshRuntime | None = None,
) -> _ProjectionRebaseResolution:
    active_runtime = runtime or LaneRefreshRuntime()
    paths: list[str] = []
    gaps: list[str] = []
    next_actions: list[str] = []
    completed = initial
    for _ in range(MAX_PROJECTION_REBASE_STEPS):
        if getattr(completed, "returncode", 1) == 0:
            return _projection_rebase_resolution(
                ok=bool(paths),
                paths=paths,
                gaps=gaps,
                next_actions=next_actions,
                stderr="",
            )
        projection_resolution = _resolve_projection_only_rebase_conflict(
            root, runtime=active_runtime
        )
        if projection_resolution["ok"]:
            _append_unique(paths, projection_resolution["paths"])
            _append_unique(gaps, projection_resolution["gaps"])
            _append_unique(next_actions, projection_resolution["next_actions"])
            completed = active_runtime.run_git(
                root, "-c", "core.editor=true", "rebase", "--continue", check=False
            )
            continue
        if paths and _empty_projection_patch(str(getattr(completed, "stderr", ""))):
            completed = active_runtime.run_git(root, "rebase", "--skip", check=False)
            continue
        return _projection_rebase_resolution(
            ok=False,
            paths=paths,
            gaps=gaps,
            next_actions=next_actions,
            stderr=str(getattr(completed, "stderr", "")),
        )
    return _projection_rebase_resolution(
        ok=False,
        paths=paths,
        gaps=gaps,
        next_actions=next_actions,
        stderr="projection rebase recovery exceeded bounded step limit",
    )


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime()
    policy = active_runtime.load_branch_role_policy(root)
    status = active_runtime.workspace_status(root)
    current_head = active_runtime.run_git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    gaps.extend(_candidate_worktree_gaps(candidate, candidate_path, runtime=active_runtime))
    gaps.extend(
        _apply_gaps(
            apply=apply,
            authorized=authorized,
            expect_head=expect_head,
            current_head=current_head,
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
    if active_runtime.is_ancestor(root, candidate_head, current_head):
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
    completed = active_runtime.run_git(root, "rebase", policy.candidate_branch, check=False)
    projection_resolution = _resolve_projection_rebase(root, completed, runtime=active_runtime)
    if completed.returncode != 0 and projection_resolution["ok"]:
        refreshed_head = active_runtime.run_git(root, "rev-parse", "HEAD").stdout.strip()
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
        active_runtime.run_git(root, "rebase", "--abort", check=False)
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
    refreshed_head = active_runtime.run_git(root, "rev-parse", "HEAD").stdout.strip()
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

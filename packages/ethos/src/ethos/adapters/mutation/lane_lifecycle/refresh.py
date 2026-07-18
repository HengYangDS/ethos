from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.projection_rebase.core import resolve_projection_rebase
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class LaneRefreshRuntime:
    """Explicit dependencies used for candidate and Work Lane base refresh."""

    repo_root: Callable[..., Any] = repo_root
    default_candidate_path: Callable[..., Any] = default_candidate_path
    load_branch_role_policy: Callable[..., Any] = load_branch_role_policy
    workspace_status: Callable[..., Any] = workspace_status
    changed_paths: Callable[..., Any] = changed_paths
    is_ancestor: Callable[..., Any] = is_ancestor
    run_git: Callable[..., Any] = run_git


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

    def report(*, ok: bool, state: str, gaps: list[str], **details: object) -> dict[str, object]:
        return _refresh_report(
            ok=ok,
            state=state,
            branch=policy.candidate_branch,
            head=current_head,
            gaps=gaps,
            **details,
        )

    details = {"path": target.as_posix()}
    gaps = [
        gap
        for gap, present in (
            (
                "candidate_bootstrap_requires_clean_accepted_root",
                status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"],
            ),
            ("expect_head_mismatch", expect_head is not None and expect_head != current_head),
        )
        if present
    ]
    if gaps:
        return report(ok=False, state="blocked", gaps=gaps, **details)
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        return report(ok=True, state="present", gaps=[], path=str(candidate["worktree_path"]))
    if not apply:
        return report(ok=True, state="planned", gaps=[], **details)
    if target.exists():
        return report(ok=False, state="blocked", gaps=["candidate_worktree_path_exists"], **details)
    if not candidate["exists"]:
        completed = active_runtime.run_git(
            repo, "branch", policy.candidate_branch, current_head, check=False
        )
        if completed.returncode != 0:
            return report(
                ok=False,
                state="blocked",
                gaps=["candidate_bootstrap_failed"],
                stderr=completed.stderr.strip(),
                **details,
            )
    completed = active_runtime.run_git(
        repo, "worktree", "add", target.as_posix(), policy.candidate_branch, check=False
    )
    failed = completed.returncode != 0
    return report(
        ok=not failed,
        state="blocked" if failed else "bootstrapped",
        gaps=["candidate_worktree_add_failed"] if failed else [],
        stderr=completed.stderr.strip() if failed else "",
        **details,
    )


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
    return (
        ["candidate_worktree_dirty"] if active_runtime.changed_paths(Path(candidate_path)) else []
    )


def _refresh_report(
    *,
    ok: bool,
    state: str,
    branch: str,
    head: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "ok": ok,
            "state": state,
            "branch": branch,
            "head": head,
            "required_gaps": gaps,
            **details,
        }.items()
        if value not in ("", None)
    }


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    runtime: LaneRefreshRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LaneRefreshRuntime(run_git=run_git)
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
        return _refresh_report(
            ok=False,
            state="blocked",
            branch=policy.candidate_branch,
            head=current_head,
            gaps=gaps,
            previous_head=candidate_head,
            path=candidate_path,
        )
    if candidate_head == current_head:
        return _refresh_report(
            ok=True,
            state="base_current",
            branch=policy.candidate_branch,
            head=current_head,
            gaps=[],
            previous_head=candidate_head,
            path=candidate_path,
        )
    if not apply:
        return _refresh_report(
            ok=True,
            state="ready_to_refresh_from_accepted",
            branch=policy.candidate_branch,
            head=current_head,
            gaps=[],
            previous_head=candidate_head,
            path=candidate_path,
        )
    # Rewind candidate/dev onto the accepted head. This target is already contained in the
    # accepted branch, so the reference-transaction hook's candidate admission admits it
    # without a fresh proof (see _contained_in_accepted); no ref-move escape is needed now
    # that the ETHOS_ALLOW_REF_MOVE bypass has been removed from the candidate train.
    completed = active_runtime.run_git(
        Path(candidate_path),
        "reset",
        "--hard",
        current_head,
        check=False,
    )
    if completed.returncode != 0:
        return _refresh_report(
            ok=False,
            state="blocked",
            branch=policy.candidate_branch,
            head=current_head,
            gaps=["candidate_refresh_from_accepted_failed"],
            previous_head=candidate_head,
            path=candidate_path,
            stderr=completed.stderr.strip(),
        )
    return _refresh_report(
        ok=True,
        state="refreshed_from_accepted",
        branch=policy.candidate_branch,
        head=current_head,
        gaps=[],
        previous_head=candidate_head,
        path=candidate_path,
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
        return _refresh_report(
            ok=False,
            state="blocked",
            branch=branch,
            head=current_head,
            gaps=gaps,
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
        )
    if active_runtime.is_ancestor(root, candidate_head, current_head):
        return _refresh_report(
            ok=True,
            state="base_current",
            branch=branch,
            head=current_head,
            gaps=[],
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
        )
    if not apply:
        return _refresh_report(
            ok=True,
            state="ready_to_refresh_base",
            branch=branch,
            head=current_head,
            gaps=[],
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
        )
    completed = active_runtime.run_git(
        root,
        "-c",
        "rebase.updateRefs=false",
        "rebase",
        policy.candidate_branch,
        check=False,
    )
    projection_resolution = resolve_projection_rebase(root, completed, runtime=active_runtime)
    projection_recovered = completed.returncode != 0 and projection_resolution["ok"]
    if completed.returncode != 0 and not projection_recovered:
        active_runtime.run_git(root, "rebase", "--abort", check=False)
        return _refresh_report(
            ok=False,
            state="blocked",
            branch=branch,
            head=current_head,
            gaps=["refresh_base_failed"],
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
            stderr=completed.stderr.strip(),
        )
    refreshed_head = active_runtime.run_git(root, "rev-parse", "HEAD").stdout.strip()
    if not active_runtime.is_ancestor(root, candidate_head, refreshed_head):
        return _refresh_report(
            ok=False,
            state="blocked",
            branch=branch,
            head=refreshed_head,
            gaps=["refresh_base_postcondition_failed"],
            previous_head=current_head,
            candidate_branch=policy.candidate_branch,
            candidate_head=candidate_head,
            candidate_path=candidate_path,
            next_actions=[
                "inspect current Git ancestry and runner, signing, or hook diagnostics",
                "repair the replay environment and rerun ethos lane refresh-base",
            ],
            stderr="candidate head is not an ancestor of refreshed work-lane head",
        )
    report = _refresh_report(
        ok=True,
        state="base_refreshed",
        branch=branch,
        head=refreshed_head,
        gaps=[],
        previous_head=current_head,
        candidate_branch=policy.candidate_branch,
        candidate_head=candidate_head,
        candidate_path=candidate_path,
    )
    if projection_recovered:
        semantic = "semantic_ledger_merged:source_budget_debt" in projection_resolution["gaps"]
        report.update(
            {
                "state": "base_refreshed" if semantic else "base_refreshed_projection_stale",
                "projection_refresh_required": not semantic,
                "projection_refresh_gaps": projection_resolution["gaps"],
                "stale_projection_paths": projection_resolution["paths"],
                "next_actions": projection_resolution["next_actions"]
                + ["ethos prove --execute --expect-head $(git rev-parse HEAD) --json"],
            }
        )
    return report

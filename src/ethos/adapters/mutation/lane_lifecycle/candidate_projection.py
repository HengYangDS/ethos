"""Create and synchronize the local candidate branch projection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.start import default_worktree_path
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan


def _report(
    branch: str, head: str, state: str, gaps: list[str], **details: object
) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "verdict": "block" if gaps else "pass",
            "state": state,
            "branch": branch,
            "head": head,
            "required_gaps": gaps,
            **details,
        }.items()
        if value not in ("", None)
    }


def _candidate_plan(
    *,
    root: Path,
    accepted_branch: str,
    candidate_branch: str,
    expected: str,
    desired: str,
    operation: str,
) -> TransitionPlan:
    effect = GitEffect(
        updates={
            f"refs/heads/{candidate_branch}": GitRefUpdate(expected=expected, desired=desired)
        },
        assertions={f"refs/heads/{accepted_branch}": desired},
    )
    return compile_observed_git_effect(
        root,
        None,
        effect,
        head=desired,
        prior_attestations={},
        policy={"operation": operation, "subject": candidate_branch},
    )


def _recovery_plan(root: Path, accepted: str, candidate: str, desired: str, operation: str):
    return recover_plan(
        root=root,
        ref_name=f"refs/heads/{candidate}",
        operation=operation,
        desired=desired,
        assertions={f"refs/heads/{accepted}": desired},
    )


def _add_candidate_worktree(root: Path, path: Path, branch: str) -> None:
    head = run_git(root, "rev-parse", branch).stdout.strip()
    add_worktree(root, path, branch=branch, head=head)
    install_hook_launchers(path)


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    target = (path or default_worktree_path(repo, policy.candidate_branch)).resolve()
    details = {"path": target.as_posix()}
    gap = (
        "candidate_bootstrap_requires_clean_accepted_root"
        if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]
        else "expect_head_mismatch"
        if expect_head is not None and expect_head != head
        else ""
    )
    if gap:
        return _report(policy.candidate_branch, head, "blocked", [gap], **details)
    candidate = cast("dict[str, object]", status["candidate"])
    if candidate["exists"] and candidate["worktree_exists"]:
        gaps: list[str] = []
        try:
            plan = _recovery_plan(
                repo, policy.accepted_branch, policy.candidate_branch, head, "candidate.bootstrap"
            )
            if plan is not None:
                execute_git_effect(repo, plan, issuer=issuer)
            install_hook_launchers(Path(str(candidate["worktree_path"])))
        except ValueError as error:
            gaps.append(str(error))
        return _report(
            policy.candidate_branch,
            head,
            "blocked" if gaps else "present",
            gaps,
            path=str(candidate["worktree_path"]),
        )
    if not apply or target.exists():
        gaps = [] if not apply else ["candidate_worktree_path_exists"]
        return _report(
            policy.candidate_branch,
            head,
            "blocked" if gaps else "planned",
            gaps,
            **details,
        )
    operation = "candidate.bootstrap"
    try:
        plan = (
            _recovery_plan(repo, policy.accepted_branch, policy.candidate_branch, head, operation)
            if candidate["exists"]
            else _candidate_plan(
                root=repo,
                accepted_branch=policy.accepted_branch,
                candidate_branch=policy.candidate_branch,
                expected="0" * len(head),
                desired=head,
                operation=operation,
            )
        )
        if plan is None:
            return _report(
                policy.candidate_branch,
                head,
                "blocked",
                ["git_effect_recovery_unproven"],
                **details,
            )
        execute_git_effect(repo, plan, issuer=issuer)
        _add_candidate_worktree(repo, target, policy.candidate_branch)
    except (OSError, ValueError) as error:
        ref = run_git(repo, "rev-parse", policy.candidate_branch, check=False)
        gap = (
            "candidate_worktree_add_failed"
            if ref.returncode == 0 and ref.stdout.strip() == head
            else "candidate_ref_creation_failed"
        )
        if str(error).startswith("git_effect_recovery_"):
            gap = str(error)
        return _report(
            policy.candidate_branch, head, "blocked", [gap], stderr=str(error), **details
        )
    return _report(policy.candidate_branch, head, "bootstrapped", [], **details)


def _sync_candidate_worktree(
    root: Path, path: Path, branch: str, ref_head: str, previous: str, desired: str
) -> None:
    paths = (path,)
    gap = worktree_sync_gap(root, paths, branch, ref_head, previous, desired)
    if gap:
        if worktree_sync_gap(root, paths, branch, ref_head, desired, desired):
            raise ValueError(gap)
        return
    result = cast(
        "list[dict[str, str]]",
        sync_ref_worktrees(root, paths, branch, desired, previous)["worktrees"],
    )[0]
    if result["state"] != "synced":
        raise ValueError(result["stderr"] or "candidate_worktree_sync_failed")


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    candidate = cast("dict[str, object]", status["candidate"])
    previous = str(candidate.get("head") or "")
    path = Path(str(candidate.get("worktree_path") or ""))
    details = {"previous_head": previous, "path": str(path)}
    gaps = [
        gap
        for gap, present in (
            ("accepted_root_required", status["role"] != ROLE_ACCEPTED_ROOT),
            ("accepted_root_dirty", status["role"] == ROLE_ACCEPTED_ROOT and status["dirty"]),
            ("candidate_branch_missing", not candidate["exists"]),
            (
                "candidate_worktree_missing",
                candidate["exists"] and not candidate["worktree_exists"],
            ),
            ("authorization_required", apply and not authorized),
            ("expect_head_required", apply and expect_head is None),
            ("expect_head_mismatch", apply and expect_head not in {None, head}),
        )
        if present
    ]
    plan = None
    if not gaps and apply and previous == head:
        try:
            plan = _recovery_plan(
                repo, policy.accepted_branch, policy.candidate_branch, head, "candidate.refresh"
            )
        except ValueError as error:
            gaps.append(str(error))
    if not gaps:
        current_gap = worktree_sync_gap(
            repo, (path,), policy.candidate_branch, previous, previous, previous
        )
        if current_gap and plan is None:
            gap = (
                "git_effect_recovery_unproven"
                if apply and previous == head and current_gap == "worktree_index_mismatch"
                else "candidate_worktree_dirty"
            )
            gaps.append(gap)
    if gaps:
        return _report(policy.candidate_branch, head, "blocked", gaps, **details)
    if previous == head and plan is None:
        return _report(policy.candidate_branch, head, "base_current", [], **details)
    if not apply:
        return _report(
            policy.candidate_branch, head, "ready_to_refresh_from_accepted", [], **details
        )
    try:
        plan = plan or _candidate_plan(
            root=repo,
            accepted_branch=policy.accepted_branch,
            candidate_branch=policy.candidate_branch,
            expected=previous,
            desired=head,
            operation="candidate.refresh",
        )
        previous = (
            git_effect_from_plan(plan).updates[f"refs/heads/{policy.candidate_branch}"].expected
        )
        execute_git_effect(repo, plan, issuer=issuer)
        _sync_candidate_worktree(repo, path, policy.candidate_branch, head, previous, head)
    except (OSError, ValueError) as error:
        message = str(error)
        gap = (
            message
            if previous == head and message.startswith(("git_effect_recovery_", "candidate_"))
            else "candidate_worktree_dirty"
            if previous == head
            else "candidate_refresh_from_accepted_failed"
        )
        return _report(policy.candidate_branch, head, "blocked", [gap], stderr=message, **details)
    return _report(policy.candidate_branch, head, "refreshed_from_accepted", [], **details)

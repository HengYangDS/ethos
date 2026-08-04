"""Refresh one clean Work Lane onto the current candidate base."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan


def _candidate_worktree_gap(candidate: dict[str, object], candidate_path: str) -> str:
    return (
        "candidate_branch_missing"
        if not candidate["exists"]
        else "candidate_worktree_missing"
        if not candidate["worktree_exists"]
        else "candidate_worktree_dirty"
        if changed_paths(Path(candidate_path))
        else ""
    )


def _report(
    context: tuple[str, str, str, str],
    head: str,
    state: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    branch, candidate_branch, candidate_head, candidate_path = context
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "branch": branch,
        "head": head,
        "required_gaps": gaps,
        "candidate_branch": candidate_branch,
        "candidate_head": candidate_head,
        "candidate_path": candidate_path,
        **details,
    }


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
    if branch == "detached" and apply:
        try:
            return _recover_work_lane(root, policy.candidate_branch, candidate_head, candidate_path)
        except ValueError as error:
            context = ("detached", policy.candidate_branch, candidate_head, candidate_path)
            return _report(context, current_head, "blocked", [str(error)])
    context = (branch, policy.candidate_branch, candidate_head, candidate_path)

    gaps = [
        gap
        for gap, present in (
            ("protected_root_mutation", status["role"] != ROLE_WORK_LANE),
            ("work_lane_dirty", status["role"] == ROLE_WORK_LANE and status["dirty"]),
        )
        if present
    ]
    if candidate_gap := _candidate_worktree_gap(candidate, candidate_path):
        gaps.append(candidate_gap)
    gaps.extend(
        gap
        for gap, present in (
            ("authorization_required", apply and not authorized),
            ("expect_head_required", apply and expect_head is None),
            ("expect_head_mismatch", apply and expect_head not in {None, current_head}),
        )
        if present
    )
    if gaps:
        return _report(context, current_head, "blocked", gaps)
    if is_ancestor(root, candidate_head, current_head):
        return _report(context, current_head, "base_current", [])
    if not apply:
        return _report(context, current_head, "ready_to_refresh_base", [])
    return _refresh_work_lane(root, context, current_head)


def _refresh_work_lane(
    root: Path,
    context: tuple[str, str, str, str],
    current_head: str,
) -> dict[str, object]:
    branch, candidate_branch, candidate_head, _candidate_path = context
    snapshot_gaps = [
        f"refresh_base_snapshot_stale:{name}"
        for name, ref, admitted in (
            ("work_lane", "HEAD", current_head),
            ("candidate", candidate_branch, candidate_head),
        )
        if (
            current_tracked_head(root)
            if ref == "HEAD"
            else run_git(root, "rev-parse", ref, check=False).stdout.strip()
        )
        != admitted
    ]
    if snapshot_gaps:
        return _report(context, current_head, "blocked", snapshot_gaps)
    completed = run_git(
        root, "-c", "rebase.updateRefs=false", "rebase", candidate_head, current_head, check=False
    )
    if completed.returncode != 0:
        run_git(root, "rebase", "--abort", check=False)
        restored = run_git(root, "switch", branch, check=False)
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            [
                "refresh_base_failed",
                *([] if restored.returncode == 0 else ["refresh_base_worktree_restore_failed"]),
            ],
            stderr=completed.stderr.strip(),
        )
    rebased_head = current_tracked_head(root)
    if not is_ancestor(root, candidate_head, rebased_head):
        run_git(root, "switch", branch, check=False)
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            ["refresh_base_postcondition_failed"],
            previous_head=current_head,
            next_action="inspect current Git ancestry and runner, signing, or hook diagnostics",
            stderr="candidate head is not an ancestor of refreshed work-lane head",
        )
    plan = _refresh_transition_plan(
        root,
        branch,
        current_head,
        rebased_head,
        candidate_branch,
        candidate_head,
    )
    try:
        execute_git_effect(
            root,
            plan,
            issuer=_actor(),
            projection=lambda: _attach_work_lane(root, branch, rebased_head),
            detached_branch=branch,
        )
    except (OSError, ValueError) as error:
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            [
                "refresh_base_worktree_attach_failed"
                if "attachment" in str(error)
                else "refresh_base_snapshot_stale:work_lane"
            ],
            plan_digest=plan.digest,
            previous_head=current_head,
            stderr=str(error),
        )
    refreshed_head = current_tracked_head(root)
    if refreshed_head != rebased_head:
        return _report(
            context,
            refreshed_head,
            "blocked",
            ["refresh_base_snapshot_stale:work_lane"],
            previous_head=current_head,
            stderr="work-lane branch advanced after refresh compare-and-swap",
        )
    return _report(context, refreshed_head, "base_refreshed", [], previous_head=current_head)


def _attach_work_lane(root: Path, branch: str, head: str) -> None:
    attached = run_git(root, "switch", branch, check=False)
    if attached.returncode or current_tracked_head(root) != head:
        raise ValueError(attached.stderr.strip() or "work-lane branch attachment stale")


def _recover_work_lane(
    root: Path, candidate_branch: str, candidate_head: str, candidate_path: str
) -> dict[str, object]:
    head = current_tracked_head(root)
    plan = recover_plan(
        root,
        operation="lane.refresh",
        desired=head,
        assertions={f"refs/heads/{candidate_branch}": candidate_head},
    )
    if plan is None:
        msg = "git_effect_recovery_ambiguous"
        raise ValueError(msg)
    effect = git_effect_from_plan(plan)
    if len(effect.updates) != 1:
        msg = "git_effect_recovery_unproven"
        raise ValueError(msg)
    ref_name, update = next(iter(effect.updates.items()))
    branch = ref_name.removeprefix("refs/heads/")
    if not branch.startswith("work/") or plan.policy.get("execution_branch") != branch:
        msg = "git_effect_recovery_unproven"
        raise ValueError(msg)
    execute_git_effect(
        root,
        plan,
        issuer=_actor(),
        projection=lambda: _attach_work_lane(root, branch, head),
        detached_branch=branch,
    )
    return _report(
        (branch, candidate_branch, candidate_head, candidate_path),
        head,
        "base_refreshed",
        [],
        previous_head=update.expected,
    )


def _actor() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"


def _refresh_transition_plan(
    root: Path,
    branch: str,
    current_head: str,
    rebased_head: str,
    candidate_branch: str,
    candidate_head: str,
) -> TransitionPlan:
    lease = leases_by_branch(root).get(branch, {})
    return compile_observed_git_effect(
        root,
        load_repository_commitment(root, tree_ref=rebased_head),
        GitEffect(
            updates={
                f"refs/heads/{branch}": GitRefUpdate(expected=current_head, desired=rebased_head)
            },
            assertions={f"refs/heads/{candidate_branch}": candidate_head},
        ),
        head=rebased_head,
        prior_attestations={},
        policy={"operation": "lane.refresh", "execution_branch": branch},
        values={"lease_generation": lease_generation(lease)},
    )

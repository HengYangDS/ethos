"""Refresh one clean Work Lane onto the current candidate base."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit_identity import equivalent_commit_identity
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import attach_worktree
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


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
    if equivalent_commit_identity(root, candidate_head, current_head):
        return _report(
            context,
            current_head,
            "blocked",
            ["commit_identity_replacement_required"],
            next_action=(
                "ethos lane repair-identity --old-commit "
                f"{candidate_head} --new-commit {current_head} --json"
            ),
        )
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
        root,
        "-c",
        "rebase.updateRefs=false",
        "-c",
        "commit.gpgSign=false",
        "rebase",
        candidate_head,
        current_head,
        check=False,
    )
    if completed.returncode != 0:
        run_git(root, "rebase", "--abort", check=False)
        try:
            _attach_work_lane(root, branch, current_head)
            restore_gap: list[str] = []
        except (OSError, ValueError):
            restore_gap = ["refresh_base_worktree_restore_failed"]
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            ["refresh_base_failed", *restore_gap],
            stderr=completed.stderr.strip(),
        )
    rebased_head = current_tracked_head(root)
    if not is_ancestor(root, candidate_head, rebased_head):
        _attach_work_lane(root, branch, current_head)
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            ["refresh_base_postcondition_failed"],
            previous_head=current_head,
            next_action="inspect current Git ancestry and runner, signing, or hook diagnostics",
            stderr="candidate head is not an ancestor of refreshed work-lane head",
        )
    rebase_attestation = _rebase_attestation(
        root,
        branch=branch,
        previous=current_head,
        candidate_head=candidate_head,
        head=rebased_head,
    )
    plan = _refresh_transition_plan(
        root,
        branch,
        current_head,
        rebased_head,
        candidate_branch,
        candidate_head,
        rebase_attestation,
    )
    attachment_attestation: Attestation | None = None

    def attach() -> None:
        nonlocal attachment_attestation
        attachment_attestation = _attach_work_lane(root, branch, rebased_head)

    try:
        ref_attestation = execute_git_effect(
            root,
            plan,
            issuer=_actor(),
            projection=attach,
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
    post_gaps = [
        gap
        for invalid, gap in (
            (refreshed_head != rebased_head, "refresh_base_snapshot_stale:work_lane"),
            (attachment_attestation is None, "refresh_base_worktree_attach_failed"),
        )
        if invalid
    ]
    if post_gaps:
        return _report(
            context,
            refreshed_head,
            "blocked",
            post_gaps,
            previous_head=current_head,
            stderr=(
                "work-lane branch advanced after refresh compare-and-swap"
                if refreshed_head != rebased_head
                else ""
            ),
        )
    attachment = cast("Attestation", attachment_attestation)
    return _report(
        context,
        refreshed_head,
        "base_refreshed",
        [],
        previous_head=current_head,
        rebase_attestation=rebase_attestation.model_dump(mode="json"),
        ref_attestation=ref_attestation.model_dump(mode="json"),
        attachment_attestation=attachment.model_dump(mode="json"),
    )


def _attach_work_lane(root: Path, branch: str, head: str) -> Attestation:
    try:
        return attach_worktree(root, root, branch=branch, head=head)
    except ValueError as error:
        message = f"work-lane branch attachment stale:{error}"
        raise ValueError(message) from error


def _rebase_attestation(
    root: Path,
    *,
    branch: str,
    previous: str,
    candidate_head: str,
    head: str,
) -> Attestation:
    before = {"branch": branch, "head": previous, "candidate_head": candidate_head}
    after = {"branch": "detached", "head": head, "candidate_head": candidate_head}
    repository = load_repository_commitment(root, tree_ref=head)
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:git-rebase",
            operation="git.rebase",
            command=("git", "rebase"),
            subject={"branch": branch, "candidate_head": candidate_head},
            before=before,
            after=after,
        ),
        state="applied",
        commitment_digest=repository.digest(),
        repository_id=repository.id,
    )


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

    def attach() -> None:
        _attach_work_lane(root, branch, head)

    execute_git_effect(
        root,
        plan,
        issuer=_actor(),
        projection=attach,
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
    rebase_attestation: Attestation,
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
        prior_attestations={"rebase": rebase_attestation.model_dump(mode="json")},
        policy={"operation": "lane.refresh", "execution_branch": branch},
        values={"lease_generation": lease_generation(lease)},
    )

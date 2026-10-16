"""Refresh one clean Work Lane onto the current candidate base."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.merge import MergeMode
from ethos.adapters.mutation.lane_lifecycle.merge import merge_work_lane
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_record import PendingRefresh
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_record import clear_pending_refresh
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_record import read_pending_refresh
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh_record import write_pending_refresh
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.commit.creation import commit_environment
from ethos.adapters.repo.commit.integration import validate_replayed_commits
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import pending_merge_heads
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
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
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.commit import commit_policy_from_text

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
    strategy: Literal["rebase", "merge"] = "rebase",
    source_ref: str | None = None,
    mode: MergeMode = "inspect",
    expect_state: str | None = None,
    subject: str | None = None,
) -> dict[str, object]:
    if strategy == "merge" or source_ref is not None:
        return (
            merge_work_lane(
                root=root,
                mode=mode,
                apply=apply,
                authorized=authorized,
                expect_head=expect_head,
                expect_state=expect_state,
                subject=subject,
                source_ref=source_ref,
            )
            if strategy == "merge"
            else {
                "verdict": "block",
                "state": "blocked",
                "required_gaps": ["merge_source_ref_requires_merge_strategy"],
            }
        )
    policy = load_branch_role_policy(root)
    status = workspace_status(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    if branch == "detached" and apply:
        try:
            result = _recover_work_lane(
                root,
                policy.candidate_branch,
                candidate_head,
                candidate_path,
                dirty=bool(status.get("dirty")),
            )
            return _with_action(root, result, apply=apply)
        except ValueError as error:
            context = ("detached", policy.candidate_branch, candidate_head, candidate_path)
            return _with_action(
                root,
                _report(context, current_head, "blocked", [str(error)]),
                apply=apply,
            )
    context = (branch, policy.candidate_branch, candidate_head, candidate_path)

    if status.get("dirty") and pending_merge_heads(root):
        return _report(
            context,
            current_head,
            "blocked",
            ["merge_in_progress"],
            next_action=(
                "ethos lane refresh-base --strategy merge "
                f"--root {shlex.quote(root.resolve().as_posix())} --json"
            ),
        )

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
        return _with_action(
            root,
            _report(context, current_head, "blocked", gaps),
            apply=apply,
        )
    if is_ancestor(root, candidate_head, current_head):
        result = _report(context, current_head, "base_current", [])
    elif admission := _write_admission_gaps(root):
        gaps, action = admission
        result = _report(context, current_head, "blocked", gaps, next_action=action)
    elif not apply:
        result = _report(context, current_head, "ready_to_refresh_base", [])
    else:
        result = _refresh_work_lane(root, context, current_head)
    return _with_action(root, result, apply=apply)


def _write_admission_gaps(root: Path) -> tuple[list[str], str] | None:
    """Refuse a rewrite that the armed hooks would reject, before any effect."""
    runtime = hook_runtime_binding(root)
    gaps = list(string_sequence(runtime.get("required_gaps")))
    return (gaps, str(runtime.get("next_action") or "")) if gaps else None


def _process_failure(error: Exception) -> dict[str, object]:
    """Keep native refusal evidence instead of reducing it to its code."""
    return {"process_failure": error.evidence()} if isinstance(error, ProcessExecutionError) else {}


def _exact_refresh(root: Path, head: str) -> str:
    return (
        "ethos lane refresh-base --apply --authorize "
        f"--expect-head {head} --root {shlex.quote(root.resolve().as_posix())} --json"
    )


def _with_action(root: Path, report: dict[str, object], *, apply: bool) -> dict[str, object]:
    """Attach the operation-owned continuation before CLI projection."""
    gaps = tuple(str(item) for item in cast("list[object]", report.get("required_gaps", [])))
    state = str(report.get("state") or "")
    exact_refresh = _exact_refresh(root, str(report.get("head") or ""))
    if report.get("next_action"):
        action = str(report["next_action"])
    elif not gaps and state == "ready_to_refresh_base":
        action = exact_refresh
    elif not gaps:
        action = f"ethos land --root {shlex.quote(root.resolve().as_posix())} --json"
    elif "authorization_required" in gaps:
        action = exact_refresh
    else:
        action = f"ethos status --root {shlex.quote(root.resolve().as_posix())} --json"
    return report | {
        "next_action": action,
        "user_decision_required": (
            (not apply and state == "ready_to_refresh_base") or "authorization_required" in gaps
        ),
    }


def _refresh_work_lane(
    root: Path,
    context: tuple[str, str, str, str],
    current_head: str,
) -> dict[str, object]:
    branch, candidate_branch, candidate_head, _candidate_path = context
    snapshot_gaps = _refresh_snapshot_gaps(root, current_head, candidate_branch, candidate_head)
    if snapshot_gaps:
        return _report(context, current_head, "blocked", snapshot_gaps)
    try:
        commit_policy = commit_policy_from_text(
            committed_file_text(root, candidate_head, ".ethos/workspace.toml")
        )
        environment = commit_environment(root, None)
        write_pending_refresh(
            root,
            PendingRefresh(
                branch=branch, previous_head=current_head, candidate_head=candidate_head
            ),
        )
    except (OSError, TypeError, ValueError) as error:
        return _report(context, current_head, "blocked", [str(error)])
    completed = run_git(
        root,
        "-c",
        "rebase.updateRefs=false",
        "rebase",
        "-S",
        candidate_head,
        current_head,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        run_git(root, "rebase", "--abort", check=False)
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            ["refresh_base_failed", *_restore_original_work_lane(root, branch, current_head)],
            stderr=completed.stderr.strip(),
        )
    rebased_head = current_tracked_head(root)
    if not is_ancestor(root, candidate_head, rebased_head):
        restore_gaps = _restore_original_work_lane(root, branch, current_head)
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            ["refresh_base_postcondition_failed", *restore_gaps],
            previous_head=current_head,
            next_action=(f"ethos status --root {shlex.quote(root.resolve().as_posix())} --json"),
            stderr="candidate head is not an ancestor of refreshed work-lane head",
        )
    policy_gaps = validate_replayed_commits(
        root, baseline_commit=candidate_head, proposed_commit=rebased_head, policy=commit_policy
    )
    if policy_gaps:
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            [*policy_gaps, *_restore_original_work_lane(root, branch, current_head)],
            previous_head=current_head,
        )
    return _complete_refresh(root, context, current_head, rebased_head)


def _refresh_snapshot_gaps(
    root: Path,
    current_head: str,
    candidate_branch: str,
    candidate_head: str,
) -> list[str]:
    """Return stale coordinates before native rebase starts."""
    observed = {
        "work_lane": current_tracked_head(root),
        "candidate": run_git(root, "rev-parse", candidate_branch, check=False).stdout.strip(),
    }
    admitted = {"work_lane": current_head, "candidate": candidate_head}
    return [
        f"refresh_base_snapshot_stale:{name}"
        for name, value in observed.items()
        if value != admitted[name]
    ]


def _restore_original_work_lane(root: Path, branch: str, head: str) -> list[str]:
    """Return the detached lane to its original head, then re-attach its branch."""
    try:
        _detach_at(root, head)
        _attach_work_lane(root, branch, head)
        clear_pending_refresh(root)
    except (OSError, ValueError):
        return ["refresh_base_worktree_restore_failed"]
    return []


def _detach_at(root: Path, head: str) -> None:
    switched = run_git(root, "switch", "--detach", head, check=False)
    if switched.returncode:
        raise ValueError(switched.stderr.strip() or "refresh_base_worktree_restore_failed")


def _complete_refresh(
    root: Path,
    context: tuple[str, str, str, str],
    current_head: str,
    rebased_head: str,
) -> dict[str, object]:
    """Apply and attest the admitted ref and worktree effects."""
    branch, candidate_branch, candidate_head, _candidate_path = context
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
    try:
        ref_attestation = execute_git_effect(
            root,
            plan,
            issuer=_actor(),
            detached_branch=branch,
        )
    except (OSError, ValueError) as error:
        return _report(
            context,
            current_tracked_head(root),
            "blocked",
            [
                "refresh_base_snapshot_stale:work_lane",
                *_restore_original_work_lane(root, branch, current_head),
            ],
            plan_digest=plan.digest,
            previous_head=current_head,
            stderr=str(error),
            **_process_failure(error),
        )
    attachment_attestation = None
    attachment_error = ""
    try:
        attachment_attestation = _attach_work_lane(root, branch, rebased_head)
    except (OSError, ValueError) as error:
        attachment_error = str(error)
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
            next_action=_exact_refresh(root, refreshed_head) if attachment_error else "",
            stderr=attachment_error
            or (
                "work-lane branch advanced after refresh compare-and-swap"
                if refreshed_head != rebased_head
                else ""
            ),
        )
    clear_pending_refresh(root)
    return _report(
        context,
        refreshed_head,
        "base_refreshed",
        [],
        previous_head=current_head,
        rebase_attestation=rebase_attestation.model_dump(mode="json"),
        ref_attestation=ref_attestation.model_dump(mode="json"),
        attachment_attestation=cast("Attestation", attachment_attestation).model_dump(mode="json"),
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
        commitment_digest=None,
        repository_id=repository_identity(root, tree_ref=head),
    )


def _recover_work_lane(
    root: Path, candidate_branch: str, candidate_head: str, candidate_path: str, *, dirty: bool
) -> dict[str, object]:
    head = current_tracked_head(root)
    plan = recover_plan(
        root,
        operation="lane.refresh",
        desired=head,
        assertions={f"refs/heads/{candidate_branch}": candidate_head},
    )
    if plan is None:
        candidate = (candidate_branch, candidate_head, candidate_path)
        return _restore_interrupted_refresh(root, head, candidate, dirty=dirty)
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
        detached_branch=branch,
    )
    _attach_work_lane(root, branch, head)
    clear_pending_refresh(root)
    return _report(
        (branch, candidate_branch, candidate_head, candidate_path),
        head,
        "base_refreshed",
        [],
        previous_head=update.expected,
    )


def _restore_interrupted_refresh(
    root: Path, head: str, candidate: tuple[str, str, str], *, dirty: bool
) -> dict[str, object]:
    """Return a lane left detached by an interrupted refresh to its recorded head."""
    pending = read_pending_refresh(root)
    if pending is None:
        msg = "git_effect_recovery_ambiguous"
        raise ValueError(msg)
    if any(git_path(root, name).exists() for name in ("rebase-merge", "rebase-apply")):
        msg = "refresh_base_rebase_in_progress"
        raise ValueError(msg)
    if dirty:
        msg = "work_lane_dirty"
        raise ValueError(msg)
    tip = run_git(root, "rev-parse", "--verify", f"refs/heads/{pending.branch}", check=False)
    if tip.stdout.strip() != pending.previous_head:
        msg = "git_effect_recovery_unproven"
        raise ValueError(msg)
    if gaps := _restore_original_work_lane(root, pending.branch, pending.previous_head):
        raise ValueError(gaps[0])
    return _report(
        (pending.branch, *candidate),
        pending.previous_head,
        "base_restored",
        [],
        previous_head=head,
        next_action=_exact_refresh(root, pending.previous_head),
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
    effect = GitEffect(
        updates={f"refs/heads/{branch}": GitRefUpdate(expected=current_head, desired=rebased_head)},
        assertions={f"refs/heads/{candidate_branch}": candidate_head},
    )
    return compile_observed_git_effect(
        root,
        None,
        effect,
        head=rebased_head,
        prior_attestations={"rebase": rebase_attestation.model_dump(mode="json")},
        policy={
            "operation": "lane.refresh",
            "execution_branch": branch,
        },
        values={"lease_generation": lease_generation(lease)},
    )

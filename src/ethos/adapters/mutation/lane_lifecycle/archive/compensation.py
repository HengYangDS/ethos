"""Compensate an unlanded OpenSpec archive through one exact Git effect."""

from __future__ import annotations

import os
import shlex
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.repo.attestation_lifetime import published_refs
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan

if TYPE_CHECKING:
    from pathlib import Path


def compensate_archive(
    root: Path,
    *,
    branch: str,
    head: str,
    change: str,
    expect_head: str,
    apply: bool,
) -> dict[str, object]:
    """Return an archive commit that has not landed to its exact pre-archive head."""
    ref, lease = f"refs/heads/{branch}", leases_by_branch(root).get(branch, {})
    done = recover_plan(root, operation="openspec.archive.compensate", desired=head, ref_name=ref)
    # An interrupted compensation has already moved the ref and only restores the worktree.
    resumed = done is not None and git_effect_from_plan(done).updates[ref].expected == expect_head
    archived = expect_head if resumed else head
    gaps = work_lane_transition_gaps(
        root,
        branch=branch,
        head=archived,
        expect_head=expect_head,
        lease=lease,
        actor=os.environ.get("ETHOS_ACTOR", "").strip(),
        role_gap="archive_requires_work_lane",
        require_clean=not resumed,
    )
    attested = (
        None if gaps or resumed else attested_archive_transition(root, head=head, change=change)
    )
    # A proposal of the archived head is retired first, while this lane still retains the head.
    published = [] if gaps or resumed else _published(root, head)
    if not (gaps or resumed):
        if attested is None or attested[1].get("resolved_head") != head:
            gaps.append(f"openspec_archive_compensation_unavailable:{change}")
        elif is_ancestor(root, head, load_branch_role_policy(root).candidate_branch):
            gaps.append(f"openspec_archive_landed:{change}")
        elif published:
            gaps.append(f"openspec_archive_published:{change}")
    if resumed and not gaps and not _restorable(root, archived):
        gaps.append("work_lane_dirty")
    target = head if resumed else git_stdout(root, "rev-parse", f"{head}^")
    if gaps or not apply:
        return lifecycle_report(
            branch,
            head,
            "blocked" if gaps else "ready_to_compensate",
            gaps,
            change=change,
            previous_head=target,
            **lifecycle_effect_outcome(
                kind="zero_effect",
                next_action=(
                    _retirement(published[0], head) if published else "ethos lane status --json"
                )
                if gaps
                else archive_recovery_command(change, expect_head, compensate=True),
                user_decision_required=bool(gaps),
            ),
        )
    if attested is not None:
        commitment, archive = attested
        plan = compile_observed_git_effect(
            root,
            commitment,
            GitEffect(updates={ref: GitRefUpdate(expected=head, desired=target)}),
            head=head,
            policy={
                "operation": "openspec.archive.compensate",
                "branch": branch,
                "change": change,
                "execution_branch": branch,
            },
            values={"lease_generation": lease_generation(lease), "archive": archive},
        )
        execute_git_effect(root, plan, issuer=str(lease.get("holder_ref") or ""))
    compensate_git_worktree(root, head=target)
    return lifecycle_report(
        branch,
        target,
        "compensated",
        [],
        change=change,
        archived_head=archived,
        **lifecycle_effect_outcome(
            kind="mutation_compensated", next_action="ethos lane status --json"
        ),
    )


def _restorable(root: Path, archived: str) -> bool:
    """Whether the index and worktree are restored, or still hold exactly the archived tree."""
    if not git_stdout(root, "status", "--short"):
        return True
    return (
        not git_stdout(root, "ls-files", "--others", "--exclude-standard")
        and not git_stdout(root, "diff", "--name-only")
        and git_stdout(root, "write-tree") == current_tree(root, archived)
    )


def _published(root: Path, head: str) -> list[str]:
    """The refs whose latest recorded publication on some peer selects the head."""
    selected = published_refs(read_attestation_set(root)[1]).items()
    return sorted({ref for (_peer, ref), desired in selected if desired == head})


def _retirement(ref: str, head: str) -> str:
    """Retire the proposal on every peer while this lane still retains its head."""
    retire = ("ethos", "publish", "--retire", "--ref", ref, "--probe-remote", "--expect-head")
    return shlex.join((*retire, head, "--json"))

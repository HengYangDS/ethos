"""Archive one completed OpenSpec Change through the common Git effect executor."""

from __future__ import annotations

import os
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.mutation.lane_lifecycle.archive.effect import compile_archive_plan
from ethos.adapters.mutation.lane_lifecycle.archive.effect import complete_archive
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.dirty.change_provenance import changed_paths as dirty_changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import move_tracked_tree
from ethos.adapters.repo.git_effects import restore_git_index
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.git_signing import create_git_commit
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class ArchiveCollision(NamedTuple):
    """One immutable archive collision and its preservation target."""

    path: str
    tree: str
    preserved_path: str


def archive_collision(root: Path, head: str, change: str) -> ArchiveCollision | None:
    """Describe the deterministic preservation target for today's collision."""
    path = f"openspec/changes/archive/{datetime.now(UTC).date()}-{change}"
    tree = git_stdout(root, "rev-parse", f"{head}:{path}")
    if not tree:
        return None
    preserved = collision_preservation_path(path, tree, head)
    if git_stdout(root, "rev-parse", f"{head}:{preserved}") or os.path.lexists(root / preserved):
        message = "openspec_archive_collision_preservation_conflict"
        raise ValueError(message)
    return ArchiveCollision(path, tree, preserved)


def archive_change(
    *, root: Path, change: str, expect_head: str, apply: bool = False
) -> dict[str, object]:
    """Run official OpenSpec archive through one exact Git effect."""
    repo = root.resolve()
    status, authority = workspace_status_observation(repo, include_foreign_path_scope=False)
    head = str(status.get("head") or current_tracked_head(repo))
    branch = str(status.get("branch") or git_stdout(repo, "branch", "--show-current"))
    try:
        if head != expect_head:
            existing = _existing_archive_report(
                repo,
                branch=branch,
                head=head,
                change=change,
                apply=apply,
            )
            if existing is not None:
                return existing
        observed = archive_postimage(repo, head=head, change=change)
        resolution = resolve_current_resolution(
            repo,
            status=status,
            authority=authority,
            change=change,
            changed=False,
            intent_tree_ref=(head if observed is not None and observed.scope is not None else None),
        )
        staged = observed is not None and observed.scope is not None
        resolution_gaps = (
            list(resolution.required_gaps)
            if resolution.verdict != "pass" or resolution.commitment is None
            else []
        )
        if not staged:
            resolution_gaps = _archive_readiness(resolution, change)
        elif not resolution_gaps and resolution.commitment is None:
            resolution_gaps = [f"commitment_invalid:{change}"]
        if resolution_gaps:
            return archive_preflight_report(
                branch,
                head,
                change,
                resolution_gaps,
                lease=resolution.lease,
                next_action=resolution.next_action or None,
                user_decision_required=resolution.user_decision_required,
            )
        gaps = _archive_coordinate_gaps(
            repo,
            str(status.get("role") or ""),
            head,
            expect_head,
        )
        if gaps:
            return archive_preflight_report(branch, head, change, gaps, lease=resolution.lease)
        if staged:
            return _finalize_existing_archive(
                repo,
                branch,
                head,
                change,
                dict(observed.scope),
                apply=apply,
                resolution=resolution,
            )
        return _archive_active_change(
            repo,
            branch,
            head,
            change,
            active_present=observed.active_present if observed is not None else False,
            apply=apply,
            resolution=resolution,
        )
    except (OSError, TypeError, ValueError) as error:
        current = current_tracked_head(repo)
        return lifecycle_report(
            branch,
            current,
            "repair_required",
            [str(error)],
            change=change,
            **lifecycle_effect_outcome(
                kind="committed_residue" if current != expect_head else "zero_effect",
                next_action=archive_recovery_command(change, expect_head),
            ),
        )


def _existing_archive_report(
    root: Path,
    *,
    branch: str,
    head: str,
    change: str,
    apply: bool,
) -> dict[str, object] | None:
    plan = recover_plan(
        root,
        operation="openspec.archive",
        desired=head,
        ref_name=f"refs/heads/{branch}",
    )
    if plan is None:
        return None
    if (
        plan.policy.get("transition") != "openspec.archive"
        or plan.policy.get("branch") != branch
        or plan.policy.get("change") != change
    ):
        return None
    return complete_archive(root, branch, change, plan, head, apply=apply)


def _archive_active_change(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    *,
    active_present: bool,
    apply: bool,
    resolution: CurrentResolution,
) -> dict[str, object]:
    gaps = (
        ["openspec_archive_delta_invalid"]
        if not active_present
        else ["work_lane_dirty"]
        if git_stdout(repo, "status", "--short")
        else _archive_readiness(resolution, change)
    )
    collision = None
    if not gaps:
        try:
            collision = archive_collision(repo, head, change)
        except ValueError as error:
            gaps = [str(error)]
    if gaps or not apply:
        return lifecycle_report(
            branch,
            head,
            "blocked" if gaps else "ready_to_archive",
            gaps,
            change=change,
            **lifecycle_effect_outcome(
                kind="zero_effect",
                next_action=(
                    "ethos lane status --json" if gaps else archive_recovery_command(change, head)
                ),
                user_decision_required=bool(gaps),
            ),
            **({"archive_collision": collision._asdict()} if collision else {}),
        )
    try:
        return _apply_archive(
            repo,
            branch,
            head,
            change,
            resolution=resolution,
            collision=collision,
        )
    except (OSError, TypeError, ValueError) as error:
        if current_tracked_head(repo) != head:
            return lifecycle_report(
                branch,
                current_tracked_head(repo),
                "repair_required",
                [str(error)],
                change=change,
                **lifecycle_effect_outcome(
                    kind="committed_residue",
                    next_action=archive_recovery_command(change, head),
                ),
                **({"archive_collision": collision._asdict()} if collision else {}),
            )

        def compensate() -> None:
            compensate_git_worktree(
                repo,
                head=head,
                untracked_path=collision.preserved_path if collision else "",
            )

        return archive_failure_report(
            branch,
            head,
            change,
            [str(error)],
            compensate=compensate,
            **({"archive_collision": collision._asdict()} if collision else {}),
        )


def _archive_coordinate_gaps(
    root: Path,
    role: str,
    head: str,
    expect_head: str,
) -> list[str]:
    gaps: list[str] = []
    if role != ROLE_WORK_LANE:
        gaps.append("archive_requires_work_lane")
    elif head != expect_head:
        gaps.append("expect_head_mismatch")
    if not gaps:
        gaps.extend(proof_gaps(root, head))
    return list(dict.fromkeys(gaps))


def _finalize_existing_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    postimage: dict[str, Any],
    *,
    apply: bool,
    resolution: CurrentResolution,
) -> dict[str, object]:
    if apply:
        return _commit_archive_postimage(
            repo,
            branch,
            head,
            change,
            postimage,
            resolution=resolution,
            owned_mutation=False,
        )
    return lifecycle_report(
        branch,
        head,
        "ready_to_finalize_archive",
        [],
        change=change,
        archive_path=postimage["archive_path"],
        changed_paths=postimage["changed_paths"],
        **lifecycle_effect_outcome(
            kind="zero_effect",
            next_action=archive_recovery_command(change, head),
        ),
    )


def _archive_readiness(resolution: CurrentResolution, change: str) -> list[str]:
    gaps = list(resolution.required_gaps)
    if resolution.commitment is None and not gaps:
        gaps.append(f"commitment_invalid:{change}")
    lifecycle = resolution.openspec.get("lifecycle")
    if isinstance(lifecycle, dict):
        rows = lifecycle.get("changes", [])
        complete = (
            isinstance(rows, list)
            and len(rows) == 1
            and isinstance(rows[0], dict)
            and rows[0].get("name") == change
            and isinstance(rows[0].get("progress"), dict)
            and rows[0]["progress"].get("remaining") == 0
        )
        if not complete:
            gaps.append(f"openspec_change_incomplete:{change}")
    elif not gaps:
        gaps.append(f"openspec_change_incomplete:{change}")
    return list(dict.fromkeys(gaps))


def _apply_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    *,
    resolution: CurrentResolution,
    collision: ArchiveCollision | None = None,
) -> dict[str, object]:
    command = openspec_cli.openspec_base_command()
    if command is None:
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_official_cli_missing"],
            change=change,
            **lifecycle_effect_outcome(
                kind="zero_effect",
                next_action="ethos lane status --json",
                user_decision_required=True,
            ),
        )
    if collision is not None:
        move_tracked_tree(repo, collision.path, collision.preserved_path)
    archive_command = openspec_cli.archive_command(repo, change)
    result = openspec_cli.run_json(repo, command, archive_command[1:])
    mutation_gaps, archive_path = openspec_cli.archive_result(repo, change, result)
    compensation_path = collision.preserved_path if collision else archive_path

    def compensate() -> None:
        compensate_git_worktree(repo, head=head, untracked_path=compensation_path)

    if mutation_gaps:
        return archive_failure_report(
            branch,
            head,
            change,
            mutation_gaps,
            compensate=compensate,
            command=result.get("command", []),
            **({"archive_collision": collision._asdict()} if collision else {}),
        )
    normalize_projected_specs(repo, paths=dirty_changed_paths(repo))
    observed = archive_postimage(repo, head=head, change=change)
    if observed is None or observed.active_present or observed.scope is None:
        return archive_failure_report(
            branch,
            head,
            change,
            ["openspec_archive_delta_invalid"],
            compensate=compensate,
        )
    return _commit_archive_postimage(
        repo,
        branch,
        head,
        change,
        dict(observed.scope),
        resolution=resolution,
        owned_mutation=True,
        collision=collision,
        result=result,
    )


def _commit_archive_postimage(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    scope: dict[str, Any],
    *,
    resolution: CurrentResolution,
    owned_mutation: bool,
    collision: ArchiveCollision | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, object]:
    commitment = resolution.commitment
    if commitment is None:
        message = f"commitment_invalid:{change}"
        raise ValueError(message)
    archive_path = str(scope["archive_path"])
    changed = tuple(str(path) for path in scope["changed_paths"])
    compensation_path = collision.preserved_path if collision else archive_path
    original_index_tree = git_stdout(repo, "write-tree")

    def restore_failure_boundary() -> None:
        if owned_mutation:
            compensate_git_worktree(repo, head=head, untracked_path=compensation_path)
        else:
            restore_git_index(repo, tree=original_index_tree)

    stage_git_worktree(repo, previous=head)
    staged_tree = git_stdout(repo, "write-tree")
    staged_paths = tuple(
        git_stdout(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )
    if staged_tree != scope["tree"] or staged_paths != changed:
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_delta_changed"],
            change=change,
            changed_paths=list(staged_paths),
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, head),
            ),
        )
    committed = create_git_commit(
        repo,
        tree=staged_tree,
        parent=head,
        message=lifecycle_commit_subject(repo, "archive", change),
    )
    if committed.returncode:
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_commit_failed"],
            change=change,
            stderr=committed.stderr.strip(),
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, head),
            ),
        )
    target_head = committed.stdout.strip()
    try:
        plan = compile_archive_plan(
            repo,
            branch,
            change,
            head,
            target_head,
            resolution.lease,
            commitment=commitment,
        )
        return complete_archive(
            repo,
            branch,
            change,
            plan,
            target_head,
            apply=True,
            result=result,
        )
    except (OSError, TypeError, ValueError):
        if current_tracked_head(repo) == head:
            restore_failure_boundary()
        raise


def archive_preflight_report(
    branch: str,
    head: str,
    change: str,
    gaps: list[str],
    *,
    lease: dict[str, object] | None = None,
    next_action: str | None = None,
    user_decision_required: bool | None = None,
) -> dict[str, object]:
    """Project the first exact coordinate failure before any archive effect."""
    first = gaps[0]
    state = {
        f"work_lane_missing_lease:{branch}": "lease_missing",
        f"work_lane_lease_expired:{branch}": "lease_expired",
        "lease_actor_mismatch": "different_holder",
    }.get(first, "blocked")
    generation = lease or {}
    resolved_action = next_action or "ethos lane status --json"
    decision_required = (
        state in {"lease_missing", "different_holder"}
        if user_decision_required is None
        else user_decision_required
    )
    if next_action is None and state == "different_holder":
        resolved_action = (
            "ethos attestation query --predicate lane-resolution:takeover "
            f"--subject git:branch:{branch} --json"
        )
    elif next_action is None and state == "lease_expired":
        resolved_action = (
            "ethos lane lease resume "
            f"--generation {generation.get('generation', '')} "
            f"--expires-at {generation.get('expires_at', '')} "
            f"--branch {branch} "
            f"--holder-ref {generation.get('holder_ref', '')} "
            "--apply --json"
        )
    return lifecycle_report(
        branch,
        head,
        state,
        gaps,
        change=change,
        **lifecycle_effect_outcome(
            kind="zero_effect",
            next_action=resolved_action,
            user_decision_required=decision_required,
        ),
    )


def archive_failure_report(
    branch: str,
    head: str,
    change: str,
    gaps: list[str],
    *,
    compensate: Callable[[], None],
    **details: object,
) -> dict[str, object]:
    """Report exact pre-CAS compensation without inventing recovery state."""
    try:
        compensate()
    except (OSError, ValueError) as error:
        return lifecycle_report(
            branch,
            head,
            "repair_required",
            [*gaps, "openspec_archive_compensation_failed"],
            change=change,
            **lifecycle_effect_outcome(
                kind="compensation_failed",
                next_action="ethos lane status --json",
                user_decision_required=True,
            ),
            compensation_error=str(error),
            **details,
        )
    return lifecycle_report(
        branch,
        head,
        "blocked",
        gaps,
        change=change,
        **lifecycle_effect_outcome(
            kind="mutation_compensated",
            next_action=archive_recovery_command(change, head),
        ),
        **details,
    )

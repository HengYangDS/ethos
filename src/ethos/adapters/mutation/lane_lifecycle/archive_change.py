"""Archive one completed OpenSpec Change as one governed Work Lane commit."""

from __future__ import annotations

import os
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.lane_lifecycle.archive_recovery import archive_attestation_recovery
from ethos.adapters.mutation.lane_lifecycle.archive_recovery import archive_failure_report
from ethos.adapters.mutation.lane_lifecycle.archive_recovery import archive_preflight_report
from ethos.adapters.mutation.lane_lifecycle.archive_recovery import finish_archive
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_effect import archive_postimage
from ethos.adapters.openspec.lifecycle.archive_effect import archive_transition_environment
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.dirty.change_provenance import changed_paths as dirty_changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import move_tracked_tree
from ethos.adapters.repo.git_effects import restore_git_index
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.status.bindings import leases_by_branch

if TYPE_CHECKING:
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
    *,
    root: Path,
    change: str,
    expect_head: str,
    apply: bool = False,
) -> dict[str, object]:
    """Run official OpenSpec archive and commit its exact Lease-bound delta."""
    repo = root.resolve()
    head = current_tracked_head(repo)
    branch = git_stdout(repo, "branch", "--show-current")
    lease = leases_by_branch(repo).get(branch, {})
    result = archive_attestation_recovery(
        repo,
        branch=branch,
        head=head,
        lease=lease,
        change=change,
        expect_head=expect_head,
        apply=apply,
    )
    if result is None and not lease:
        observed = archive_postimage(repo, head=head, change=change)
        if observed is not None and observed.scope is not None:
            gaps = [] if head == expect_head else ["expect_head_mismatch"]
            if not gaps:
                gaps.extend(proof_gaps(repo, head))
            result = (
                archive_preflight_report(branch, head, change, gaps, lease=lease)
                if gaps
                else _finalize_existing_archive(
                    repo,
                    branch,
                    head,
                    change,
                    dict(observed.scope),
                    apply=apply,
                    ownerless=True,
                )
            )
        elif observed is not None and not observed.active_present:
            result = archive_preflight_report(
                branch,
                head,
                change,
                [f"work_lane_missing_lease:{branch}"],
            )
    if result is None:
        gaps = _archive_coordinate_gaps(repo, branch, head, expect_head, lease, change)
        if gaps:
            result = archive_preflight_report(branch, head, change, gaps, lease=lease)
    if result is None:
        observed = archive_postimage(repo, head=head, change=change)
        result = (
            _finalize_existing_archive(
                repo, branch, head, change, dict(observed.scope), apply=apply
            )
            if observed is not None and observed.scope is not None
            else _archive_active_change(
                repo,
                branch,
                head,
                change,
                active_present=observed.active_present if observed is not None else False,
                apply=apply,
            )
        )
    return result


def _archive_active_change(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    *,
    active_present: bool,
    apply: bool,
) -> dict[str, object]:
    gaps = (
        ["openspec_archive_delta_invalid"]
        if not active_present
        else ["work_lane_dirty"]
        if git_stdout(repo, "status", "--short")
        else _archive_readiness(repo, change)
    )
    collision = None
    if not gaps:
        try:
            collision = archive_collision(repo, head, change)
        except ValueError as error:
            gaps = [str(error)]
    guard = local_state_mutation_guard(repo) if apply and not gaps else {"required_gaps": []}
    if guard["required_gaps"]:
        gaps = ["local_state_migration_required"]
    if gaps or not apply:
        next_action = "ethos lane status --json" if gaps else archive_recovery_command(change, head)
        if guard["required_gaps"]:
            next_action = str(guard["next_action"])
        return lifecycle_report(
            branch,
            head,
            "blocked" if gaps else "ready_to_archive",
            gaps,
            change=change,
            **lifecycle_effect_outcome(
                kind="zero_effect",
                next_action=next_action,
                user_decision_required=bool(gaps),
            ),
            **({"archive_collision": collision._asdict()} if collision else {}),
        )
    try:
        return _apply_archive(repo, branch, head, change, collision=collision)
    except (OSError, TypeError, ValueError) as error:
        if current_tracked_head(repo) != head:
            return lifecycle_report(
                branch,
                current_tracked_head(repo),
                "repair_required",
                [str(error)],
                change=change,
                **lifecycle_effect_outcome(
                    kind="mutation_uncompensated",
                    next_action="ethos lane status --json",
                    user_decision_required=True,
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
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    change: str,
) -> list[str]:
    gaps = work_lane_transition_gaps(
        root,
        branch=branch,
        head=head,
        expect_head=expect_head,
        lease=lease,
        actor=os.environ.get("ETHOS_ACTOR", "").strip(),
        role_gap="archive_requires_work_lane",
    )
    if not gaps and lease.get("base_commitment_path") != (
        f"openspec/changes/{change}/commitment.toml"
    ):
        gaps.append(f"openspec_active_change_missing:{change}")
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
    ownerless: bool = False,
) -> dict[str, object]:
    guard = local_state_mutation_guard(repo) if apply else {"required_gaps": []}
    if guard["required_gaps"]:
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["local_state_migration_required"],
            change=change,
            **lifecycle_effect_outcome(
                kind="zero_effect",
                next_action=str(guard["next_action"]),
            ),
        )
    if apply:
        return _commit_archive_postimage(
            repo,
            branch,
            head,
            change,
            postimage,
            owned_mutation=False,
            ownerless=ownerless,
        )
    state = "ready_to_finalize_ownerless_archive" if ownerless else "ready_to_finalize_archive"
    return lifecycle_report(
        branch,
        head,
        state,
        [],
        change=change,
        archive_path=postimage["archive_path"],
        changed_paths=postimage["changed_paths"],
        **lifecycle_effect_outcome(
            kind="zero_effect",
            next_action=archive_recovery_command(change, head),
        ),
    )


def _archive_readiness(
    root: Path,
    change: str,
) -> list[str]:
    gaps: list[str] = []
    governance = openspec_governance_report(root, change=change, lifecycle=True)
    gaps.extend(str(gap) for gap in governance.get("required_gaps", ()))
    lifecycle = governance.get("lifecycle")
    rows = lifecycle.get("changes", []) if isinstance(lifecycle, dict) else []
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
    return list(dict.fromkeys(gaps))


def _apply_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    *,
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

    normalize_projected_specs(
        repo,
        paths=dirty_changed_paths(repo),
    )
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
    owned_mutation: bool,
    ownerless: bool = False,
    collision: ArchiveCollision | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Commit one already-selected archive post-image and finish its terminal effects."""
    archive_path = str(scope["archive_path"])
    changed = tuple(str(path) for path in scope["changed_paths"])
    completion_artifacts = tuple(str(path) for path in scope["completion_artifacts"])
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
    try:
        archive_commit = commit_git_worktree(
            repo,
            previous=head,
            message=lifecycle_commit_subject(repo, "archive", change),
            environment=archive_transition_environment(
                repo,
                change=change,
                head=head,
                changed_paths=changed,
                official_change_complete=True,
                completion_artifacts=completion_artifacts,
            ),
        )
    except ValueError as error:
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            head,
            "blocked",
            [str(error)],
            change=change,
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, head),
            ),
        )
    if archive_commit["verdict"] != "pass":
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_commit_failed"],
            change=change,
            stderr=str(archive_commit.get("error") or ""),
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, head),
            ),
        )
    return finish_archive(
        repo,
        branch,
        head,
        change,
        result or {},
        archive_path,
        changed,
        preserved_archive_path=collision.preserved_path if collision else "",
        ownerless=ownerless,
    )

"""Archive one completed OpenSpec Change as one governed Work Lane commit."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import advance_committed_lease
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.generation.attestation import exact_archive_paths
from ethos.adapters.openspec.generation.attestation import issue_archive_effect
from ethos.adapters.openspec.governance import artifact_output_paths
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_binding import exact_carrier_relocation
from ethos.adapters.openspec.lifecycle.archive_binding import valid_archive_carrier
from ethos.adapters.openspec.lifecycle.archive_transition import archive_transition_environment
from ethos.adapters.openspec.lifecycle.archive_transition import lease_bound_archive_scope_report
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.dirty.change_provenance import changed_paths as dirty_changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import move_tracked_tree
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.status.bindings import leases_by_branch

if TYPE_CHECKING:
    from pathlib import Path


class ArchiveCollision(NamedTuple):
    """One immutable archive collision and its preservation target."""

    path: str
    tree: str
    preserved_path: str


class ArchiveRecovery(NamedTuple):
    """Exact committed archive facts used by recovery and reporting."""

    change: str
    previous_head: str
    archive_path: str
    changed_paths: tuple[str, ...]
    lease: dict[str, object]


def archive_collision(root: Path, head: str, change: str) -> ArchiveCollision | None:
    """Describe the deterministic preservation target for today's collision."""
    path = f"openspec/changes/archive/{datetime.now().astimezone().date()}-{change}"
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
    recovery = _archive_attestation_recovery(
        repo,
        branch=branch,
        head=head,
        lease=lease,
        change=change,
        expect_head=expect_head,
        apply=apply,
    )
    if recovery is not None:
        return recovery
    gaps, official_complete, completion_artifacts = _archive_readiness(
        repo, branch, head, expect_head, lease, change
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
        return lifecycle_report(
            branch,
            head,
            "blocked" if gaps else "ready_to_archive",
            gaps,
            change=change,
            **({"next_action": guard["next_action"]} if guard["required_gaps"] else {}),
            **({"archive_collision": collision._asdict()} if collision else {}),
        )
    try:
        return _apply_archive(
            repo,
            branch,
            head,
            change,
            official_complete=official_complete,
            completion_artifacts=completion_artifacts,
            collision=collision,
        )
    except (OSError, TypeError, ValueError) as error:
        if current_tracked_head(repo) == head:
            compensate_git_worktree(
                repo,
                head=head,
                untracked_path=collision.preserved_path if collision else "",
            )
        return lifecycle_report(
            branch,
            current_tracked_head(repo),
            "repair_required",
            [str(error)],
            change=change,
            **({"archive_collision": collision._asdict()} if collision else {}),
        )


def _archive_readiness(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    change: str,
) -> tuple[list[str], bool, tuple[str, ...]]:
    gaps = work_lane_transition_gaps(
        root,
        branch=branch,
        head=head,
        expect_head=expect_head,
        lease=lease,
        actor=os.environ.get("ETHOS_ACTOR", "").strip(),
        role_gap="archive_requires_work_lane",
        require_clean=True,
    )
    if lease.get("base_commitment_path") != f"openspec/changes/{change}/commitment.toml":
        gaps.append(f"openspec_active_change_missing:{change}")
    if not gaps:
        gaps.extend(proof_gaps(root, head))
    gaps = list(dict.fromkeys(gaps))
    if gaps:
        return gaps, False, ()
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
    commands = governance.get("commands")
    status = commands.get("status", {}) if isinstance(commands, dict) else {}
    status_payload = status.get("json", {}) if isinstance(status, dict) else {}
    artifacts = artifact_output_paths(
        root,
        status_payload if isinstance(status_payload, dict) else {},
    )
    return list(dict.fromkeys(gaps)), complete, artifacts


def _apply_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    *,
    official_complete: bool,
    completion_artifacts: tuple[str, ...],
    collision: ArchiveCollision | None = None,
) -> dict[str, object]:
    command = openspec_cli.openspec_base_command()
    if command is None:
        return lifecycle_report(
            branch, head, "blocked", ["openspec_official_cli_missing"], change=change
        )
    if collision is not None:
        move_tracked_tree(repo, collision.path, collision.preserved_path)
    archive_command = openspec_cli.archive_command(repo, change)
    result = openspec_cli.run_json(repo, command, archive_command[1:])
    mutation_gaps, archive_path = openspec_cli.archive_result(repo, change, result)
    compensation_path = collision.preserved_path if collision else archive_path
    if mutation_gaps:
        compensate_git_worktree(repo, head=head, untracked_path=compensation_path)
        return lifecycle_report(
            branch,
            head,
            "blocked",
            mutation_gaps,
            change=change,
            command=result.get("command", []),
            **({"archive_collision": collision._asdict()} if collision else {}),
        )

    normalize_projected_specs(
        repo,
        paths=dirty_changed_paths(repo),
    )
    stage_git_worktree(repo, previous=head)
    changed = tuple(
        git_stdout(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )
    scope = lease_bound_archive_scope_report(
        repo,
        changed_paths=changed,
        requested_change=change,
        official_change_complete=official_complete,
        completion_artifacts=completion_artifacts,
        preserved_archive=(collision.path, collision.preserved_path) if collision else None,
    )
    if (
        scope is None
        or scope.get("verdict") != "pass"
        or scope.get("state") != "archive_transition"
    ):
        compensate_git_worktree(repo, head=head, untracked_path=compensation_path)
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_delta_invalid"],
            change=change,
            changed_paths=list(changed),
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
                official_change_complete=official_complete,
                completion_artifacts=completion_artifacts,
            ),
        )
    except ValueError as error:
        compensate_git_worktree(repo, head=head, untracked_path=compensation_path)
        return lifecycle_report(branch, head, "blocked", [str(error)], change=change)
    if archive_commit["verdict"] != "pass":
        compensate_git_worktree(repo, head=head, untracked_path=compensation_path)
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_commit_failed"],
            change=change,
            stderr=str(archive_commit.get("error") or ""),
        )
    return _finish_archive(repo, branch, head, change, result, archive_path, changed, collision)


def _finish_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    result: dict[str, Any],
    archive_path: str,
    changed: tuple[str, ...],
    collision: ArchiveCollision | None,
) -> dict[str, object]:
    archived_head = current_tracked_head(repo)
    archived_lease = leases_by_branch(repo).get(branch, {})
    if archived_lease.get("expected_head") != archived_head:
        work_lane_ref_transition_report(
            root=repo,
            phase="committed",
            ref_name=f"refs/heads/{branch}",
            old_value=head,
            new_value=archived_head,
        )
        archived_lease = leases_by_branch(repo).get(branch, {})
    post = openspec_governance_report(repo, lifecycle=True)
    post_gaps = [str(gap) for gap in post.get("required_gaps", ())]
    if archived_lease.get("expected_head") != archived_head:
        post_gaps.append("openspec_archive_lease_not_advanced")
    if archived_lease.get("base_commitment_path") != f"{archive_path}/commitment.toml":
        post_gaps.append("openspec_archive_commitment_not_relocated")
    if post_gaps:
        return lifecycle_report(
            branch,
            archived_head,
            "repair_required",
            post_gaps,
            change=change,
            previous_head=head,
            archive_path=archive_path,
        )
    try:
        receipt = issue_archive_effect(
            repo,
            change=change,
            previous_head=head,
            head=archived_head,
            archive_path=archive_path,
            changed_paths=changed,
            lease=archived_lease,
        )
        record_attestations(repo, (receipt,))
    except (OSError, TypeError, ValueError) as error:
        return _archive_attestation_pending(
            branch,
            archived_head,
            facts=ArchiveRecovery(change, head, archive_path, changed, archived_lease),
            reason=str(error),
        )
    return lifecycle_report(
        branch,
        archived_head,
        "archived",
        [],
        change=change,
        previous_head=head,
        archive_path=archive_path,
        **({"preserved_archive_path": collision.preserved_path} if collision else {}),
        changed_paths=list(changed),
        tool_version=openspec_cli.OFFICIAL_VERSION,
        command=result["command"],
        warnings=[line for line in str(result.get("stderr") or "").splitlines() if line],
        no_op=not bool(result["json"]["archive"].get("specsUpdated")),
        totals=result["json"]["archive"].get("totals", {}),
        lease=archived_lease,
        attestation=receipt.model_dump(mode="json"),
    )


def _archive_attestation_recovery(
    root: Path,
    *,
    branch: str,
    head: str,
    lease: dict[str, object],
    change: str,
    expect_head: str,
    apply: bool,
) -> dict[str, object] | None:
    """Finish the Lease and Attestation for one exact committed archive."""
    previous_head = git_stdout(root, "rev-parse", f"{head}^")
    changed = tuple(
        git_stdout(
            root, "diff", "--name-only", "--diff-filter=ACMRTD", previous_head, head
        ).splitlines()
    )
    stale_lease = lease.get("expected_head") == expect_head and head != expect_head
    carrier = next((path for path in changed if valid_archive_carrier(path, change)), "")
    carrier = carrier if stale_lease else str(lease.get("base_commitment_path") or "")
    archive_path = carrier.removesuffix("/commitment.toml")
    if not (
        valid_archive_carrier(f"{archive_path}/commitment.toml", change)
        and exact_carrier_relocation(
            root, previous_head, head, f"openspec/changes/{change}", archive_path
        )
        and exact_archive_paths(root, head, archive_path, changed)
    ):
        return None
    if stale_lease:
        lease, outcome = _recover_archive_lease(
            root, branch, head, expect_head, change, apply=apply
        )
        if outcome is not None:
            return outcome
        expect_head = head
    if work_lane_transition_gaps(
        root,
        branch=branch,
        head=head,
        expect_head=expect_head,
        lease=lease,
        actor=os.environ.get("ETHOS_ACTOR", "").strip(),
        role_gap="archive_requires_work_lane",
        require_clean=True,
    ):
        return None
    facts = ArchiveRecovery(change, previous_head, archive_path, changed, lease)
    return _recover_archive_receipt(root, branch, head, facts, apply=apply)


def _recover_archive_receipt(
    root: Path,
    branch: str,
    head: str,
    facts: ArchiveRecovery,
    *,
    apply: bool,
) -> dict[str, object]:
    try:
        receipt = issue_archive_effect(
            root,
            change=facts.change,
            previous_head=facts.previous_head,
            head=head,
            archive_path=facts.archive_path,
            changed_paths=facts.changed_paths,
            lease=facts.lease,
        )
        selected = receipt in read_attestation_set(root)[1]
    except (OSError, TypeError, ValueError) as error:
        return _archive_recovery_report(branch, head, "blocked", [str(error)], facts)
    if selected:
        return _archive_recovery_report(
            branch,
            head,
            "blocked",
            [f"openspec_active_change_missing:{facts.change}"],
            facts,
            attestation=receipt,
        )
    if not apply:
        return _archive_recovery_report(
            branch,
            head,
            "ready_to_recover_archive_attestation",
            [],
            facts,
            attestation=receipt,
        )
    try:
        record_attestations(root, (receipt,))
    except (OSError, TypeError, ValueError) as error:
        return _archive_attestation_pending(branch, head, facts=facts, reason=str(error))
    return _archive_recovery_report(
        branch, head, "archive_attestation_recovered", [], facts, attestation=receipt
    )


def _archive_recovery_report(
    branch: str,
    head: str,
    state: str,
    gaps: list[str],
    facts: ArchiveRecovery,
    *,
    attestation: Any = None,
) -> dict[str, object]:
    return lifecycle_report(
        branch,
        head,
        state,
        gaps,
        **(facts._asdict() | {"changed_paths": list(facts.changed_paths)}),
        **({"attestation": attestation.model_dump(mode="json")} if attestation else {}),
    )


def _recover_archive_lease(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    change: str,
    *,
    apply: bool,
) -> tuple[dict[str, object], dict[str, object] | None]:
    if apply:
        try:
            lease = advance_committed_lease(
                root,
                branch=branch,
                previous_head=expect_head,
                head=head,
                failure_gap="openspec_archive_lease_not_advanced",
            )
        except ValueError as error:
            state, gaps = "repair_required", [str(error)]
        else:
            return lease, None
    else:
        state, gaps = "ready_to_recover_archive_lease", []
    return {}, lifecycle_report(
        branch,
        head,
        state,
        gaps,
        change=change,
        previous_head=expect_head,
        partial=True,
    )


def _archive_attestation_pending(
    branch: str,
    head: str,
    *,
    facts: ArchiveRecovery,
    reason: str,
) -> dict[str, object]:
    """Project the sole resumable state after archive Git and Lease effects complete."""
    command = (
        f"ethos lane archive-change --change {facts.change} --expect-head {head} --apply --json"
    )
    return _archive_recovery_report(
        branch,
        head,
        "archive_attestation_pending",
        ["openspec_archive_attestation_not_recorded"],
        facts,
    ) | {
        "partial": True,
        "recovery": {"operation": "record_archive_attestation", "reason": reason},
        "next_action": command,
    }

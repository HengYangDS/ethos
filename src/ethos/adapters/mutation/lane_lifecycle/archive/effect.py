"""Compile, execute, and recognize the exact OpenSpec archive Git effect."""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.mutation.remediation.guidance import proof_recovery_command
from ethos.adapters.openspec.archive_projection import archive_projection_updates
from ethos.adapters.openspec.archive_projection import refresh_archive_projections
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.governance import openspec_validation_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage_scope_report
from ethos.adapters.openspec.lifecycle.validation import validation_items
from ethos.adapters.repo.commit.creation import create_git_commit
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_attestation import validated_plan_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import restore_git_index
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def recover_archive_effect(
    root: Path,
    *,
    branch: str,
    head: str,
    change: str,
    apply: bool,
) -> dict[str, object] | None:
    """Recognize one already committed archive effect from durable evidence."""
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


def compile_archive_plan(
    root: Path,
    branch: str,
    change: str,
    previous_head: str,
    head: str,
    lease: dict[str, object],
    *,
    commitment: Commitment,
) -> TransitionPlan:
    if git_stdout(root, "rev-parse", f"{head}^") != previous_head:
        message = "openspec_archive_target_parent_mismatch"
        raise ValueError(message)
    changed = tuple(
        git_stdout(
            root,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTD",
            previous_head,
            head,
        ).splitlines()
    )
    scope = archive_postimage_scope_report(
        root,
        changed_paths=changed,
        requested_change=change,
        tree=current_tree(root, head),
        source_head=previous_head,
    )
    archive_path = str(scope.get("archive_path") or "") if scope is not None else ""
    if scope is None or scope.get("verdict") != "pass" or not archive_path:
        message = "openspec_archive_target_invalid"
        raise ValueError(message)
    return compile_observed_git_effect(
        root,
        commitment,
        GitEffect(
            updates={
                f"refs/heads/{branch}": GitRefUpdate(
                    expected=previous_head,
                    desired=head,
                )
            }
        ),
        head=previous_head,
        policy={
            "operation": "openspec.archive",
            "branch": branch,
            "change": change,
            "holder_ref": str(lease.get("holder_ref") or ""),
            "execution_branch": branch,
        },
        values={
            "archive_path": archive_path,
            "changed_paths": list(changed),
            "preserved_archive_path": str(scope.get("preserved_archive_path") or ""),
            "command": list(openspec_cli.archive_command(root, change)),
        },
    )


def commit_archive_postimage(
    root: Path,
    branch: str,
    change: str,
    previous_head: str,
    scope: dict[str, Any],
    *,
    commitment: Commitment | None,
    lease: dict[str, object],
    owned_mutation: bool,
    compensation_path: str,
    subject: str,
    result: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Commit one observed post-image and execute its exact Git effect."""
    if commitment is None:
        message = f"commitment_invalid:{change}"
        raise ValueError(message)
    changed = tuple(str(path) for path in scope["changed_paths"])
    original_index_tree = git_stdout(root, "write-tree")
    projection_restore: dict[str, tuple[bytes, bytes]] = {}

    def restore_failure_boundary() -> None:
        if owned_mutation:
            compensate_git_worktree(root, head=previous_head, untracked_path=compensation_path)
        else:
            restore_git_index(root, tree=original_index_tree)
            _restore_projection_postimage(root, projection_restore)

    stage_git_worktree(root, previous=previous_head)
    staged_tree = git_stdout(root, "write-tree")
    staged_paths = tuple(
        git_stdout(root, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )
    if staged_tree != scope["tree"] or staged_paths != changed:
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            previous_head,
            "blocked",
            ["openspec_archive_delta_changed"],
            change=change,
            changed_paths=list(staged_paths),
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, previous_head, subject=subject),
            ),
        )
    try:
        staged_tree = _complete_pending_archive_projection(
            root,
            previous_head,
            change,
            scope,
            staged_tree,
            staged_paths,
            projection_restore,
        )
    except (OSError, TypeError, ValueError):
        restore_failure_boundary()
        raise
    native = openspec_validation_report(root)
    native_gaps = [str(gap) for gap in native.get("required_gaps", ())]
    if native_gaps:
        restore_failure_boundary()
        repair_action = _archive_source_repair_action(root, change, native, staged_paths)
        return lifecycle_report(
            branch,
            previous_head,
            "blocked",
            native_gaps,
            change=change,
            **lifecycle_effect_outcome(
                kind="mutation_compensated" if owned_mutation else "mutation_uncompensated",
                next_action=repair_action or "ethos lane status --json",
                user_decision_required=not bool(repair_action),
            ),
        )
    committed = create_git_commit(
        root,
        tree=staged_tree,
        parent=previous_head,
        message=subject,
    )
    if committed.returncode:
        restore_failure_boundary()
        return lifecycle_report(
            branch,
            previous_head,
            "blocked",
            ["openspec_archive_commit_failed"],
            change=change,
            stderr=committed.stderr.strip(),
            **lifecycle_effect_outcome(
                kind="mutation_compensated",
                next_action=archive_recovery_command(change, previous_head, subject=subject),
            ),
        )
    target_head = committed.stdout.strip()
    try:
        plan = compile_archive_plan(
            root,
            branch,
            change,
            previous_head,
            target_head,
            lease,
            commitment=commitment,
        )
        return complete_archive(
            root,
            branch,
            change,
            plan,
            target_head,
            apply=True,
            result=result,
        )
    except (OSError, TypeError, ValueError):
        if current_tracked_head(root) == previous_head:
            restore_failure_boundary()
        raise


def _complete_pending_archive_projection(
    root: Path,
    previous_head: str,
    change: str,
    scope: dict[str, Any],
    staged_tree: str,
    staged_paths: tuple[str, ...],
    projection_restore: dict[str, tuple[bytes, bytes]],
) -> str:
    """Capture derived preimages before completing the optional archive projection."""
    if not scope.get("pending_projection_paths"):
        return staged_tree
    updates = archive_projection_updates(
        root,
        source_head=previous_head,
        tree=staged_tree,
        changed_paths=staged_paths,
    )
    projection_restore.update(
        {path: ((root / path).read_bytes(), content) for path, content in updates.items()}
    )
    return _complete_projection_postimage(root, previous_head, change)


def _archive_source_repair_action(
    root: Path,
    change: str,
    native: dict[str, Any],
    changed_paths: tuple[str, ...],
) -> str:
    """Map an official changed-spec finding back to its retained Change delta."""
    validation = native.get("validation")
    payload = validation.get("json") if isinstance(validation, dict) else None
    items = validation_items(payload) if isinstance(payload, dict) else None
    if items is None:
        return ""
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id")
        if item.get("type") != "spec" or not isinstance(identifier, str):
            continue
        capability = PurePosixPath(identifier)
        if capability.is_absolute() or not capability.parts or ".." in capability.parts:
            continue
        canonical = f"openspec/specs/{identifier}/spec.md"
        source = f"openspec/changes/{change}/specs/{identifier}/spec.md"
        if canonical not in changed_paths or not (root / source).is_file():
            continue
        if item.get("valid") is True and not item.get("issues"):
            continue
        resolved = shlex.quote(root.resolve().as_posix())
        return (
            f"ethos lane prewrite --paths {shlex.quote(source)} "
            f"--editor-root {resolved} --require-editor-root --root {resolved} --json"
        )
    return ""


def _complete_projection_postimage(root: Path, head: str, change: str) -> str:
    """Complete native and caller-supplied archive inputs through one owner."""
    refresh_archive_projections(root, source_head=head)
    completed = archive_postimage(root, head=head, change=change)
    if (
        completed is None
        or completed.scope is None
        or completed.scope.get("pending_projection_paths")
    ):
        message = "archive_projection_completion_invalid"
        raise ValueError(message)
    stage_git_worktree(root, previous=head)
    tree = git_stdout(root, "write-tree")
    if tree != completed.scope["tree"]:
        message = "openspec_archive_delta_changed"
        raise ValueError(message)
    return tree


def _restore_projection_postimage(
    root: Path,
    restore: dict[str, tuple[bytes, bytes]],
) -> None:
    """Restore only our derived edit; preserve and report any concurrent content."""
    for relative, (before, after) in restore.items():
        path = root / relative
        current = path.read_bytes()
        if current not in {before, after}:
            message = f"archive_projection_compensation_conflict:{relative}"
            raise ValueError(message)
        if current != before:
            path.write_bytes(before)


def complete_archive(
    root: Path,
    branch: str,
    change: str,
    plan: TransitionPlan,
    head: str,
    *,
    apply: bool,
    result: dict[str, Any] | None = None,
) -> dict[str, object]:
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    if (
        plan.policy.get("transition") != "openspec.archive"
        or plan.policy.get("branch") != branch
        or plan.policy.get("change") != change
    ):
        message = "openspec_archive_plan_mismatch"
        raise ValueError(message)
    archive_path = str(facts.get("archive_path") or "")
    changed = tuple(str(path) for path in facts.get("changed_paths", ()))
    if not archive_path or not changed:
        message = "openspec_archive_plan_facts_invalid"
        raise ValueError(message)
    current_lease = leases_by_branch(root).get(branch, {})
    recovering = current_tracked_head(root) == head
    validated = (
        validated_plan_attestation(
            root,
            plan.digest,
            issuer=str(current_lease.get("holder_ref") or ""),
        )
        if recovering
        else None
    )
    recognized = validated is not None
    if validated is not None:
        attestation = validated[1]
    elif not apply:
        return lifecycle_report(
            branch,
            head,
            "ready_to_recover",
            [],
            change=change,
            previous_head=str(plan.facts.get("head") or ""),
            archive_path=archive_path,
            changed_paths=list(changed),
            **lifecycle_effect_outcome(
                kind="committed_residue",
                next_action=archive_recovery_command(change, str(plan.facts.get("head") or "")),
            ),
        )
    else:
        attestation = execute_git_effect(
            root,
            plan,
            issuer=str(current_lease.get("holder_ref") or ""),
        )
        recognized = False
    post = openspec_governance_report(root, change=change, lifecycle=True)
    post_gaps = [str(gap) for gap in post.get("required_gaps", ())]
    quality_gaps = [] if post_gaps else proof_gaps(root, head, change_id=change)
    post_gaps.extend(quality_gaps)
    if post_gaps:
        return lifecycle_report(
            branch,
            head,
            "repair_required",
            post_gaps,
            change=change,
            previous_head=str(plan.facts.get("head") or ""),
            archive_path=archive_path,
            changed_paths=list(changed),
            lease=current_lease,
            attestation=attestation.model_dump(mode="json"),
            **lifecycle_effect_outcome(
                kind="committed_residue",
                next_action=(
                    f"{proof_recovery_command(head, change=change)} --root {shlex.quote(str(root))}"
                    if quality_gaps
                    else "ethos lane status --json"
                ),
                user_decision_required=not bool(quality_gaps),
            ),
        )
    archive = result.get("json", {}).get("archive", {}) if result else {}
    projected_specs = any(path.startswith("openspec/specs/") for path in changed)
    return lifecycle_report(
        branch,
        head,
        "recognized" if recognized else "recovered" if recovering else "archived",
        [],
        change=change,
        previous_head=str(plan.facts.get("head") or ""),
        archive_path=archive_path,
        **(
            {"preserved_archive_path": facts["preserved_archive_path"]}
            if facts.get("preserved_archive_path")
            else {}
        ),
        changed_paths=list(changed),
        tool_version=openspec_cli.OFFICIAL_VERSION,
        command=list(facts.get("command", ())),
        warnings=[line for line in str(result.get("stderr") or "").splitlines() if line]
        if result
        else [],
        no_op=not bool(archive.get("specsUpdated", projected_specs)),
        totals=archive.get("totals", {}),
        lease=current_lease,
        attestation=attestation.model_dump(mode="json"),
        **lifecycle_effect_outcome(kind="committed_complete"),
    )

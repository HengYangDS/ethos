"""Archive one completed OpenSpec Change as one governed Work Lane commit."""

from __future__ import annotations

import os
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import NamedTuple

import yaml

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.archive_projection import normalize_projected_specs
from ethos.adapters.openspec.governance import artifact_output_paths
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_transition_environment
from ethos.adapters.openspec.lifecycle.archive_transition import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_transition import lease_bound_archive_scope_report
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import relocated_commitment_fields_to
from ethos.adapters.repo.dirty.change_provenance import changed_paths as dirty_changed_paths
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import move_tracked_tree
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.semantic import Attestation


class _ArchiveTransition(NamedTuple):
    change: str
    previous_head: str
    head: str
    archive_path: str
    changed_paths: tuple[str, ...]


class _ArchiveCollision(NamedTuple):
    path: str
    tree: str
    preserved_path: str


class _ArchiveFinish(NamedTuple):
    branch: str
    previous_head: str
    change: str
    result: dict[str, Any]
    archive_path: str
    changed_paths: tuple[str, ...]
    collision: _ArchiveCollision | None


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
    gaps = _archive_preflight(repo, branch, head, expect_head, lease, change)
    collision = None
    if not gaps:
        try:
            collision = _archive_collision(repo, head, change)
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
            **({"archive_collision": _collision_payload(collision)} if collision else {}),
        )
    try:
        return _apply_archive(repo, branch, head, change, collision=collision)
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
            **({"archive_collision": _collision_payload(collision)} if collision else {}),
        )


def _archive_preflight(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    change: str,
) -> list[str]:
    gaps = _precondition_gaps(
        root,
        branch,
        head,
        expect_head,
        lease,
        os.environ.get("ETHOS_ACTOR", "").strip(),
        change,
    )
    if gaps:
        return gaps
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
    collision: _ArchiveCollision | None = None,
) -> dict[str, object]:
    governance = openspec_governance_report(repo, change=change, lifecycle=True)
    lifecycle = governance.get("lifecycle")
    rows = lifecycle.get("changes", []) if isinstance(lifecycle, dict) else []
    official_complete = (
        isinstance(rows, list)
        and len(rows) == 1
        and isinstance(rows[0], dict)
        and rows[0].get("name") == change
        and isinstance(rows[0].get("progress"), dict)
        and rows[0]["progress"].get("remaining") == 0
    )
    commands = governance.get("commands")
    status = commands.get("status", {}) if isinstance(commands, dict) else {}
    status_payload = status.get("json", {}) if isinstance(status, dict) else {}
    completion_artifacts = artifact_output_paths(
        repo,
        status_payload if isinstance(status_payload, dict) else {},
    )
    command = openspec_cli.openspec_base_command()
    if command is None:
        return lifecycle_report(
            branch, head, "blocked", ["openspec_official_cli_missing"], change=change
        )
    if collision is not None:
        move_tracked_tree(repo, collision.path, collision.preserved_path)
    archive_args = (
        "archive",
        change,
        "--yes",
        *(("--skip-specs",) if _skip_specs_change(repo, change) else ()),
        "--json",
    )
    result = openspec_cli.run_json(repo, command, archive_args)
    mutation_gaps, archive_path = _official_result_gaps(repo, change, result)
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
            **({"archive_collision": _collision_payload(collision)} if collision else {}),
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
        compensate_git_worktree(
            repo,
            head=head,
            untracked_path=compensation_path,
        )
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
        compensate_git_worktree(
            repo,
            head=head,
            untracked_path=compensation_path,
        )
        return lifecycle_report(branch, head, "blocked", [str(error)], change=change)
    if archive_commit["verdict"] != "pass":
        compensate_git_worktree(
            repo,
            head=head,
            untracked_path=compensation_path,
        )
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_archive_commit_failed"],
            change=change,
            stderr=str(archive_commit.get("error") or ""),
        )
    return _finish_archive(
        repo,
        _ArchiveFinish(branch, head, change, result, archive_path, changed, collision),
    )


def _skip_specs_change(root: Path, change: str) -> bool:
    """Return the exact official archive mode declared by one Change carrier."""
    path = root / "openspec" / "changes" / change / ".openspec.yaml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return False
    return isinstance(payload, dict) and payload.get("skip_specs") is True


def _finish_archive(
    repo: Path,
    finish: _ArchiveFinish,
) -> dict[str, object]:
    branch, head, change, result, archive_path, changed, collision = finish
    archived_head = current_tracked_head(repo)
    archived_lease = leases_by_branch(repo).get(branch, {})
    if archived_lease.get("expected_head") != archived_head:
        target = (
            relocated_commitment_fields_to(
                repo,
                old_head=head,
                new_head=archived_head,
                lease=archived_lease,
                carrier=f"{archive_path}/commitment.toml",
            )
            if collision
            else None
        )
        transition = work_lane_ref_transition_report(
            root=repo,
            phase="committed",
            ref_name=f"refs/heads/{branch}",
            old_value=head,
            new_value=archived_head,
        )
        if target is not None and transition.get("verdict") != "pass":
            transition = _advance_archive_lease(
                repo,
                branch=branch,
                previous_head=head,
                lease=archived_lease,
                target=target,
            )
        if transition.get("verdict") == "pass":
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
    archive_payload = result["json"]["archive"]
    try:
        receipt = _archive_attestation(
            repo,
            transition=_ArchiveTransition(change, head, archived_head, archive_path, changed),
            lease=archived_lease,
        )
        record_attestations(repo, (receipt,))
    except (OSError, TypeError, ValueError) as error:
        return _archive_attestation_pending(
            branch,
            archived_head,
            change=change,
            previous_head=head,
            archive_path=archive_path,
            changed_paths=changed,
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
        no_op=not bool(archive_payload.get("specsUpdated")),
        totals=archive_payload.get("totals", {}),
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
    """Recognize and finish the exact archive effect already selected by Git and Lease."""
    archive_path = str(lease.get("base_commitment_path") or "").removesuffix("/commitment.toml")
    if not (
        archive_path.startswith("openspec/changes/archive/") and archive_path.endswith(f"-{change}")
    ):
        return None
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
    previous_head = git_stdout(root, "rev-parse", f"{head}^")
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
    scope = (
        lease_bound_archive_scope_report(
            root,
            changed_paths=changed,
            requested_change=change,
            official_change_complete=True,
            completion_artifacts=changed,
        )
        if previous_head and changed and not gaps
        else None
    )
    if (
        scope is None
        or scope.get("verdict") != "pass"
        or scope.get("state") != "post_archive_closeout"
    ):
        return None
    receipt = _archive_attestation(
        root,
        transition=_ArchiveTransition(change, previous_head, head, archive_path, changed),
        lease=lease,
    )
    try:
        _selected_root, selected = read_attestation_set(root)
    except (OSError, TypeError, ValueError) as error:
        return lifecycle_report(
            branch,
            head,
            "blocked",
            [str(error)],
            change=change,
            previous_head=previous_head,
            archive_path=archive_path,
            changed_paths=list(changed),
        )
    if any(item.canonical_json() == receipt.canonical_json() for item in selected):
        outcome = None
    elif not apply:
        outcome = lifecycle_report(
            branch,
            head,
            "ready_to_recover_archive_attestation",
            [],
            change=change,
            previous_head=previous_head,
            archive_path=archive_path,
            changed_paths=list(changed),
            attestation=receipt.model_dump(mode="json"),
        )
    else:
        try:
            record_attestations(root, (receipt,))
        except (OSError, TypeError, ValueError) as error:
            outcome = _archive_attestation_pending(
                branch,
                head,
                change=change,
                previous_head=previous_head,
                archive_path=archive_path,
                changed_paths=changed,
                reason=str(error),
            )
        else:
            outcome = lifecycle_report(
                branch,
                head,
                "archive_attestation_recovered",
                [],
                change=change,
                previous_head=previous_head,
                archive_path=archive_path,
                changed_paths=list(changed),
                lease=lease,
                attestation=receipt.model_dump(mode="json"),
            )
    return outcome


def _archive_attestation_pending(
    branch: str,
    head: str,
    *,
    change: str,
    previous_head: str,
    archive_path: str,
    changed_paths: tuple[str, ...],
    reason: str,
) -> dict[str, object]:
    """Project the sole resumable state after archive Git and Lease effects complete."""
    command = f"ethos lane archive-change --change {change} --expect-head {head} --apply --json"
    return lifecycle_report(
        branch,
        head,
        "archive_attestation_pending",
        ["openspec_archive_attestation_not_recorded"],
        change=change,
        previous_head=previous_head,
        archive_path=archive_path,
        changed_paths=list(changed_paths),
        partial=True,
        recovery={"operation": "record_archive_attestation", "reason": reason},
        next_action=command,
    )


def _archive_collision(root: Path, head: str, change: str) -> _ArchiveCollision | None:
    """Describe the deterministic preservation target for today's immutable collision."""
    local_date = datetime.now().astimezone().date().isoformat()
    path = f"openspec/changes/archive/{local_date}-{change}"
    tree = git_stdout(root, "rev-parse", f"{head}:{path}")
    if not tree:
        return None
    preserved = collision_preservation_path(path, tree, head)
    existing = git_stdout(root, "rev-parse", f"{head}:{preserved}")
    if existing or os.path.lexists(root / preserved):
        message = "openspec_archive_collision_preservation_conflict"
        raise ValueError(message)
    return _ArchiveCollision(path, tree, preserved)


def _advance_archive_lease(
    root: Path,
    *,
    branch: str,
    previous_head: str,
    lease: dict[str, object],
    target: dict[str, str],
) -> dict[str, object]:
    """Advance the Lease after one collision-preserving archive commit."""
    try:
        updated = advance_lease_ref(
            state_database(root),
            request=LeaseOperationRequest(
                operation="advance",
                branch=branch,
                holder_ref=os.environ.get("ETHOS_ACTOR", "").strip(),
                lease_id=str(lease.get("lease_id") or ""),
                expected_epoch=integer_value(lease.get("epoch")),
                expect_head=previous_head,
                expected_expires_at=str(lease.get("expires_at") or ""),
                expected_payload_sha256=str(lease.get("payload_sha256") or ""),
                apply=True,
            ),
            binding=target,
        )
    except ValueError as error:
        return {"verdict": "block", "required_gaps": [str(error)]}
    return {"verdict": "pass", "state": "lease_ref_advanced", "lease": updated}


def _collision_payload(collision: _ArchiveCollision) -> dict[str, str]:
    return {
        "path": collision.path,
        "tree": collision.tree,
        "preserved_path": collision.preserved_path,
    }


def _archive_attestation(
    root: Path,
    *,
    transition: _ArchiveTransition,
    lease: dict[str, object],
) -> Attestation:
    change, previous_head, head, archive_path, changed_paths = transition
    repository = load_repository_commitment(root, tree_ref=head)
    commitment = load_commitment(
        root,
        carrier=f"{archive_path}/commitment.toml",
        change_id=change,
        tree_ref=head,
    )
    issued = datetime.fromtimestamp(
        int(git_stdout(root, "show", "-s", "--format=%ct", head)),
        UTC,
    )
    receipt = issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-archive",
            operation="openspec.archive",
            command=_archive_effect_command(
                root,
                head=head,
                change=change,
                archive_path=archive_path,
            ),
            subject={
                "change": change,
                "archive_path": archive_path,
                "tool_version": openspec_cli.OFFICIAL_VERSION,
            },
            before={
                "head": previous_head,
                "tree": current_tree(root, previous_head),
                "commitment_digest": commitment.digest(),
            },
            after={
                "head": head,
                "tree": current_tree(root, head),
                "archive_path": archive_path,
                "changed_paths": changed_paths,
                "lease": _archive_lease_binding(lease),
            },
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id=repository.id,
    )
    payload = receipt.model_dump(mode="python", exclude={"id"})
    payload.update(issued_at=issued, valid_from=issued)
    return Attestation.issue(payload)


def _archive_effect_command(
    root: Path,
    *,
    head: str,
    change: str,
    archive_path: str,
) -> tuple[str, ...]:
    """Derive the stable semantic command from the archived Git tree."""
    metadata = git_stdout(root, "show", f"{head}:{archive_path}/.openspec.yaml")
    try:
        declaration = yaml.safe_load(metadata) if metadata else None
    except yaml.YAMLError:
        declaration = None
    skip_specs = isinstance(declaration, dict) and declaration.get("skip_specs") is True
    return (
        "openspec",
        "archive",
        change,
        "--yes",
        *(("--skip-specs",) if skip_specs else ()),
        "--json",
    )


def _archive_lease_binding(lease: dict[str, object]) -> dict[str, object]:
    """Project only the immutable Lease coordinates consumed by archive evidence."""
    return {
        name: lease.get(name)
        for name in (
            "lease_id",
            "lane_incarnation_id",
            "lane_ref",
            "holder_ref",
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }


def _precondition_gaps(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    actor: str,
    change: str,
) -> list[str]:
    gaps = work_lane_transition_gaps(
        root,
        branch=branch,
        head=head,
        expect_head=expect_head,
        lease=lease,
        actor=actor,
        role_gap="archive_requires_work_lane",
        require_clean=True,
    )
    if lease.get("base_commitment_path") != f"openspec/changes/{change}/commitment.toml":
        gaps.append(f"openspec_active_change_missing:{change}")
    if not gaps:
        gaps.extend(proof_gaps(root, head))
    return list(dict.fromkeys(gaps))


def _official_result_gaps(root: Path, change: str, result: dict[str, Any]) -> tuple[list[str], str]:
    payload = result.get("json")
    archive = payload.get("archive") if isinstance(payload, dict) else None
    archive_path = ""
    if isinstance(archive, dict):
        absolute = str(archive.get("path") or "")
        try:
            archive_path = Path(absolute).resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            archive_path = ""
    valid = (
        result.get("exit_code") == 0
        and not result.get("parse_error")
        and isinstance(archive, dict)
        and archive.get("change") == change
        and archive_path.startswith("openspec/changes/archive/")
        and archive_path.endswith(f"-{change}")
    )
    return ([] if valid else ["openspec_archive_result_invalid"], archive_path)

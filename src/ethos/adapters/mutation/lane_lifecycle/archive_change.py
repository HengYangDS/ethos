"""Archive one completed OpenSpec Change as one governed Work Lane commit."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import NamedTuple

import yaml

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import persist_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.governance import artifact_output_paths
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_transition_environment
from ethos.adapters.openspec.lifecycle.archive_transition import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_transition import lease_bound_archive_scope_report
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import relocated_commitment_fields_to
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import exact_rename_target
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import move_tracked_tree
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.repository.hooks import initiating_hook_transaction


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
    rebuild_from: str = "",
    apply: bool = False,
) -> dict[str, object]:
    """Run official OpenSpec archive and commit its exact Lease-bound delta."""
    repo = root.resolve()
    head = current_tracked_head(repo)
    branch = git_stdout(repo, "branch", "--show-current")
    lease = leases_by_branch(repo).get(branch, {})
    if rebuild_from:
        gaps = _rebuild_preflight(repo, branch, head, expect_head, rebuild_from, lease, change)
        if gaps or not apply:
            return _report(
                branch,
                head,
                "blocked" if gaps else "ready_to_rebuild",
                gaps,
                change=change,
                rebuild_from=rebuild_from,
            )
        try:
            return _rebuild_archive(repo, branch, head, rebuild_from, change, lease)
        except (OSError, TypeError, ValueError) as error:
            return _report(
                branch,
                current_tracked_head(repo),
                "repair_required",
                [str(error)],
                change=change,
                rebuild_from=rebuild_from,
            )
    gaps = _archive_preflight(repo, branch, head, expect_head, lease, change)
    collision = _archive_collision(repo, head, change) if not gaps else None
    guard = local_state_mutation_guard(repo) if apply and not gaps else {"required_gaps": []}
    if guard["required_gaps"]:
        gaps = ["local_state_migration_required"]
    if gaps or not apply:
        return _report(
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
        return _report(
            branch,
            current_tracked_head(repo),
            "repair_required",
            [str(error)],
            change=change,
            **({"archive_collision": _collision_payload(collision)} if collision else {}),
        )


def _rebuild_preflight(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    rebuild_from: str,
    lease: dict[str, object],
    change: str,
) -> list[str]:
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    role = load_branch_role_policy(root).role_for_branch(branch)
    archive_carrier = str(lease.get("base_commitment_path") or "")
    active_carrier = f"openspec/changes/{change}/commitment.toml"
    parents = run_git(root, "rev-list", "--parents", "-n", "1", head).stdout.split()
    checks = (
        (role == ROLE_WORK_LANE, "archive_requires_work_lane"),
        (head == expect_head, "expect_head_mismatch"),
        (not git_stdout(root, "status", "--short"), "work_lane_dirty"),
        (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
        (lease.get("holder_ref") == actor, "lease_actor_mismatch"),
        (lease.get("expected_head") == head, "lease_head_stale"),
        (lease.get("expected_tree") == current_tree(root, head), "lease_tree_stale"),
        (parents == [head, rebuild_from], "openspec_archive_rebuild_parent_mismatch"),
        (
            exact_rename_target(root, rebuild_from, head, active_carrier) == archive_carrier,
            "openspec_archive_rebuild_transition_mismatch",
        ),
        (
            _archive_rebuild_paths(root, rebuild_from, head, change, archive_carrier),
            "openspec_archive_rebuild_scope_mismatch",
        ),
        (
            not _governed_archive_exists(root, head, change),
            "openspec_archive_rebuild_already_governed",
        ),
    )
    gaps = [gap for valid, gap in checks if not valid]
    if gaps:
        return list(dict.fromkeys(gaps))
    try:
        archived = load_lease_bound_commitment(root, change_id=change, lease=lease)
        active = load_commitment(
            root,
            carrier=active_carrier,
            change_id=change,
            tree_ref=rebuild_from,
        )
        if archived.digest() != active.digest():
            gaps.append("openspec_archive_rebuild_commitment_mismatch")
    except ValueError as error:
        gaps.append(str(error))
    if not gaps:
        gaps.extend(proof_gaps(root, head))
    return list(dict.fromkeys(gaps))


def _governed_archive_exists(root: Path, head: str, change: str) -> bool:
    for path in attestation_store_dir(root).glob("*.json"):
        try:
            attestation = Attestation.model_validate_json(path.read_bytes())
            output = attestation.statement.get("output")
        except (OSError, ValueError):
            continue
        if (
            attestation.predicate == "effect:openspec-archive"
            and isinstance(output, Mapping)
            and output.get("head") == head
            and attestation.statement.get("freshness", {}).get("change") == change
        ):
            return True
    return False


def _archive_rebuild_paths(
    root: Path,
    previous: str,
    head: str,
    change: str,
    archive_carrier: str,
) -> bool:
    archive_root = archive_carrier.removesuffix("/commitment.toml") + "/"
    active_root = f"openspec/changes/{change}/"
    changed = run_git(
        root,
        "diff",
        "--name-only",
        "--diff-filter=ACMRTD",
        previous,
        head,
        check=False,
    )
    return (
        changed.returncode == 0
        and bool(changed.stdout.splitlines())
        and all(
            path.startswith((active_root, archive_root, "openspec/specs/"))
            for path in changed.stdout.splitlines()
        )
    )


def _rebuild_archive(
    root: Path,
    branch: str,
    archived_head: str,
    previous_head: str,
    change: str,
    lease: dict[str, object],
) -> dict[str, object]:
    authority = load_lease_bound_commitment(root, change_id=change, lease=lease)
    effect = GitEffect(
        updates={
            f"refs/heads/{branch}": GitRefUpdate(
                expected=archived_head,
                desired=previous_head,
            )
        }
    )
    plan = compile_observed_git_effect(
        root,
        authority,
        effect,
        head=archived_head,
        policy={"operation": "openspec.archive.rebuild", "execution_branch": branch},
        prior_attestations={},
        values={"lease_generation": lease_generation(lease), "change": change},
    )

    def synchronize() -> None:
        sync_worktree(
            root,
            root,
            branch=branch,
            previous=archived_head,
            head=previous_head,
        )

    execute_git_effect(
        root,
        plan,
        issuer=str(lease["holder_ref"]),
        projection=synchronize,
    )
    rebound = leases_by_branch(root).get(branch, {})
    if not _rebuild_lease_matches(root, change=change, head=previous_head, lease=rebound):
        message = "openspec_archive_rebuild_lease_transition_failed"
        raise ValueError(message)
    rebuilt = _apply_archive(root, branch, previous_head, change)
    rebuilt["replaced_head"] = archived_head
    return rebuilt


def _rebuild_lease_matches(
    root: Path,
    *,
    change: str,
    head: str,
    lease: dict[str, object],
) -> bool:
    """Recognize the exact Lease postcondition already applied by the ref hook."""
    if lease.get("expected_head") != head or lease.get("expected_tree") != current_tree(root, head):
        return False
    try:
        load_lease_bound_commitment(root, change_id=change, lease=lease)
    except ValueError:
        return False
    return lease.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"


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
        return _report(branch, head, "blocked", ["openspec_official_cli_missing"], change=change)
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
    if mutation_gaps:
        compensate_git_worktree(repo, head=head, untracked_path=archive_path)
        return _report(
            branch,
            head,
            "blocked",
            mutation_gaps,
            change=change,
            command=result.get("command", []),
            **({"archive_collision": _collision_payload(collision)} if collision else {}),
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
            untracked_path=collision.preserved_path if collision else archive_path,
        )
        return _report(
            branch,
            head,
            "blocked",
            ["openspec_archive_delta_invalid"],
            change=change,
            changed_paths=list(changed),
        )
    try:
        with initiating_hook_transaction(repo) as hook_environment:
            archive_commit = commit_git_worktree(
                repo,
                previous=head,
                message=f"archive OpenSpec change {change}",
                environment=hook_environment
                | archive_transition_environment(
                    repo,
                    change=change,
                    head=head,
                    changed_paths=changed,
                    official_change_complete=official_complete,
                    completion_artifacts=completion_artifacts,
                ),
            )
    except ValueError as error:
        compensate_git_worktree(repo, head=head, untracked_path=archive_path)
        return _report(branch, head, "blocked", [str(error)], change=change)
    if archive_commit["verdict"] != "pass":
        compensate_git_worktree(repo, head=head, untracked_path=archive_path)
        return _report(
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
        return _report(
            branch,
            archived_head,
            "repair_required",
            post_gaps,
            change=change,
            previous_head=head,
            archive_path=archive_path,
        )
    archive_payload = result["json"]["archive"]
    receipt = _archive_attestation(
        repo,
        transition=_ArchiveTransition(change, head, archived_head, archive_path, changed),
        result=result,
        lease=archived_lease,
    )
    persist_attestation(repo, receipt)
    return _report(
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


def _archive_collision(root: Path, head: str, change: str) -> _ArchiveCollision | None:
    """Describe the deterministic preservation target for today's immutable collision."""
    local_date = datetime.now().astimezone().date().isoformat()
    path = f"openspec/changes/archive/{local_date}-{change}"
    tree = git_stdout(root, "rev-parse", f"{head}:{path}")
    if not tree:
        return None
    preserved = collision_preservation_path(path, tree, head)
    existing = git_stdout(root, "rev-parse", f"{head}:{preserved}")
    if existing and existing != tree:
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
    result: dict[str, Any],
    lease: dict[str, object],
):
    change, previous_head, head, archive_path, changed_paths = transition
    repository = load_repository_commitment(root, tree_ref=head)
    commitment = load_commitment(
        root,
        carrier=f"{archive_path}/commitment.toml",
        change_id=change,
        tree_ref=head,
    )
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-archive",
            operation="openspec.archive",
            command=tuple(str(item) for item in result["command"]),
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
                "official_result": result["json"],
                "lease": lease,
            },
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id=repository.id,
    )


def _precondition_gaps(
    root: Path,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    actor: str,
    change: str,
) -> list[str]:
    gaps: list[str] = []
    role = load_branch_role_policy(root).role_for_branch(branch)
    checks = (
        (role == ROLE_WORK_LANE, "archive_requires_work_lane"),
        (head == expect_head, "expect_head_mismatch"),
        (not git_stdout(root, "status", "--short"), "work_lane_dirty"),
        (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
        (lease.get("holder_ref") == actor, "lease_actor_mismatch"),
        (lease.get("expected_head") == head, "lease_head_stale"),
        (lease.get("expected_tree") == current_tree(root, head), "lease_tree_stale"),
        (
            lease.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml",
            f"openspec_active_change_missing:{change}",
        ),
    )
    gaps.extend(gap for valid, gap in checks if not valid)
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


def _report(
    branch: str,
    head: str,
    state: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "branch": branch,
        "head": head,
        "required_gaps": list(dict.fromkeys(gaps)),
        **details,
    }

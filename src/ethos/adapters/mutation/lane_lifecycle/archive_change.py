"""Archive one completed OpenSpec Change as one governed Work Lane commit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import persist_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import lease_bound_archive_scope_report
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_git_worktree
from ethos.adapters.repo.git_effects import stage_git_worktree
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy


class _ArchiveTransition(NamedTuple):
    change: str
    previous_head: str
    head: str
    archive_path: str
    changed_paths: tuple[str, ...]


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
    gaps = _archive_preflight(repo, branch, head, expect_head, lease, change)
    if gaps or not apply:
        return _report(
            branch,
            head,
            "blocked" if gaps else "ready_to_archive",
            gaps,
            change=change,
        )
    return _apply_archive(repo, branch, head, change)


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
) -> dict[str, object]:

    command = openspec_cli.openspec_base_command()
    if command is None:
        return _report(branch, head, "blocked", ["openspec_official_cli_missing"], change=change)
    result = openspec_cli.run_json(repo, command, ("archive", change, "--yes", "--json"))
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
        )

    stage_git_worktree(repo, previous=head)
    changed = tuple(
        git_stdout(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD").splitlines()
    )
    scope = lease_bound_archive_scope_report(
        repo,
        changed_paths=changed,
        requested_change=change,
    )
    if (
        scope is None
        or scope.get("verdict") != "pass"
        or scope.get("state") != "archive_transition"
    ):
        compensate_git_worktree(repo, head=head, untracked_path=archive_path)
        return _report(
            branch,
            head,
            "blocked",
            ["openspec_archive_delta_invalid"],
            change=change,
            changed_paths=list(changed),
        )
    archive_commit = commit_git_worktree(
        repo,
        previous=head,
        message=f"archive OpenSpec change {change}",
    )
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

    archived_head = current_tracked_head(repo)
    archived_lease = leases_by_branch(repo).get(branch, {})
    if archived_lease.get("expected_head") != archived_head:
        transition = work_lane_ref_transition_report(
            root=repo,
            phase="committed",
            ref_name=f"refs/heads/{branch}",
            old_value=head,
            new_value=archived_head,
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
        changed_paths=list(changed),
        tool_version=openspec_cli.OFFICIAL_VERSION,
        command=result["command"],
        warnings=[line for line in str(result.get("stderr") or "").splitlines() if line],
        no_op=not bool(archive_payload.get("specsUpdated")),
        totals=archive_payload.get("totals", {}),
        lease=archived_lease,
        attestation=receipt.model_dump(mode="json"),
    )


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

"""Compile, execute, and recognize the exact OpenSpec archive Git effect."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage_scope_report
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import validated_plan_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


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
    post = openspec_governance_report(root, lifecycle=True)
    post_gaps = [str(gap) for gap in post.get("required_gaps", ())]
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
                next_action="ethos lane status --json",
                user_decision_required=True,
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

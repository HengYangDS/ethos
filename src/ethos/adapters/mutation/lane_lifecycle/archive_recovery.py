"""Close committed OpenSpec archive effects through Lease and Attestation recovery."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import advance_committed_lease
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_binding import exact_carrier_relocation
from ethos.adapters.openspec.lifecycle.archive_binding import valid_archive_carrier
from ethos.adapters.openspec.lifecycle.archive_effect import exact_archive_paths
from ethos.adapters.openspec.lifecycle.archive_effect import issue_archive_effect
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import leases_by_branch

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


class ArchiveRecovery(NamedTuple):
    """Exact committed archive facts used by recovery and reporting."""

    change: str
    previous_head: str
    archive_path: str
    changed_paths: tuple[str, ...]
    lease: dict[str, object]


def archive_recovery_next_action(root: Path, gap: str, *, target_head: str = "") -> str:
    """Return one exact public continuation for a committed archive Lease gap."""
    if not gap.startswith("lease_head_stale:"):
        return ""
    branch = git_stdout(root, "branch", "--show-current")
    lease = leases_by_branch(root).get(branch, {})
    expected_head = str(lease.get("expected_head") or "")
    head = current_tracked_head(root)
    if target_head and target_head != head:
        return ""
    try:
        change = load_lease_bound_commitment(root, lease=lease).id.removeprefix("change:")
    except (OSError, TypeError, ValueError):
        return ""
    facts = _committed_archive_facts(
        root,
        head=head,
        lease=lease,
        change=change,
        expect_head=expected_head,
    )
    return archive_recovery_command(change, expected_head) if facts is not None else ""


def archive_transition_candidate(root: Path, *, lease: dict[str, object], head: str) -> bool:
    """Return whether a target attempts to move the bound carrier into the archive."""
    old_head = str(lease.get("expected_head") or "")
    try:
        change = load_lease_bound_commitment(root, lease=lease).id.removeprefix("change:")
    except ValueError:
        return False
    if git_stdout(root, "rev-parse", f"{head}^") != old_head:
        return False
    changed = git_stdout(
        root, "diff", "--name-only", "--diff-filter=ACMRTD", old_head, head
    ).splitlines()
    source = f"openspec/changes/{change}/commitment.toml"
    return not git_stdout(root, "rev-parse", f"{head}:{source}") and any(
        valid_archive_carrier(path, change) for path in changed
    )


def archive_preflight_report(
    branch: str,
    head: str,
    change: str,
    gaps: list[str],
    *,
    lease: dict[str, object] | None = None,
) -> dict[str, object]:
    """Project the first exact coordinate failure before any archive effect."""
    first = gaps[0]
    state = {
        f"work_lane_missing_lease:{branch}": "lease_missing",
        f"work_lane_lease_expired:{branch}": "lease_expired",
        "lease_actor_mismatch": "different_holder",
    }.get(first, "blocked")
    generation = lease or {}
    next_action = "ethos lane status --json"
    user_decision_required = state in {"lease_missing", "different_holder"}
    if state == "different_holder":
        next_action = (
            "ethos attestation query --predicate lane-resolution:takeover "
            f"--subject git:branch:{branch} --json"
        )
    elif state == "lease_expired":
        next_action = (
            "ethos lane lease resume "
            f"--lease-id {generation.get('lease_id', '')} "
            f"--epoch {generation.get('epoch', '')} "
            f"--expect-head {generation.get('expected_head') or head} "
            f"--expires-at {generation.get('expires_at', '')} "
            f"--payload-sha256 {generation.get('payload_sha256', '')} "
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
            next_action=next_action,
            user_decision_required=user_decision_required,
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
    """Preserve the first mutation gap while reporting exact compensation residue."""
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


def finish_archive(
    repo: Path,
    branch: str,
    head: str,
    change: str,
    result: dict[str, Any],
    archive_path: str,
    changed: tuple[str, ...],
    *,
    preserved_archive_path: str = "",
    ownerless: bool = False,
) -> dict[str, object]:
    """Close one committed archive through exact Lease and Attestation effects."""
    archived_head = current_tracked_head(repo)
    archived_lease = leases_by_branch(repo).get(branch, {})
    if not ownerless and archived_lease.get("expected_head") != archived_head:
        work_lane_ref_transition_report(
            root=repo,
            phase="committed",
            ref_name=f"refs/heads/{branch}",
            old_value=head,
            new_value=archived_head,
        )
        archived_lease = leases_by_branch(repo).get(branch, {})
    post = openspec_governance_report(repo, lifecycle=True) if not ownerless else {}
    post_gaps = [str(gap) for gap in post.get("required_gaps", ())]
    if not ownerless and archived_lease.get("expected_head") != archived_head:
        post_gaps.append("openspec_archive_lease_not_advanced")
    if not ownerless and archived_lease.get("base_commitment_path") != (
        f"{archive_path}/commitment.toml"
    ):
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
            **lifecycle_effect_outcome(
                kind="committed_residue",
                next_action="ethos lane status --json",
                user_decision_required=True,
            ),
        )
    facts = ArchiveRecovery(change, head, archive_path, changed, archived_lease)
    observed = _archive_receipt(repo, archived_head, facts, apply=True)
    receipt, persisted, _reason = observed
    if receipt is None or not persisted:
        return _recover_archive_receipt(
            repo,
            branch,
            archived_head,
            facts,
            apply=True,
            observed=observed,
        )
    archive = result.get("json", {}).get("archive", {}) if result else {}
    projected_specs = any(path.startswith("openspec/specs/") for path in changed)
    return lifecycle_report(
        branch,
        archived_head,
        "archived",
        [],
        change=change,
        previous_head=head,
        archive_path=archive_path,
        **({"preserved_archive_path": preserved_archive_path} if preserved_archive_path else {}),
        changed_paths=list(changed),
        tool_version=openspec_cli.OFFICIAL_VERSION,
        command=result.get("command", []),
        warnings=[line for line in str(result.get("stderr") or "").splitlines() if line],
        no_op=not bool(archive.get("specsUpdated", projected_specs)),
        totals=archive.get("totals", {}),
        lease=archived_lease,
        attestation=receipt.model_dump(mode="json"),
        **lifecycle_effect_outcome(kind="committed_complete"),
    )


def archive_attestation_recovery(
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
    facts = _committed_archive_facts(
        root,
        head=head,
        lease=lease,
        change=change,
        expect_head=expect_head,
    )
    if facts is None:
        return None
    previous_head = facts.previous_head
    changed = facts.changed_paths
    stale_lease = lease.get("expected_head") == expect_head and head != expect_head
    ownerless = not lease
    archive_path = facts.archive_path
    outcome: dict[str, object] | None = None
    if ownerless:
        command = archive_recovery_command(change, head)
        if not apply:
            outcome = lifecycle_report(
                branch,
                head,
                "ready_to_recover_ownerless_archive",
                [],
                change=change,
                previous_head=previous_head,
                archive_path=archive_path,
                changed_paths=list(changed),
                partial=True,
                **lifecycle_effect_outcome(
                    kind="lease_finalization_pending",
                    next_action=command,
                ),
            )
        elif expect_head != head:
            outcome = lifecycle_report(
                branch,
                head,
                "blocked",
                ["expect_head_mismatch"],
                change=change,
                previous_head=previous_head,
                archive_path=archive_path,
                changed_paths=list(changed),
                **lifecycle_effect_outcome(
                    kind="lease_finalization_pending",
                    next_action=command,
                    user_decision_required=True,
                ),
            )
    if outcome is None and stale_lease:
        if not apply:
            outcome = lifecycle_report(
                branch,
                head,
                "ready_to_recover_archive_lease",
                [],
                change=change,
                previous_head=expect_head,
                partial=True,
                **lifecycle_effect_outcome(
                    kind="lease_finalization_pending",
                    next_action=archive_recovery_command(change, expect_head),
                ),
            )
        else:
            try:
                lease = advance_committed_lease(
                    root,
                    branch=branch,
                    previous_head=expect_head,
                    head=head,
                    failure_gap="openspec_archive_lease_not_advanced",
                )
            except ValueError as error:
                outcome = lifecycle_report(
                    branch,
                    head,
                    "repair_required",
                    [str(error)],
                    change=change,
                    previous_head=expect_head,
                    partial=True,
                    **lifecycle_effect_outcome(
                        kind="lease_finalization_pending",
                        next_action="ethos lane status --json",
                        user_decision_required=True,
                    ),
                )
            else:
                expect_head = head
                facts = facts._replace(lease=lease)
    if (
        outcome is None
        and lease
        and work_lane_transition_gaps(
            root,
            branch=branch,
            head=head,
            expect_head=expect_head,
            lease=lease,
            actor=os.environ.get("ETHOS_ACTOR", "").strip(),
            role_gap="archive_requires_work_lane",
            require_clean=True,
        )
    ):
        return None
    return outcome or _recover_archive_receipt(root, branch, head, facts, apply=apply)


def _committed_archive_facts(
    root: Path,
    *,
    head: str,
    lease: dict[str, object],
    change: str,
    expect_head: str,
) -> ArchiveRecovery | None:
    """Recognize one exact direct-child archive post-image from Git facts."""
    previous_head = git_stdout(root, "rev-parse", f"{head}^")
    if lease and previous_head != expect_head:
        return None
    changed = tuple(
        git_stdout(
            root, "diff", "--name-only", "--diff-filter=ACMRTD", previous_head, head
        ).splitlines()
    )
    stale_lease = lease.get("expected_head") == expect_head and head != expect_head
    ownerless = not lease
    carrier = next((path for path in changed if valid_archive_carrier(path, change)), "")
    carrier = carrier if stale_lease or ownerless else str(lease.get("base_commitment_path") or "")
    archive_path = carrier.removesuffix("/commitment.toml")
    if not (
        valid_archive_carrier(f"{archive_path}/commitment.toml", change)
        and exact_carrier_relocation(
            root, previous_head, head, f"openspec/changes/{change}", archive_path
        )
        and exact_archive_paths(root, head, archive_path, changed)
    ):
        return None
    return ArchiveRecovery(change, previous_head, archive_path, changed, lease)


def _recover_archive_receipt(
    root: Path,
    branch: str,
    head: str,
    facts: ArchiveRecovery,
    *,
    apply: bool,
    observed: tuple[Attestation | None, bool, str] | None = None,
) -> dict[str, object]:
    """Project or persist the sole terminal archive Attestation."""
    receipt, persisted, reason = observed or _archive_receipt(root, head, facts, apply=apply)
    details = facts._asdict() | {"changed_paths": list(facts.changed_paths)}
    command = archive_recovery_command(facts.change, head)
    if receipt is not None:
        state = (
            "archive_attestation_recovered" if persisted else "ready_to_recover_archive_attestation"
        )
        return lifecycle_report(
            branch,
            head,
            state,
            [],
            **details,
            **lifecycle_effect_outcome(
                kind="committed_complete" if persisted else "terminal_attestation_pending",
                next_action="" if persisted else command,
            ),
            attestation=receipt.model_dump(mode="json"),
        )
    if apply:
        return lifecycle_report(
            branch,
            head,
            "archive_attestation_pending",
            ["openspec_archive_attestation_not_recorded"],
            **details,
            **lifecycle_effect_outcome(
                kind="terminal_attestation_pending",
                next_action=command,
            ),
            partial=True,
            recovery={"operation": "record_archive_attestation", "reason": reason},
        )
    return lifecycle_report(
        branch,
        head,
        "blocked",
        [reason],
        **details,
        **lifecycle_effect_outcome(
            kind="committed_residue",
            next_action="ethos lane status --json",
            user_decision_required=True,
        ),
    )


def _archive_receipt(
    root: Path,
    head: str,
    facts: ArchiveRecovery,
    *,
    apply: bool,
) -> tuple[Attestation | None, bool, str]:
    """Select or record the sole exact archive Attestation at the storage boundary."""
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
        if receipt in read_attestation_set(root)[1]:
            return receipt, True, ""
        if apply:
            selected = record_attestation_once(root, receipt)
            if selected != receipt:
                return None, False, "attestation_set_semantic_collision"
            return receipt, True, ""
    except (OSError, TypeError, ValueError) as error:
        return None, False, str(error)
    else:
        return receipt, False, ""

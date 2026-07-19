"""Policy for exceptional unbound Work Lane retirement."""

from pathlib import Path
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

EVENT = "lane_retire/unbound_exceptional"
_CONTROL_ROOT_UNAVAILABLE = "unbound_retire_accepted_control_root_unavailable"


def _failed(*, first: bool = False, **checks: bool) -> list[str]:
    gaps = [gap for gap, failed in checks.items() if failed]
    return gaps[:1] if first else gaps


def admission_gaps(  # noqa: PLR0913, RUF100 - exact admission preserves bound state dimensions
    repo: Path,
    *,
    branch: str,
    expect_head: str,
    reason: str,
    apply: bool,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    observed: dict[str, Any],
) -> list[str]:
    """Return every fail-closed admission gap before a ref effect."""
    branch_gap = branch_admission_gap(repo, branch=branch, observed=observed)
    protected = observed["protected_refs"]
    gaps = [branch_gap] if branch_gap else []
    gaps += _failed(
        retire_reason_required=not reason,
        expect_head_required=not expect_head,
        expect_head_mismatch=bool(expect_head) and expect_head != observed["head"],
        unbound_retire_protected_ref_unavailable=not isinstance(protected, dict)
        or not all(protected.values()),
    )
    gaps += chronicle_gaps(observed["chronicle"], branch=branch, head=str(observed["head"]))
    gaps += _failed(
        authorization_required=apply and not authorized,
        unbound_retire_requires_break_glass=apply and not break_glass,
        irreversible_confirmation_required=apply and not confirm_irreversible,
    )
    return sorted(set(gaps))


def branch_admission_gap(repo: Path, *, branch: str, observed: dict[str, Any]) -> str:
    """Return the first target/ref/lifecycle mismatch for this transition."""
    gaps = _failed(
        first=True,
        unbound_retire_branch_required=not branch,
        unbound_retire_not_work_lane=load_branch_role_policy(repo).role_for_branch(branch)
        != ROLE_WORK_LANE,
        unbound_retire_branch_not_found=not str(observed["head"]),
        unbound_retire_ref_not_unbound=not bool(observed["status_unbound"]),
        unbound_retire_worktree_binding_drift=observed["worktree_binding"] != "unbound",
        unbound_retire_not_accepted_ancestor=observed["relation_to_accepted"]
        != "ancestor_of_accepted",
    )
    return gaps[0] if gaps else ""


def lease_relinquish_gap(observed: dict[str, object], *, holder_ref: str) -> str:
    """Require an active source lease to match this exact invocation."""
    if not bool(observed[observation.HAS_ACTIVE_LEASE]):
        return ""
    lease = cast("dict[str, object]", observed["active_lease"])
    invalid = (
        not holder_ref
        or str(lease.get("holder_ref") or "") != holder_ref
        or not str(lease.get("lease_id") or "")
        or str(lease.get("expected_head") or "") != str(observed.get("head") or "")
    )
    return "unbound_retire_active_lease" if invalid else ""


def active_lease_gaps(observed: dict[str, object]) -> list[str]:
    """Require no active lease after relinquishment and before ref deletion."""
    return ["unbound_retire_active_lease"] if observed[observation.HAS_ACTIVE_LEASE] else []


def chronicle_gaps(chronicle: dict[str, Any], *, branch: str, head: str) -> list[str]:
    """Require accepted, exact Chronicle and Claim evidence in priority order."""
    return (
        reference_gaps(chronicle)
        or target_gaps(chronicle, branch=branch, head=head)
        or claim_gaps(chronicle)
    )


def reference_gaps(chronicle: dict[str, Any]) -> list[str]:
    """Validate Chronicle path and accepted-byte identity."""
    return _failed(
        first=True,
        unbound_retire_chronicle_ref_required=not chronicle["ref"],
        unbound_retire_chronicle_ref_invalid=not chronicle["path_valid"],
        unbound_retire_chronicle_missing=not chronicle[observation.HAS_LOCAL_CHRONICLE],
        unbound_retire_chronicle_not_accepted=not chronicle[observation.HAS_ACCEPTED_CHRONICLE],
        unbound_retire_chronicle_content_drift=not chronicle["byte_identical_to_accepted"],
    )


def target_gaps(chronicle: dict[str, Any], *, branch: str, head: str) -> list[str]:
    """Require the Chronicle to name the exact exceptional target."""
    return _failed(
        first=True,
        unbound_retire_chronicle_event_missing=chronicle["event"] != EVENT,
        unbound_retire_chronicle_target_mismatch=chronicle["target_branch"] != branch
        or chronicle["target_head"] != head,
    )


def claim_gaps(chronicle: dict[str, Any]) -> list[str]:
    """Require the Chronicle-named active Claim to match accepted bytes."""
    return _failed(
        first=True,
        unbound_retire_chronicle_claim_missing=not chronicle["target_claim"],
        unbound_retire_claim_missing=not chronicle[observation.HAS_LOCAL_CLAIM]
        or not chronicle[observation.HAS_ACCEPTED_CLAIM],
        unbound_retire_claim_content_drift=not chronicle["claim_byte_identical_to_accepted"],
        unbound_retire_claim_target_mismatch=not chronicle["claim_id_matches_target"]
        or not chronicle["claim_active"],
    )


def accepted_control_root(
    status: dict[str, object], *, accepted_head: str
) -> tuple[Path | None, str]:
    """Find the current accepted-root checkout owning durable local records."""
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None, _CONTROL_ROOT_UNAVAILABLE
    for item in worktrees:
        if not isinstance(item, dict) or item.get("role") != ROLE_ACCEPTED_ROOT:
            continue
        raw_path = str(item.get("path") or "")
        root = Path(raw_path).resolve() if raw_path else None
        if root is None or not root.is_dir():
            return None, _CONTROL_ROOT_UNAVAILABLE
        current = observation.ref_head(root, "HEAD")
        if current and current == accepted_head:
            return root, ""
        return None, "unbound_retire_accepted_control_root_stale"
    return None, _CONTROL_ROOT_UNAVAILABLE


def post_effect_gaps(
    *, before: dict[str, Any], after: dict[str, Any], deleted: object
) -> list[str]:
    """Verify that compare-and-delete achieved no more or less."""
    return sorted(
        set(
            _failed(
                unbound_retire_ref_delete_failed=int(getattr(deleted, "returncode", 1)) != 0,
                unbound_retire_protected_refs_changed=before["protected_refs"]
                != after["protected_refs"],
                unbound_retire_chronicle_changed=observation.chronicle_binding(before)
                != observation.chronicle_binding(after),
                unbound_retire_ref_remove_not_observed=bool(after["head"]),
                unbound_retire_status_postcondition_not_observed=bool(after["status_unbound"])
                or after["worktree_binding"] == "unbound",
                unbound_retire_active_lease=bool(after[observation.HAS_ACTIVE_LEASE]),
            )
        )
    )

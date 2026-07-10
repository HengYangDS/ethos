"""Product operations over generation-bound local Lane Leases.

These operations bind one exact request to Git and ignored SQLite observations.
They coordinate cooperative writers; they do not mint identity or authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state import accept_lease_handoff
from ethos.adapters.store.state import normalize_lease
from ethos.adapters.store.state import offer_lease_handoff
from ethos.adapters.store.state import renew_lease
from ethos.adapters.store.state import resume_lease
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.coordination import HolderRef


def normalize_work_lane_lease(
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    expect_head: str,
    apply: bool,
) -> dict[str, object]:
    """Normalize one exact legacy lease observation without adopting unknown state."""
    return _lease_lifecycle_operation(
        root=root,
        operation="normalize",
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=None,
        expect_head=expect_head,
        apply=apply,
    )


def renew_work_lane_lease(
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    ttl_seconds: int,
    apply: bool,
) -> dict[str, object]:
    """Renew one exact, unexpired local lease generation."""
    return _lease_lifecycle_operation(
        root=root,
        operation="renew",
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        ttl_seconds=ttl_seconds,
        apply=apply,
    )


def resume_work_lane_lease(
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    ttl_seconds: int,
    contrary_decision: bool,
    apply: bool,
) -> dict[str, object]:
    """Resume one expired lease only for its previous holder and generation."""
    extra_gaps = ("lease_resume_blocked_by_decision",) if contrary_decision else ()
    return _lease_lifecycle_operation(
        root=root,
        operation="resume",
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        ttl_seconds=ttl_seconds,
        apply=apply,
        extra_gaps=extra_gaps,
    )


def offer_work_lane_handoff(
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    apply: bool,
) -> dict[str, object]:
    """Offer one local holder handoff without changing the current holder."""
    return _lease_lifecycle_operation(
        root=root,
        operation="handoff_offer",
        branch=branch,
        holder_ref=holder_ref,
        target_holder_ref=target_holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        apply=apply,
    )


def accept_work_lane_handoff(
    *,
    root: Path,
    branch: str,
    target_holder_ref: str,
    offer_id: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    holder_quiesced: bool,
    ttl_seconds: int,
    apply: bool,
) -> dict[str, object]:
    """Accept one exact offer and replace the local holder plus generation."""
    extra_gaps = () if holder_quiesced else ("holder_quiescence_confirmation_required",)
    return _lease_lifecycle_operation(
        root=root,
        operation="handoff_accept",
        branch=branch,
        holder_ref=target_holder_ref,
        target_holder_ref=target_holder_ref,
        offer_id=offer_id,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        holder_quiesced=holder_quiesced,
        ttl_seconds=ttl_seconds,
        apply=apply,
        confirmation_present=holder_quiesced,
        extra_gaps=extra_gaps,
    )


def _lease_lifecycle_operation(
    *,
    root: Path,
    operation: str,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int | None,
    expect_head: str,
    apply: bool,
    ttl_seconds: int = 86_400,
    target_holder_ref: str = "",
    offer_id: str = "",
    holder_quiesced: bool = False,
    confirmation_present: bool = False,
    extra_gaps: tuple[str, ...] = (),
) -> dict[str, object]:
    repo = repo_root(root)
    status = workspace_status(repo)
    current_branch = str(status.get("branch") or "")
    current_head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    expected_state, holder_gaps = _lease_expected_state(
        repo=repo,
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        target_holder_ref=target_holder_ref,
        offer_id=offer_id,
    )
    gaps = _lease_request_gaps(
        operation=operation,
        status=status,
        current_branch=current_branch,
        current_head=current_head,
        branch=branch,
        expect_head=expect_head,
        lease_id=lease_id,
        epoch=epoch,
        ttl_seconds=ttl_seconds,
        offer_id=offer_id,
        initial=extra_gaps + holder_gaps,
    )
    request = MutationRequest(
        command=f"lane-{operation.replace('_', '-')}",
        apply=apply,
        authorized=confirmation_present,
        expect_head=expect_head or None,
    )
    result = _initial_lease_result(branch=branch, apply=apply, operation=operation, gaps=gaps)
    if apply and not gaps:
        _apply_lease_effect(
            result=result,
            db_path=_state_root(status, repo) / ".ethos" / "state" / "state.sqlite",
            operation=operation,
            branch=branch,
            expected_state=expected_state,
            offer_id=offer_id,
            lease_id=lease_id,
            epoch=epoch or 0,
            expect_head=expect_head,
            holder_quiesced=holder_quiesced,
            ttl_seconds=ttl_seconds,
        )
    required_gaps = tuple(str(gap) for gap in cast("list[object]", result["required_gaps"]))
    result["mutation"] = mutation_envelope(
        request,
        action=f"lane.lease.{operation.replace('_', '.')}",
        resource=f"refs/heads/{branch}",
        expected_state=expected_state,
        verdict=cast("Any", "allow" if result["ok"] else "block"),
        required_gaps=required_gaps,
        why=(str(result["state"]),) if result["ok"] else (),
        state=str(result["state"]),
        identity_basis="holder_ref_equality",
        evidence_boundary="current_git_and_local_lease_observation",
        enforcement_boundary="local_sqlite_compare_and_swap",
        verifier_provenance="current_worktree_runner",
    )
    return result


def _lease_expected_state(
    *,
    repo: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int | None,
    expect_head: str,
    target_holder_ref: str,
    offer_id: str,
) -> tuple[dict[str, object], tuple[str, ...]]:
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "branch": branch,
        "head": expect_head,
        "holder_ref": holder_ref,
        "lease_id": lease_id,
        "epoch": epoch or 0,
        "target_holder_ref": target_holder_ref,
        "offer_id": offer_id,
    }
    try:
        expected_state["holder_ref"] = HolderRef.parse(holder_ref).serialize()
        if target_holder_ref:
            expected_state["target_holder_ref"] = HolderRef.parse(target_holder_ref).serialize()
    except ValueError:
        return expected_state, ("holder_ref_invalid",)
    return expected_state, ()


def _lease_request_gaps(
    *,
    operation: str,
    status: dict[str, object],
    current_branch: str,
    current_head: str,
    branch: str,
    expect_head: str,
    lease_id: str,
    epoch: int | None,
    ttl_seconds: int,
    offer_id: str,
    initial: tuple[str, ...],
) -> list[str]:
    gaps = list(initial)
    if status.get("role") != ROLE_WORK_LANE:
        gaps.append("work_lane_required")
    if current_branch != branch:
        gaps.append("lane_branch_mismatch")
    if not expect_head:
        gaps.append("expect_head_required")
    elif current_head != expect_head:
        gaps.append("expect_head_mismatch")
    if not lease_id:
        gaps.append("lease_id_required")
    if operation != "normalize" and (epoch is None or epoch < 1):
        gaps.append("lease_epoch_required")
    if ttl_seconds < 1:
        gaps.append("lease_ttl_invalid")
    if operation == "handoff_accept" and not offer_id:
        gaps.append("handoff_offer_id_required")
    return list(dict.fromkeys(gaps))


def _initial_lease_result(
    *, branch: str, apply: bool, operation: str, gaps: list[str]
) -> dict[str, object]:
    return {
        "ok": not gaps,
        "state": "planned" if not apply and not gaps else "blocked" if gaps else operation,
        "branch": branch,
        "lease": {},
        "handoff_offer": {},
        "receipt": {},
        "required_gaps": gaps,
    }


def _apply_lease_effect(
    *,
    result: dict[str, object],
    db_path: Path,
    operation: str,
    branch: str,
    expected_state: dict[str, object],
    offer_id: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    holder_quiesced: bool,
    ttl_seconds: int,
) -> None:
    try:
        effect = _apply_lease_lifecycle_operation(
            db_path=db_path,
            operation=operation,
            branch=branch,
            holder_ref=str(expected_state["holder_ref"]),
            target_holder_ref=str(expected_state["target_holder_ref"]),
            offer_id=offer_id,
            lease_id=lease_id,
            epoch=epoch,
            expect_head=expect_head,
            holder_quiesced=holder_quiesced,
            ttl_seconds=ttl_seconds,
        )
    except ValueError as exc:
        result.update(ok=False, state="blocked", required_gaps=[str(exc)])
        return
    result["handoff_offer" if operation == "handoff_offer" else "lease"] = effect
    result["state"] = {
        "normalize": "normalized",
        "renew": "renewed",
        "resume": "resumed",
        "handoff_offer": "handoff_offered",
        "handoff_accept": "handoff_accepted",
    }[operation]
    result["receipt"] = _lease_operation_receipt(
        operation=operation,
        branch=branch,
        applied=True,
        effect=effect,
    )


def _apply_lease_lifecycle_operation(
    *,
    db_path: Path,
    operation: str,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    offer_id: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    holder_quiesced: bool,
    ttl_seconds: int,
) -> dict[str, object]:
    if operation == "normalize":
        return normalize_lease(
            db_path,
            subject=branch,
            holder_ref=holder_ref,
            expected_lease_id=lease_id,
            expected_head=expect_head,
        )
    if operation == "renew":
        return renew_lease(
            db_path,
            subject=branch,
            holder_ref=holder_ref,
            expected_lease_id=lease_id,
            expected_epoch=epoch,
            expected_head=expect_head,
            ttl_seconds=ttl_seconds,
        )
    if operation == "resume":
        return resume_lease(
            db_path,
            subject=branch,
            holder_ref=holder_ref,
            expected_lease_id=lease_id,
            expected_epoch=epoch,
            expected_head=expect_head,
            ttl_seconds=ttl_seconds,
        )
    if operation == "handoff_offer":
        return offer_lease_handoff(
            db_path,
            subject=branch,
            holder_ref=holder_ref,
            expected_lease_id=lease_id,
            expected_epoch=epoch,
            target_holder_ref=target_holder_ref,
            expected_head=expect_head,
        )
    if operation == "handoff_accept":
        return accept_lease_handoff(
            db_path,
            subject=branch,
            target_holder_ref=target_holder_ref,
            offer_id=offer_id,
            expected_lease_id=lease_id,
            expected_epoch=epoch,
            expected_head=expect_head,
            holder_quiesced=holder_quiesced,
            ttl_seconds=ttl_seconds,
        )
    raise ValueError(f"lease_operation_unknown:{operation}")


def _state_root(status: dict[str, object], default_root: Path) -> Path:
    """Resolve the accepted checkout that owns Git-common-directory local state."""
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            if worktree.get("role") == ROLE_ACCEPTED_ROOT and worktree.get("path"):
                return Path(str(worktree["path"]))
    return default_root


def _lease_operation_receipt(
    *, operation: str, branch: str, applied: bool, effect: dict[str, object]
) -> dict[str, object]:
    return {
        "receipt_id": f"receipt:{operation}:{effect.get('lease_id') or effect.get('offer_id')}",
        "operation": operation.replace("handoff_", "handoff-"),
        "branch": branch,
        "applied": applied,
        "lease_id": str(effect.get("lease_id") or ""),
        "epoch": int(effect.get("epoch") or 0),
        "expected_head": str(effect.get("expected_head") or ""),
        "mints_authority": False,
        "transferable": False,
    }

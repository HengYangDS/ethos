"""Native exceptional retirement of one accepted-policy-bound unbound Work Lane ref."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
import ethos.adapters.mutation.lane_retirement.unbound.reporting.core as reporting
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease

if TYPE_CHECKING:
    from pathlib import Path


def retire_unbound_work_lane_ref(  # noqa: PLR0913, RUF100 - exact retirement protocol shape
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    chronicle_ref: str = "",
    apply: bool = False,
    authorized: bool = False,
    break_glass: bool = False,
    confirm_irreversible: bool = False,
) -> dict[str, object]:
    """Retire exactly one accepted-policy-bound unbound ``work/*`` ref."""
    repo = repo_root(root)
    branch, expected, reason, chronicle_ref = (
        branch.strip(),
        (expect_head or "").strip(),
        reason.strip(),
        chronicle_ref.strip(),
    )
    before = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    gaps = policy.admission_gaps(
        repo,
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=apply,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observed=before,
    )
    lease_gap = policy.lease_relinquish_gap(
        before,
        holder_ref=lane_retirement_shared.current_holder_ref(),
    )
    if lease_gap:
        gaps.append(lease_gap)
    result = reporting.report(
        branch=branch,
        expect_head=expected,
        reason=reason,
        chronicle_ref=chronicle_ref,
        apply=apply,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observed=before,
        gaps=gaps,
    )
    if gaps or not apply:
        return result
    return _apply_retirement(
        repo=repo,
        branch=branch,
        expected=expected,
        reason=reason,
        chronicle_ref=chronicle_ref,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        before=before,
        result=result,
        holder_ref=lane_retirement_shared.current_holder_ref(),
    )


def _apply_retirement(  # noqa: PLR0913, RUF100 - bound irreversible transition shape
    *,
    repo: Path,
    branch: str,
    expected: str,
    reason: str,
    chronicle_ref: str,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    before: dict[str, object],
    result: dict[str, object],
    holder_ref: str,
) -> dict[str, object]:
    """Apply an already-admitted native exceptional retirement."""

    control_root, control_gap = policy.accepted_control_root(
        cast("dict[str, object]", before["status"]),
        accepted_head=str(before["accepted_head"]),
    )
    if control_root is None:
        return reporting.blocked(result, [control_gap])
    records_root = control_root.parent / f"{control_root.name}-records"
    operation_id = records.operation_id(
        branch=branch,
        expect_head=expected,
        accepted_head=str(before["accepted_head"]),
        protected_refs=cast("dict[str, str]", before["protected_refs"]),
        claim_id=str(before["claim_id"]),
        chronicle=observation.chronicle_binding(before),
        reason=reason,
        observation_sha256=str(before["observation_sha256"]),
    )
    attempt = records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        observation=before,
    )
    try:
        attempt_path = records.write_record(
            records.attempt_path(records_root, operation_id),
            attempt,
            kind=records.ATTEMPT_KIND,
        )
    except (OSError, TypeError, ValueError) as exc:
        return reporting.blocked(result, [records.stable_gap(exc)])

    pre_effect = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    pre_effect_gaps = policy.admission_gaps(
        repo,
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=True,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observed=pre_effect,
    )
    if observation.operation_bindings(before) != observation.operation_bindings(pre_effect):
        pre_effect_gaps.append("unbound_retire_pre_effect_observation_stale")
    if pre_effect_gaps:
        return reporting.blocked(
            {
                **result,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "observation": observation.public_observation(pre_effect),
            },
            pre_effect_gaps,
        )

    return _relinquish_then_delete(
        repo=repo,
        control_root=control_root,
        records_root=records_root,
        branch=branch,
        expected=expected,
        reason=reason,
        chronicle_ref=chronicle_ref,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        before=before,
        pre_effect=pre_effect,
        result=result,
        attempt_path=attempt_path,
        operation_id=operation_id,
        holder_ref=holder_ref,
    )


def _relinquish_then_delete(  # noqa: PLR0913, RUF100 - bound irreversible transition shape
    *,
    repo: Path,
    control_root: Path,
    records_root: Path,
    branch: str,
    expected: str,
    reason: str,
    chronicle_ref: str,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    before: dict[str, object],
    pre_effect: dict[str, object],
    result: dict[str, object],
    attempt_path: str,
    operation_id: str,
    holder_ref: str,
) -> dict[str, object]:
    """Relinquish the observed lease, then perform one guarded ref deletion."""
    lease_relinquished = relinquish_owned_lease(
        control_root,
        observed=pre_effect,
        holder_ref=holder_ref,
    )
    if lease_relinquished is None:
        return reporting.blocked(
            {
                **result,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "observation": observation.public_observation(pre_effect),
            },
            ["unbound_retire_active_lease"],
        )

    before_delete = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    delete_gaps = policy.admission_gaps(
        repo,
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=True,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observed=before_delete,
    )
    delete_gaps.extend(policy.active_lease_gaps(before_delete))
    if observation.retirement_bindings(pre_effect) != observation.retirement_bindings(
        before_delete
    ):
        delete_gaps.append("unbound_retire_pre_effect_observation_stale")
    if delete_gaps:
        return reporting.blocked(
            {
                **result,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "lease_relinquished": lease_relinquished,
                "observation": observation.public_observation(before_delete),
            },
            delete_gaps,
        )

    deleted = run_git(repo, "update-ref", "-d", f"refs/heads/{branch}", expected, check=False)
    after = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    effect = records.effect_summary(deleted)
    post_gaps = policy.post_effect_gaps(before=before, after=after, deleted=deleted)
    if post_gaps:
        return reporting.blocked(
            {
                **result,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "effect": effect,
                "lease_relinquished": lease_relinquished,
                "observation": observation.public_observation(after),
            },
            post_gaps,
        )
    receipt = records.receipt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        before=before,
        after=after,
        effect=effect,
        chronicle_unchanged=observation.chronicle_binding(before)
        == observation.chronicle_binding(after),
        lease_relinquished=lease_relinquished,
    )
    try:
        receipt_path = records.write_record(
            records.receipt_path(records_root, operation_id),
            receipt,
            kind=records.RECEIPT_KIND,
        )
    except (OSError, TypeError, ValueError) as exc:
        return reporting.blocked(
            {
                **result,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "effect": effect,
                "observation": observation.public_observation(after),
            },
            [records.stable_gap(exc)],
        )
    return {
        **result,
        "ok": True,
        "state": "retired_unbound_exceptional",
        "operation_id": operation_id,
        "attempt_path": attempt_path,
        "receipt_path": receipt_path,
        "receipt": receipt,
        "effect": effect,
        "lease_relinquished": lease_relinquished,
        "observation": observation.public_observation(after),
        "required_gaps": [],
        "mutation": reporting.mutation(
            branch=branch,
            expect_head=expected,
            reason=reason,
            chronicle_ref=chronicle_ref,
            apply=True,
            confirmed=True,
            observed=after,
            break_glass=break_glass,
            confirm_irreversible=confirm_irreversible,
            gaps=[],
        ),
    }


def _observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    """Keep the local seam for observation-drift contract tests."""
    return observation.observe(repo, branch=branch, chronicle_ref=chronicle_ref)


def relinquish_owned_lease(
    control_root: Path,
    *,
    observed: dict[str, object],
    holder_ref: str,
) -> dict[str, object] | None:
    """Revoke only this actor's exact lease generation within the native transition."""
    if not bool(observed[observation.HAS_ACTIVE_LEASE]):
        return {}
    lease = cast("dict[str, object]", observed["active_lease"])
    epoch = lease.get("epoch")
    if (
        str(lease.get("holder_ref") or "") != holder_ref
        or not isinstance(epoch, int)
        or isinstance(epoch, bool)
        or epoch <= 0
    ):
        return None
    try:
        return revoke_lease(
            control_root / ".ethos" / "state" / "state.sqlite",
            subject=str(observed["branch"]),
            holder_ref=holder_ref,
            expected_lease_id=str(lease["lease_id"]),
            expected_epoch=epoch,
            expected_head=str(lease["expected_head"]),
        )
    except (KeyError, TypeError, ValueError):
        return None

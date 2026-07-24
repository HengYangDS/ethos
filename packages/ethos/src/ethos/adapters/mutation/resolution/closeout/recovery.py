"""Crash recovery and effect orchestration for exceptional lane resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution._effects import recover_completed_ownerless_closeout
from ethos.adapters.mutation.resolution._effects import retire_lane
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.core import require_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.records.reservations import (
    ownerless_closeout_reservation_path,
)
from ethos.adapters.mutation.resolution.records.reservations import (
    read_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_OWNERLESS_RECEIPT_FIELDS = tuple(OwnerlessCloseoutBinding.model_fields)


@dataclass(frozen=True, slots=True)
class ResolutionRuntime:
    """Mutation seams supplied by the public lane adapter at call time."""

    accepted_control_root: Callable[[Path], Path]
    current_record_root: Callable[[Path], Path]
    observe_lane: Callable[[Path, str], tuple[LaneObservation, list[str]]]
    prepare_resolution_effect: Callable[
        ...,
        tuple[dict[str, object], dict[str, object], str, str],
    ]
    reserve_resolution_receipt: Callable[..., Path]
    release_resolution_receipt_reservation: Callable[..., None]
    retire_clean_ownerless_lane: Callable[..., dict[str, object]]
    write_resolution_receipt: Callable[..., str]
    release_closeout_fence: Callable[..., None]
    block_resolution_report: Callable[..., None]
    ownerless_closeout_candidate: Callable[[str, LaneObservation], bool]


@dataclass(frozen=True, slots=True)
class _ResolutionContext:
    control_root: Path
    artifact_root: Path
    runtime: ResolutionRuntime


def ownerless_recovery_context(  # noqa: PLR0911, RUF100 - fail-closed states
    *,
    root: Path,
    decision: dict[str, Any],
    disposition: str,
    runtime: ResolutionRuntime,
) -> tuple[dict[str, object], Path | None, Path | None, str]:
    """Return an exact resumable ownerless transition, or its blocking gap."""
    if disposition != "retire" or not decision:
        return {}, None, None, ""
    observation = cast("dict[str, object]", decision.get("observation") or {})
    if (
        not valid_decision_id(str(decision.get("decision_id") or ""))
        or bool(observation.get("dirty"))
        or not bool(observation.get("orphan"))
        or bool(observation.get("holder_ref"))
    ):
        return {}, None, None, ""
    control_root, artifact_root, root_gap = _resolution_roots(root, runtime)
    if root_gap or control_root is None or artifact_root is None:
        return {}, control_root, artifact_root, root_gap
    lane_ref = str(observation.get("lane_ref") or "")
    head = str(observation.get("head") or "")
    if not lane_ref or not head:
        return {}, control_root, artifact_root, ""
    lane_observation = LaneObservation.model_validate(observation)
    receipt_recovery, receipt_gap = cleanup.ownerless_receipt_recovery_context(
        control_root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=lane_observation,
    )
    if receipt_gap:
        return {}, control_root, artifact_root, receipt_gap
    reservation, reservation_gap = _ownerless_reservation_context(
        control_root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=lane_observation,
        receipt_recovery=receipt_recovery,
    )
    return reservation, control_root, artifact_root, reservation_gap


def _ownerless_reservation_context(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    receipt_recovery: dict[str, object],
) -> tuple[dict[str, object], str]:
    """Resolve the target reservation without weakening receipt-first recovery."""
    reservation_path = ownerless_closeout_reservation_path(
        control_root,
        target_digest(observation.lane_ref, observation.head),
        artifact_root=artifact_root,
    )
    if not reservation_path.exists() and not reservation_path.is_symlink():
        return receipt_recovery, ""
    try:
        reservation = read_ownerless_closeout_reservation(
            record_root=artifact_root,
            path=reservation_path,
        )
    except (OSError, TypeError, ValueError) as error:
        return {}, _transition_gap(error, "lane_resolution_ownerless_reservation_invalid")
    exact = (
        reservation.get("decision_id") == decision.get("decision_id")
        and reservation.get("lane_ref") == observation.lane_ref
        and reservation.get("head") == observation.head
    )
    if not exact:
        return reservation, "lane_resolution_ownerless_recovery_binding_mismatch"
    if receipt_recovery and reservation != receipt_recovery:
        return reservation, "lane_resolution_ownerless_receipt_mismatch"
    recovery_state = str(reservation["recovery_state"])
    if recovery_state not in {"reserved_no_effect", "effect_complete_receipt_missing"}:
        return reservation, f"lane_resolution_ownerless_reconciliation_required:{recovery_state}"
    return reservation, ""


def recover_ownerless_resolution(  # noqa: PLR0913, RUF100 - exact recovery envelope
    *,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    reservation: dict[str, object],
    report: dict[str, object],
    runtime: ResolutionRuntime,
    chronicle_event: Callable[[dict[str, Any], dict[str, object] | None], dict[str, object]],
) -> None:
    """Finalize a completed ownerless effect without re-observing its removed lane."""
    context = _ResolutionContext(control_root, artifact_root, runtime)
    decision_id = str(decision.get("decision_id") or "")
    if cleanup.recover_existing_ownerless_receipt(
        control_root=control_root,
        artifact_root=artifact_root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        reservation=reservation,
        report=report,
        runtime=runtime,
        chronicle_event=chronicle_event,
    ):
        return
    if reservation_gap := _reserve_receipt(
        control_root,
        artifact_root,
        decision_id,
        runtime,
        reuse_existing=True,
    ):
        runtime.block_resolution_report(report, reservation_gap, state="partial_transition")
        return
    receipt_written = False
    try:
        executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
        if not executor_ref:
            runtime.block_resolution_report(
                report,
                "lane_resolution_ownerless_executor_required",
                state="partial_transition",
            )
            return
        try:
            binding = recover_completed_ownerless_closeout(
                root=control_root,
                decision_path=decision_path,
                decision=decision,
                observation=observation,
                executor_ref=executor_ref,
                reservation=reservation,
            )
        except OwnerlessCloseoutError as error:
            runtime.block_resolution_report(
                report,
                _transition_gap(error, "lane_resolution_ownerless_recovery_not_finalizable"),
                state="partial_transition",
            )
            return
        package, receipt, state, effect_gaps = _prepare_resolution(
            context=context,
            decision=decision,
            observation=observation,
            disposition="retire",
        )
        if effect_gaps:
            runtime.block_resolution_report(report, *effect_gaps, state="partial_transition")
            return
        receipt_binding = {field: binding[field] for field in _OWNERLESS_RECEIPT_FIELDS}
        receipt["ownerless_closeout_binding"] = receipt_binding
        try:
            receipt_path = runtime.write_resolution_receipt(
                root=control_root,
                receipt=receipt,
                artifact_root=artifact_root,
                require_ownerless_closeout_binding=True,
            )
        except (OSError, ValueError):
            runtime.block_resolution_report(
                report,
                "lane_resolution_receipt_write_failed_after_effect",
                state="partial_transition",
            )
            return
        receipt_written = True
        report.update(
            state=state,
            preservation_package=package,
            receipt=receipt,
            receipt_path=receipt_path,
            ownerless_closeout_binding=receipt_binding,
            chronicle_event=chronicle_event(decision, receipt),
        )
        cleanup_gap = cleanup.release_ownerless_closeout_resources(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            binding=binding,
            runtime=runtime,
        )
        if cleanup_gap:
            runtime.block_resolution_report(report, cleanup_gap, state="partial_transition")
    finally:
        cleanup_gap = cleanup.release_receipt_reservation(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            release_allowed=receipt_written,
            runtime=runtime,
        )
        if cleanup_gap:
            current_gaps = cast("list[str]", report["required_gaps"])
            runtime.block_resolution_report(
                report,
                *current_gaps,
                cleanup_gap,
                state="partial_transition" if receipt_written else "blocked",
            )


def apply_resolution(  # noqa: PLR0913, RUF100 - exact effect binding envelope
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    report: dict[str, object],
    runtime: ResolutionRuntime,
    chronicle_event: Callable[[dict[str, Any], dict[str, object] | None], dict[str, object]],
    reuse_receipt_reservation: bool = False,
) -> None:
    """Apply one bounded resolution effect and retain partial-transition evidence."""
    control_root, artifact_root, root_gap = _resolution_roots(root, runtime)
    if root_gap or control_root is None or artifact_root is None:
        runtime.block_resolution_report(report, root_gap)
        return
    context = _ResolutionContext(control_root, artifact_root, runtime)
    decision_id = str(decision.get("decision_id") or "")
    if reservation_gap := _reserve_receipt(
        control_root,
        artifact_root,
        decision_id,
        runtime,
        reuse_existing=reuse_receipt_reservation,
    ):
        runtime.block_resolution_report(report, reservation_gap)
        return

    retain_reservation = False
    receipt_written = False
    try:
        package, receipt, state, effect_gaps = _prepare_resolution(
            context=context,
            decision=decision,
            observation=observation,
            disposition=disposition,
        )
        if effect_gaps:
            runtime.block_resolution_report(report, *effect_gaps)
            return
        report.update(state=state, preservation_package=package)
        retain_reservation, retire_gap, ownerless_binding = _retire_resolution(
            root=root,
            control_root=control_root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            artifact_root=artifact_root,
            runtime=runtime,
        )
        if ownerless_binding:
            receipt_binding = {
                field: ownerless_binding[field] for field in _OWNERLESS_RECEIPT_FIELDS
            }
            receipt["ownerless_closeout_binding"] = receipt_binding
            report["ownerless_closeout_binding"] = receipt_binding
        if retire_gap:
            runtime.block_resolution_report(
                report,
                retire_gap,
                state=retire_gap.removeprefix("lane_resolution_"),
            )
            return
        destructive_effect = disposition in {"retire", "preserve-retire"}
        try:
            receipt_path = runtime.write_resolution_receipt(
                root=control_root,
                receipt=receipt,
                artifact_root=artifact_root,
                require_ownerless_closeout_binding=bool(ownerless_binding),
            )
        except (OSError, ValueError):
            runtime.block_resolution_report(
                report,
                "lane_resolution_receipt_write_failed_after_effect"
                if destructive_effect
                else "lane_resolution_receipt_write_failed",
                state="partial_transition" if destructive_effect else "blocked",
            )
            return
        receipt_written = True
        report.update(
            receipt=receipt,
            receipt_path=receipt_path,
            chronicle_event=chronicle_event(decision, receipt),
        )
        if ownerless_binding:
            cleanup_gap = cleanup.release_ownerless_closeout_resources(
                control_root=control_root,
                artifact_root=artifact_root,
                decision=decision,
                observation=observation,
                binding=ownerless_binding,
                runtime=runtime,
            )
            if cleanup_gap:
                runtime.block_resolution_report(report, cleanup_gap, state="partial_transition")
                return
    finally:
        cleanup_gap = cleanup.release_receipt_reservation(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            release_allowed=not retain_reservation or receipt_written,
            runtime=runtime,
        )
        if cleanup_gap:
            current_gaps = cast("list[str]", report["required_gaps"])
            runtime.block_resolution_report(
                report,
                *current_gaps,
                cleanup_gap,
                state="partial_transition" if receipt_written else "blocked",
            )


def _resolution_roots(
    root: Path, runtime: ResolutionRuntime
) -> tuple[Path | None, Path | None, str]:
    try:
        return runtime.accepted_control_root(root), runtime.current_record_root(root), ""
    except ValueError as error:
        return None, None, _transition_gap(error, "lane_resolution_control_root_unavailable")


def _reserve_receipt(
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    runtime: ResolutionRuntime,
    *,
    reuse_existing: bool = False,
) -> str:
    try:
        runtime.reserve_resolution_receipt(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
        )
    except (OSError, ValueError) as error:
        if isinstance(error, FileExistsError) and reuse_existing:
            try:
                require_resolution_receipt_reservation(
                    root=control_root,
                    decision_id=decision_id,
                    artifact_root=artifact_root,
                )
            except (OSError, ValueError) as reuse_error:
                error = reuse_error
            else:
                return ""
        if isinstance(error, ValueError):
            return _transition_gap(error, "lane_resolution_receipt_invalid")
        return (
            "lane_resolution_receipt_path_exists"
            if isinstance(error, FileExistsError)
            else "lane_resolution_receipt_path_unsafe"
        )
    return ""


def _prepare_resolution(
    *,
    context: _ResolutionContext,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], str, tuple[str, ...]]:
    try:
        package, receipt, state, effect_gap = context.runtime.prepare_resolution_effect(
            control_root=context.control_root,
            artifact_root=context.artifact_root,
            decision=decision,
            observation=observation,
            disposition=disposition,
        )
    except (OSError, ValueError) as error:
        return {}, {}, "blocked", (_transition_gap(error, "lane_resolution_effect_failed"),)
    if effect_gap:
        return package, receipt, state, (effect_gap,)
    if disposition != "preserve-retire":
        return package, receipt, state, ()
    current, current_gaps = context.runtime.observe_lane(context.control_root, observation.lane_ref)
    if current_gaps or current.digest() != observation.digest():
        return (
            package,
            receipt,
            state,
            tuple(dict.fromkeys((*current_gaps, "lane_resolution_observation_stale"))),
        )
    return package, receipt, state, ()


def _retire_resolution(  # noqa: PLR0911, PLR0913, RUF100 - fail-closed branches
    *,
    root: Path,
    control_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    artifact_root: Path,
    runtime: ResolutionRuntime,
) -> tuple[bool, str, dict[str, object]]:
    if disposition not in {"retire", "preserve-retire"}:
        return False, "", {}
    if runtime.ownerless_closeout_candidate(disposition, observation):
        executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
        if not executor_ref:
            return False, "lane_resolution_ownerless_executor_required", {}
        accepted_branch = load_branch_role_policy(control_root).accepted_branch
        accepted = run_git(
            control_root,
            "rev-parse",
            "--verify",
            f"refs/heads/{accepted_branch}",
            check=False,
        )
        accepted_head = accepted.stdout.strip() if accepted.returncode == 0 else ""
        if not accepted_head:
            return False, "lane_resolution_ownerless_accepted_head_unavailable", {}
        try:
            binding = runtime.retire_clean_ownerless_lane(
                root=control_root,
                decision_path=decision_path,
                decision=decision,
                observation=observation,
                executor_ref=executor_ref,
                accepted_branch=accepted_branch,
                accepted_head=accepted_head,
                artifact_root=artifact_root,
            )
        except OwnerlessCloseoutError as error:
            return (
                error.fence_acquired,
                _transition_gap(error, "lane_resolution_ownerless_transition_unknown"),
                {},
            )
        return True, "", binding
    try:
        retire_lane(
            root=root,
            observation=observation,
            force=disposition == "preserve-retire" and observation.dirty,
        )
    except ValueError as error:
        gap = _transition_gap(error, "lane_resolution_branch_delete_failed")
        return (
            gap
            in {
                "lane_resolution_branch_delete_failed_after_worktree_removed",
                "lane_resolution_branch_delete_state_uncertain",
            },
            gap,
            {},
        )
    return True, "", {}


def _transition_gap(error: Exception, fallback: str) -> str:
    message = str(error).strip()
    return message if message.startswith(("lane_resolution_", "lane_closeout_")) else fallback

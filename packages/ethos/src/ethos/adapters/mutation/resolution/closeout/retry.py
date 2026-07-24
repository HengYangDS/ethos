"""Fail-closed rebinding for ownerless attempts that performed no effect."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.resolution.records.core import target_digest

if TYPE_CHECKING:
    from ethos.adapters.mutation.resolution.closeout.effect import OwnerlessCloseoutRuntime
    from ethos_core.contracts.resolution.lane import LaneObservation

_ACCEPTED_HEAD_STALE = "lane_resolution_ownerless_accepted_head_stale"
_DECISION_STALE = "lane_resolution_ownerless_decision_stale"
_FENCE_STALE = "lane_resolution_ownerless_fence_stale"
_FENCE_UNVERIFIABLE = "lane_resolution_ownerless_fence_unverifiable"
_OBSERVATION_STALE = "lane_resolution_ownerless_observation_stale"


def _ownerless_gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def ownerless_reservation(  # noqa: PLR0913, RUF100 - exact durable reservation binding
    *,
    decision: dict[str, Any],
    observation: LaneObservation,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    wcp: dict[str, object],
    wcp_binding_digest: str,
    target_binding_digest: str,
) -> dict[str, object]:
    """Build the initial exact reservation for one fenced ownerless target."""
    return {
        "schema_version": 1,
        "decision_id": str(decision.get("decision_id") or ""),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "executor_ref": executor_ref,
        "wcp_schema_version": str(wcp.get("schema_version") or ""),
        "wcp_decision_sha256": str(wcp.get("decision_sha256") or ""),
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "wcp_binding_digest": wcp_binding_digest,
        "target_digest": target_digest(observation.lane_ref, observation.head),
        "target_binding_digest": target_binding_digest,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def reset_reserved_no_effect_retry(  # noqa: PLR0913, RUF100 - exact retry binding envelope
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    database: Path,
    record_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    wcp: dict[str, object],
    wcp_binding_digest: str,
) -> None:
    """Reset one exact zero-effect attempt, mapping operational failures to a stable gap."""
    try:
        _reset_reserved_no_effect_retry(
            runtime=runtime,
            root=root,
            database=database,
            record_root=record_root,
            decision_path=decision_path,
            decision=decision,
            decision_sha256=decision_sha256,
            observation=observation,
            executor_ref=executor_ref,
            accepted_branch=accepted_branch,
            accepted_head=accepted_head,
            wcp=wcp,
            wcp_binding_digest=wcp_binding_digest,
        )
    except runtime.ownerless_error_type:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise runtime.ownerless_error(
            _ownerless_gap("retry_reset_failed"), fence_acquired=False
        ) from error


def _reset_reserved_no_effect_retry(  # noqa: PLR0913, RUF100 - exact retry binding envelope
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    database: Path,
    record_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    wcp: dict[str, object],
    wcp_binding_digest: str,
) -> None:
    reservation_path = runtime.reservation_path(
        root,
        target_digest(observation.lane_ref, observation.head),
        artifact_root=record_root,
    )
    if not reservation_path.exists() and not reservation_path.is_symlink():
        return
    try:
        reservation = runtime.read_reservation(record_root=record_root, path=reservation_path)
    except (OSError, TypeError, ValueError) as error:
        raise runtime.ownerless_error(
            _ownerless_gap("reservation_failed"), fence_acquired=False
        ) from error
    _verify_retry_binding(
        runtime=runtime,
        root=root,
        decision_path=decision_path,
        decision=decision,
        decision_sha256=decision_sha256,
        observation=observation,
        reservation=reservation,
        executor_ref=executor_ref,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
    )
    fence_state, fence = runtime.probe_fence(database, subject=observation.lane_ref)
    expected_fence = _expected_fence(
        decision=decision,
        decision_sha256=decision_sha256,
        observation=observation,
        reservation=reservation,
    )
    probe_valid = (fence_state == "present" and isinstance(fence, dict)) or (
        fence_state == "absent" and fence is None
    )
    if not probe_valid:
        raise runtime.ownerless_error(_FENCE_UNVERIFIABLE, fence_acquired=False)
    if reservation["target_binding_digest"] != expected_fence["target_binding_digest"]:
        raise runtime.ownerless_error(_FENCE_STALE, fence_acquired=True)
    if fence_state == "present" and fence != expected_fence:
        raise runtime.ownerless_error(_FENCE_STALE, fence_acquired=True)
    current_binding = (
        reservation["accepted_head"] == accepted_head
        and reservation["wcp_schema_version"] == wcp.get("schema_version")
        and reservation["wcp_decision_sha256"] == wcp.get("decision_sha256")
        and reservation["wcp_binding_digest"] == wcp_binding_digest
    )
    if fence_state == "present" and current_binding:
        return
    _verify_retry_state(
        runtime=runtime,
        root=root,
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        observation=observation,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
    )
    _release_old_binding(
        runtime=runtime,
        root=root,
        database=database,
        record_root=record_root,
        decision=decision,
        observation=observation,
        reservation=reservation,
        fence_state=fence_state,
    )


def _verify_retry_binding(  # noqa: PLR0913, RUF100 - exact immutable retry binding
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    reservation: dict[str, object],
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
) -> None:
    expected = {
        "decision_id": str(decision.get("decision_id") or ""),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "executor_ref": executor_ref,
        "wcp_decision_sha256": decision_sha256,
        "accepted_branch": accepted_branch,
        "target_digest": target_digest(observation.lane_ref, observation.head),
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    mismatch = next(
        (field for field, value in expected.items() if reservation.get(field) != value),
        "",
    )
    if mismatch:
        raise runtime.ownerless_error(
            _ownerless_gap(f"recovery_binding_mismatch:{mismatch}"),
            fence_acquired=True,
        )
    ancestry = runtime.run_git(
        root,
        "merge-base",
        "--is-ancestor",
        str(reservation["accepted_head"]),
        accepted_head,
        check=False,
    )
    if ancestry.returncode != 0:
        raise runtime.ownerless_error(_ACCEPTED_HEAD_STALE, fence_acquired=True)
    if _path_digest(decision_path) != decision_sha256:
        raise runtime.ownerless_error(_DECISION_STALE, fence_acquired=True)


def _verify_retry_state(  # noqa: PLR0913, RUF100 - exact live zero-effect proof
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    decision_path: Path,
    decision_sha256: str,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
) -> None:
    if _path_digest(decision_path) != decision_sha256:
        raise runtime.ownerless_error(_DECISION_STALE, fence_acquired=True)
    if _ref_head(runtime, root, accepted_branch) != accepted_head:
        raise runtime.ownerless_error(_ACCEPTED_HEAD_STALE, fence_acquired=True)
    current, gaps = runtime.observe_lane(root, observation.lane_ref)
    if gaps or current.digest() != observation.digest():
        raise runtime.ownerless_error(_OBSERVATION_STALE, fence_acquired=True)
    if observation.lane_ref in runtime.leases_by_branch(root):
        raise runtime.ownerless_error(
            _ownerless_gap("recovery_binding_mismatch:coordination"),
            fence_acquired=True,
        )


def _release_old_binding(  # noqa: PLR0913, RUF100 - exact cross-store cleanup ordering
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    database: Path,
    record_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    reservation: dict[str, object],
    fence_state: str,
) -> None:
    try:
        if fence_state == "present":
            runtime.release_fence(
                database,
                subject=observation.lane_ref,
                decision_id=str(decision["decision_id"]),
                target_binding_digest=str(reservation["target_binding_digest"]),
            )
        runtime.release_no_effect_reservation(
            root=root,
            expected=reservation,
            artifact_root=record_root,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        gap = str(error).strip()
        reset_gap = (
            gap
            if gap.startswith(("lane_resolution_", "lane_closeout_"))
            else _ownerless_gap("retry_reset_failed")
        )
        raise runtime.ownerless_error(
            reset_gap,
            fence_acquired=fence_state == "present",
        ) from error


def _expected_fence(
    *,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    reservation: dict[str, object],
) -> dict[str, object]:
    binding: dict[str, object] = {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": str(decision.get("decision_id") or ""),
        "executor_ref": str(reservation["executor_ref"]),
        "accepted_branch": str(reservation["accepted_branch"]),
        "accepted_head": str(reservation["accepted_head"]),
        "payload": {
            "target_path": Path(observation.path).resolve(strict=False).as_posix(),
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": decision_sha256,
            "chronicle_digest": str(decision.get("chronicle_digest") or ""),
            "wcp_schema_version": str(reservation["wcp_schema_version"]),
            "wcp_decision_sha256": str(reservation["wcp_decision_sha256"]),
            "wcp_binding_digest": str(reservation["wcp_binding_digest"]),
        },
    }
    return {**binding, "target_binding_digest": _canonical_digest(binding)}


def _ref_head(runtime: OwnerlessCloseoutRuntime, root: Path, branch: str) -> str:
    state, oid = runtime.probe_ref(root, branch)
    return oid if state == "oid" else ""


def _path_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""

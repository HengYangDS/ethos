"""Fail-closed effects and recovery for clean ownerless Work Lanes."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.resolution.closeout.retry import reset_reserved_no_effect_retry
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPCloseoutExpectation
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPResponseError
from ethos.adapters.mutation.resolution.receipts import canonical_resolution_decision_snapshot
from ethos.adapters.mutation.resolution.receipts import exact_ownerless_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import target_digest
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable

_OWNERLESS_EXECUTOR_REQUIRED = "lane_resolution_ownerless_executor_required"
_OWNERLESS_DECISION_INVALID = "lane_resolution_ownerless_decision_invalid"
_OWNERLESS_DECISION_STALE = "lane_resolution_ownerless_decision_stale"
_OWNERLESS_ACCEPTED_HEAD_STALE = "lane_resolution_ownerless_accepted_head_stale"
_OWNERLESS_FENCE_STALE = "lane_resolution_ownerless_fence_stale"
_OWNERLESS_FENCE_UNVERIFIABLE = "lane_resolution_ownerless_fence_unverifiable"
_OWNERLESS_OBSERVATION_STALE = "lane_resolution_ownerless_observation_stale"
_OWNERLESS_RECEIPT_MISMATCH = "lane_resolution_ownerless_receipt_mismatch"
_OWNERLESS_WCP_EXPECTATION_INVALID = "lane_resolution_ownerless_wcp_expectation_invalid"
_WCP_LANE_ID_RE = re.compile(r"^(?P<date>\d{8})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutRuntime:
    """Repository effects injected by the compatibility adapter at call time."""

    run_git: Callable[..., subprocess.CompletedProcess[str]]
    observe_lane: Callable[[Path, str], tuple[LaneObservation, list[str]]]
    records_artifact_root: Callable[[Path], Path]
    reservation_path: Callable[..., Path]
    read_reservation: Callable[..., dict[str, object]]
    reserve_target: Callable[..., Path]
    release_no_effect_reservation: Callable[..., None]
    transition_reservation: Callable[..., dict[str, object]]
    leases_by_branch: Callable[[Path], dict[str, dict[str, object]]]
    acquire_fence: Callable[..., dict[str, object]]
    release_fence: Callable[..., None]
    get_fence: Callable[..., dict[str, object] | None]
    probe_fence: Callable[..., tuple[str, dict[str, object] | None]]
    state_database: Callable[[Path], Path]
    run_wcp: Callable[..., dict[str, object]]
    ownerless_error: Callable[..., ValueError]
    ownerless_error_type: type[ValueError]
    verify_pre_effect: Callable[..., None]
    retire_cas: Callable[..., None]
    probe_ref: Callable[[Path, str], tuple[str, str]]
    verify_postconditions: Callable[..., dict[str, object]]


def _ownerless_gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _decision_snapshot(
    *,
    decision_bytes: bytes,
    decision: dict[str, Any],
    runtime: OwnerlessCloseoutRuntime,
    fence_acquired: bool,
) -> dict[str, Any]:
    snapshot, gap = canonical_resolution_decision_snapshot(
        decision_bytes=decision_bytes,
        decision=decision,
    )
    if gap:
        raise runtime.ownerless_error(gap, fence_acquired=fence_acquired)
    return cast("dict[str, Any]", snapshot)


def _wcp_lane_identity(
    root: Path,
    observation: LaneObservation,
    runtime: OwnerlessCloseoutRuntime,
) -> tuple[str, str]:
    """Mirror the WCP identity contract for supported ownerless lane layouts."""
    if not observation.lane_ref.startswith("work/"):
        raise runtime.ownerless_error(_OWNERLESS_WCP_EXPECTATION_INVALID, fence_acquired=False)
    branch_lane_id = observation.lane_ref.removeprefix("work/")
    if not branch_lane_id:
        raise runtime.ownerless_error(_OWNERLESS_WCP_EXPECTATION_INVALID, fence_acquired=False)
    canonical_worktrees = root.resolve().parent / f"{root.resolve().name}-worktrees"
    lane_path = Path(observation.path).resolve()
    if lane_path.parent != canonical_worktrees:
        return branch_lane_id, "legacy_ownerless"
    if lane_path.name == branch_lane_id:
        return branch_lane_id, "canonical"
    historical = _WCP_LANE_ID_RE.fullmatch(lane_path.name)
    if historical is not None and historical.group("slug") == branch_lane_id:
        return lane_path.name, "historical_ownerless"
    raise runtime.ownerless_error(_OWNERLESS_WCP_EXPECTATION_INVALID, fence_acquired=False)


def retire_clean_ownerless_lane(  # noqa: PLR0913, PLR0915, RUF100 - exact cross-owner binding envelope
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    runtime: OwnerlessCloseoutRuntime,
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Run strict WCP admission, durable fencing, exact CAS, and postverification."""
    if not executor_ref:
        raise runtime.ownerless_error(_OWNERLESS_EXECUTOR_REQUIRED, fence_acquired=False)
    try:
        decision_bytes = decision_path.read_bytes()
    except OSError as error:
        raise runtime.ownerless_error(
            _ownerless_gap("decision_unavailable"), fence_acquired=False
        ) from error
    decision = _decision_snapshot(
        decision_bytes=decision_bytes,
        decision=decision,
        runtime=runtime,
        fence_acquired=False,
    )
    decision_sha256 = hashlib.sha256(decision_bytes).hexdigest()
    lane_id, lane_layout = _wcp_lane_identity(root, observation, runtime)
    accepted_tree_result = runtime.run_git(
        root, "rev-parse", f"{accepted_head}^{{tree}}", check=False
    )
    accepted_tree = (
        accepted_tree_result.stdout.strip() if accepted_tree_result.returncode == 0 else ""
    )
    if not accepted_tree:
        raise runtime.ownerless_error(
            _ownerless_gap("accepted_tree_unavailable"), fence_acquired=False
        )
    expected = WCPCloseoutExpectation(
        branch=observation.lane_ref,
        path=observation.path,
        head=observation.head,
        lane_id=lane_id,
        lane_layout=lane_layout,
        executor_ref=executor_ref,
        decision_bytes=decision_bytes,
        observation=observation.model_dump(mode="json"),
        chronicle_ref=str(decision.get("chronicle_ref") or ""),
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        accepted_tree=accepted_tree,
    )
    try:
        wcp = runtime.run_wcp(
            repo=root,
            decision_path=decision_path,
            expected=expected,
        )
    except WCPResponseError as error:
        raise runtime.ownerless_error(
            _ownerless_gap("wcp_rejected"), fence_acquired=False
        ) from error
    wcp_binding_digest = _canonical_digest(wcp)
    record_root = artifact_root or runtime.records_artifact_root(root)
    database = runtime.state_database(root)
    reset_reserved_no_effect_retry(
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
    try:
        fence = runtime.acquire_fence(
            database,
            subject=observation.lane_ref,
            expected_head=observation.head,
            decision_id=str(decision.get("decision_id") or ""),
            executor_ref=executor_ref,
            accepted_branch=accepted_branch,
            accepted_head=accepted_head,
            target_path=observation.path,
            lane_incarnation_id=observation.lane_incarnation_id,
            observation_digest=observation.digest(),
            decision_sha256=decision_sha256,
            chronicle_digest=str(decision.get("chronicle_digest") or ""),
            wcp_schema_version=str(wcp.get("schema_version") or ""),
            wcp_decision_sha256=str(wcp.get("decision_sha256") or ""),
            wcp_binding_digest=wcp_binding_digest,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        gap = str(error).strip()
        raise runtime.ownerless_error(
            gap if gap.startswith("lane_closeout_") else _ownerless_gap("fence_failed"),
            fence_acquired=False,
        ) from error
    reservation = OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=str(decision.get("decision_id") or ""),
        lane_ref=observation.lane_ref,
        head=observation.head,
        executor_ref=executor_ref,
        decision_sha256=decision_sha256,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        target_digest=target_digest(observation.lane_ref, observation.head),
        target_binding_digest=str(fence["target_binding_digest"]),
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    ).to_payload()
    try:
        runtime.reserve_target(
            root=root,
            reservation=reservation,
            artifact_root=record_root,
        )
    except (OSError, TypeError, ValueError) as error:
        raise runtime.ownerless_error(
            _ownerless_gap("reservation_failed"),
            fence_acquired=True,
        ) from error
    try:
        runtime.verify_pre_effect(
            root=root,
            database=database,
            decision_path=decision_path,
            decision_sha256=decision_sha256,
            observation=observation,
            accepted_branch=accepted_branch,
            accepted_head=accepted_head,
            fence=fence,
        )
        runtime.retire_cas(
            root=root,
            observation=observation,
            accepted_branch=accepted_branch,
            accepted_head=accepted_head,
        )
        postconditions = runtime.verify_postconditions(
            root=root,
            database=database,
            decision_path=decision_path,
            decision_sha256=decision_sha256,
            observation=observation,
            accepted_branch=accepted_branch,
            accepted_head=accepted_head,
            fence=fence,
        )
    except runtime.ownerless_error_type as error:
        _record_ownerless_partial(
            runtime=runtime,
            root=root,
            artifact_root=record_root,
            reservation=reservation,
            error=error,
        )
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        gap = str(error).strip()
        transition_gap = (
            gap if gap.startswith("lane_resolution_") else _ownerless_gap("transition_unknown")
        )
        transition_error = runtime.ownerless_error(
            transition_gap,
            fence_acquired=True,
        )
        _record_ownerless_partial(
            runtime=runtime,
            root=root,
            artifact_root=record_root,
            reservation=reservation,
            error=transition_error,
        )
        raise transition_error from error
    postcondition_digest = _canonical_digest(postconditions)
    try:
        runtime.transition_reservation(
            root=root,
            expected=reservation,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
            postcondition_digest=postcondition_digest,
            artifact_root=record_root,
        )
    except (OSError, TypeError, ValueError) as error:
        raise runtime.ownerless_error(
            _ownerless_gap("reservation_update_failed"),
            fence_acquired=True,
        ) from error
    return OwnerlessCloseoutBinding(
        executor_ref=executor_ref,
        decision_sha256=decision_sha256,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        target_digest=str(reservation["target_digest"]),
        target_binding_digest=str(fence["target_binding_digest"]),
        postcondition_digest=postcondition_digest,
    ).model_dump(mode="json")


def recover_completed_ownerless_closeout(  # noqa: PLR0913, RUF100 - exact recovery binding envelope
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    executor_ref: str,
    reservation: dict[str, object],
    runtime: OwnerlessCloseoutRuntime,
    receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    """Reverify one exact completed effect before its missing receipt is written."""
    try:
        decision_bytes = decision_path.read_bytes()
    except OSError as error:
        raise runtime.ownerless_error(_OWNERLESS_DECISION_STALE, fence_acquired=True) from error
    decision = _decision_snapshot(
        decision_bytes=decision_bytes,
        decision=decision,
        runtime=runtime,
        fence_acquired=True,
    )
    observation = LaneObservation.model_validate(decision["observation"])
    decision_sha256 = hashlib.sha256(decision_bytes).hexdigest()
    exact_target = (
        reservation.get("decision_id") == decision.get("decision_id")
        and reservation.get("lane_ref") == observation.lane_ref
        and reservation.get("head") == observation.head
    )
    if not exact_target or decision_sha256 != reservation.get("decision_sha256"):
        raise runtime.ownerless_error(_OWNERLESS_DECISION_STALE, fence_acquired=True)
    if executor_ref != reservation.get("executor_ref"):
        raise runtime.ownerless_error(
            _ownerless_gap("recovery_binding_mismatch:executor_ref"),
            fence_acquired=True,
        )
    accepted_branch = str(reservation.get("accepted_branch") or "")
    accepted_head = str(reservation.get("accepted_head") or "")
    if _ref_head(runtime, root, accepted_branch) != accepted_head:
        raise runtime.ownerless_error(_OWNERLESS_ACCEPTED_HEAD_STALE, fence_acquired=True)
    fence_state, fence = runtime.probe_fence(
        runtime.state_database(root), subject=observation.lane_ref
    )
    expected_fence: dict[str, object] = {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": str(decision.get("decision_id") or ""),
        "executor_ref": executor_ref,
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "target_binding_digest": str(reservation.get("target_binding_digest") or ""),
        "payload": {
            "target_path": Path(observation.path).resolve(strict=False).as_posix(),
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": decision_sha256,
            "chronicle_digest": str(decision.get("chronicle_digest") or ""),
        },
    }
    expected_binding = {
        "executor_ref": reservation.get("executor_ref"),
        "decision_sha256": decision_sha256,
        "accepted_branch": reservation.get("accepted_branch"),
        "accepted_head": reservation.get("accepted_head"),
        "target_digest": reservation.get("target_digest"),
        "target_binding_digest": reservation.get("target_binding_digest"),
        "postcondition_digest": reservation.get("postcondition_digest"),
    }
    exact_receipt = exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=expected_binding,
    )
    if receipt is not None and not exact_receipt:
        raise runtime.ownerless_error(_OWNERLESS_RECEIPT_MISMATCH, fence_acquired=True)
    if fence_state == "unverifiable":
        raise runtime.ownerless_error(_OWNERLESS_FENCE_UNVERIFIABLE, fence_acquired=True)
    if (fence_state == "present" and not _fence_contains(fence, expected_fence)) or (
        fence_state == "absent" and not exact_receipt
    ):
        raise runtime.ownerless_error(_OWNERLESS_FENCE_STALE, fence_acquired=True)
    postconditions = runtime.verify_postconditions(
        root=root,
        database=runtime.state_database(root),
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        observation=observation,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        fence=fence,
        decision_bytes=decision_bytes,
    )
    if _canonical_digest(postconditions) != reservation.get("postcondition_digest"):
        raise runtime.ownerless_error(
            _ownerless_gap("postcondition_failed:postcondition_digest"),
            fence_acquired=True,
        )
    return OwnerlessCloseoutBinding.model_validate(expected_binding).model_dump(mode="json")


def _fence_contains(fence: dict[str, object] | None, expected: dict[str, object]) -> bool:
    """Match the native fence binding while its state carrier still has extra metadata."""
    if not isinstance(fence, dict):
        return False
    expected_payload = expected.get("payload")
    actual_payload = fence.get("payload")
    if not isinstance(expected_payload, dict) or not isinstance(actual_payload, dict):
        return False
    top_level = set(expected) - {"payload"}
    return all(fence.get(field) == expected[field] for field in top_level) and all(
        actual_payload.get(field) == value for field, value in expected_payload.items()
    )


def _record_ownerless_partial(
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    artifact_root: Path,
    reservation: dict[str, object],
    error: ValueError,
) -> None:
    gap = str(error)
    if "worktree_removed_ref_present" in gap:
        phase, recovery_state = "effect", "worktree_removed_ref_present"
    elif "postcondition_failed" in gap:
        phase, recovery_state = "postcondition", "postcondition_failed"
    elif "transition_unknown" in gap:
        phase, recovery_state = "unknown", "transition_unknown"
    else:
        return
    try:
        runtime.transition_reservation(
            root=root,
            expected=reservation,
            phase=phase,
            recovery_state=recovery_state,
            artifact_root=artifact_root,
        )
    except (OSError, TypeError, ValueError) as transition_error:
        raise runtime.ownerless_error(
            _ownerless_gap("reservation_update_failed"),
            fence_acquired=True,
        ) from transition_error


def verify_ownerless_pre_effect(  # noqa: PLR0913, RUF100 - exact pre-effect CAS dimensions
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    database: Path,
    decision_path: Path,
    decision_sha256: str,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
    fence: dict[str, object],
) -> None:
    """Verify the exact fence, decision, accepted ref, and observation before CAS."""
    current_fence_state, current_fence = runtime.probe_fence(database, subject=observation.lane_ref)
    if current_fence_state != "present" or current_fence != fence:
        raise runtime.ownerless_error(_OWNERLESS_FENCE_STALE, fence_acquired=True)
    if _path_digest(decision_path) != decision_sha256:
        raise runtime.ownerless_error(_OWNERLESS_DECISION_STALE, fence_acquired=True)
    if _ref_head(runtime, root, accepted_branch) != accepted_head:
        raise runtime.ownerless_error(_OWNERLESS_ACCEPTED_HEAD_STALE, fence_acquired=True)
    current, gaps = runtime.observe_lane(root, observation.lane_ref)
    if gaps or current.digest() != observation.digest():
        raise runtime.ownerless_error(_OWNERLESS_OBSERVATION_STALE, fence_acquired=True)


def verify_ownerless_postconditions(  # noqa: PLR0913, RUF100 - exact postcondition dimensions
    *,
    runtime: OwnerlessCloseoutRuntime,
    root: Path,
    database: Path,
    decision_path: Path,
    decision_sha256: str,
    observation: LaneObservation,
    accepted_branch: str,
    accepted_head: str,
    fence: dict[str, object] | None,
    decision_bytes: bytes | None = None,
) -> dict[str, object]:
    """Verify exact ref, worktree, path, coordination, decision, and fence outcomes."""
    worktrees = runtime.run_git(root, "worktree", "list", "--porcelain", check=False)
    target_ref_state, _ = runtime.probe_ref(root, observation.lane_ref)
    current_fence_state, current_fence = runtime.probe_fence(database, subject=observation.lane_ref)
    checks = {
        "target_ref_absent": target_ref_state == "absent",
        "worktree_registration_absent": worktrees.returncode == 0
        and f"worktree {observation.path}\n" not in worktrees.stdout,
        "target_path_absent": not Path(observation.path).exists()
        and not Path(observation.path).is_symlink(),
        "accepted_head_unchanged": _ref_head(runtime, root, accepted_branch) == accepted_head,
        "coordination_absent": observation.lane_ref not in runtime.leases_by_branch(root),
        "decision_unchanged": (
            hashlib.sha256(decision_bytes).hexdigest()
            if decision_bytes is not None
            else _path_digest(decision_path)
        )
        == decision_sha256,
        "fence_unchanged": current_fence_state == ("absent" if fence is None else "present")
        and current_fence == fence,
    }
    failed = next((name for name, ok in checks.items() if not ok), "")
    if failed:
        gap = f"lane_resolution_ownerless_postcondition_failed:{failed}"
        raise runtime.ownerless_error(
            gap,
            fence_acquired=True,
        )
    return checks


def _ref_head(runtime: OwnerlessCloseoutRuntime, root: Path, branch: str) -> str:
    state, oid = runtime.probe_ref(root, branch)
    return oid if state == "oid" else ""


def _path_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""

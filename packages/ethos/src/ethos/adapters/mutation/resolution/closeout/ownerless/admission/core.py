"""Native admission for clean ownerless Work Lane closeout."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from typing import NoReturn

import ethos.adapters.mutation.resolution.closeout.ownerless.admission.policy as policy_reader
import ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core as receipt
import ethos.adapters.mutation.resolution.observation as git
import ethos.adapters.mutation.resolution.records.current.validation.core as validation
import ethos.adapters.store.state.closeout as state_closeout
import ethos_core.contracts.branch.roles as roles
import ethos_core.contracts.resolution.lane as lane
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation

_POLICY_PATH = ".ethos/workspace.toml"
_MAX_POLICY_BYTES = 1024 * 1024
_MAX_CHRONICLE_BYTES = 16 * 1024 * 1024
_ADMISSION_UNVERIFIABLE = "admission_unverifiable"
_BindingAuthority = tuple[str, str, str, str]


class OwnerlessCloseoutAdmissionError(ValueError):
    """Stable native-admission gap with separate non-authoritative detail."""

    def __init__(self, gap: str, detail: str = "") -> None:
        super().__init__(f"{gap}:{detail}" if detail else gap)
        self.gap = gap
        self.detail = detail


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutAdmission:
    """Immutable fact snapshot admitted before ownerless closeout fencing."""

    root: Path
    decision_path: Path
    decision: lane.LaneResolutionDecision
    decision_bytes: bytes
    decision_sha256: str
    observation: lane.LaneObservation
    registration_token: git.GitWorktreeRegistrationToken
    executor_ref: str
    policy: roles.BranchRolePolicy
    accepted_branch: str
    accepted_head: str
    target_digest: str
    target_binding_digest: str
    existing_reservation: OwnerlessCloseoutReservation | None


def admit_ownerless_closeout(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
) -> OwnerlessCloseoutAdmission:
    """Admit one exact clean ownerless target using native repository facts."""
    try:
        return admit_ownerless_closeout_facts(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            receipt_reservation=None,
        )
    except OwnerlessCloseoutAdmissionError:
        raise
    except Exception as error:
        raise _error(_ADMISSION_UNVERIFIABLE, error.__class__.__name__) from error


def reobserve_ownerless_closeout_under_fence(
    *, admission: OwnerlessCloseoutAdmission, fence: dict[str, object]
) -> OwnerlessCloseoutAdmission:
    """Require the exact fence before and after complete native re-observation."""
    try:
        return reobserve_ownerless_closeout_facts(
            admission=admission,
            fence=fence,
            receipt_reservation=None,
        )
    except OwnerlessCloseoutAdmissionError:
        raise
    except Exception as error:
        raise _error(_ADMISSION_UNVERIFIABLE, error.__class__.__name__) from error


def admit_ownerless_closeout_facts(  # noqa: PLR0913, RUF100 - exact native admission facts
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    fence_observation: tuple[str, dict[str, object] | None] | None = None,
    receipt_reservation: receipt.OwnerlessReceiptReservationContext | None = None,
) -> OwnerlessCloseoutAdmission:
    """Build one native fact snapshot with an optional locally held receipt reservation."""
    control = root.absolute()
    policy, executor = _authority_context(control, executor_ref)
    try:
        record_root = current_record_root(control)
        model, raw = validation.admit_ownerless_decision_snapshot(
            root=control,
            record_root=record_root,
            decision_path=decision_path,
            supplied=decision,
        )
    except validation.OwnerlessDecisionAdmissionError as error:
        _fail(error.kind, error.detail)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        _raise("decision_invalid", "records", error)
    if policy.role_for_branch(model.observation.lane_ref) != roles.ROLE_WORK_LANE:
        _fail("target_role_invalid", "role")
    facts = _git_observation(control, model.observation.lane_ref, policy.accepted_branch)
    if facts.observation != model.observation:
        _fail("observation_stale", _observation_difference(model.observation, facts.observation))
    _chronicle(control, model, facts.accepted_head)
    decision_sha256 = hashlib.sha256(raw).hexdigest()
    target = target_digest(facts.observation.lane_ref, facts.observation.head)
    authority = (executor, policy.accepted_branch, facts.accepted_head, decision_sha256)
    binding = _binding(model=model, observation=facts.observation, authority=authority)
    binding_digest = _digest(binding)
    expected = OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=model.decision_id,
        lane_ref=facts.observation.lane_ref,
        head=facts.observation.head,
        executor_ref=executor,
        decision_sha256=decision_sha256,
        accepted_branch=policy.accepted_branch,
        accepted_head=facts.accepted_head,
        target_digest=target,
        target_binding_digest=binding_digest,
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    )
    existing, reservation_gap = receipt.ownerless_reservation_admission_or_gap(
        root=control,
        record_root=record_root,
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        expected=expected,
        receipt_reservation=receipt_reservation,
    )
    if reservation_gap:
        detail = "reservation" if reservation_gap.endswith("reservation_competing") else "records"
        raise OwnerlessCloseoutAdmissionError(reservation_gap, detail)
    if existing is not None:
        _require_ancestor(control, existing.accepted_head, facts.accepted_head, target=False)
    observed_fence = _state(control, facts.observation.lane_ref, fence_observation)
    if fence_observation is not None or observed_fence[0] == "present":
        if fence_observation is None and existing is None:
            _fail("fence_mismatch", "competition")
        detail = "held" if fence_observation is not None else "competition"
        acquisition_id = _acquisition_id(observed_fence, detail)
        fence_head = existing.accepted_head if existing is not None else facts.accepted_head
        fence_authority = (executor, policy.accepted_branch, fence_head, decision_sha256)
        retry_fence = _fence(model, facts.observation, fence_authority, acquisition_id)
        _exact_fence(observed_fence, retry_fence, detail)
        if (
            existing is not None
            and existing.target_binding_digest != retry_fence["target_binding_digest"]
        ):
            _fail("reservation_competing", "reservation")
    _require_ancestor(control, facts.observation.head, facts.accepted_head, target=True)
    return OwnerlessCloseoutAdmission(
        root=control,
        decision_path=decision_path.absolute(),
        decision=model,
        decision_bytes=raw,
        decision_sha256=decision_sha256,
        observation=facts.observation,
        registration_token=facts.registration_token,
        executor_ref=executor,
        policy=policy,
        accepted_branch=policy.accepted_branch,
        accepted_head=facts.accepted_head,
        target_digest=target,
        target_binding_digest=binding_digest,
        existing_reservation=existing,
    )


def reobserve_ownerless_closeout_facts(
    *,
    admission: OwnerlessCloseoutAdmission,
    fence: dict[str, object],
    receipt_reservation: receipt.OwnerlessReceiptReservationContext | None,
) -> OwnerlessCloseoutAdmission:
    """Reobserve exact facts under one fence and optional locally held receipt reservation."""
    try:
        with receipt.ownerless_receipt_reservation_guard(receipt_reservation):
            database = _database(admission.root)
            before = state_closeout.probe_closeout_fence(
                database, subject=admission.observation.lane_ref
            )
            acquisition_id = _acquisition_id(before, "before")
            expected = _admission_fence(admission, acquisition_id)
            _exact_fence(before, expected, "before", supplied=fence)
            try:
                fresh = admit_ownerless_closeout_facts(
                    root=admission.root,
                    decision_path=admission.decision_path,
                    decision=admission.decision.to_payload(),
                    executor_ref=admission.executor_ref,
                    fence_observation=before,
                    receipt_reservation=receipt_reservation,
                )
                for field in fields(OwnerlessCloseoutAdmission):
                    if getattr(fresh, field.name) != getattr(admission, field.name):
                        _fail("reobservation_stale", field.name)
                return fresh
            finally:
                after = state_closeout.probe_closeout_fence(
                    database, subject=admission.observation.lane_ref
                )
                _exact_fence(after, expected, "after", supplied=fence)
    except receipt.OwnerlessReceiptReservationError as error:
        _raise("reservation_competing", "receipt_reservation", error)


def _authority_context(root: Path, executor_ref: str) -> tuple[roles.BranchRolePolicy, str]:
    if type(executor_ref) is not str:
        _fail("policy_invalid", "executor_ref")
    try:
        snapshot = policy_reader.read_optional_root_bound_regular_file(
            root, _POLICY_PATH, maximum_bytes=_MAX_POLICY_BYTES
        )
        policy = (
            roles.BranchRolePolicy()
            if snapshot is None
            else roles.strict_branch_role_policy_from_text(snapshot.raw.decode("utf-8"))
        )
        executor = HolderRef.parse(executor_ref).serialize()
    except OwnerlessCloseoutAdmissionError:
        raise
    except (
        git.OwnerlessGitObservationError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as error:
        if not isinstance(error, git.OwnerlessGitObservationError) and "holder_ref" in str(error):
            _raise("policy_invalid", "executor_ref", error)
        _raise("policy_invalid", "workspace", error)
    if executor != executor_ref:
        _fail("policy_invalid", "executor_ref")
    return policy, executor


def _chronicle(root: Path, decision: lane.LaneResolutionDecision, accepted_head: str) -> None:
    reference = decision.chronicle_ref
    path = PurePosixPath(reference)
    if (
        not reference.startswith("evidence/chronicle/")
        or path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != reference
    ):
        _fail("chronicle_invalid", "path")
    try:
        raw = git.read_root_bound_regular_file(
            root, reference, maximum_bytes=_MAX_CHRONICLE_BYTES
        ).raw
    except git.OwnerlessGitObservationError as error:
        _raise("chronicle_invalid", "path_type", error)
    if hashlib.sha256(raw).hexdigest() != decision.chronicle_digest:
        _fail("chronicle_stale", "working_digest")
    if b"lane_resolution/retire" not in raw.splitlines():
        _fail("chronicle_invalid", "disposition")
    try:
        committed = git.git_object_bytes(root, f"{accepted_head}:{reference}")
    except git.OwnerlessGitObservationError as error:
        if error.detail == "git_object_mode":
            _fail("chronicle_invalid", "accepted_mode")
        _raise("git_unverifiable", "chronicle_git", error)
    if committed != raw:
        _fail("chronicle_stale", "accepted_bytes")


def _git_observation(root: Path, branch: str, accepted_branch: str):
    try:
        return git.observe_ownerless_git(root, branch=branch, accepted_branch=accepted_branch)
    except git.OwnerlessGitObservationError as error:
        if error.kind == "dirty":
            _fail("worktree_dirty", error.detail)
        if error.kind == "registration" and error.detail.startswith("accepted"):
            _fail("accepted_head_stale", error.detail)
        if error.kind == "registration":
            _fail("observation_stale", error.detail)
        _fail("git_unverifiable", error.detail)


def _state(
    root: Path,
    branch: str,
    observed_fence: tuple[str, dict[str, object] | None] | None,
) -> tuple[str, dict[str, object] | None]:
    try:
        return state_closeout.observe_ownerless_closeout_state(
            _database(root), subject=branch, observed_fence=observed_fence
        )
    except state_closeout.OwnerlessCloseoutStateError as error:
        _fail(error.kind, error.detail)


def _database(root: Path) -> Path:
    try:
        return state_database(root)
    except (OSError, TypeError, ValueError) as error:
        _raise("state_unverifiable", "database", error)


def _require_ancestor(root: Path, ancestor: str, descendant: str, *, target: bool) -> None:
    state = git.git_ancestry(root, ancestor, descendant)
    if state == "ancestor":
        return
    if state == "diverged":
        _fail("target_not_accepted_ancestor" if target else "accepted_head_stale", "ancestry")
    _fail("ancestry_unverifiable", "ancestry")


def _binding(
    *,
    model: lane.LaneResolutionDecision,
    observation: lane.LaneObservation,
    authority: _BindingAuthority,
) -> dict[str, Any]:
    executor_ref, accepted_branch, accepted_head, decision_sha256 = authority
    return {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": model.decision_id,
        "executor_ref": executor_ref,
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "payload": {
            "target_path": observation.path,
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": decision_sha256,
            "chronicle_digest": model.chronicle_digest,
        },
    }


def _digest(binding: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _fence(
    model: lane.LaneResolutionDecision,
    observation: lane.LaneObservation,
    authority: _BindingAuthority,
    acquisition_id: str,
) -> dict[str, object]:
    binding = _binding(model=model, observation=observation, authority=authority)
    binding["payload"] = {**binding["payload"], "acquisition_id": acquisition_id}
    return {**binding, "target_binding_digest": _digest(binding)}


def _admission_fence(
    admission: OwnerlessCloseoutAdmission, acquisition_id: str
) -> dict[str, object]:
    authority = (
        admission.executor_ref,
        admission.accepted_branch,
        admission.accepted_head,
        admission.decision_sha256,
    )
    return _fence(admission.decision, admission.observation, authority, acquisition_id)


def ownerless_retry_fence(
    *,
    admission: OwnerlessCloseoutAdmission,
    reservation: OwnerlessCloseoutReservation,
    acquisition_id: str,
) -> dict[str, object]:
    """Render the exact retained no-effect fence from durable reservation facts."""
    authority = (
        reservation.executor_ref,
        reservation.accepted_branch,
        reservation.accepted_head,
        reservation.decision_sha256,
    )
    return _fence(admission.decision, admission.observation, authority, acquisition_id)


def _acquisition_id(observed: tuple[str, dict[str, object] | None], detail: str) -> str:
    state, current = observed
    if state == "unverifiable":
        _fail("fence_unverifiable", detail)
    payload = current.get("payload") if state == "present" and current is not None else None
    acquisition_id = payload.get("acquisition_id") if isinstance(payload, dict) else None
    if not isinstance(acquisition_id, str) or type(acquisition_id) is not str:
        _fail("fence_mismatch", detail)
    return acquisition_id


def _exact_fence(
    observed: tuple[str, dict[str, object] | None],
    expected: dict[str, object],
    detail: str,
    *,
    supplied: dict[str, object] | None = None,
) -> None:
    state, current = observed
    if state == "unverifiable":
        _fail("fence_unverifiable", detail)
    if state != "present" or current != expected or (supplied is not None and supplied != expected):
        _fail("fence_mismatch", detail)


def _observation_difference(left: lane.LaneObservation, right: lane.LaneObservation) -> str:
    return next(
        (
            field
            for field in lane.LaneObservation.model_fields
            if getattr(left, field) != getattr(right, field)
        ),
        "observation",
    )


def _error(suffix: str, detail: str = "") -> OwnerlessCloseoutAdmissionError:
    return OwnerlessCloseoutAdmissionError(f"lane_resolution_ownerless_{suffix}", detail)


def _raise(suffix: str, detail: str, cause: Exception) -> NoReturn:
    raise _error(suffix, detail) from cause


def _fail(suffix: str, detail: str = "") -> NoReturn:
    gap = suffix if suffix.startswith("lane_") else f"lane_resolution_ownerless_{suffix}"
    raise OwnerlessCloseoutAdmissionError(gap, detail)

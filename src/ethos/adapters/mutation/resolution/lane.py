"""Two-phase exceptional Work Lane resolution with preservation-first effects."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.resolution._shared import accepted_preserve_retire_chronicle
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.closeout.recovery import apply_resolution
from ethos.adapters.mutation.resolution.closeout.recovery import ownerless_recovery_context
from ethos.adapters.mutation.resolution.closeout.recovery import recover_ownerless_resolution
from ethos.adapters.mutation.resolution.observation import ExactFileSnapshot
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError
from ethos.adapters.mutation.resolution.observation import git_object_bytes
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos.adapters.mutation.resolution.observation import read_root_bound_regular_file
from ethos.adapters.mutation.resolution.receipts import chronicle_event
from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.adapters.mutation.resolution.records.current.core import current_record_integrity_gap
from ethos.adapters.mutation.resolution.records.current.snapshot import read_current_record_path
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import accepted_control_root
from ethos.adapters.mutation.resolution.records.roots import canonical_record_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.lifecycle.reducer import TransitionFacts
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.contracts.lifecycle.reducer import reduce_transition
from ethos.contracts.resolution.lane import LaneObservation
from ethos.contracts.resolution.lane import LaneResolutionDecision
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path

_DISPOSITIONS = {"block", "preserve", "retire", "preserve-retire"}
_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"


def plan_lane_resolution(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    disposition: str,
    reason: str,
    evidence_refs: tuple[str, ...],
    chronicle_ref: str,
    recovery_plan: str,
    decision_path: Path,
    break_glass: bool,
    apply: bool,
) -> dict[str, object]:
    """Create the first-phase exceptional judgment; no lane effect occurs."""
    observation, gaps = observe_lane(root, branch)
    chronicle, chronicle_digest, chronicle_gaps = _accepted_chronicle(
        root,
        chronicle_ref=chronicle_ref,
        disposition=disposition,
        observation=observation,
    )
    evaluation = reduce_transition(
        load_lifecycle_declaration(root).policy("guarded"),
        TransitionRequest(apply=apply),
        TransitionFacts(
            initial_gaps=(
                *(
                    gap
                    for satisfied, gap in (
                        (disposition in _DISPOSITIONS, "lane_resolution_disposition_invalid"),
                        (bool(reason.strip()), "lane_resolution_reason_required"),
                        (bool(evidence_refs), "lane_resolution_evidence_required"),
                    )
                    if not satisfied
                ),
                *gaps,
                *chronicle_gaps,
            ),
            checks=(
                (bool(recovery_plan.strip()), "lane_resolution_recovery_plan_required"),
                (
                    disposition not in {"retire", "preserve-retire"} or break_glass,
                    "retire_exception_requires_break_glass",
                ),
                (
                    canonical_record_path(root, decision_path),
                    "lane_resolution_decision_path_not_local_artifact",
                ),
            ),
        ),
    )
    report = _report(branch, evaluation)
    if apply and evaluation.ok:
        decision = LaneResolutionDecision(
            decision_id=f"lane-decision:{uuid.uuid4()}",
            disposition=cast("Any", disposition),
            observation=observation,
            evidence_refs=evidence_refs,
            chronicle_ref=chronicle,
            chronicle_digest=chronicle_digest,
            recovery_plan=recovery_plan,
            reason=reason,
            break_glass=break_glass,
        ).to_payload()
        if not validate_schema_instance(
            "lane-resolution-decision.schema.json", decision, root=root
        )["ok"]:
            report.update(
                ok=False, state="blocked", required_gaps=["lane_resolution_decision_invalid"]
            )
            return report
        destination = decision_path.absolute()
        try:
            write_json_atomic(
                destination,
                decision,
                record_root=current_record_root(root),
            )
        except FileExistsError:
            report.update(
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_decision_path_exists"],
            )
        except (OSError, ValueError):
            report.update(
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_decision_path_not_local_artifact"],
            )
        else:
            report.update(
                state="decision_recorded",
                decision=decision,
                decision_path=destination.as_posix(),
                chronicle_event=chronicle_event(decision),
            )
    return _finish(
        report,
        command="lane-resolution-plan",
        action="lane.resolution.decide",
        resource=branch,
        expected_state={"observation_digest": observation.digest() if evaluation.ok else ""},
        apply=apply,
    )


def apply_lane_resolution(
    *, root: Path, decision_path: Path, confirm_irreversible: bool, apply: bool
) -> dict[str, object]:
    """Recompute the decision observation, then apply the bounded disposition."""
    decision, gaps = _read_decision(decision_path, root=root)
    branch = str(decision.get("observation", {}).get("lane_ref") or "")
    disposition = str(decision.get("disposition") or "")
    expected_state: dict[str, object] = {
        "decision_id": str(decision.get("decision_id") or ""),
        "observation_digest": str(decision.get("observation_digest") or ""),
        "confirm_irreversible": confirm_irreversible,
    }
    integrity_gap = current_record_integrity_gap(
        inventory=lane_resolution_inventory(root=root),
    )
    if integrity_gap or _CURRENT_RECORD_INVALID in gaps:
        evaluation = reduce_transition(
            load_lifecycle_declaration(root).policy("guarded"),
            TransitionRequest(apply=apply),
            TransitionFacts(
                initial_gaps=(*gaps, *((integrity_gap,) if integrity_gap else ())),
            ),
        )
        return _finish(
            _report(branch, evaluation),
            command="lane-resolution-apply",
            action=f"lane.resolution.{disposition or 'unknown'}",
            resource=branch or decision_path.resolve().as_posix(),
            expected_state=expected_state,
            apply=apply,
            confirmation=confirm_irreversible,
        )
    recovery, control_root, artifact_root, recovery_gap = (
        ownerless_recovery_context(
            root=root,
            decision=decision,
            disposition=disposition,
        )
        if not gaps
        else ({}, None, None, "")
    )
    if recovery_gap:
        evaluation = reduce_transition(
            load_lifecycle_declaration(root).policy("guarded"),
            TransitionRequest(apply=apply),
            TransitionFacts(initial_gaps=(*gaps, recovery_gap)),
        )
        report = _report(branch, evaluation)
        if recovery_gap.startswith(("lane_resolution_ownerless_", "lane_resolution_receipt_")):
            _block_resolution_report(report, recovery_gap, state="partial_transition")
        return _finish(
            report,
            command="lane-resolution-apply",
            action=f"lane.resolution.{disposition or 'unknown'}",
            resource=branch or decision_path.resolve().as_posix(),
            expected_state=expected_state,
            apply=apply,
            confirmation=confirm_irreversible,
        )
    if recovery and str(recovery["recovery_state"]) == "effect_complete_receipt_missing":
        observation = LaneObservation.model_validate(decision["observation"])
        evaluation = reduce_transition(
            load_lifecycle_declaration(root).policy("guarded"),
            TransitionRequest(apply=apply),
            TransitionFacts(
                initial_gaps=tuple(gaps),
                checks=((confirm_irreversible, "irreversible_confirmation_required"),),
            ),
        )
        report = _report(branch, evaluation)
        if apply and evaluation.ok and control_root is not None and artifact_root is not None:
            recover_ownerless_resolution(
                control_root=control_root,
                artifact_root=artifact_root,
                decision_path=decision_path,
                decision=decision,
                observation=observation,
                reservation=recovery,
                report=report,
            )
        return _finish(
            report,
            command="lane-resolution-apply",
            action=f"lane.resolution.{disposition or 'unknown'}",
            resource=branch or decision_path.resolve().as_posix(),
            expected_state=expected_state,
            apply=apply,
            confirmation=confirm_irreversible,
        )
    observation, observation_gaps = observe_lane(root, branch)
    chronicle_gaps: tuple[str, ...] = ()
    if disposition == "preserve-retire":
        _, chronicle_digest, current_chronicle_gaps = _accepted_chronicle(
            root,
            chronicle_ref=str(decision.get("chronicle_ref") or ""),
            disposition=disposition,
            observation=observation,
        )
        chronicle_gaps = tuple(current_chronicle_gaps)
        if not chronicle_gaps and chronicle_digest != str(decision.get("chronicle_digest") or ""):
            chronicle_gaps = ("lane_resolution_chronicle_stale",)
    evaluation = reduce_transition(
        load_lifecycle_declaration(root).policy("guarded"),
        TransitionRequest(apply=apply),
        TransitionFacts(
            initial_gaps=(*gaps, *observation_gaps, *chronicle_gaps),
            checks=(
                (
                    not decision
                    or observation.digest() == str(decision.get("observation_digest") or ""),
                    "lane_resolution_observation_stale",
                ),
                (
                    disposition not in {"retire", "preserve-retire"} or confirm_irreversible,
                    "irreversible_confirmation_required",
                ),
                (
                    disposition != "retire" or not observation.dirty,
                    "dirty_lane_retirement_blocked",
                ),
            ),
        ),
    )
    report = _report(branch, evaluation)
    if apply and evaluation.ok:
        apply_resolution(
            root=root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            report=report,
            recover_receipt_reservation=bool(
                recovery and str(recovery["recovery_state"]) == "reserved_no_effect"
            ),
        )
    return _finish(
        report,
        command="lane-resolution-apply",
        action=f"lane.resolution.{disposition or 'unknown'}",
        resource=branch or decision_path.resolve().as_posix(),
        expected_state=expected_state,
        apply=apply,
        confirmation=confirm_irreversible,
    )


def _block_resolution_report(report: dict[str, object], *gaps: str, state: str = "blocked") -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def _read_decision(path: Path, *, root: Path) -> tuple[dict[str, Any], list[str]]:
    if not canonical_record_path(root, path):
        return {}, ["lane_resolution_decision_path_not_local_artifact"]
    content, read_state = read_current_record_path(current_record_root(root), path)
    if content is None:
        gap = (
            "lane_resolution_decision_invalid"
            if read_state == "missing"
            else _CURRENT_RECORD_INVALID
        )
        return {}, [gap]
    try:
        payload = json.loads(content)
        decision = LaneResolutionDecision.model_validate_json(
            json.dumps({field: payload[field] for field in LaneResolutionDecision.model_fields})
        )
    except (
        KeyError,
        OSError,
        OverflowError,
        RecursionError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ):
        return {}, ["lane_resolution_decision_invalid"]
    gap = (
        "lane_resolution_decision_invalid"
        if not validate_schema_instance("lane-resolution-decision.schema.json", payload, root=root)[
            "ok"
        ]
        or not valid_decision_id(str(payload.get("decision_id") or ""))
        else _CURRENT_RECORD_INVALID
        if content != canonical_current_record_bytes(cast("dict[str, object]", payload))
        else "lane_resolution_decision_digest_invalid"
        if decision.observation.digest() != payload.get("observation_digest")
        else ""
    )
    return cast("dict[str, Any]", payload), [gap] if gap else []


def _accepted_chronicle(
    root: Path,
    *,
    chronicle_ref: str,
    disposition: str,
    observation: LaneObservation | None = None,
) -> tuple[str, str, list[str]]:
    if not chronicle_ref.strip():
        return "", "", ["lane_resolution_chronicle_required"]
    relative, gap = _chronicle_reference(chronicle_ref)
    if gap:
        return relative, "", [gap]
    if disposition == "preserve-retire":
        digest, gaps = _preserve_retire_chronicle_digest(root, relative, observation)
        return relative, digest, gaps
    working, gap = _chronicle_working(root, relative, disposition)
    if gap or working is None:
        return relative, "", [gap or "lane_resolution_chronicle_invalid"]
    if not _accepted_chronicle_matches(root, relative, working):
        return relative, "", ["lane_resolution_chronicle_invalid"]
    return relative, hashlib.sha256(working.raw).hexdigest(), []


def _preserve_retire_chronicle_digest(
    root: Path,
    relative: str,
    observation: LaneObservation | None,
) -> tuple[str, list[str]]:
    if observation is None:
        return "", ["lane_resolution_chronicle_invalid"]
    try:
        control_root = accepted_control_root(root)
    except ValueError as error:
        control_gap = str(error).strip()
        return "", [
            control_gap
            if control_gap.startswith("lane_resolution_")
            else "lane_resolution_chronicle_invalid"
        ]
    working, gap = accepted_preserve_retire_chronicle(
        control_root,
        chronicle_ref=relative,
        target_branch=observation.lane_ref,
        target_head=observation.head,
    )
    if gap or working is None:
        return "", [gap or "lane_resolution_chronicle_invalid"]
    return hashlib.sha256(working).hexdigest(), []


def _chronicle_reference(chronicle_ref: str) -> tuple[str, str]:
    relative_path = PurePosixPath(chronicle_ref)
    invalid_path = (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.as_posix() != chronicle_ref
    )
    if invalid_path:
        return "", "lane_resolution_chronicle_outside_repository"
    relative = relative_path.as_posix()
    gap = "" if relative.startswith("evidence/chronicle/") else "lane_resolution_chronicle_missing"
    return relative, gap


def _chronicle_working(
    root: Path, relative: str, disposition: str
) -> tuple[ExactFileSnapshot | None, str]:
    try:
        working = read_root_bound_regular_file(root, relative, maximum_bytes=16 * 1024 * 1024)
    except OwnerlessGitObservationError as error:
        gap = (
            "lane_resolution_chronicle_missing"
            if error.detail == "file_missing"
            else "lane_resolution_chronicle_invalid"
        )
        return None, gap
    try:
        text = working.raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "lane_resolution_chronicle_invalid"
    if f"lane_resolution/{disposition}" not in text:
        return None, "lane_resolution_chronicle_disposition_mismatch"
    return working, ""


def _accepted_chronicle_matches(root: Path, relative: str, working: ExactFileSnapshot) -> bool:
    try:
        accepted = git_object_bytes(root, f"HEAD:{relative}")
        current = read_root_bound_regular_file(root, relative, maximum_bytes=16 * 1024 * 1024)
    except OwnerlessGitObservationError:
        return False
    return accepted == working.raw and current == working


def _report(branch: str, evaluation: Any) -> dict[str, object]:
    return {
        "ok": evaluation.ok,
        "state": evaluation.state,
        "branch": branch,
        "decision": {},
        "decision_path": "",
        "preservation_package": {},
        "receipt": {},
        "receipt_path": "",
        "ownerless_closeout_binding": {},
        "chronicle_event": {},
        "required_gaps": list(evaluation.gaps),
    }


def _finish(  # noqa: PLR0913, RUF100
    report: dict[str, object],
    *,
    command: str,
    action: str,
    resource: str,
    expected_state: dict[str, object],
    apply: bool,
    confirmation: bool = False,
) -> dict[str, object]:
    gaps = tuple(str(gap) for gap in cast("list[object]", report["required_gaps"]))
    report["mutation"] = mutation_envelope(
        TransitionRequest(command=command, apply=apply, authorized=confirmation, expect_head=None),
        action=action,
        resource=resource,
        expected_state=expected_state,
        verdict=cast("Any", "allow" if report["ok"] else "block"),
        required_gaps=gaps,
        state=str(report["state"]),
        evidence_boundary="accepted_chronicle_decision_and_recomputed_observation",
        enforcement_boundary="local_git_and_filesystem_transition",
        verifier_provenance="current_runner",
    )
    return report

"""Two-phase exceptional Work Lane resolution."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from pydantic import ValidationError

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.resolution._effects import prepare_resolution_effect
from ethos.adapters.mutation.resolution._effects import retire_lane
from ethos.adapters.mutation.resolution._observation import observe_lane
from ethos.adapters.mutation.resolution._shared import accepted_control_root
from ethos.adapters.mutation.resolution._shared import canonical_record_path
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import release_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.records.core import reserve_resolution_receipt
from ethos.contracts.resolution.lane import LaneObservation
from ethos.contracts.resolution.lane import LaneResolutionDecision
from ethos.contracts.transitions import GUARDED_TRANSITION
from ethos.contracts.transitions import TransitionFacts
from ethos.contracts.transitions import TransitionRequest
from ethos.contracts.transitions import reduce_transition
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path

_DISPOSITIONS = {"block", "preserve", "retire", "preserve-retire"}
_DESTRUCTIVE = {"retire", "preserve-retire"}


def plan_lane_resolution(
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
    """Record one immutable decision; no lane effect occurs in this phase."""
    observation, gaps = observe_lane(root, branch)
    chronicle, chronicle_digest, chronicle_gaps = _accepted_chronicle(
        root, chronicle_ref=chronicle_ref, disposition=disposition
    )
    evaluation = reduce_transition(
        GUARDED_TRANSITION,
        TransitionRequest(apply=apply),
        TransitionFacts(
            initial_gaps=(
                *(
                    gap
                    for ok, gap in (
                        (disposition in _DISPOSITIONS, "lane_resolution_disposition_invalid"),
                        (bool(reason.strip()), "lane_resolution_reason_required"),
                        (bool(evidence_refs), "lane_resolution_evidence_required"),
                    )
                    if not ok
                ),
                *gaps,
                *chronicle_gaps,
            ),
            checks=(
                (bool(recovery_plan.strip()), "lane_resolution_recovery_plan_required"),
                (
                    disposition not in _DESTRUCTIVE or break_glass,
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
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_decision_invalid"],
            )
        else:
            destination = decision_path.resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                report.update(
                    ok=False,
                    state="blocked",
                    required_gaps=["lane_resolution_decision_path_exists"],
                )
            else:
                destination.write_text(
                    json.dumps(decision, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                    errors="strict",
                )
                report.update(
                    state="decision_recorded",
                    decision=decision,
                    decision_path=destination.as_posix(),
                    chronicle_event=_chronicle_event(decision),
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
    """Recompute facts and apply one bounded native resolution effect."""
    decision, gaps = _read_decision(decision_path, root=root)
    branch = str(cast("dict[str, object]", decision.get("observation") or {}).get("lane_ref") or "")
    disposition = str(decision.get("disposition") or "")
    observation, observation_gaps = observe_lane(root, branch)
    handoff_required = bool(decision and disposition in _DESTRUCTIVE and observation.holder_ref)
    evaluation = reduce_transition(
        GUARDED_TRANSITION,
        TransitionRequest(apply=apply),
        TransitionFacts(
            initial_gaps=(*gaps, *observation_gaps),
            checks=(
                (
                    not decision
                    or observation.digest() == str(decision.get("observation_digest") or ""),
                    "lane_resolution_observation_stale",
                ),
                (
                    disposition not in _DESTRUCTIVE or confirm_irreversible,
                    "irreversible_confirmation_required",
                ),
                (disposition != "retire" or not observation.dirty, "dirty_lane_retirement_blocked"),
                (not handoff_required, "lane_resolution_handoff_required"),
            ),
        ),
    )
    report = _report(branch, evaluation)
    if apply and evaluation.ok:
        _apply_resolution(
            root=root,
            decision=decision,
            observation=observation,
            disposition=disposition,
            report=report,
        )
    return _finish(
        report,
        command="lane-resolution-apply",
        action=f"lane.resolution.{disposition or 'unknown'}",
        resource=branch or decision_path.resolve().as_posix(),
        expected_state={
            "decision_id": str(decision.get("decision_id") or ""),
            "observation_digest": str(decision.get("observation_digest") or ""),
            "confirm_irreversible": confirm_irreversible,
        },
        apply=apply,
        confirmation=confirm_irreversible,
    )


def _apply_resolution(
    *,
    root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    report: dict[str, object],
) -> None:
    try:
        control_root = accepted_control_root(root)
        artifact_root = records_artifact_root(root)
    except ValueError as error:
        _block(report, _gap(error, "lane_resolution_control_root_unavailable"))
        return
    if not _reserve_receipt(control_root, artifact_root, str(decision["decision_id"]), report):
        return
    _execute_resolution(
        control_root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=observation,
        disposition=disposition,
        report=report,
    )


def _reserve_receipt(
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    report: dict[str, object],
) -> bool:
    try:
        reserve_resolution_receipt(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
        )
    except FileExistsError:
        _block(report, "lane_resolution_receipt_path_exists")
        return False
    except OSError:
        _block(report, "lane_resolution_receipt_path_unsafe")
        return False
    except ValueError as error:
        _block(report, _gap(error, "lane_resolution_receipt_path_unsafe"))
        return False
    return True


def _execute_resolution(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    report: dict[str, object],
) -> None:
    decision_id = str(decision["decision_id"])
    completed = False
    effect_applied = False
    destructive = disposition in _DESTRUCTIVE
    try:
        try:
            package, receipt, state, gap = prepare_resolution_effect(
                control_root=control_root,
                artifact_root=artifact_root,
                decision=decision,
                observation=observation,
                disposition=disposition,
            )
        except (OSError, ValueError) as error:
            _block(report, _gap(error, "lane_resolution_effect_failed"))
            return
        if gap:
            _block(report, gap)
            return
        report.update(state=state, preservation_package=package)
        if disposition == "preserve-retire":
            current, current_gaps = observe_lane(control_root, observation.lane_ref)
            if current_gaps or current.digest() != observation.digest():
                _block(report, *current_gaps, "lane_resolution_observation_stale")
                return
        if destructive:
            try:
                retire_lane(
                    root=control_root,
                    observation=observation,
                    force=disposition == "preserve-retire" and observation.dirty,
                )
            except ValueError as error:
                _block(report, _gap(error, "lane_resolution_branch_delete_failed"))
                return
            effect_applied = True
        try:
            receipt_path = write_resolution_receipt(
                root=control_root, receipt=receipt, artifact_root=artifact_root
            )
        except (OSError, ValueError):
            _block(
                report,
                "lane_resolution_receipt_write_failed_after_effect"
                if destructive
                else "lane_resolution_receipt_write_failed",
                state="partial_transition" if destructive else "blocked",
            )
            return
        completed = True
        report.update(
            receipt=receipt,
            receipt_path=receipt_path,
            chronicle_event=_chronicle_event(decision, receipt),
        )
    finally:
        if not (effect_applied and not completed):
            try:
                release_resolution_receipt_reservation(
                    root=control_root,
                    decision_id=decision_id,
                    artifact_root=artifact_root,
                )
            except OSError:
                _block(
                    report,
                    "lane_resolution_receipt_reservation_release_failed",
                    state="partial_transition" if completed else "blocked",
                )


def _read_decision(path: Path, *, root: Path) -> tuple[dict[str, Any], list[str]]:
    if not canonical_record_path(root, path):
        return {}, ["lane_resolution_decision_path_not_local_artifact"]
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
        decision = LaneResolutionDecision.model_validate_json(
            json.dumps({field: payload[field] for field in LaneResolutionDecision.model_fields})
        )
    except (KeyError, OSError, json.JSONDecodeError, ValidationError, TypeError):
        return {}, ["lane_resolution_decision_invalid"]
    if not validate_schema_instance("lane-resolution-decision.schema.json", payload, root=root)[
        "ok"
    ]:
        return cast("dict[str, Any]", payload), ["lane_resolution_decision_invalid"]
    if not valid_decision_id(str(payload.get("decision_id") or "")):
        return cast("dict[str, Any]", payload), ["lane_resolution_decision_invalid"]
    return (
        cast("dict[str, Any]", payload),
        []
        if decision.observation.digest() == payload.get("observation_digest")
        else ["lane_resolution_decision_digest_invalid"],
    )


def _accepted_chronicle(
    root: Path, *, chronicle_ref: str, disposition: str
) -> tuple[str, str, list[str]]:
    if not chronicle_ref.strip():
        return "", "", ["lane_resolution_chronicle_required"]
    path = (root / chronicle_ref).resolve()
    try:
        relative = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return "", "", ["lane_resolution_chronicle_outside_repository"]
    if not relative.startswith("evidence/chronicle/") or not path.is_file():
        return relative, "", ["lane_resolution_chronicle_missing"]
    if f"lane_resolution/{disposition}" not in path.read_text(encoding="utf-8"):
        return relative, "", ["lane_resolution_chronicle_disposition_mismatch"]
    return relative, hashlib.sha256(path.read_bytes()).hexdigest(), []


def _chronicle_event(
    decision: dict[str, Any], receipt: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "event_type": "state_change" if receipt else "decision",
        "subject_id": str(decision["observation"]["lane_ref"]),
        "decision": str(decision["disposition"]),
        "evidence_ids": (
            [str(receipt["receipt_id"])] if receipt else list(decision["evidence_refs"])
        ),
        "current_state_delta": str(receipt["state"])
        if receipt
        else "exceptional resolution accepted; effect pending recomputation",
    }


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
        "chronicle_event": {},
        "required_gaps": list(evaluation.gaps),
    }


def _block(report: dict[str, object], *gaps: str, state: str = "blocked") -> None:
    current = cast("list[object]", report.get("required_gaps") or [])
    report.update(
        ok=False,
        state=state,
        required_gaps=list(
            dict.fromkeys([*(str(gap) for gap in current), *(gap for gap in gaps if gap)])
        ),
    )


def _gap(error: Exception, fallback: str) -> str:
    message = str(error).strip()
    return message if message.startswith("lane_resolution_") else fallback


def _finish(
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

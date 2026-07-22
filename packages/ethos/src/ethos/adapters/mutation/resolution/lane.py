"""Two-phase exceptional Work Lane resolution with preservation-first effects."""

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
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.contracts.lifecycle.core import reduce_guards
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

if TYPE_CHECKING:
    from pathlib import Path

_DISPOSITIONS = {"block", "preserve", "retire", "preserve-retire"}


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
        root, chronicle_ref=chronicle_ref, disposition=disposition
    )
    evaluation = reduce_guards(
        apply=apply,
        initial_gaps=(*gaps, *chronicle_gaps),
        prefix_checks=(
            (disposition in _DISPOSITIONS, "lane_resolution_disposition_invalid"),
            (bool(reason.strip()), "lane_resolution_reason_required"),
            (bool(evidence_refs), "lane_resolution_evidence_required"),
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
        destination = decision_path.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(decision, indent=2, sort_keys=True) + "\n")
        except FileExistsError:
            report.update(
                ok=False,
                state="blocked",
                required_gaps=["lane_resolution_decision_path_exists"],
            )
        else:
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
    """Recompute the decision observation, then apply the bounded disposition."""
    decision, gaps = _read_decision(decision_path, root=root)
    branch = str(decision.get("observation", {}).get("lane_ref") or "")
    observation, observation_gaps = observe_lane(root, branch)
    disposition = str(decision.get("disposition") or "")
    expected_state: dict[str, object] = {
        "decision_id": str(decision.get("decision_id") or ""),
        "observation_digest": str(decision.get("observation_digest") or ""),
        "confirm_irreversible": confirm_irreversible,
    }
    evaluation = reduce_guards(
        apply=apply,
        initial_gaps=(*gaps, *observation_gaps),
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
            (disposition != "retire" or not observation.dirty, "dirty_lane_retirement_blocked"),
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
        expected_state=expected_state,
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
    control_root, artifact_root, root_gap = _resolution_roots(root)
    if root_gap or control_root is None or artifact_root is None:
        _block(report, root_gap)
        return
    decision_id = str(decision.get("decision_id") or "")
    if reservation_gap := _reserve_receipt(control_root, artifact_root, decision_id):
        _block(report, reservation_gap)
        return

    retain_reservation = False
    receipt_written = False
    try:
        package, receipt, state, effect_gaps = _prepare_resolution(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            disposition=disposition,
        )
        if effect_gaps:
            _block(report, *effect_gaps)
            return
        report.update(state=state, preservation_package=package)
        retain_reservation, retire_gap = _retire_resolution(
            root=root,
            observation=observation,
            disposition=disposition,
        )
        if retire_gap:
            _block(report, retire_gap, state=retire_gap.removeprefix("lane_resolution_"))
            return
        destructive_effect = disposition in {"retire", "preserve-retire"}
        try:
            receipt_path = write_resolution_receipt(
                root=control_root,
                receipt=receipt,
                artifact_root=artifact_root,
            )
        except OSError:
            _block(
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
            chronicle_event=_chronicle_event(decision, receipt),
        )
    finally:
        cleanup_gap = _release_receipt_reservation_unless_partial(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            retain_reservation=retain_reservation,
            receipt_written=receipt_written,
        )
        if cleanup_gap:
            current_gaps = cast("list[str]", report["required_gaps"])
            _block(
                report,
                *current_gaps,
                cleanup_gap,
                state="partial_transition" if receipt_written else "blocked",
            )


def _resolution_roots(root: Path) -> tuple[Path | None, Path | None, str]:
    try:
        return accepted_control_root(root), records_artifact_root(root), ""
    except ValueError as error:
        return None, None, _transition_gap(error, "lane_resolution_control_root_unavailable")


def _reserve_receipt(control_root: Path, artifact_root: Path, decision_id: str) -> str:
    try:
        reserve_resolution_receipt(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
        )
    except ValueError as error:
        return _transition_gap(error, "lane_resolution_receipt_invalid")
    except OSError as error:
        return (
            "lane_resolution_receipt_path_exists"
            if isinstance(error, FileExistsError)
            else "lane_resolution_receipt_path_unsafe"
        )
    return ""


def _prepare_resolution(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], str, tuple[str, ...]]:
    try:
        package, receipt, state, effect_gap = prepare_resolution_effect(
            control_root=control_root,
            artifact_root=artifact_root,
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
    current, current_gaps = observe_lane(control_root, observation.lane_ref)
    if current_gaps or current.digest() != observation.digest():
        return (
            package,
            receipt,
            state,
            tuple(dict.fromkeys((*current_gaps, "lane_resolution_observation_stale"))),
        )
    return package, receipt, state, ()


def _retire_resolution(
    *, root: Path, observation: LaneObservation, disposition: str
) -> tuple[bool, str]:
    if disposition not in {"retire", "preserve-retire"}:
        return False, ""
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
        )
    return True, ""


def _block(report: dict[str, object], *gaps: str, state: str = "blocked") -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def _release_receipt_reservation_unless_partial(
    *,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    retain_reservation: bool,
    receipt_written: bool,
) -> str:
    if retain_reservation and not receipt_written:
        return ""
    try:
        release_resolution_receipt_reservation(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
        )
    except OSError:
        return "lane_resolution_receipt_reservation_release_failed"
    return ""


def _transition_gap(error: Exception, fallback: str) -> str:
    message = str(error).strip()
    return message if message.startswith("lane_resolution_") else fallback


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
    gaps = (
        []
        if decision.observation.digest() == payload.get("observation_digest")
        else ["lane_resolution_decision_digest_invalid"]
    )
    return cast("dict[str, Any]", payload), gaps


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
        "evidence_ids": [str(receipt["receipt_id"])]
        if receipt
        else list(decision["evidence_refs"]),
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
        MutationRequest(command=command, apply=apply, authorized=confirmation, expect_head=None),
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

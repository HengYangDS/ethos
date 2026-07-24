"""Two-phase exceptional Work Lane resolution with preservation-first effects."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.resolution._effects import prepare_resolution_effect
from ethos.adapters.mutation.resolution._effects import retire_clean_ownerless_lane
from ethos.adapters.mutation.resolution._observation import observe_lane
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.closeout.recovery import ResolutionRuntime
from ethos.adapters.mutation.resolution.closeout.recovery import apply_resolution
from ethos.adapters.mutation.resolution.closeout.recovery import ownerless_recovery_context
from ethos.adapters.mutation.resolution.closeout.recovery import recover_ownerless_resolution
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.core import release_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.adapters.mutation.resolution.records.current.core import current_record_integrity_gap
from ethos.adapters.mutation.resolution.records.current.snapshot import read_current_record_path
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import accepted_control_root
from ethos.adapters.mutation.resolution.records.roots import canonical_record_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.contracts.lifecycle.core import reduce_guards
from ethos_core.contracts.resolution.lane import LaneObservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

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
        evaluation = reduce_guards(
            apply=apply,
            initial_gaps=(*gaps, *((integrity_gap,) if integrity_gap else ())),
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
    runtime = _resolution_runtime()
    recovery, control_root, artifact_root, recovery_gap = (
        ownerless_recovery_context(
            root=root,
            decision=decision,
            disposition=disposition,
            runtime=runtime,
        )
        if not gaps
        else ({}, None, None, "")
    )
    if recovery_gap:
        evaluation = reduce_guards(apply=apply, initial_gaps=(*gaps, recovery_gap))
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
        evaluation = reduce_guards(
            apply=apply,
            initial_gaps=tuple(gaps),
            checks=((confirm_irreversible, "irreversible_confirmation_required"),),
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
                runtime=runtime,
                chronicle_event=_chronicle_event,
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
        apply_resolution(
            root=root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            report=report,
            runtime=runtime,
            chronicle_event=_chronicle_event,
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


def _resolution_runtime() -> ResolutionRuntime:
    return ResolutionRuntime(
        accepted_control_root=accepted_control_root,
        current_record_root=current_record_root,
        observe_lane=observe_lane,
        prepare_resolution_effect=prepare_resolution_effect,
        release_resolution_receipt_reservation=release_resolution_receipt_reservation,
        retire_clean_ownerless_lane=retire_clean_ownerless_lane,
        write_resolution_receipt=write_resolution_receipt,
        release_closeout_fence=release_closeout_fence,
        block_resolution_report=_block_resolution_report,
        ownerless_closeout_candidate=_ownerless_closeout_candidate,
    )


def _ownerless_closeout_candidate(disposition: str, observation: LaneObservation) -> bool:
    return (
        disposition == "retire"
        and not observation.dirty
        and observation.orphan
        and not observation.holder_ref
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

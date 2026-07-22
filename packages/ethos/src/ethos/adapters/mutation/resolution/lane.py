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
from ethos.adapters.mutation.resolution._effects import write_completion_receipt
from ethos.adapters.mutation.resolution._observation import observe_lane
from ethos.adapters.mutation.resolution._shared import accepted_control_root
from ethos.adapters.mutation.resolution._shared import canonical_record_path
from ethos.adapters.mutation.resolution._shared import records_artifact_root
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.record_store import release_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.record_store import reserve_resolution_receipt
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.contracts.lifecycle.core import LANE_RESOLUTION_APPLY
from ethos_core.contracts.lifecycle.core import LANE_RESOLUTION_DECIDE
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.contracts.lifecycle.core import reduce_guards
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
        LANE_RESOLUTION_DECIDE,
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
                _local_artifact_path(root, decision_path),
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
        LANE_RESOLUTION_APPLY,
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

    def finish_report() -> dict[str, object]:
        return _finish(
            report,
            command="lane-resolution-apply",
            action=f"lane.resolution.{disposition or 'unknown'}",
            resource=branch or decision_path.resolve().as_posix(),
            expected_state=expected_state,
            apply=apply,
            confirmation=confirm_irreversible,
        )

    def stop(gap: str, *, state: str = "blocked") -> dict[str, object]:
        report.update(ok=False, state=state, required_gaps=[gap])
        return finish_report()

    if apply and evaluation.ok:
        control_root = accepted_control_root(root)
        artifact_root = records_artifact_root(root)
        decision_id = str(decision.get("decision_id") or "")
        try:
            reserve_resolution_receipt(
                root=control_root,
                decision_id=decision_id,
                artifact_root=artifact_root,
            )
        except OSError as error:
            return stop(
                "lane_resolution_receipt_path_exists"
                if isinstance(error, FileExistsError)
                else "lane_resolution_receipt_path_unsafe"
            )
        effect_started = False
        receipt_written = False
        try:
            package, receipt, state, effect_gap = prepare_resolution_effect(
                control_root=control_root,
                artifact_root=artifact_root,
                decision=decision,
                observation=observation,
                disposition=disposition,
            )
            if effect_gap:
                return stop(effect_gap)
            report.update(state=state, preservation_package=package, receipt=receipt)
            destructive_effect = disposition in {"retire", "preserve-retire"}
            if destructive_effect:
                effect_started = True
                retire_lane(root=root, observation=observation)
            receipt_path, write_gap = write_completion_receipt(
                control_root=control_root,
                artifact_root=artifact_root,
                receipt=receipt,
                destructive_effect=destructive_effect,
            )
            if write_gap:
                return stop(
                    write_gap,
                    state="partial_transition",
                )
            receipt_written = True
            report.update(
                receipt_path=receipt_path,
                chronicle_event=_chronicle_event(decision, receipt),
            )
        finally:
            if not effect_started or receipt_written:
                release_resolution_receipt_reservation(
                    root=control_root,
                    decision_id=decision_id,
                    artifact_root=artifact_root,
                )
    return finish_report()


def _read_decision(path: Path, *, root: Path) -> tuple[dict[str, Any], list[str]]:
    if not canonical_record_path(root, path):
        return {}, ["lane_resolution_decision_path_not_local_artifact"]
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
        decision = LaneResolutionDecision.model_validate(
            {field: payload[field] for field in LaneResolutionDecision.model_fields}
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


def _local_artifact_path(root: Path, path: Path) -> bool:
    return canonical_record_path(root, path)


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

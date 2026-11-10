"""Work Lane retirement: landed and superseded lanes, absorbed refs, abandonment and recovery.

Each operation takes the resolved root and its catalog request, runs the one owner of its effect
and projects that owner's report through `lane_result`. An abandonment or a recovery executes an
immutable receipt, so both report the effects it completed and the effects that remain.
"""

from pathlib import Path
from typing import Literal
from typing import cast

from ethos.adapters.mutation.lane_retirement.abandonment import derive_lane_abandonment
from ethos.adapters.mutation.lane_retirement.absorbed import retire_absorbed_ref
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.mutation.lane_retirement.operation import execute_retirement_operation
from ethos.application.lane.result import lane_result
from ethos.contracts.operations.retire import AbandonRequest
from ethos.contracts.operations.retire import AbsorbedRefRequest
from ethos.contracts.operations.retire import LandedRequest
from ethos.contracts.operations.retire import RecoverRequest
from ethos.contracts.operations.retire import SupersededRequest
from ethos.contracts.retirement import LinkedRetirementRequest
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

# An abandonment applies only through the receipt that its derivation keeps.
_RECEIPT_REQUIRED: dict[str, object] = {
    "verdict": "block",
    "state": "blocked",
    "required_gaps": ["lane_retirement_receipt_required"],
    "next_action": "",
    "user_decision_required": False,
}


def _receipt_result(command: str, report: dict[str, object]) -> EthosResult:
    """Project one receipt's report alike whether it was derived, applied or recovered."""
    summary = {name: report.get(name) or "" for name in ("branch", "head")}
    summary |= {name: report.get(name) or [] for name in ("completed_effects", "remaining_effects")}
    return lane_result(command, report, summary=summary)


def _executed(
    root: Path, request: AbandonRequest | RecoverRequest, mode: Literal["abandon"] | None
) -> dict[str, object]:
    """Apply or resume one receipt, or preview it, after authority and mode admission."""
    return execute_retirement_operation(
        root=root,
        receipt_path=request.receipt or "",
        receipt_sha256=request.receipt_sha256 or "",
        apply=request.apply,
        authorized=request.authorize,
        expected_mode=mode,
    )


def derive_abandonment(root: Path, request: AbandonRequest) -> EthosResult:
    """Derive and keep the abandonment's receipt; an apply without that receipt is refused."""
    fields = request.model_dump(include={"path", "reason_code", "reason", "review_content"})
    report = (
        dict(_RECEIPT_REQUIRED)
        if request.apply
        else derive_lane_abandonment(root=root, branch=request.branch or "", **fields)
    )
    return _receipt_result("lane retire abandon", report)


def abandon_by_receipt(root: Path, request: AbandonRequest) -> EthosResult:
    """Apply, or preview, the abandonment that one derived receipt binds."""
    return _receipt_result("lane retire abandon", _executed(root, request, "abandon"))


def recover_retirement(root: Path, request: RecoverRequest) -> EthosResult:
    """Resume one exact partial retirement from its immutable receipt."""
    return _receipt_result("lane retire recover", _executed(root, request, None))


def retire_absorbed(root: Path, request: AbsorbedRefRequest) -> EthosResult:
    """Retire one exact unlinked, unleased local topic ref absorbed by accepted truth."""
    report = retire_absorbed_ref(root=root, **request.model_dump())
    summary = {
        "branch": request.branch,
        "head": request.expect_head,
        "accepted_head": request.accepted_head,
        "retire_ready": report_verdict(report) == "pass",
    }
    return lane_result("lane retire absorbed-ref", report, summary=summary)


def retire_superseded(root: Path, request: SupersededRequest) -> EthosResult:
    """Retire absorbed work, or derive exact receipt-bound retained-topic retirement."""
    linked = LinkedRetirementRequest(**request.model_dump())
    report = retire_linked_work_lane(root=root, mode="superseded", request=linked)
    lane = cast("dict[str, object]", report["lane"])
    summary = {
        "branch": report["branch"],
        "head": lane.get("head") or linked.expect_head or "",
        "absorbed_by": linked.absorbed_by.strip(),
        "retire_ready": bool(lane.get("retire_ready")) and report_verdict(report) == "pass",
    }
    return lane_result("lane retire superseded", report, summary=summary)


def retire_landed(root: Path, request: LandedRequest) -> EthosResult:
    """Retire an explicitly selected clean topic worktree absorbed by accepted truth."""
    linked = LinkedRetirementRequest(**request.model_dump())
    report = retire_linked_work_lane(root=root, mode="landed", request=linked)
    lanes = cast("list[dict[str, object]]", report["lanes"])
    selected = next((lane for lane in lanes if lane["branch"] == request.branch), {})
    passed = report_verdict(report) == "pass"
    summary = {
        "landed_lane_count": sum(bool(lane.get("retire_ready")) for lane in lanes) if passed else 0,
        "selected_branch": request.branch or "",
        "selected_retire_ready": bool(selected.get("retire_ready")) and passed,
        "selected_blockers": tuple(string_sequence(selected.get("required_gaps"))),
    }
    return lane_result("lane retire landed", report, summary=summary)

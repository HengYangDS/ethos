"""The Work Lane lifecycle: status, housekeeping, the candidate, start, base refresh and archive.

Each operation takes the resolved root and its catalog request, runs the one adapter that owns its
effect and projects the adapter's report through `lane_result`.
"""

from pathlib import Path
from typing import cast

import ethos.domain.prove as prove_domain
from ethos.adapters.mutation.lane_lifecycle.archive.command import archive_change
from ethos.adapters.mutation.lane_lifecycle.candidate.materialization import materialize_candidate
from ethos.adapters.mutation.lane_lifecycle.candidate_projection import bootstrap_candidate
from ethos.adapters.mutation.lane_lifecycle.candidate_projection import (
    refresh_candidate_from_accepted,
)
from ethos.adapters.mutation.lane_lifecycle.start import start_work_lane
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh import refresh_work_lane_base
from ethos.adapters.mutation.worktree.detached_cleanup import housekeeping_worktrees
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.application.land.closeout import closeout_command_from_status
from ethos.application.lane.result import lane_result
from ethos.contracts.operations.lane import ArchiveChangeRequest
from ethos.contracts.operations.lane import CandidateRequest
from ethos.contracts.operations.lane import HousekeepingRequest
from ethos.contracts.operations.lane import RefreshBaseRequest
from ethos.contracts.operations.lane import StartRequest
from ethos.contracts.operations.lane import StatusRequest
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

_CANDIDATE = ("branch", "head", "path")
# The fields only a materialization reads.
_MATERIALIZED = {"preserved_preimage", "retention_ref", "reason", "expect_state"}


def _path(value: str | None) -> Path | None:
    return Path(value) if value is not None else None


def inspect_lane_status(root: Path, _request: StatusRequest) -> EthosResult:
    """Inspect Work Lane topology and foreign lanes, validated as proof validates them."""
    report = workspace_status(root)
    foreign = cast("list[dict[str, object]]", report.get("foreign_work_lanes") or [])
    unbound = cast("list[dict[str, object]]", report.get("unbound_work_lane_refs") or [])
    validation = prove_domain.workspace_status_validation(root, report)
    gaps = (
        *string_sequence(report.get("required_gaps")),
        *prove_domain.workspace_status_validation_gaps(validation),
    )
    report.update(
        verdict=reduce_verdicts(report_verdict(validation), required_gaps=gaps),
        required_gaps=gaps,
    )
    stage_gates = cast("dict[str, object]", report.get("stage_gates") or {})
    action = closeout_command_from_status(root, report) or str(stage_gates.get("next_action") or "")
    summary = {
        "branch": report["branch"],
        "role": report["role"],
        "coordination_detail_state": "exact",
        "foreign_work_lane_count": len(foreign),
        "unbound_work_lane_count": len(unbound),
        "missing_lease_count": sum(lane.get("lease_state") == "missing" for lane in foreign),
        "dirty_foreign_work_lane_count": sum(lane.get("dirty") is True for lane in foreign),
        "coordination_advisory_count": len(string_sequence(report.get("coordination_gaps"))),
        "coordination_blocking": any(gap.startswith("coordination_gap:") for gap in gaps),
        "coordination_next_action": action,
    }
    decision = bool(stage_gates.get("user_decision_required", False))
    return lane_result(
        "lane status",
        report | {"next_action": action, "user_decision_required": decision},
        summary=summary,
        diagnostics=(validation,),
        data=report,
        passed="ready",
    )


def keep_lane_house(root: Path, request: HousekeepingRequest) -> EthosResult:
    """Remove only clean detached worktrees below controlled temporary roots."""
    report = housekeeping_worktrees(root=root, authorized=request.authorize, apply=request.apply)
    summary = cast("dict[str, object]", report["summary"])
    return lane_result("lane housekeeping", report, summary=summary)


def bootstrap_lane_candidate(root: Path, request: CandidateRequest) -> EthosResult:
    """Bootstrap the local candidate worktree, or report the one a bootstrap would create."""
    report = bootstrap_candidate(
        root=root, path=_path(request.path), expect_head=request.expect_head, apply=request.apply
    )
    return lane_result("lane candidate", report, fields=_CANDIDATE)


def refresh_lane_candidate(root: Path, request: CandidateRequest) -> EthosResult:
    """Refresh the candidate from the accepted head; dropping its own commits needs confirming."""
    fields = request.model_dump(include={"apply", "expect_head", "confirm_irreversible"})
    report = refresh_candidate_from_accepted(root=root, authorized=request.authorize, **fields)
    return lane_result("lane candidate", report, fields=_CANDIDATE)


def materialize_lane_candidate(root: Path, request: CandidateRequest) -> EthosResult:
    """Freshly admit one retained candidate projection, and materialize it by exact state."""
    fields = request.model_dump(include=_MATERIALIZED | {"apply", "expect_head"})
    report = materialize_candidate(root=root, authorized=request.authorize, **fields)
    return lane_result("lane candidate", report, fields=_CANDIDATE)


def start_lane(root: Path, request: StartRequest) -> EthosResult:
    """Start an owned Work Lane and acquire a local lease."""
    fields = request.model_dump(exclude={"path"})
    report = start_work_lane(root=root, path=_path(request.path), **fields)
    return lane_result("lane start", report, fields=("branch", "path"))


def refresh_lane_base(root: Path, request: RefreshBaseRequest) -> EthosResult:
    """Refresh the current Work Lane onto the configured candidate branch, or merge into it."""
    fields = request.model_dump(exclude={"authorize"})
    report = refresh_work_lane_base(root=root, authorized=request.authorize, **fields)
    names = ("branch", "candidate_branch", "head", "candidate_head")
    return lane_result("lane refresh-base", report, fields=names)


def archive_lane_change(root: Path, request: ArchiveChangeRequest) -> EthosResult:
    """Archive one completed Change, or with `--compensate` return its unlanded archive."""
    report = archive_change(root=root, **request.model_dump())
    diagnostics = object_sequence(report.get("diagnostics"))
    return lane_result(
        "lane archive-change",
        report,
        fields=("branch", "change", "head", "archive_path"),
        diagnostics=tuple(item for item in diagnostics if isinstance(item, dict)),
    )

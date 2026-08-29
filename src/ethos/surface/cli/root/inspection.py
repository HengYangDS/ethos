"""Cyclopts declarations for the bounded repository reader."""

from __future__ import annotations

from typing import cast

from ethos.adapters.openspec.start_effect import CurrentGenerationScope
from ethos.adapters.openspec.start_effect import current_generation_binding
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import closeout_command_from_status
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import repository_context
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


def _count(value: object) -> int:
    return len(value) if isinstance(value, list | tuple) else 0


@app.command
def status(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Inspect bounded truth, authority, gaps, coordination, and next action."""
    repo = resolve_root(root)
    observed, authority = workspace_status_observation(repo, include_foreign_path_scope=False)
    try:
        generation_scope = (
            current_generation_binding(
                repo,
                status=observed,
                repository_id=repository_identity(repo),
                authority=authority,
            ).scope
            if observed.get("role") == ROLE_WORK_LANE
            else CurrentGenerationScope((), {})
        )
    except ValueError:
        generation_scope = CurrentGenerationScope(
            (), {}, gaps=("change_generation_binding_invalid",)
        )
    validation = workspace_status_validation(repo, observed)
    landing = cast("dict[str, object]", observed.get("landing_readiness") or {})
    generation_gaps = (
        ()
        if "candidate_base_stale" in string_sequence(landing.get("required_gaps"))
        else generation_scope.gaps
    )
    gaps = tuple(
        dict.fromkeys(
            (
                *string_sequence(observed.get("required_gaps")),
                *workspace_status_validation_gaps(validation),
                *generation_gaps,
                *(
                    ("change_scope_exceeded",)
                    if any(item.state == "uncovered" for item in generation_scope.attributions)
                    else ()
                ),
            )
        )
    )
    foreign = cast("list[dict[str, object]]", observed.get("foreign_work_lanes") or [])
    unbound = cast("list[dict[str, object]]", observed.get("unbound_work_lane_refs") or [])
    coordination_gaps = string_sequence(observed.get("coordination_gaps"))
    authority_projection = authority.projection() if authority is not None else {}
    data = {
        "root": observed.get("root", ""),
        "branch": observed.get("branch", ""),
        "head": observed.get("head", ""),
        "role": observed.get("role", ""),
        "dirty": bool(observed.get("dirty")),
        "changed_path_count": _count(observed.get("changed_paths")),
        "selected_carrier": generation_scope.selected_carrier,
        "path_attributions": list(generation_scope.attribution_projection()),
        "authority": authority_projection,
        "landing_readiness": {
            "state": landing.get("state", ""),
            "required_gaps": string_sequence(landing.get("required_gaps")),
            "next_action": landing.get("next_action", ""),
        },
        "hook_runtime": hook_runtime_binding(repo),
        "coordination": {
            "detail_state": "deferred",
            "blocking": any(gap.startswith("coordination_gap:") for gap in gaps),
            "foreign_work_lane_count": len(foreign),
            "unbound_work_lane_count": len(unbound),
            "missing_lease_count": sum(lane.get("lease_state") == "missing" for lane in foreign),
            "advisory_count": len(coordination_gaps),
            "required_count": sum(gap.startswith("coordination_gap:") for gap in gaps),
        },
    }
    compact_coordination = data["coordination"]
    verdict = reduce_verdicts(report_verdict(validation), required_gaps=gaps)
    closeout_action = closeout_command_from_status(repo, observed)
    result = EthosResult(
        command="status",
        verdict=verdict,
        state=(
            "blocked"
            if verdict == "block"
            else "unknown"
            if verdict == "unknown"
            else "dirty"
            if data["dirty"]
            else "ready"
        ),
        summary={
            key: data[key] for key in ("root", "branch", "role", "dirty", "changed_path_count")
        }
        | {
            "foreign_work_lane_count": compact_coordination["foreign_work_lane_count"],
            "unbound_work_lane_count": compact_coordination["unbound_work_lane_count"],
            "missing_lease_count": compact_coordination["missing_lease_count"],
            "coordination_detail_state": compact_coordination["detail_state"],
            "coordination_advisory_count": compact_coordination["advisory_count"],
            "coordination_blocking": compact_coordination["blocking"],
        },
        diagnostics=(validation,),
        required_gaps=gaps,
        next_action=closeout_action
        or (
            "repair the selected Commitment scope for the uncovered current-generation paths"
            if any(item.state == "uncovered" for item in generation_scope.attributions)
            else str(
                cast("dict[str, object]", observed.get("stage_gates") or {}).get("next_action")
                or ""
            )
        ),
        governance_context=repository_context(repo),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)

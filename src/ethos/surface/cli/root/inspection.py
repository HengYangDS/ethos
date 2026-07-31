"""Cyclopts declarations for the bounded repository reader."""

from __future__ import annotations

from typing import cast

from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.normalization.coercion import integer
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
    observed = workspace_status(repo, include_foreign_path_scope=False)
    validation = workspace_status_validation(repo, observed)
    gaps = tuple(
        dict.fromkeys(
            (
                *string_sequence(observed.get("required_gaps")),
                *workspace_status_validation_gaps(validation),
            )
        )
    )
    coordination = cast("dict[str, object]", observed.get("coordination") or {})
    landing = cast("dict[str, object]", observed.get("landing_readiness") or {})
    data = {
        "root": observed.get("root", ""),
        "branch": observed.get("branch", ""),
        "head": observed.get("head", ""),
        "role": observed.get("role", ""),
        "dirty": bool(observed.get("dirty")),
        "changed_path_count": _count(observed.get("changed_paths")),
        "authority": cast("dict[str, object]", observed.get("stage_gates") or {}),
        "landing_readiness": {
            "state": landing.get("state", ""),
            "required_gaps": string_sequence(landing.get("required_gaps")),
            "next_action": landing.get("next_action", ""),
        },
        "coordination": {
            "detail_state": coordination.get("detail_state", "exact"),
            "blocking": bool(coordination.get("blocking")),
            "foreign_work_lane_count": integer(coordination.get("foreign_work_lane_count")),
            "unbound_work_lane_count": integer(coordination.get("unbound_work_lane_count")),
            "missing_lease_count": integer(coordination.get("missing_lease_count")),
            "advisory_count": _count(coordination.get("advisory_gaps")),
            "required_count": _count(coordination.get("required_gaps")),
        },
    }
    compact_coordination = data["coordination"]
    verdict = reduce_verdicts(report_verdict(validation), required_gaps=gaps)
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
        next_actions=tuple(
            string_sequence(
                cast("dict[str, object]", observed.get("stage_gates") or {}).get("next_commands")
            )
        ),
        governance_context=repository_context(repo),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)

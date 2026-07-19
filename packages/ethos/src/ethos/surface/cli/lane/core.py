"""Lane command group — Work Lane lifecycle and bounded retirement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.domain.prove as prove_domain
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.refresh import bootstrap_candidate
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_candidate_from_accepted
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_work_lane_base
from ethos.adapters.mutation.lane_retirement.core import SupersededLaneRetirementRequest
from ethos.adapters.mutation.lane_retirement.core import retire_superseded_work_lane
from ethos.adapters.mutation.lane_retirement.landed.core import retire_landed_work_lanes
from ethos.adapters.mutation.lane_retirement.unbound.core import retire_unbound_work_lane_ref
from ethos.adapters.mutation.lanes import bind_work_lane_claim
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.mutation.worktree.core import housekeeping_worktrees
from ethos.adapters.repo.status.core import workspace_status
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_app
from ethos.surface.cli._base import lane_retire_app
from ethos.surface.cli._base import resolve_root
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


@dataclass(frozen=True, slots=True)
class _RetireSupersededOptions:
    """CLI options for `ethos lane retire superseded`."""

    branch: Annotated[str, Parameter(name="--branch")]
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    absorbed_by: Annotated[str, Parameter(name="--absorbed-by")] = ""
    reason: Annotated[str, Parameter(name="--reason")] = ""
    authorize: bool = False
    apply: bool = False


_DEFAULT_RETIRE_SUPERSEDED_OPTIONS = _RetireSupersededOptions(branch="")


@lane_app.command(name="status")
def lane_status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect Work Lane topology and foreign lanes."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    validation = prove_domain.workspace_status_validation(repo, status_payload)
    validation_gaps = prove_domain.workspace_status_validation_gaps(validation)
    ok = bool(validation["ok"])
    result = EthosResult(
        command="lane status",
        ok=ok,
        state="ready" if ok else "invalid",
        summary=_lane_status_summary(status_payload),
        diagnostics=(validation,),
        required_gaps=tuple(string_sequence(status_payload.get("required_gaps"))) + validation_gaps,
        next_actions=_lane_status_next_actions(status_payload),
        data=status_payload,
    )
    emit(result, json_output=json_output, enforce=False)


@lane_app.command
def housekeeping(
    *,
    authorize: bool = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Remove only clean detached worktrees below controlled temporary roots."""
    repo = resolve_root(root)
    report = housekeeping_worktrees(root=repo, authorized=authorize, apply=apply)
    result = EthosResult(
        command="lane housekeeping",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=cast("dict[str, object]", report["summary"]),
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos lane housekeeping --authorize --apply --json",)
        if not apply and cast("dict[str, object]", report["summary"])["removable_count"]
        else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=apply)


def _lane_status_summary(status_payload: dict[str, object]) -> dict[str, object]:
    coordination = cast("dict[str, object]", status_payload.get("coordination", {}))
    foreign_lanes = cast("list[dict[str, object]]", status_payload.get("foreign_work_lanes", []))
    advisory_items = _object_list(coordination.get("advisory_gaps", []))
    return {
        "branch": status_payload["branch"],
        "role": status_payload["role"],
        "coordination_detail_state": str(coordination.get("detail_state") or "exact"),
        "foreign_work_lane_count": _int_value(
            coordination.get("foreign_work_lane_count"),
            default=len(foreign_lanes),
        ),
        "unbound_work_lane_count": _int_value(coordination.get("unbound_work_lane_count")),
        "missing_lease_count": _int_value(coordination.get("missing_lease_count")),
        "closeout_residue_count": _int_value(coordination.get("closeout_residue_count")),
        "dirty_closeout_residue_count": _int_value(
            coordination.get("dirty_closeout_residue_count")
        ),
        "dirty_foreign_work_lane_count": _int_value(
            coordination.get("dirty_foreign_work_lane_count"),
            default=sum(1 for lane in foreign_lanes if lane.get("dirty") is True),
        ),
        "coordination_advisory_count": len(advisory_items),
        "coordination_blocking": bool(coordination.get("blocking")),
        "coordination_next_action": str(coordination.get("next_action") or ""),
    }


def _object_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list | tuple) else []


def _int_value(value: object, *, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _lane_status_next_actions(status_payload: dict[str, object]) -> tuple[str, ...]:
    role = str(status_payload.get("role") or "")
    if role == "work_lane":
        gates = cast("dict[str, object]", status_payload.get("stage_gates", {}))
        commands = cast("list[object]", gates.get("next_commands", []))
        return tuple(str(command) for command in commands) or ("ethos lane prewrite <path>",)
    raw_gaps = status_payload.get("required_gaps", ())
    gap_items = raw_gaps if isinstance(raw_gaps, list | tuple) else ()
    if gap_items:
        return ("ethos orient --json",)
    coordination = cast("dict[str, object]", status_payload.get("coordination", {}))
    if coordination.get("advisory_gaps"):
        return ("ethos orient --json", "ethos lane status --json")
    return ("ethos lane start <name> --path <path> --holder-ref <holder-ref> --apply --json",)


@lane_app.command
def candidate(
    *,
    apply: bool = False,
    path: Annotated[Path | None, Parameter(name="--path")] = None,
    expect_head: str | None = None,
    refresh_from_accepted: Annotated[bool, Parameter(name="--refresh-from-accepted")] = False,
    authorize: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Bootstrap, inspect, or refresh the local candidate train."""
    repo = resolve_root(root)
    if refresh_from_accepted:
        report = refresh_candidate_from_accepted(
            root=repo,
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        )
    else:
        report = bootstrap_candidate(root=repo, path=path, expect_head=expect_head, apply=apply)
    required_gaps = tuple(cast("tuple[str, ...] | list[str]", report["required_gaps"]))
    result = EthosResult(
        command="lane candidate",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "head": report["head"],
            "path": report["path"],
        },
        required_gaps=required_gaps,
        next_actions=("ethos lane start <name>",) if report["ok"] else ("ethos status",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=apply)


@lane_app.command
def prewrite(
    paths: Annotated[tuple[Path, ...], Parameter(consume_multiple=True)],
    *,
    editor_root: Annotated[Path | None, Parameter(name="--editor-root")] = None,
    require_editor_root: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check tracked write admission before editing files."""
    repo = resolve_root(root)
    report = prewrite_guard(
        root=repo,
        paths=[
            path
            if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
            else repo / path
            for path in paths
        ],
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )
    result = EthosResult(
        command="lane prewrite",
        ok=bool(report["ok"]),
        state="admitted" if report["ok"] else "blocked",
        summary={
            "path_count": len(paths),
            "role": report["role"],
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos lane start <name>",) if not report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=True)


@lane_app.command
def start(
    name: str,
    *,
    path: Annotated[Path | None, Parameter(name="--path")] = None,
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    claim_id: Annotated[str | None, Parameter(name="--claim-id")] = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Start an owned Work Lane and acquire a local lease."""
    repo = resolve_root(root)
    report = start_work_lane(
        root=repo,
        name=name,
        path=path,
        holder_ref=holder_ref,
        claim_id=claim_id,
        apply=apply,
    )
    result = EthosResult(
        command="lane start",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "path": report.get("path", ""),
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=_start_next_actions(report),
        data=report,
    )
    emit(result, json_output=json_output)


def _start_next_actions(report: dict[str, object]) -> tuple[str, ...]:
    if not report["ok"]:
        return ()
    bootstrap = cast("dict[str, object]", report.get("runner_bootstrap", {}))
    runner_action = str(bootstrap.get("next_action") or "")
    actions = ["ethos lane prewrite <path>"]
    if runner_action:
        actions.insert(0, runner_action)
    return tuple(actions)


@lane_app.command(name="refresh-base")
def lane_refresh_base(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Replay the current Work Lane onto the configured candidate branch."""
    repo = resolve_root(root)
    report = refresh_work_lane_base(
        root=repo,
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
    )
    result = EthosResult(
        command="lane refresh-base",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "candidate_branch": report["candidate_branch"],
            "head": report["head"],
            "candidate_head": report["candidate_head"],
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=_refresh_base_next_actions(report),
        data=report,
    )
    emit(result, json_output=json_output)


def _refresh_base_next_actions(report: dict[str, object]) -> tuple[str, ...]:
    actions = report.get("next_actions")
    if isinstance(actions, list | tuple):
        return tuple(str(action) for action in actions)
    return ("ethos land --json",) if report["ok"] else ("ethos status --json",)


@lane_app.command(name="bind-claim")
def lane_bind_claim(
    *,
    claim_id: Annotated[str, Parameter(name="--claim-id")],
    branch: Annotated[str | None, Parameter(name="--branch")] = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Bind an existing Work Lane lease to a trust-bearing claim."""
    repo = resolve_root(root)
    report = bind_work_lane_claim(
        root=repo,
        branch=branch,
        claim_id=claim_id,
        apply=apply,
    )
    result = EthosResult(
        command="lane bind-claim",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "claim_id": report["claim_id"],
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos lane status",) if report["ok"] else ("ethos lane start <name>",),
        data=report,
    )
    emit(result, json_output=json_output)


@lane_retire_app.command(name="unbound")
def lane_retire_unbound(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None,
    reason: Annotated[str, Parameter(name="--reason")] = "",
    chronicle_ref: Annotated[str, Parameter(name="--chronicle-ref")] = "",
    authorize: bool = False,
    break_glass: Annotated[bool, Parameter(name="--break-glass")] = False,
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Exceptionally retire one accepted-policy-bound unbound Work Lane ref."""
    repo = resolve_root(root)
    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=expect_head,
        reason=reason,
        chronicle_ref=chronicle_ref,
        apply=apply,
        authorized=authorize,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
    )
    result = EthosResult(
        command="lane retire unbound",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "head": report["head"],
            "relation_to_accepted": report["relation_to_accepted"],
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos status",) if report["ok"] else ("ethos lane status",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=apply)


@lane_retire_app.command(name="superseded")
def lane_retire_superseded(
    options: Annotated[
        _RetireSupersededOptions,
        Parameter(name="*"),
    ] = _DEFAULT_RETIRE_SUPERSEDED_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Retire a clean linked Work Lane already absorbed by accepted truth."""
    repo = resolve_root(root)
    report = retire_superseded_work_lane(
        root=repo,
        request=SupersededLaneRetirementRequest(
            branch=options.branch,
            expect_head=options.expect_head,
            absorbed_by=options.absorbed_by,
            reason=options.reason,
            apply=options.apply,
            authorized=options.authorize,
        ),
    )
    result = EthosResult(
        command="lane retire superseded",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "head": report["head"],
            "absorbed_by": report["absorbed_by"],
            "retire_ready": report["retire_ready"],
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos status",) if report["ok"] else ("ethos lane status",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=options.apply)


@lane_retire_app.command(name="landed")
def lane_retire_landed(
    *,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Retire a landed Work Lane after it is merged into the accepted root."""
    repo = resolve_root(root)
    report = retire_landed_work_lanes(
        root=repo,
        branch=branch,
        expect_head=expect_head,
        apply=apply,
    )
    summary = _retire_landed_summary(report, branch=branch)
    result = EthosResult(
        command="lane retire landed",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=summary,
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos status",) if report["ok"] else ("ethos lane status",),
        data=report,
    )
    emit(result, json_output=json_output)


def _retire_landed_summary(report: dict[str, object], *, branch: str | None) -> dict[str, object]:
    lanes = cast("list[dict[str, object]]", report["lanes"])
    selected_lane = next((lane for lane in lanes if lane["branch"] == branch), {})
    retired = report.get("retired")
    retired_lane = retired if isinstance(retired, dict) else {}
    if not selected_lane and retired_lane.get("branch") == branch:
        selected_lane = cast("dict[str, object]", retired_lane)
    selected_blockers = tuple(
        cast("tuple[str, ...] | list[str]", selected_lane.get("required_gaps", ()))
    )
    landed_lane_count = sum(1 for lane in lanes if lane["retire_ready"])
    retired_branch = retired_lane.get("branch")
    retired_missing_from_lanes = bool(retired_branch) and all(
        lane.get("branch") != retired_branch for lane in lanes
    )
    if retired_missing_from_lanes and retired_lane.get("retire_ready"):
        landed_lane_count += 1
    return {
        "landed_lane_count": landed_lane_count,
        "selected_branch": branch or "",
        "selected_retire_ready": bool(selected_lane.get("retire_ready")),
        "selected_blockers": selected_blockers,
    }

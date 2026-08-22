"""Cyclopts declarations for hidden Work Lane lifecycle operations."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from typing import ClassVar
from typing import cast

from cyclopts import App
from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.domain.prove as prove_domain
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.lane_lifecycle.candidate_projection import bootstrap_candidate
from ethos.adapters.mutation.lane_lifecycle.candidate_projection import (
    refresh_candidate_from_accepted,
)
from ethos.adapters.mutation.lane_lifecycle.work_lane_refresh import refresh_work_lane_base
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.mutation.worktree.detached_cleanup import housekeeping_worktrees
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import app as root_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

lane_app = App(name="lane", help="Work Lane lifecycle and write admission.", show=False)
root_app.command(lane_app)


class LaneCommandOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    command: ClassVar[str]

    root: RootOption | None = None
    json_output: JsonFlag = False


class AppliedLaneCommandOptions(LaneCommandOptions):
    apply: bool = False


class _Housekeeping(AppliedLaneCommandOptions):
    command = "lane housekeeping"
    authorize: bool = False


class _RefreshBase(AppliedLaneCommandOptions):
    command = "lane refresh-base"
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None


class _Start(AppliedLaneCommandOptions):
    command = "lane start"
    source_root: Annotated[str | None, Parameter(name="--source-root")] = None
    commitment: Annotated[str | None, Parameter(name="--commitment")] = None
    path: Annotated[str | None, Parameter(name="--path")] = None
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]


class _ArchiveChange(AppliedLaneCommandOptions):
    command = "lane archive-change"
    change: Annotated[str, Parameter(name="--change")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]


_DEFAULT_HOUSEKEEPING = _Housekeeping()
_DEFAULT_REFRESH_BASE = _RefreshBase()


Summary = Callable[[dict[str, object]], dict[str, object]]
Action = Callable[[dict[str, object], Verdict], str]


def _fields(*names: str) -> Summary:
    return lambda report: {name: report.get(name, "") for name in names}


def _actions(success: str, blocked: str = "") -> Action:
    return lambda _report, verdict: success if verdict == "pass" else blocked


def _status_action(report: dict[str, object], verdict: Verdict) -> str:
    gates = cast("dict[str, object]", report.get("stage_gates") or {})
    action = str(gates.get("next_action") or "")
    if verdict != "pass":
        return action or (
            "ethos lane prewrite <path>"
            if report.get("role") == "work_lane"
            else "ethos status --json"
        )
    return action or (
        "ethos lane prewrite <path>"
        if report.get("role") == "work_lane"
        else (
            "ethos lane start <name> --commitment <commitment.toml> "
            "--holder-ref <holder-ref> --apply --json"
        )
    )


def _start_action(report: dict[str, object], verdict: Verdict) -> str:
    if verdict != "pass":
        return ""
    bootstrap = cast("dict[str, object]", report.get("runner_bootstrap") or {})
    return str(bootstrap.get("next_action") or "ethos lane prewrite <path>")


def _refresh_action(report: dict[str, object], verdict: Verdict) -> str:
    action = str(report.get("next_action") or "")
    if verdict == "pass":
        return action or "ethos land --json"
    return action or "ethos status --json"


def _report_action(report: dict[str, object], _verdict: Verdict) -> str:
    return str(report.get("next_action") or "")


def _prewrite_action(report: dict[str, object], verdict: Verdict) -> str:
    return "" if verdict == "pass" else str(report.get("next_action") or "")


def _retirement_action(_report: dict[str, object], verdict: Verdict) -> str:
    return "ethos status" if verdict == "pass" else "ethos lane status"


def _public_state(command: str, report: dict[str, object], verdict: Verdict) -> str:
    if command == "lane status":
        return "ready" if verdict == "pass" else "blocked" if verdict == "block" else "unknown"
    if command == "lane prewrite":
        return "admitted" if verdict == "pass" else "blocked" if verdict == "block" else "unknown"
    if verdict == "block":
        return "blocked"
    if verdict == "unknown":
        return "unknown"
    return str(report.get("state") or "ready")


_SUMMARIES: dict[str, Summary] = {
    "lane housekeeping": lambda report: cast("dict[str, object]", report["summary"]),
    "lane candidate": _fields("branch", "head", "path"),
    "lane prewrite": lambda report: {
        "path_count": integer(report.get("path_count")),
        "role": report.get("role", ""),
    },
    "lane start": _fields("branch", "path"),
    "lane refresh-base": _fields("branch", "candidate_branch", "head", "candidate_head"),
    "lane archive-change": _fields("branch", "change", "head", "archive_path"),
}
_ACTIONS: dict[str, Action] = {
    "lane status": _status_action,
    "lane candidate": _actions(
        "ethos lane start <name> --commitment <commitment.toml> "
        "--holder-ref <holder-ref> --apply --json",
        "ethos status",
    ),
    "lane prewrite": _prewrite_action,
    "lane start": _start_action,
    "lane refresh-base": _refresh_action,
    "lane rebind-commitment": _report_action,
    "lane rebind-commitment derive": _report_action,
    "lane retire superseded": _retirement_action,
    "lane retire landed": _retirement_action,
}


def project_lane_result(
    command: str,
    report: dict[str, object],
    *,
    summary: dict[str, object] | None = None,
    diagnostics: tuple[dict[str, object], ...] = (),
    actions: str | Action | None = None,
    enforce: bool = False,
    json_output: bool,
) -> None:
    verdict = report_verdict(report)
    if actions is None:
        next_action = _ACTIONS.get(command, _actions(""))(report, verdict)
    elif isinstance(actions, str):
        next_action = actions
    else:
        next_action = actions(report, verdict)
    required_gaps = tuple(string_sequence(report.get("required_gaps")))
    result = EthosResult(
        command=command,
        verdict=verdict,
        state=_public_state(command, report, verdict),
        summary=summary or _SUMMARIES.get(command, lambda _report: {})(report),
        diagnostics=diagnostics,
        required_gaps=required_gaps,
        next_action=next_action,
        data=report,
    )
    emit(result, json_output=json_output, enforce=enforce)


@lane_app.command(name="status")
def lane_status(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Inspect Work Lane topology and foreign lanes."""
    repo = resolve_root(root)
    report = workspace_status(repo)
    foreign = cast("list[dict[str, object]]", report.get("foreign_work_lanes") or [])
    unbound = cast("list[dict[str, object]]", report.get("unbound_work_lane_refs") or [])
    coordination_gaps = string_sequence(report.get("coordination_gaps"))
    validation = prove_domain.workspace_status_validation(repo, report)
    gaps = (
        *string_sequence(report.get("required_gaps")),
        *prove_domain.workspace_status_validation_gaps(validation),
    )
    report.update(
        verdict=reduce_verdicts(report_verdict(report), report_verdict(validation)),
        required_gaps=gaps,
    )
    stage_gates = cast("dict[str, object]", report.get("stage_gates") or {})
    summary = {
        "branch": report["branch"],
        "role": report["role"],
        "coordination_detail_state": "exact",
        "foreign_work_lane_count": len(foreign),
        "unbound_work_lane_count": len(unbound),
        "missing_lease_count": sum(lane.get("lease_state") == "missing" for lane in foreign),
        "dirty_foreign_work_lane_count": sum(lane.get("dirty") is True for lane in foreign),
        "coordination_advisory_count": len(coordination_gaps),
        "coordination_blocking": any(gap.startswith("coordination_gap:") for gap in gaps),
        "coordination_next_action": str(stage_gates.get("next_action") or ""),
    }
    project_lane_result(
        "lane status",
        report,
        summary=summary,
        diagnostics=(validation,),
        json_output=json_output,
    )


@lane_app.command
def housekeeping(
    options: Annotated[_Housekeeping, Parameter(name="*")] = _DEFAULT_HOUSEKEEPING,
) -> None:
    """Remove only clean detached worktrees below controlled temporary roots."""
    report = housekeeping_worktrees(
        root=resolve_root(options.root), authorized=options.authorize, apply=options.apply
    )
    removable = integer(cast("dict[str, object]", report["summary"]).get("removable_count"))
    project_lane_result(
        options.command,
        report,
        actions=lambda _report, verdict: (
            "ethos lane housekeeping --authorize --apply --json"
            if verdict == "pass" and removable and not options.apply
            else ""
        ),
        enforce=options.apply,
        json_output=options.json_output,
    )


@lane_app.command
def candidate(
    *,
    apply: bool = False,
    path: Annotated[str | None, Parameter(name="--path")] = None,
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None,
    refresh_from_accepted: Annotated[bool, Parameter(name="--refresh-from-accepted")] = False,
    authorize: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Bootstrap, inspect, or refresh the local candidate train."""
    repo = resolve_root(root)
    report = (
        refresh_candidate_from_accepted(
            root=repo,
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        )
        if refresh_from_accepted
        else bootstrap_candidate(
            root=repo,
            path=Path(path) if path is not None else None,
            expect_head=expect_head,
            apply=apply,
        )
    )
    project_lane_result("lane candidate", report, enforce=apply, json_output=json_output)


@lane_app.command
def prewrite(
    paths: Annotated[tuple[str, ...], Parameter(consume_multiple=True)],
    *,
    editor_root: Annotated[str | None, Parameter(name="--editor-root")] = None,
    require_editor_root: Annotated[bool, Parameter(name="--require-editor-root")] = False,
    patch_path: Annotated[str | None, Parameter(name="--patch")] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check tracked write admission before editing files."""
    repo = resolve_root(root)
    typed_paths = tuple(Path(path) for path in paths)
    resolved_paths = [
        path
        if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
        else repo / path
        for path in typed_paths
    ]
    report = prewrite_guard(
        root=repo,
        paths=resolved_paths,
        editor_root=Path(editor_root) if editor_root is not None else None,
        require_editor_root=require_editor_root,
        patch=(
            sys.stdin.read()
            if patch_path == "-"
            else Path(patch_path).read_text(encoding="utf-8")
            if patch_path is not None
            else ""
        ),
    )
    report = {
        **report,
        "path_count": len(resolved_paths),
    }
    project_lane_result("lane prewrite", report, enforce=True, json_output=json_output)


@lane_app.command
def start(
    name: str,
    options: Annotated[_Start, Parameter(name="*")],
) -> None:
    """Start an owned Work Lane and acquire a local lease."""
    report = start_work_lane(
        root=resolve_root(options.root),
        name=name,
        source_root=Path(options.source_root) if options.source_root is not None else None,
        commitment_path=Path(options.commitment) if options.commitment is not None else None,
        path=Path(options.path) if options.path is not None else None,
        holder_ref=options.holder_ref,
        apply=options.apply,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )


@lane_app.command(name="refresh-base")
def lane_refresh_base(
    options: Annotated[_RefreshBase, Parameter(name="*")] = _DEFAULT_REFRESH_BASE,
) -> None:
    """Refresh the current Work Lane onto the configured candidate branch."""
    report = refresh_work_lane_base(
        root=resolve_root(options.root),
        apply=options.apply,
        authorized=options.authorize,
        expect_head=options.expect_head,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )


@lane_app.command(name="archive-change")
def lane_archive_change(
    options: Annotated[_ArchiveChange, Parameter(name="*")],
) -> None:
    """Archive one completed Change through the official governed transition."""
    report = archive_change(
        root=resolve_root(options.root),
        change=options.change,
        expect_head=options.expect_head,
        apply=options.apply,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )

"""Cyclopts declarations for hidden Work Lane lifecycle operations."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from typing import ClassVar
from typing import cast

from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.domain.prove as prove_domain
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lane_lifecycle.refresh import bootstrap_candidate
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_candidate_from_accepted
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_work_lane_base
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.mutation.worktree.detached_cleanup import housekeeping_worktrees
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import lane_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


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


_DEFAULT_HOUSEKEEPING = _Housekeeping()
_DEFAULT_REFRESH_BASE = _RefreshBase()


Summary = Callable[[dict[str, object]], dict[str, object]]
Actions = Callable[[dict[str, object]], tuple[str, ...]]


def _fields(*names: str) -> Summary:
    return lambda report: {name: report.get(name, "") for name in names}


def _actions(success: tuple[str, ...], blocked: tuple[str, ...] = ()) -> Actions:
    return lambda report: success if report["ok"] else blocked


_SUMMARIES: dict[str, Summary] = {
    "lane housekeeping": lambda report: cast("dict[str, object]", report["summary"]),
    "lane candidate": _fields("branch", "head", "path"),
    "lane prewrite": lambda report: {
        "path_count": integer(report.get("path_count")),
        "role": report.get("role", ""),
    },
    "lane start": _fields("branch", "path"),
    "lane refresh-base": _fields("branch", "candidate_branch", "head", "candidate_head"),
}
_ACTIONS: dict[str, Actions] = {
    "lane candidate": _actions(("ethos lane start <name>",), ("ethos status",)),
    "lane prewrite": _actions((), ("ethos lane start <name>",)),
}


def project_lane_result(
    command: str,
    report: dict[str, object],
    *,
    summary: dict[str, object] | None = None,
    diagnostics: tuple[dict[str, object], ...] = (),
    actions: tuple[str, ...] | None = None,
    enforce: bool = False,
    json_output: bool,
) -> None:
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=summary or _SUMMARIES.get(command, lambda _report: {})(report),
        diagnostics=diagnostics,
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=(
            actions if actions is not None else _ACTIONS.get(command, lambda _report: ())(report)
        ),
        data=report,
    )
    emit(result, json_output=json_output, enforce=enforce)


@lane_app.command(name="status")
def lane_status(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Inspect Work Lane topology and foreign lanes."""
    repo = resolve_root(root)
    report = workspace_status(repo)
    validation = prove_domain.workspace_status_validation(repo, report)
    gaps = (
        *string_sequence(report.get("required_gaps")),
        *prove_domain.workspace_status_validation_gaps(validation),
    )
    report = {
        **report,
        "ok": bool(validation["ok"]),
        "state": "ready" if validation["ok"] else "invalid",
        "required_gaps": gaps,
    }
    coordination = cast("dict[str, object]", report.get("coordination") or {})
    foreign = cast("list[dict[str, object]]", report.get("foreign_work_lanes") or [])
    summary = {
        "branch": report["branch"],
        "role": report["role"],
        "coordination_detail_state": coordination.get("detail_state", "exact"),
        "foreign_work_lane_count": (
            integer(coordination.get("foreign_work_lane_count")) or len(foreign)
        ),
        "unbound_work_lane_count": integer(coordination.get("unbound_work_lane_count")),
        "missing_lease_count": integer(coordination.get("missing_lease_count")),
        "closeout_residue_count": integer(coordination.get("closeout_residue_count")),
        "dirty_closeout_residue_count": integer(coordination.get("dirty_closeout_residue_count")),
        "dirty_foreign_work_lane_count": integer(coordination.get("dirty_foreign_work_lane_count"))
        or sum(lane.get("dirty") is True for lane in foreign),
        "coordination_advisory_count": len(string_sequence(coordination.get("advisory_gaps"))),
        "coordination_blocking": bool(coordination.get("blocking")),
        "coordination_next_action": str(coordination.get("next_action") or ""),
    }
    gates = cast("dict[str, object]", report.get("stage_gates") or {})
    commands = tuple(str(item) for item in cast("list[object]", gates.get("next_commands") or []))
    actions = commands or (
        ("ethos lane prewrite <path>",)
        if report.get("role") == "work_lane"
        else ("ethos status --json",)
        if gaps
        else ("ethos lane start <name> --path <path> --holder-ref <holder-ref> --apply --json",)
    )
    project_lane_result(
        "lane status",
        report,
        summary=summary,
        diagnostics=(validation,),
        actions=actions,
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
    actions = (
        ("ethos lane housekeeping --authorize --apply --json",)
        if removable and not options.apply
        else ()
    )
    project_lane_result(
        options.command,
        report,
        actions=actions,
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
        "state": "admitted" if report["ok"] else "blocked",
    }
    project_lane_result("lane prewrite", report, enforce=True, json_output=json_output)


@lane_app.command
def start(
    name: str,
    *,
    source_root: Annotated[str | None, Parameter(name="--source-root")] = None,
    path: Annotated[str | None, Parameter(name="--path")] = None,
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Start an owned Work Lane and acquire a local lease."""
    report = start_work_lane(
        root=resolve_root(root),
        name=name,
        source_root=Path(source_root) if source_root is not None else None,
        path=Path(path) if path is not None else None,
        holder_ref=holder_ref,
        apply=apply,
    )
    bootstrap = cast("dict[str, object]", report.get("runner_bootstrap") or {})
    actions = (
        tuple(filter(None, (str(bootstrap.get("next_action") or ""), "ethos lane prewrite <path>")))
        if report["ok"]
        else ()
    )
    project_lane_result("lane start", report, actions=actions, json_output=json_output)


@lane_app.command(name="refresh-base")
def lane_refresh_base(
    options: Annotated[_RefreshBase, Parameter(name="*")] = _DEFAULT_REFRESH_BASE,
) -> None:
    """Replay the current Work Lane onto the configured candidate branch."""
    report = refresh_work_lane_base(
        root=resolve_root(options.root),
        apply=options.apply,
        authorized=options.authorize,
        expect_head=options.expect_head,
    )
    raw = report.get("next_actions")
    actions = (
        tuple(str(item) for item in raw)
        if isinstance(raw, list | tuple)
        else (("ethos land --json",) if report["ok"] else ("ethos status --json",))
    )
    project_lane_result(options.command, report, actions=actions, json_output=options.json_output)

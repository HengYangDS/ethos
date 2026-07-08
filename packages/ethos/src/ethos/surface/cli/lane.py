"""Lane command group — Work Lane lifecycle: status, start, candidate, land,
refresh-base, bind-claim, retire-landed, retire-unbound."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.domain.prove as prove_domain
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lanes import bind_work_lane_claim
from ethos.adapters.mutation.lanes import bootstrap_candidate
from ethos.adapters.mutation.lanes import refresh_candidate_from_accepted
from ethos.adapters.mutation.lanes import refresh_work_lane_base
from ethos.adapters.mutation.lanes import retire_landed_work_lanes
from ethos.adapters.mutation.lanes import retire_unbound_work_lane_ref
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status.core import workspace_status
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


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
        summary={
            "branch": status_payload["branch"],
            "role": status_payload["role"],
            "foreign_work_lane_count": len(status_payload["foreign_work_lanes"]),
        },
        diagnostics=(validation,),
        required_gaps=tuple(status_payload.get("required_gaps", ())) + validation_gaps,
        next_actions=("ethos lane prewrite <path>",),
        data=status_payload,
    )
    emit(result, json_output=json_output, enforce=False)


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
    paths: tuple[Path, ...],
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
        paths=[path if path.is_absolute() else repo / path for path in paths],
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
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane start <name>",) if not report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=True)


@lane_app.command
def start(
    name: str,
    *,
    path: Annotated[Path | None, Parameter(name="--path")] = None,
    owner: str,
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
        owner=owner,
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
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane prewrite <path>",) if report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output)


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
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos land --json",) if report["ok"] else ("ethos status --json",),
        data=report,
    )
    emit(result, json_output=json_output)


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
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane status",) if report["ok"] else ("ethos lane start <name>",),
        data=report,
    )
    emit(result, json_output=json_output)


@lane_app.command(name="retire-unbound")
def lane_retire_unbound(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None,
    reason: Annotated[str, Parameter(name="--reason")] = "",
    authorize: bool = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Retire an unbound local Work Lane ref with head-bound authorization."""
    repo = resolve_root(root)
    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=expect_head,
        reason=reason,
        apply=apply,
        authorized=authorize,
    )
    result = EthosResult(
        command="lane retire-unbound",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "head": report["head"],
            "relation_to_accepted": report["relation_to_accepted"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos status",) if report["ok"] else ("ethos lane status",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=apply)


@lane_app.command(name="retire-landed")
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
        command="lane retire-landed",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=summary,
        required_gaps=tuple(report["required_gaps"]),
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

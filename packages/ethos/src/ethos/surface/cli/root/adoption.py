"""Root adoption commands."""

from __future__ import annotations

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.core import MutationRequest
from ethos.domain.status import adoption_mutation_gaps
from ethos.repository.adoption.planner import adoption_plan
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def _adoption_result(
    request: MutationRequest,
    *,
    root: RootOption | None,
    profile: str | None,
    overlay: bool,
) -> EthosResult:
    target = resolve_root(root)
    current_head = git.current_head(target)
    mutation_gaps = adoption_mutation_gaps(
        apply=request.apply,
        authorize=request.authorized,
        expect_head=request.expect_head,
        current_head=current_head,
    )
    do_apply = request.apply and not mutation_gaps
    plan_payload = adoption_plan(target, profile=profile, overlay=overlay, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(plan_payload.get("required_gaps", ()))
    ok = not required_gaps
    hooks_armed = False
    if do_apply and ok:
        hooks_armed = git.set_hooks_path(target, ".githooks")
    result = EthosResult(
        command=request.command,
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={
            "planned_file_count": len(plan_payload["planned_files"]),
            "hooks_armed": hooks_armed,
        },
        next_actions=("ethos status",),
        required_gaps=required_gaps,
        data=plan_payload,
    )
    result.data["mutation"] = {
        "apply": request.apply,
        "authorized": request.authorized,
        "expect_head": request.expect_head,
        "current_head": current_head,
    }
    return result


@app.command
def init(
    *,
    root: RootOption | None = None,
    dry_run: bool = True,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    profile: str | None = None,
    overlay: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Initialize ETHOS adoption for a repository."""
    _ = dry_run
    result = _adoption_result(
        MutationRequest(
            command="init",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=root,
        profile=profile,
        overlay=overlay,
    )
    emit(result, json_output=json_output, enforce=apply)


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    dry_run: bool = True,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    profile: str | None = None,
    overlay: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    _ = dry_run
    result = _adoption_result(
        MutationRequest(
            command="adopt",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=root,
        profile=profile,
        overlay=overlay,
    )
    emit(result, json_output=json_output, enforce=apply)

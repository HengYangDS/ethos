"""Root adoption commands."""

from __future__ import annotations

import ethos.adapters.repo.git as git
from ethos.contracts.transitions import ADOPT_TRANSITION
from ethos.contracts.transitions import TransitionFacts
from ethos.contracts.transitions import TransitionRequest
from ethos.contracts.transitions import reduce_transition
from ethos.normalization.core import object_sequence
from ethos.normalization.core import string_sequence
from ethos.repository.adoption.planner import adoption_plan
from ethos.result import EthosResult
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root


def _adoption_result(
    request: TransitionRequest,
    *,
    root: RootOption | None,
) -> EthosResult:
    target = resolve_root(root)
    current_head = git.current_head(target)
    mutation = reduce_transition(
        ADOPT_TRANSITION,
        request,
        TransitionFacts(current_head=current_head),
    )
    do_apply = request.apply and mutation.ok
    plan_payload = adoption_plan(target, apply=do_apply)
    required_gaps = mutation.gaps + tuple(string_sequence(plan_payload.get("required_gaps")))
    ok = not required_gaps
    result = EthosResult(
        command=request.command,
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={"planned_file_count": len(object_sequence(plan_payload.get("planned_files")))},
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


def adopt(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    result = _adoption_result(
        TransitionRequest(
            command="adopt",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=root,
    )
    emit(result, json_output=json_output, enforce=apply)

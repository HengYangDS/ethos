"""Root adoption commands."""

from __future__ import annotations

import ethos.adapters.repo.git as git
from ethos.domain.status import adoption_mutation_gaps
from ethos.repository.adoption.planner import adoption_plan
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.normalization.core import object_sequence
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


def _adoption_result(
    request: MutationRequest,
    *,
    root: RootOption | None,
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
    plan_payload = adoption_plan(target, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(string_sequence(plan_payload.get("required_gaps")))
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
        MutationRequest(
            command="adopt",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=root,
    )
    emit(result, json_output=json_output, enforce=apply)

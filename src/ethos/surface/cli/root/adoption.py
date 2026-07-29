"""Root adoption commands."""

from __future__ import annotations

import ethos.adapters.repo.git as git
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.repository.adoption.planner import adoption_plan
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


def _adoption_result(
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    root: RootOption | None,
    repository_id: str | None = None,
    expect_plan_digest: str | None = None,
) -> EthosResult:
    target = resolve_root(root)
    current_head = git.current_head(target)
    gaps = []
    if apply and not authorize:
        gaps.append("authorization_required")
    if apply and expect_head is None:
        gaps.append("expect_head_required")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expected_head_mismatch")
    do_apply = apply and not gaps
    plan_payload = adoption_plan(
        target,
        apply=do_apply,
        repository_id=repository_id,
        expect_plan_digest=expect_plan_digest,
    )
    required_gaps = tuple(gaps) + tuple(string_sequence(plan_payload.get("required_gaps")))
    ok = not required_gaps
    result = EthosResult(
        command="adopt",
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={"planned_file_count": len(object_sequence(plan_payload.get("planned_files")))},
        next_actions=("ethos status",),
        required_gaps=required_gaps,
        data=plan_payload,
    )
    result.data["mutation"] = {
        "apply": apply,
        "authorized": authorize,
        "expect_head": expect_head,
        "current_head": current_head,
    }
    return result


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    repository_id: str | None = None,
    expect_plan_digest: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    result = _adoption_result(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        root=root,
        repository_id=repository_id,
        expect_plan_digest=expect_plan_digest,
    )
    emit(result, json_output=json_output, enforce=apply)

"""Compose adoption requests, exact admission and typed results for every surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.decision import request_gaps
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.repository.adoption.planner import adoption_plan
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


def adopt_repository(
    root: Path,
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    expect_plan_digest: str | None = None,
) -> EthosResult:
    """Plan or apply native adoption with unchanged exact-request admission."""
    target = root.resolve()
    current_head = git.current_head(target)
    gaps = request_gaps(
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )
    do_apply = apply and not gaps
    plan_payload = adoption_plan(
        target,
        apply=do_apply,
        expect_plan_digest=expect_plan_digest,
    )
    required_gaps = tuple(gaps) + tuple(string_sequence(plan_payload.get("required_gaps")))
    ok = not required_gaps
    return EthosResult(
        command="adopt",
        verdict="pass" if ok else "block",
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={"planned_file_count": len(object_sequence(plan_payload.get("planned_files")))},
        next_action="ethos status",
        required_gaps=required_gaps,
        data=plan_payload
        | {
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": current_head,
            }
        },
    )

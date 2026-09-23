"""Compose adoption requests, exact admission and typed results for every surface."""

import shlex
from pathlib import Path

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.decision import request_gaps
from ethos.adapters.repo.adoption import adoption_plan
from ethos.contracts.verdict import report_verdict
from ethos.domain.execution import application_result
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult


@application_result("adopt")
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
    try:
        plan_payload = adoption_plan(
            target,
            apply=do_apply,
            expect_plan_digest=expect_plan_digest,
        )
    except (OSError, ExceptionGroup) as error:
        return EthosResult(
            command="adopt",
            verdict="unknown",
            state="unknown",
            required_gaps=("adoption_effect_observation_required",),
            next_action=shlex.join(("ethos", "adopt", "--root", str(target), "--json")),
            data={"root": str(target), "failure": _failure_evidence(error)},
        )
    required_gaps = tuple(gaps) + tuple(string_sequence(plan_payload.get("required_gaps")))
    ok = not required_gaps
    verdict = "block" if gaps else report_verdict(plan_payload)
    applied = do_apply and ok
    conflicts = tuple(gap for gap in required_gaps if gap.startswith("adoption_conflict:"))
    action = ["ethos", "status" if applied else "adopt", "--root", str(target), "--json"]
    if not apply and ok:
        action.extend(
            [
                "--apply",
                "--authorize",
                "--expect-head",
                current_head,
                "--expect-plan-digest",
                str(plan_payload["plan_digest"]),
            ]
        )
    next_action = shlex.join(action)
    if conflicts:
        next_action = f"Resolve {', '.join(conflicts)} in {target}; then {next_action}"
    return EthosResult(
        command="adopt",
        verdict=verdict,
        state="unknown"
        if verdict == "unknown"
        else "applied"
        if applied
        else "blocked"
        if required_gaps
        else "planned",
        summary={"planned_file_count": len(object_sequence(plan_payload.get("planned_files")))},
        next_action=next_action,
        user_decision_required=bool(conflicts)
        or "authorization_required" in required_gaps
        or (not apply and ok),
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


def _failure_evidence(error: BaseException) -> dict[str, object]:
    evidence: dict[str, object] = {"type": type(error).__name__, "message": str(error)}
    if isinstance(error, BaseExceptionGroup):
        evidence["causes"] = [_failure_evidence(cause) for cause in error.exceptions]
    return evidence

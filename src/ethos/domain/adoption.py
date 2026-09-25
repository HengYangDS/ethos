"""Compose adoption requests, exact admission and typed results for every surface."""

import shlex
from pathlib import Path

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.decision import request_gaps
from ethos.adapters.repo.adoption import adoption_plan
from ethos.adapters.repo.formation import formation_plan
from ethos.contracts.verdict import report_verdict
from ethos.domain.execution import application_result
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult


@application_result("adopt")
def adopt_repository(
    root: Path,
    *,
    create: bool = False,
    purpose: str = "",
    starter: str = "",
    author_name: str = "",
    author_email: str = "",
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    expect_plan_digest: str | None = None,
) -> EthosResult:
    """Plan or apply native adoption with unchanged exact-request admission."""
    if create:
        return _form_repository(
            root,
            purpose=purpose,
            starter=starter,
            author_name=author_name,
            author_email=author_email,
            apply=apply,
            authorize=authorize,
            expect_plan_digest=expect_plan_digest,
            expect_head=expect_head,
        )
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


def _form_repository(
    root: Path,
    *,
    purpose: str,
    starter: str,
    author_name: str,
    author_email: str,
    apply: bool,
    authorize: bool,
    expect_plan_digest: str | None,
    expect_head: str | None,
) -> EthosResult:
    """Keep creation distinct from existing-repository HEAD-bound adoption."""
    plan = formation_plan(
        root,
        purpose=purpose,
        starter=starter,
        author_name=author_name,
        author_email=author_email,
        apply=apply and expect_head is None,
        authorized=authorize,
        expect_plan_digest=expect_plan_digest,
    )
    gaps = list(string_sequence(plan.get("required_gaps")))
    if expect_head is not None:
        gaps.append("formation_expect_head_not_applicable")
    verdict = "block" if expect_head is not None else report_verdict(plan)
    digest = str(plan.get("plan_digest") or "")
    applied = plan.get("applied") is True and verdict == "pass"
    target = Path(str(plan.get("root") or root.absolute()))
    sources = plan.get("source_inputs")
    selected = sources if isinstance(sources, dict) else {}
    selected_name = str(selected.get("author_name") or author_name)
    selected_email = str(selected.get("author_email") or author_email)
    preview = [
        "ethos",
        "adopt",
        "--create",
        "--root",
        str(target),
        "--starter",
        starter,
        "--purpose",
        purpose,
        *(("--author-name", selected_name) if selected_name else ()),
        *(("--author-email", selected_email) if selected_email else ()),
        "--json",
    ]
    mutation = [*preview, "--apply", "--authorize", "--expect-plan-digest", digest]
    if applied or (verdict == "unknown" and (target / ".git").is_dir()):
        next_action = shlex.join(("ethos", "status", "--root", str(target), "--json"))
    elif target.exists():
        next_action = f"Inspect {target} and preserve its bytes before resolving formation"
    elif "formation_git_identity_missing" in gaps:
        next_action = (
            "Supply the actual contributor's --author-name and --author-email; "
            f"then {shlex.join(preview)}"
        )
    elif "formation_starter_unavailable" in gaps:
        next_action = "Choose a supported starter (currently: foundation) before retrying"
    elif "formation_purpose_missing" in gaps:
        next_action = "Supply --purpose for the new project before retrying"
    elif "formation_parent_unsafe" in gaps:
        next_action = "Choose an existing, non-symlink parent directory before retrying"
    elif digest and (verdict == "pass" or "authorization_required" in gaps):
        next_action = shlex.join(mutation)
    else:
        next_action = shlex.join(preview)
    return EthosResult(
        command="adopt",
        verdict=verdict,
        state="applied"
        if applied
        else "planned"
        if verdict == "pass"
        else "unknown"
        if verdict == "unknown"
        else "blocked",
        summary={"planned_file_count": len(object_sequence(plan.get("planned_files")))},
        required_gaps=tuple(gaps),
        next_action=next_action,
        user_decision_required=not applied
        and (
            verdict in {"pass", "unknown"}
            or "authorization_required" in gaps
            or "formation_git_identity_missing" in gaps
            or "formation_target_exists" in gaps
            or "formation_starter_unavailable" in gaps
            or "formation_purpose_missing" in gaps
            or "formation_parent_unsafe" in gaps
        ),
        data=plan
        | {
            "mutation": {
                "create": True,
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "expect_plan_digest": expect_plan_digest,
                "author_name": author_name,
                "author_email": author_email,
            }
        },
    )


def _failure_evidence(error: BaseException) -> dict[str, object]:
    evidence: dict[str, object] = {"type": type(error).__name__, "message": str(error)}
    if isinstance(error, BaseExceptionGroup):
        evidence["causes"] = [_failure_evidence(cause) for cause in error.exceptions]
    return evidence

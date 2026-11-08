"""Compose adoption requests, exact admission and typed results for every surface."""

import shlex
from pathlib import Path

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.decision import request_gaps
from ethos.adapters.repo.adoption import adoption_plan
from ethos.adapters.repo.hook.exit import adopt_exit
from ethos.adapters.repo.starter.evolution import plan_starter_evolution
from ethos.adapters.repo.starter.formation import formation_plan
from ethos.application.catalog import invoke
from ethos.contracts.operations.adopt import AdoptRequest
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

_FORMATION_REPAIR_ACTIONS = {
    "formation_starter_unavailable": "Choose a supported starter (foundation or python-library)",
    "formation_starter_generation_failed": (
        "Repair the installed uv generator or its locked supply before previewing again"
    ),
    "formation_starter_output_unsafe": (
        "Inspect the selected starter output and reject unsafe links or shared files"
    ),
    "formation_starter_output_incomplete": (
        "Repair the selected uv generator before previewing again"
    ),
    "formation_starter_overwrote_foundation": (
        "Reject the selected starter output; it changed foundation-owned files"
    ),
    "formation_purpose_missing": "Supply --purpose for the new project before retrying",
}
_FORMATION_SIGNER_GAPS = frozenset(
    {
        "formation_commit_signer_missing",
        "git_effect_signing_key_invalid",
        "git_effect_signing_program_invalid",
        "commit_trust_anchor_missing",
        "commit_trust_anchor_not_absolute",
        "commit_trust_anchor_inside_repository",
        "commit_trust_anchor_unprotected",
    }
)


def adopt_repository(
    root: Path,
    *,
    create: bool = False,
    evolve_starter: bool = False,
    purpose: str = "",
    starter: str = "",
    author_name: str = "",
    author_email: str = "",
    signing_key: str = "",
    trust_anchor: str = "",
    signing_program: str = "",
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    expect_plan_digest: str | None = None,
    select_runtime: bool = False,
    exit_repository: bool = False,
) -> EthosResult:
    """Plan or apply native adoption with unchanged exact-request admission.

    `exit_repository` previews a repository's exit. With `apply`, `authorize`, `expect_head` and
    the previewed `expect_plan_digest`, it restores the configuration that adoption replaced and
    removes the runtime selectors; a later `ethos hook install` adopts the repository again.
    """
    return invoke("adopt", root, locals())


def adopt_existing(root: Path, request: AdoptRequest) -> EthosResult:
    """Run `adopt.preview`, `adopt.apply` and their runtime selection; only `invoke` calls it."""
    target = root.resolve()
    current_head = git.current_head(target)
    gaps = request_gaps(
        apply=request.apply,
        authorized=request.authorize,
        expect_head=request.expect_head,
        current_head=current_head,
    )
    do_apply = request.apply and not gaps
    try:
        plan_payload = adoption_plan(
            target,
            apply=do_apply,
            expect_plan_digest=request.expect_plan_digest,
            select_runtime=request.select_runtime,
        )
    except (OSError, ExceptionGroup, ValueError) as error:
        return EthosResult(
            command="adopt",
            verdict="unknown",
            state="unknown",
            required_gaps=("adoption_effect_observation_required",),
            next_action=shlex.join(
                ("ethos", "adopt", "--root", str(target), "--json")
                + (("--select-runtime",) if request.select_runtime else ())
            ),
            data={"root": str(target), "failure": _failure_evidence(error)},
        )
    required_gaps = tuple(gaps) + tuple(string_sequence(plan_payload.get("required_gaps")))
    ok = not required_gaps
    verdict = "block" if gaps else report_verdict(plan_payload)
    applied = do_apply and ok
    conflicts = tuple(gap for gap in required_gaps if gap.startswith("adoption_conflict:"))
    action = ["ethos", "status" if applied else "adopt", "--root", str(target), "--json"]
    if request.select_runtime and not applied:
        action.append("--select-runtime")
    if not request.apply and ok:
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
        or (not request.apply and ok),
        required_gaps=required_gaps,
        data=plan_payload
        | {
            "mutation": {
                "apply": request.apply,
                "authorized": request.authorize,
                "expect_head": request.expect_head,
                "current_head": current_head,
            }
        },
    )


def leave_ethos(root: Path, request: AdoptRequest) -> EthosResult:
    """Preview a repository's exit or apply its previewed plan."""
    target = root.resolve()
    head = git.current_head(target)
    gaps = request_gaps(
        apply=request.apply,
        authorized=request.authorize,
        expect_head=request.expect_head,
        current_head=head,
    )
    return adopt_exit(
        target,
        head=head,
        request_gaps=tuple(gaps),
        apply=request.apply,
        expect_plan_digest=request.expect_plan_digest,
    )


def propose_starter_evolution(root: Path, request: AdoptRequest) -> EthosResult:
    """Expose a reviewed starter proposal; its changes apply through an owned Work Lane."""
    target = root.resolve()
    if request.starter not in {"", "python-library"}:
        return EthosResult(
            command="adopt",
            verdict="block",
            state="blocked",
            required_gaps=("starter_evolution_starter_unsupported",),
            next_action="Use preview; apply reviewed changes through an owned Work Lane",
            data={"root": str(target), "changed_paths": [], "patch": ""},
        )
    report = plan_starter_evolution(target, purpose=request.purpose)
    inputs = report.get("source_inputs")
    current = inputs.get("current") if isinstance(inputs, dict) else None
    if request.expect_head is not None and current != request.expect_head:
        report = {
            "verdict": "block",
            "required_gaps": ["starter_evolution_head_changed"],
            "changed_paths": [],
            "patch": "",
        }
    verdict = report_verdict(report)
    gaps = tuple(string_sequence(report.get("required_gaps")))
    changed = tuple(string_sequence(report.get("changed_paths")))
    action = (
        "Review the patch, then obtain exact-path prewrite in an owned Work Lane"
        if verdict == "pass" and changed
        else "No starter changes to apply"
        if verdict == "pass"
        else "Resolve the reported conflict without replacing authored bytes"
        if "starter_evolution_conflict" in gaps
        else "Establish valid formation provenance before proposing an upgrade"
        if "starter_evolution_provenance_missing" in gaps
        else "Inspect required_gaps and reobserve the repository before retrying"
    )
    return EthosResult(
        command="adopt",
        verdict=verdict,
        state="planned" if verdict == "pass" else "unknown" if verdict == "unknown" else "blocked",
        summary={"planned_file_count": len(changed)},
        required_gaps=gaps,
        next_action=action,
        user_decision_required=(verdict == "pass" and bool(changed))
        or "starter_evolution_conflict" in gaps,
        data=report | {"root": str(target)},
    )


def form_repository(root: Path, request: AdoptRequest) -> EthosResult:
    """Keep creation distinct from existing-repository HEAD-bound adoption."""
    plan = formation_plan(
        root,
        purpose=request.purpose,
        starter=request.starter,
        author_name=request.author_name,
        author_email=request.author_email,
        signing_key=request.signing_key,
        trust_anchor=request.trust_anchor,
        signing_program=request.signing_program,
        apply=request.apply,
        authorized=request.authorize,
        expect_plan_digest=request.expect_plan_digest,
    )
    gaps = list(string_sequence(plan.get("required_gaps")))
    verdict = report_verdict(plan)
    digest = str(plan.get("plan_digest") or "")
    applied = plan.get("applied") is True and verdict == "pass"
    target = Path(str(plan.get("root") or root.absolute()))
    sources = plan.get("source_inputs")
    selected = sources if isinstance(sources, dict) else {}
    selected_name = str(selected.get("author_name") or request.author_name)
    selected_email = str(selected.get("author_email") or request.author_email)
    preview = [
        "ethos",
        "adopt",
        "--create",
        "--root",
        str(target),
        "--starter",
        request.starter,
        "--purpose",
        request.purpose,
        *(("--author-name", selected_name) if selected_name else ()),
        *(("--author-email", selected_email) if selected_email else ()),
        *(("--signing-key", request.signing_key) if request.signing_key else ()),
        *(("--trust-anchor", request.trust_anchor) if request.trust_anchor else ()),
        *(("--signing-program", request.signing_program) if request.signing_program else ()),
        "--json",
    ]
    mutation = [*preview, "--apply", "--authorize", "--expect-plan-digest", digest]
    repair = next((action for gap, action in _FORMATION_REPAIR_ACTIONS.items() if gap in gaps), "")
    if applied or (verdict == "unknown" and (target / ".git").is_dir()):
        next_action = shlex.join(("ethos", "status", "--root", str(target), "--json"))
    elif target.exists():
        next_action = f"Inspect {target} and preserve its bytes before resolving formation"
    elif "formation_candidate_path_exists" in gaps:
        candidate_path = str(plan["candidate_worktree_path"])
        next_action = (
            f"Inspect {candidate_path} and preserve its content; "
            "coordinate with its owner before choosing another destination"
        )
    elif "formation_git_identity_missing" in gaps:
        next_action = (
            "Supply the actual contributor's --author-name and --author-email; "
            f"then {shlex.join(preview)}"
        )
    elif _FORMATION_SIGNER_GAPS.intersection(gaps):
        next_action = (
            "Supply the creator's --signing-key (an absolute SSH public key) and "
            "--trust-anchor (an absolute protected allowed-signers file); "
            f"then {shlex.join(preview)}"
        )
    elif repair:
        next_action = repair
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
            or bool(_FORMATION_SIGNER_GAPS.intersection(gaps))
            or "formation_target_exists" in gaps
            or "formation_candidate_path_exists" in gaps
            or "formation_starter_unavailable" in gaps
            or "formation_purpose_missing" in gaps
            or "formation_parent_unsafe" in gaps
        ),
        data=plan
        | {
            "mutation": {
                "create": True,
                "apply": request.apply,
                "authorized": request.authorize,
                "expect_plan_digest": request.expect_plan_digest,
                "author_name": request.author_name,
                "author_email": request.author_email,
                "signing_key": request.signing_key,
                "trust_anchor": request.trust_anchor,
                "signing_program": request.signing_program,
            }
        },
    )


def _failure_evidence(error: BaseException) -> dict[str, object]:
    evidence: dict[str, object] = {"type": type(error).__name__, "message": str(error)}
    if isinstance(error, BaseExceptionGroup):
        evidence["causes"] = [_failure_evidence(cause) for cause in error.exceptions]
    return evidence

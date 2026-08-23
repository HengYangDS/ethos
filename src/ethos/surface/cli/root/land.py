"""Root land command and accepted/candidate integration lifecycle."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

import ethos.adapters.repo.git as git
from ethos.adapters.admission.control.replacement import control_replacement_report
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.landing import apply_candidate_to_accepted
from ethos.adapters.mutation.landing import apply_land_to_candidate
from ethos.adapters.mutation.landing import candidate_transition_readiness
from ethos.adapters.openspec.profile import active_change_names
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import closeout_audit_root
from ethos.domain.land.closeout import closeout_bootstrap_package
from ethos.domain.land.closeout import closeout_receipt_path
from ethos.domain.land.closeout import closeout_resolution
from ethos.domain.land.closeout import land_next_action
from ethos.domain.land.closeout import repository_audit_after_admission
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import repository_context
from ethos.repository.profile import load_repository_profile
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.output import emit_invalid_repository_profile
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@dataclass(frozen=True, slots=True)
class _LandOptions:
    """CLI options for `ethos land`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    candidate_head: Annotated[str | None, Parameter(name="--candidate-head")] = None
    closeout: bool = False
    independent_verification_receipt: Annotated[
        Path | None, Parameter(name="--independent-verification-receipt")
    ] = None


_DEFAULT_LAND_OPTIONS = _LandOptions()


def _closeout_result(
    *,
    repo: Path,
    command: str,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    accepted_head: str,
    candidate_head: str,
    audit_root: Path,
    audit: dict[str, object],
    lifecycle: dict[str, object],
    update: dict[str, object],
    gaps: tuple[str, ...],
    verdict: Verdict,
    control_replacement: dict[str, object],
    receipt_path: Path | None,
) -> EthosResult:
    resolution = closeout_resolution(
        repo=repo,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        audit_root=audit_root,
        audit=audit,
        lifecycle=lifecycle,
        control_replacement=control_replacement,
        update=update,
        verdict=verdict,
        gaps=gaps,
        apply=apply,
        receipt_path=receipt_path,
    )
    expected_receipt = receipt_path or closeout_receipt_path(repo, control_replacement)
    mutation_next_action = resolution.next_action
    policy = load_branch_role_policy(repo)
    expected_state = {
        "root": repo.resolve().as_posix(),
        "accepted_ref": f"refs/heads/{policy.accepted_branch}",
        "accepted_head": accepted_head,
        "candidate_ref": f"refs/heads/{policy.candidate_branch}",
        "candidate_head": candidate_head,
    }
    decision = admission_decision(
        subject=MutationSubject(
            action="accepted.advance",
            resource=f"refs/heads/{policy.accepted_branch}",
            expected_state=expected_state,
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="not_evaluated",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref=f"commitment:{command}-admission",
        required_gaps=gaps,
        why=(
            ("candidate_already_current",)
            if verdict == "pass" and candidate_head == accepted_head
            else ()
        ),
        next_action=mutation_next_action,
    )
    return EthosResult(
        command="land",
        verdict=verdict,
        state=(
            "accepted_current"
            if verdict == "pass" and candidate_head == accepted_head
            else "ready_to_closeout"
            if verdict == "pass" and not apply
            else "deferred"
            if verdict == "unknown"
            else "blocked"
            if verdict == "block"
            else str(update.get("state") or command)
        ),
        required_gaps=gaps,
        next_action=mutation_next_action,
        governance_context=repository_context(audit_root),
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "accepted_update": update,
            "control_replacement": control_replacement,
            "closeout_resolution": resolution.model_dump(mode="json"),
            "closeout_bootstrap": closeout_bootstrap_package(
                repo=repo,
                audit_root=audit_root,
                required_gaps=gaps,
                accepted_head=accepted_head,
                candidate_head=candidate_head,
                receipt_path=expected_receipt,
            ),
            "mutation": mutation_envelope(
                command=command,
                apply=apply,
                authorized=authorize,
                expect_head=expect_head,
                decision=decision,
            ),
        },
    )


def _land_expected_state(
    *,
    repo: Path,
    current_head: str,
    status_payload: Mapping[str, object],
    closeout_support: Mapping[str, object],
) -> dict[str, object]:
    policy = load_branch_role_policy(repo)
    candidate = string_mapping(status_payload.get("candidate"))
    return {
        "root": repo.resolve().as_posix(),
        "source_ref": f"refs/heads/{status_payload.get('branch', '')}",
        "source_head": current_head,
        "target_ref": f"refs/heads/{policy.candidate_branch}",
        "target_head": str(candidate.get("head") or ""),
        "holder_ref": str(closeout_support.get("holder_ref") or ""),
        "lease_id": str(closeout_support.get("lease_id") or ""),
        "lease_epoch": integer(closeout_support.get("lease_epoch")),
        "lease_expected_head": str(closeout_support.get("lease_expected_head") or ""),
        "lease_expected_tree": str(closeout_support.get("lease_expected_tree") or ""),
        "lease_base_commitment_path": str(closeout_support.get("lease_base_commitment_path") or ""),
        "lease_base_commitment_bytes_sha256": str(
            closeout_support.get("lease_base_commitment_bytes_sha256") or ""
        ),
        "lease_base_commitment_digest": str(closeout_support.get("base_commitment_digest") or ""),
        "lease_expires_at": str(closeout_support.get("lease_expires_at") or ""),
        "lease_payload_sha256": str(closeout_support.get("lease_payload_sha256") or ""),
    }


def _observed_candidate_head(repo: Path, current_head: str) -> str:
    status = workspace_status(repo, include_foreign_path_scope=False)
    return str(string_mapping(status.get("candidate")).get("head") or current_head)


def _stable_control_replacement(
    *,
    repo: Path,
    audit_root: Path,
    accepted_head: str,
    candidate_head: str,
    independent_verification_receipt: Path | None,
) -> tuple[dict[str, object], tuple[str, ...]]:
    if _observed_candidate_head(repo, accepted_head) != candidate_head:
        gaps = ("candidate_head_changed_after_closeout_audit",)
        return {"verdict": "unknown", "required_gaps": list(gaps)}, gaps
    report = control_replacement_report(
        candidate_root=audit_root,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=independent_verification_receipt,
    )
    return report, tuple(string_sequence(report.get("required_gaps")))


def _closeout_land_result(
    *,
    repo: Path,
    command: str,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    candidate_head: str | None,
    current_head: str,
    independent_verification_receipt: Path | None,
) -> EthosResult:
    """Evaluate candidate-to-accepted closeout as one semantic transition."""
    decision = evaluate_closeout_mutation(
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
        root=repo,
        current_head=current_head,
    )
    audit_root = closeout_audit_root(repo, decision)
    audited_candidate_head = _observed_candidate_head(repo, current_head)
    if candidate_head is not None and candidate_head != audited_candidate_head:
        decision = admission_decision(
            subject=decision.subject,
            verdict="block",
            basis=decision.basis,
            policy_ref=decision.policy_refs[0],
            required_gaps=("candidate_head_expectation_mismatch",),
            next_action="",
        )
    audit = repository_audit_after_admission(audit_root, decision)
    lifecycle = completed_active_changes_report(audit_root)
    control_replacement, control_gaps = _stable_control_replacement(
        repo=repo,
        audit_root=audit_root,
        accepted_head=current_head,
        candidate_head=audited_candidate_head,
        independent_verification_receipt=independent_verification_receipt,
    )
    gaps = (
        tuple(string_sequence(audit.get("required_gaps")))
        + decision.required_gaps
        + tuple(string_sequence(lifecycle.get("required_gaps")))
        + control_gaps
    )
    verdict = reduce_verdicts(
        decision.verdict,
        report_verdict(audit),
        report_verdict(lifecycle),
        report_verdict(control_replacement),
        required_gaps=gaps,
    )
    update: dict[str, object] = {}
    if verdict == "pass" and apply:
        control_replacement, fresh_control_gaps = _stable_control_replacement(
            repo=repo,
            audit_root=audit_root,
            accepted_head=current_head,
            candidate_head=audited_candidate_head,
            independent_verification_receipt=independent_verification_receipt,
        )
        gaps = tuple(dict.fromkeys((*gaps, *fresh_control_gaps)))
        verdict = reduce_verdicts(
            verdict,
            report_verdict(control_replacement),
            required_gaps=gaps,
        )
    if verdict == "pass" and apply:
        update = apply_candidate_to_accepted(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
            candidate_head=audited_candidate_head,
            control_replacement_receipt=string_mapping(
                string_mapping(control_replacement.get("independent_verification")).get("receipt")
            ),
        )
        gaps = tuple(dict.fromkeys((*gaps, *string_sequence(update.get("required_gaps")))))
        verdict = reduce_verdicts(verdict, report_verdict(update), required_gaps=gaps)
    return _closeout_result(
        repo=repo,
        command=command,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        accepted_head=current_head,
        candidate_head=audited_candidate_head,
        audit_root=audit_root,
        audit=audit,
        lifecycle=lifecycle,
        update=update,
        gaps=gaps,
        verdict=verdict,
        control_replacement=control_replacement,
        receipt_path=independent_verification_receipt,
    )


def _candidate_land_result(
    *,
    repo: Path,
    command: str,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    current_head: str,
) -> EthosResult:
    """Evaluate work-lane integration into the configured candidate role."""
    governance = repository_context(repo)
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    closeout_support = string_mapping(status_payload.get("closeout_support"))
    closeout_gaps: tuple[str, ...] = ()
    if status_payload.get("role") == "work_lane" and not closeout_support.get("supported"):
        closeout_gaps = tuple(string_sequence(closeout_support.get("required_gaps")))
    decision = evaluate_mutation(
        command=command,
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
        root=repo,
        current_head=current_head,
        status=None if apply else status_payload,
    )
    audit = repository_audit_after_admission(repo, decision)
    lifecycle = completed_active_changes_report(repo)
    archive_gaps = tuple(
        f"openspec_active_change_unarchived:{name}:work_lane"
        for name in active_change_names(repo / "openspec")
    )
    gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + decision.required_gaps
            + closeout_gaps
            + tuple(string_sequence(lifecycle.get("required_gaps")))
            + archive_gaps
        )
    )
    verdict = reduce_verdicts(
        decision.verdict,
        report_verdict(audit),
        report_verdict(lifecycle),
        required_gaps=gaps,
    )
    update: dict[str, object] = {}
    if verdict == "pass" and apply:
        update = apply_land_to_candidate(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
            admitted_decision=decision,
        )
        gaps = tuple(dict.fromkeys((*gaps, *string_sequence(update.get("required_gaps")))))
        verdict = reduce_verdicts(verdict, report_verdict(update), required_gaps=gaps)
    elif verdict == "pass":
        update = candidate_transition_readiness(root=repo, status=status_payload)
        gaps = tuple(dict.fromkeys((*gaps, *string_sequence(update.get("required_gaps")))))
        verdict = reduce_verdicts(verdict, report_verdict(update), required_gaps=gaps)
    state = (
        "ready_to_land"
        if verdict == "pass" and not apply
        else "blocked"
        if verdict == "block"
        else "unknown"
        if verdict == "unknown"
        else str(update.get("state") or "landed")
    )
    mutation_next_action = land_next_action(verdict=verdict, gaps=gaps, current_head=current_head)
    expected_state = _land_expected_state(
        repo=repo,
        current_head=current_head,
        status_payload=status_payload,
        closeout_support=closeout_support,
    )
    final_decision = admission_decision(
        subject=MutationSubject(
            action="candidate.integrate",
            resource=f"refs/heads/{load_branch_role_policy(repo).candidate_branch}",
            expected_state=expected_state,
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="not_evaluated",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref=f"commitment:{command}-admission",
        required_gaps=gaps,
        why=(state,) if verdict == "pass" else (),
        next_action=mutation_next_action,
    )
    return EthosResult(
        command="land",
        verdict=verdict,
        state=state,
        required_gaps=gaps,
        next_action=mutation_next_action,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "candidate_update": update,
            "closeout_support": closeout_support,
            "mutation": mutation_envelope(
                command=command,
                apply=apply,
                authorized=authorize,
                expect_head=expect_head,
                decision=final_decision,
            ),
        },
    )


@app.command
def land(
    options: Annotated[_LandOptions, Parameter(name="*")] = _DEFAULT_LAND_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = resolve_root(root)
    profile = load_repository_profile(repo)
    if profile.state == "invalid":
        emit_invalid_repository_profile(
            command="land",
            json_output=json_output,
            enforce=options.apply,
        )
        return
    current_head = git.current_head(repo)
    command = "closeout" if options.closeout else "land"
    result = (
        _closeout_land_result(
            repo=repo,
            command=command,
            apply=options.apply,
            authorize=options.authorize,
            expect_head=options.expect_head,
            candidate_head=options.candidate_head,
            current_head=current_head,
            independent_verification_receipt=options.independent_verification_receipt,
        )
        if options.closeout
        else _candidate_land_result(
            repo=repo,
            command=command,
            apply=options.apply,
            authorize=options.authorize,
            expect_head=options.expect_head,
            current_head=current_head,
        )
    )
    emit(result, json_output=json_output, enforce=options.apply)

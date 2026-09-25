"""Shared application operations for exact peer publication and continuation."""

import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.publication.execution import apply_remote_publication_effect
from ethos.adapters.mutation.publication.request import compile_remote_publication_request
from ethos.adapters.mutation.publication.request import load_remote_publication_request
from ethos.adapters.mutation.publication.request import observe_publication_request
from ethos.adapters.mutation.publication.request import observe_remote_publication_effect
from ethos.adapters.mutation.publication.request import persist_remote_publication_request
from ethos.adapters.mutation.publication.retirement import proposal_retirement_followup
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.publication.inspection import observe_publication
from ethos.domain.publication.inspection import publication_readiness_result
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.publication import select_publication_peers
from ethos.result import EthosResult

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan
    from ethos.domain.publication.inspection import PublicationContext
from ethos.domain.execution import application_result
from ethos.domain.execution import profile_failure_result
from ethos.repository.profile import load_repository_profile


def _object_mapping(value: object) -> dict[str, object]:
    """Return a JSON object mapping or a safe empty projection."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _remote_ref_observation(
    observations: Mapping[str, Mapping[str, object]], peer_id: str, target_ref: str
) -> dict[str, object]:
    """Return one nested peer ref observation without leaking storage shape."""
    peer = _object_mapping(observations.get(peer_id))
    refs = _object_mapping(peer.get("refs"))
    return _object_mapping(refs.get(target_ref))


def _publication_admission_gaps(
    *,
    repo: Path,
    target_refs: tuple[str, ...],
    source_object_oid: str,
    remotes: Mapping[str, str],
    observations: Mapping[str, Mapping[str, object]],
    effect_gaps: tuple[str, ...],
    proof_admission: Mapping[str, object],
    retire: bool = False,
) -> tuple[tuple[str, ...], dict[str, dict[str, object]]]:
    reports: dict[str, dict[str, object]] = {}
    for peer_id, remote in remotes.items():
        for target_ref in target_refs:
            observation = _remote_ref_observation(observations, peer_id, target_ref)
            object_oid = observation.get("object_oid")
            if (
                observation.get("state") not in {"present", "absent"}
                or not isinstance(object_oid, str)
                or (not object_oid)
            ):
                continue
            reports[f"{peer_id}:{target_ref}"] = push_admission_report(
                root=repo,
                target_ref=target_ref,
                pushed_head=zero_oid(repo) if retire else source_object_oid,
                remote_head=object_oid,
                remote_name=remote,
                proof_admission=proof_admission,
            )
    proof_gaps = set(string_sequence(proof_admission.get("required_gaps")))
    gaps = tuple(
        dict.fromkeys(
            (
                *effect_gaps,
                *(
                    gap if gap in proof_gaps else f"{gap}:{peer_id}"
                    for peer_id, report in reports.items()
                    for gap in string_sequence(report.get("required_gaps"))
                ),
            )
        )
    )
    return (gaps, reports)


def _publication_request_gaps(
    *,
    repo: Path,
    current_head: str,
    target_refs: tuple[str, ...],
    remotes: Mapping[str, str],
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    receipt: str | None,
    probe_remote: bool,
) -> list[str]:
    """Return invocation and source facts required before publication effects."""
    conditions = (
        (expect_head is None, "expect_head_required"),
        (apply and (not authorize), "authorization_required"),
        (expect_head is not None and expect_head != current_head, "expect_head_mismatch"),
        (receipt is not None and (not apply), "remote_publication_receipt_apply_required"),
        (receipt is None and (not probe_remote), "publication_remote_probe_required"),
        (not target_refs, "publication_target_ref_required"),
        (len(target_refs) != len(set(target_refs)), "publication_target_ref_duplicate"),
        (not remotes, "publication_peers_missing"),
    )
    gaps = [gap for blocked, gap in conditions if blocked]
    gaps.extend(
        f"publication_target_ref_invalid:{target_ref}"
        for target_ref in target_refs
        if not target_ref.startswith(("refs/heads/", "refs/tags/"))
        or git.run_git(repo, "check-ref-format", target_ref, check=False).returncode != 0
    )
    return gaps


def _publication_effect_observation(
    *,
    repo: Path,
    target_refs: tuple[str, ...],
    current_head: str,
    remotes: dict[str, str],
    proof_admission: Mapping[str, object],
    ref_admissions: dict[str, dict[str, object]],
    probe_remote: bool,
    retire: bool,
) -> tuple[
    PublicationEffect | None,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    tuple[str, ...],
    Verdict,
]:
    """Compile one effect and its admission reports from live peer facts."""
    if not (probe_remote and target_refs and remotes):
        return (None, {}, {}, (), "pass")
    source_ref = target_refs[0] if target_refs[0].startswith("refs/tags/") else current_head
    effect, observations, effect_gaps = observe_remote_publication_effect(
        root=repo,
        source_ref=source_ref,
        target_refs=target_refs,
        remotes=remotes,
        ref_admissions=ref_admissions,
        retire=retire,
    )
    admission_gaps, reports = _publication_admission_gaps(
        repo=repo,
        target_refs=target_refs,
        source_object_oid=effect.source.object_oid if effect is not None else current_head,
        remotes=remotes,
        observations=observations,
        effect_gaps=effect_gaps,
        proof_admission=proof_admission,
        retire=retire,
    )
    effect_verdict: Verdict = (
        "block"
        if any(
            not gap.startswith("publication_remote_observation_unavailable:") for gap in effect_gaps
        )
        else "unknown"
        if effect_gaps
        else "pass"
    )
    verdict = reduce_verdicts(effect_verdict, *(report_verdict(item) for item in reports.values()))
    return (effect, observations, reports, admission_gaps, verdict)


def _publish_projection(
    repo: Path,
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    probe_remote: bool,
    target_refs: tuple[str, ...],
    peer_ids: tuple[str, ...],
    receipt: str | None,
    receipt_sha256: str | None,
    retire: bool,
) -> EthosResult:
    """Derive or replay one full-ref plan through the sole execution path."""
    gaps: list[str] = []
    observations: dict[str, dict[str, object]] = {}
    push_admission: dict[str, dict[str, object]] = {}
    request: dict[str, object] = {}
    plan: TransitionPlan | None = None
    effect: PublicationEffect | None = None
    replay = receipt is not None
    if replay:
        request = {"path": receipt or "", "sha256": receipt_sha256 or ""}
        plan, effect, target_refs, gaps = observe_publication_request(
            repo, str(request["path"]), str(request["sha256"])
        )
    retirement = effect.retirement if effect is not None else retire
    projection_verdict: Verdict = "block" if gaps else "pass"
    context = observe_publication(
        repo, apply=False, authorized=authorize, expect_head=expect_head, target_refs=target_refs
    )
    current_head = context.head
    gaps.extend(context.required_gaps)
    selected_remotes, selection_gaps = select_publication_peers(context.remotes, peer_ids)
    if replay and peer_ids:
        selection_gaps.append("publication_peer_selection_receipt_conflict")
    request_gaps = _publication_request_gaps(
        repo=repo,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        receipt=receipt,
        probe_remote=probe_remote,
        current_head=current_head,
        target_refs=target_refs,
        remotes=context.remotes,
    )
    request_gaps.extend(selection_gaps)
    gaps.extend(request_gaps)
    if not replay and (not request_gaps):
        effect, observations, push_admission, admission_gaps, projection_verdict = (
            _publication_effect_observation(
                repo=repo,
                probe_remote=probe_remote,
                retire=retire,
                target_refs=target_refs,
                current_head=current_head,
                remotes=selected_remotes,
                proof_admission=context.proof_admission,
                ref_admissions=context.ref_admissions,
            )
        )
        gaps.extend(admission_gaps)
        if effect is not None:
            proof = _object_mapping(context.proof_admission.get("attestation"))
            if proof:
                proof = {**proof, "selection": str(context.proof_admission.get("selection") or "")}
            plan = compile_remote_publication_request(root=repo, effect=effect, proof=proof)
            gaps.extend(plan.required_gaps)
            projection_verdict = reduce_verdicts(projection_verdict, plan.verdict)
            if plan.verdict == "pass" and projection_verdict == "pass":
                request = persist_remote_publication_request(repo, plan)
    if effect is not None and effect.source.peeled_commit != current_head:
        gaps.append("remote_publication_receipt_head_mismatch")
        projection_verdict = "block"
    gaps = list(dict.fromkeys(gaps))
    verdict = reduce_verdicts(
        context.verdict,
        projection_verdict,
        "block" if request_gaps else "pass",
        required_gaps=tuple(gaps),
    )
    execution: dict[str, object] = {"state": "not_applied", "required_gaps": []}
    if apply and verdict == "pass" and (plan is not None):
        admitted = (
            plan
            if replay
            else load_remote_publication_request(repo, str(request["path"]), str(request["sha256"]))
        )
        execution = apply_remote_publication_effect(root=repo, plan=admitted)
        gaps = list(dict.fromkeys((*gaps, *string_sequence(execution.get("required_gaps")))))
        verdict = reduce_verdicts(verdict, report_verdict(execution))
    return _publication_result(
        repo,
        context,
        target_refs=target_refs,
        peer_ids=peer_ids,
        retirement=retirement,
        replay=replay,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        request=request,
        plan=plan,
        effect=effect,
        observations=observations,
        push_admission=push_admission,
        execution=execution,
        verdict=verdict,
        gaps=gaps,
    )


def _publication_result(
    repo: Path,
    context: "PublicationContext",
    *,
    target_refs: tuple[str, ...],
    peer_ids: tuple[str, ...],
    retirement: bool,
    replay: bool,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    request: dict[str, object],
    plan: "TransitionPlan | None",
    effect: PublicationEffect | None,
    observations: dict[str, dict[str, object]],
    push_admission: dict[str, dict[str, object]],
    execution: dict[str, object],
    verdict: Verdict,
    gaps: list[str],
) -> EthosResult:
    """Project confirmed peer effects and the independently admitted local continuation."""
    current_head = context.head
    selected_ids = (
        tuple(target.id for target in effect.targets)
        if effect is not None
        else tuple(peer_id for peer_id in context.remotes if not peer_ids or peer_id in peer_ids)
    )
    unselected_ids = tuple(peer_id for peer_id in context.remotes if peer_id not in selected_ids)
    target_refs = (
        tuple(update.target_ref for update in effect.targets[0].updates)
        if effect is not None
        else target_refs
    )
    state = (
        ("retired" if retirement else "published")
        if apply and verdict == "pass"
        else str(execution.get("state") or "not_applied")
        if apply and execution.get("state") != "not_applied"
        else ("ready_to_retire" if retirement else "ready_to_publish")
        if verdict == "pass"
        else "observation_unknown"
        if verdict == "unknown"
        else "blocked"
    )
    retirement_next_action = (
        next(
            (
                str(report["next_action"])
                for report in push_admission.values()
                if report_verdict(report) != "pass" and report.get("next_action")
            ),
            "",
        )
        if retirement
        else ""
    )
    next_action = (
        shlex.join(
            (
                "ethos",
                "publish",
                "--receipt",
                str(request["path"]),
                "--receipt-sha256",
                str(request["sha256"]),
                "--apply",
                "--authorize",
                "--expect-head",
                current_head,
                "--root",
                str(repo),
                "--json",
            )
        )
        if not apply and verdict == "pass"
        else ""
        if apply and verdict == "pass"
        else retirement_next_action
        or str(context.independent_verification.get("next_action") or "")
        or str(context.proof_admission.get("next_action") or "")
        or shlex.join(
            (
                "ethos",
                "publish",
                *(("--retire",) if retirement else ()),
                *(item for target_ref in target_refs for item in ("--ref", target_ref)),
                *(
                    item
                    for peer_id in (peer_ids or (selected_ids if unselected_ids else ()))
                    for item in ("--peer", peer_id)
                ),
                "--probe-remote",
                "--expect-head",
                current_head,
                "--root",
                repo.resolve().as_posix(),
                "--json",
            )
        )
    )
    followup: dict[str, object] = {}
    if retirement and apply and (verdict == "pass") and (effect is not None):
        references = tuple(
            dict.fromkeys(
                update.target_ref for target in effect.targets for update in target.updates
            )
        )
        followup = proposal_retirement_followup(repo, references)
        if followup["state"] != "complete":
            state = "retirement_pending"
            next_action = str(followup["next_action"])
            gaps = list(dict.fromkeys((*gaps, *string_sequence(followup["required_gaps"]))))
            verdict = reduce_verdicts(verdict, report_verdict(followup), required_gaps=tuple(gaps))
    decision = admission_decision(
        subject=MutationSubject(
            action="remote.publish",
            resource=",".join(target_refs) or "refs/<kind>/<name>",
            expected_state={
                "root": repo.resolve().as_posix(),
                "source_head": current_head,
                "target_refs": target_refs,
                "effect_digest": effect.digest() if effect is not None else "",
                "plan_digest": plan.digest if plan is not None else "",
            },
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="remote_ref_transition",
            identity_basis="immutable_request_receipt" if replay else "configured_push_identity",
            state_bindings=("root", "source_head", "target_refs", "plan_digest", "effect_digest"),
            evidence_boundary="exact_head_proof_and_live_remote_ref_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref="commitment:publish-admission",
        required_gaps=tuple(gaps),
        next_action=next_action,
    )
    remote_effect = effect.model_dump(mode="json") if effect is not None else {}
    remote_effect.update(execution)
    return EthosResult(
        command="publish",
        verdict=verdict,
        state=state,
        summary={
            "mode": "publication_receipt_apply" if replay else "publication",
            "target_refs": target_refs,
            "source_head": current_head,
            "remote_push": "applied"
            if execution.get("state") == "applied"
            else state
            if state in {"partial", "outcome_unknown"}
            else "not_performed",
            "declared_peer_count": len(context.remotes),
            "selected_peer_ids": list(selected_ids),
            "unselected_peer_ids": list(unselected_ids),
            "cross_provider_atomicity_claimed": False,
        },
        required_gaps=tuple(gaps),
        next_action=next_action,
        user_decision_required=bool(followup.get("user_decision_required")),
        governance_context=context.governance,
        data={
            "repository_audit": context.audit,
            "independent_verification": context.independent_verification,
            "proof_admission": dict(context.proof_admission),
            "remote_topology": context.topology,
            "remote_observations": observations,
            "push_admission": push_admission,
            "remote_effect": remote_effect,
            "retirement_followup": followup,
            "transition_plan": plan.model_dump(mode="json") if plan is not None else {},
            "request_receipt": request,
            "mutation": mutation_envelope(
                command="publish",
                apply=apply,
                authorized=authorize,
                expect_head=expect_head,
                decision=decision,
            ),
        },
    )


@application_result("publish")
def publish_repository(
    root: Path,
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    probe_remote: bool = False,
    target_refs: tuple[str, ...] = (),
    peer_ids: tuple[str, ...] = (),
    receipt: str | None = None,
    receipt_sha256: str | None = None,
    retire: bool = False,
) -> EthosResult:
    """Observe or apply exact peer publication without owning local-ref retirement effects."""
    repo = root.resolve()
    if load_repository_profile(repo).state == "invalid":
        return profile_failure_result("publish")
    if target_refs or peer_ids or receipt is not None or retire:
        return _publish_projection(
            repo,
            apply=apply,
            authorize=authorize,
            expect_head=expect_head,
            probe_remote=probe_remote,
            target_refs=target_refs,
            peer_ids=peer_ids,
            receipt=receipt,
            receipt_sha256=receipt_sha256,
            retire=retire,
        )
    context = observe_publication(
        repo,
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
        target_refs=target_refs,
    )
    return publication_readiness_result(
        context,
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
        probe_remote=probe_remote,
    )

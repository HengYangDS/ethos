"""Root publish readiness command."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.remote_publication import apply_remote_publication_effect
from ethos.adapters.mutation.remote_publication import compile_remote_publication_request
from ethos.adapters.mutation.remote_publication import load_remote_publication_request
from ethos.adapters.mutation.remote_publication import observe_remote_publication_effect
from ethos.adapters.mutation.remote_publication import persist_remote_publication_request
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.publication import PublicationContext
from ethos.domain.land.publication import observe_publication
from ethos.domain.land.publication import publication_readiness_result
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan


@dataclass(frozen=True, slots=True)
class _PublishOptions:
    """CLI options for `ethos publish`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    probe_remote: Annotated[bool, Parameter(name="--probe-remote")] = False
    target_refs: Annotated[tuple[str, ...], Parameter(name="--ref")] = ()
    receipt: Annotated[str | None, Parameter(name="--receipt")] = None
    receipt_sha256: Annotated[str | None, Parameter(name="--receipt-sha256")] = None


_DEFAULT_PUBLISH_OPTIONS = _PublishOptions()


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
    current_head: str,
    remotes: Mapping[str, str],
    observations: Mapping[str, Mapping[str, object]],
    effect_gaps: tuple[str, ...],
    proof_admission: Mapping[str, object],
) -> tuple[tuple[str, ...], dict[str, dict[str, object]]]:
    reports: dict[str, dict[str, object]] = {}
    for peer_id, remote in remotes.items():
        for target_ref in target_refs:
            observation = _remote_ref_observation(observations, peer_id, target_ref)
            object_oid = observation.get("object_oid")
            if (
                observation.get("state") not in {"present", "absent"}
                or not isinstance(object_oid, str)
                or not object_oid
            ):
                continue
            reports[f"{peer_id}:{target_ref}"] = push_admission_report(
                root=repo,
                target_ref=target_ref,
                pushed_head=current_head,
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
    return gaps, reports


def _publication_request_gaps(
    *,
    repo: Path,
    options: _PublishOptions,
    source_branch: str,
    candidate_branch: str,
    current_head: str,
    target_refs: tuple[str, ...],
    remotes: Mapping[str, str],
    ref_admissions: Mapping[str, Mapping[str, object]],
) -> list[str]:
    """Return invocation and source facts required before publication effects."""
    roles = tuple(
        str(ref_admissions.get(target_ref, {}).get("role") or "other") for target_ref in target_refs
    )
    conditions = (
        (options.expect_head is None, "expect_head_required"),
        (
            "proposal_ref" in roles and source_branch != candidate_branch,
            f"publication_source_role_mismatch:{source_branch}:proposal_ref",
        ),
        (options.apply and not options.authorize, "authorization_required"),
        (
            options.expect_head is not None and options.expect_head != current_head,
            "expect_head_mismatch",
        ),
        (not options.probe_remote, "publication_remote_probe_required"),
        (not target_refs, "publication_target_ref_required"),
        (len(target_refs) != len(set(target_refs)), "publication_target_ref_duplicate"),
        (not remotes, "publication_peers_missing"),
    )
    gaps = [gap for blocked, gap in conditions if blocked]
    gaps.extend(
        f"publication_target_ref_invalid:{target_ref}"
        for target_ref in target_refs
        if git.run_git(repo, "check-ref-format", target_ref, check=False).returncode != 0
    )
    return gaps


def _publication_effect_observation(
    *,
    repo: Path,
    options: _PublishOptions,
    target_refs: tuple[str, ...],
    current_head: str,
    remotes: dict[str, str],
    proof_admission: Mapping[str, object],
    ref_admissions: dict[str, dict[str, object]],
) -> tuple[
    PublicationEffect | None,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    tuple[str, ...],
]:
    """Compile one effect and its admission reports from live peer facts."""
    if not (options.probe_remote and target_refs and remotes):
        return None, {}, {}, ()
    source_ref = target_refs[0] if target_refs[0].startswith("refs/tags/") else current_head
    effect, observations, effect_gaps = observe_remote_publication_effect(
        root=repo,
        source_ref=source_ref,
        target_refs=target_refs,
        remotes=remotes,
        ref_admissions=ref_admissions,
    )
    admission_gaps, reports = _publication_admission_gaps(
        repo=repo,
        target_refs=target_refs,
        current_head=current_head,
        remotes=remotes,
        observations=observations,
        effect_gaps=effect_gaps,
        proof_admission=proof_admission,
    )
    return effect, observations, reports, admission_gaps


def _publish_projection(
    context: PublicationContext,
    *,
    options: _PublishOptions,
    json_output: bool,
) -> None:
    """Derive or replay one full-ref plan through the sole execution path."""
    repo, current_head = context.root, context.head
    target_refs = options.target_refs
    gaps = list(context.required_gaps)
    observations: dict[str, dict[str, object]] = {}
    push_admission: dict[str, dict[str, object]] = {}
    request: dict[str, object] = {}
    plan: TransitionPlan | None = None
    effect: PublicationEffect | None = None
    replay = options.receipt is not None
    if replay:
        gaps.extend(
            gap
            for blocked, gap in (
                (not options.apply, "remote_publication_receipt_apply_required"),
                (not options.authorize, "authorization_required"),
                (options.expect_head is None, "expect_head_required"),
                (
                    options.expect_head is not None and options.expect_head != current_head,
                    "expect_head_mismatch",
                ),
            )
            if blocked
        )
        request = {"path": options.receipt or "", "sha256": options.receipt_sha256 or ""}
        try:
            plan = load_remote_publication_request(
                repo, str(request["path"]), str(request["sha256"])
            )
            effect = publication_effect_from_plan(plan)
        except ValueError as error:
            gaps.append(str(error))
    else:
        gaps.extend(
            _publication_request_gaps(
                repo=repo,
                options=options,
                source_branch=context.branch,
                candidate_branch=context.role_policy.candidate_branch,
                current_head=current_head,
                target_refs=target_refs,
                remotes=context.remotes,
                ref_admissions=context.ref_admissions,
            )
        )
        effect, observations, push_admission, admission_gaps = _publication_effect_observation(
            repo=repo,
            options=options,
            target_refs=target_refs,
            current_head=current_head,
            remotes=context.remotes,
            proof_admission=context.proof_admission,
            ref_admissions=context.ref_admissions,
        )
        gaps.extend(admission_gaps)
        if effect is not None:
            proof = _object_mapping(context.proof_admission.get("attestation"))
            if proof:
                proof = {
                    **proof,
                    "selection": str(context.proof_admission.get("selection") or ""),
                }
            plan = compile_remote_publication_request(root=repo, effect=effect, proof=proof)
            gaps.extend(plan.required_gaps)
            if plan.verdict == "pass":
                request = persist_remote_publication_request(repo, plan)

    if effect is not None and effect.source.peeled_commit != current_head:
        gaps.append("remote_publication_receipt_head_mismatch")
    gaps = list(dict.fromkeys(gaps))
    unknown_gaps = tuple(
        gap for gap in gaps if gap.startswith("publication_remote_observation_unavailable:")
    )
    blocking_gaps = tuple(gap for gap in gaps if gap not in unknown_gaps)
    verdict: Verdict = (
        "block"
        if context.verdict == "block" or blocking_gaps
        else "unknown"
        if context.verdict == "unknown" or unknown_gaps
        else "pass"
    )
    execution: dict[str, object] = {"state": "not_applied", "required_gaps": []}
    if options.apply and verdict == "pass" and plan is not None:
        admitted = (
            plan
            if replay
            else load_remote_publication_request(repo, str(request["path"]), str(request["sha256"]))
        )
        execution = apply_remote_publication_effect(root=repo, plan=admitted)
        gaps = list(dict.fromkeys((*gaps, *string_sequence(execution.get("required_gaps")))))
        verdict = reduce_verdicts(verdict, report_verdict(execution))
    target_refs = (
        tuple(update.target_ref for update in effect.targets[0].updates)
        if effect is not None
        else target_refs
    )
    state = (
        "published"
        if options.apply and verdict == "pass"
        else str(execution.get("state") or "not_applied")
        if options.apply and execution.get("state") != "not_applied"
        else "ready_to_publish"
        if verdict == "pass"
        else "observation_unknown"
        if verdict == "unknown"
        else "blocked"
    )
    proof_next_action = str(context.proof_admission.get("next_action") or "")
    next_action = (
        f"ethos publish --receipt {request['path']} --receipt-sha256 {request['sha256']} "
        f"--apply --authorize --expect-head {current_head} --json"
        if not options.apply and verdict == "pass"
        else ""
        if options.apply and verdict == "pass"
        else proof_next_action
        or " ".join(
            (
                "ethos",
                "publish",
                *(item for target_ref in target_refs for item in ("--ref", target_ref)),
                "--probe-remote",
                "--expect-head",
                current_head,
                "--root",
                repo.resolve().as_posix(),
                "--json",
            )
        )
    )
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
    emit(
        EthosResult(
            command="publish",
            verdict=verdict,
            state=state,
            summary={
                "mode": "publication_receipt_apply" if replay else "publication",
                "target_refs": target_refs,
                "source_head": current_head,
                "remote_push": (
                    "applied"
                    if state == "published"
                    else "outcome_unknown"
                    if state == "outcome_unknown"
                    else "not_performed"
                ),
                "declared_peer_count": len(effect.targets)
                if effect is not None
                else len(context.remotes),
                "cross_provider_atomicity_claimed": False,
            },
            required_gaps=tuple(gaps),
            next_action=next_action,
            governance_context=context.governance,
            data={
                "repository_audit": context.audit,
                "independent_verification": context.independent_verification,
                "proof_admission": dict(context.proof_admission),
                "remote_topology": context.topology,
                "remote_observations": observations,
                "push_admission": push_admission,
                "remote_effect": remote_effect,
                "transition_plan": plan.model_dump(mode="json") if plan is not None else {},
                "request_receipt": request,
                "mutation": mutation_envelope(
                    command="publish",
                    apply=options.apply,
                    authorized=options.authorize,
                    expect_head=options.expect_head,
                    decision=decision,
                ),
            },
        ),
        json_output=json_output,
        enforce=options.apply or verdict == "block",
        artifact_root=repo,
    )


@app.command
def publish(
    options: Annotated[_PublishOptions, Parameter(name="*")] = _DEFAULT_PUBLISH_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    repo = resolve_root(root)
    projection_mode = bool(options.target_refs) or options.receipt is not None
    context = observe_publication(
        repo,
        apply=options.apply and not projection_mode,
        authorized=options.authorize,
        expect_head=options.expect_head,
        target_refs=options.target_refs,
    )
    if projection_mode:
        _publish_projection(context, options=options, json_output=json_output)
        return
    emit(
        publication_readiness_result(
            context,
            apply=options.apply,
            authorized=options.authorize,
            expect_head=options.expect_head,
            probe_remote=options.probe_remote,
        ),
        json_output=json_output,
        enforce=options.apply,
    )

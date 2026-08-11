"""Root publish readiness command."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.remote_publication import apply_remote_publication_effect
from ethos.adapters.mutation.remote_publication import compile_remote_publication_request
from ethos.adapters.mutation.remote_publication import load_remote_publication_request
from ethos.adapters.mutation.remote_publication import observe_remote_publication_effect
from ethos.adapters.mutation.remote_publication import persist_remote_publication_request
from ethos.adapters.openspec.profile import protected_branch_active_change_required_gaps
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.publication import RemotePublicationEffect
from ethos.contracts.publication import remote_publication_effect_from_plan
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import repository_audit_after_admission
from ethos.domain.land.publication import local_ci_fallback_package
from ethos.domain.land.publication import publication_readiness
from ethos.domain.land.publication import publication_with_remote_matrix
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import repository_context
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes
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
    proposal: Annotated[str | None, Parameter(name="--proposal")] = None
    receipt: Annotated[str | None, Parameter(name="--receipt")] = None
    receipt_sha256: Annotated[str | None, Parameter(name="--receipt-sha256")] = None


_DEFAULT_PUBLISH_OPTIONS = _PublishOptions()


def _publish_next_action(*, verdict: Verdict, publication: dict[str, object]) -> str:
    """Return top-level publish actions without hiding publication work."""
    if verdict != "pass":
        return "ethos land --json"
    return str(publication.get("next_action") or "")


def _object_mapping(value: object) -> dict[str, object]:
    """Return a JSON object mapping or a safe empty projection."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _publish_expected_state(
    *,
    repo: Path,
    branch: str,
    current_head: str,
    publication: Mapping[str, object],
    remote_observations: Mapping[str, object],
    branch_admissions: Mapping[str, object],
) -> dict[str, object]:
    target_branch = str(publication.get("proposal_branch") or branch)
    observations = {key: _object_mapping(value) for key, value in remote_observations.items()}
    targets = [
        {
            "id": key,
            "remote": str(_object_mapping(data.get("availability")).get("remote") or ""),
            "availability_state": str(
                _object_mapping(data.get("availability")).get("state") or "not_probed"
            ),
            "sync_state": str(_object_mapping(data.get("sync")).get("state") or "not_checked"),
            "observed_remote_ref": str(_object_mapping(data.get("sync")).get("remote_ref") or ""),
            "observed_remote_head": str(_object_mapping(data.get("sync")).get("remote_head") or ""),
        }
        for key, data in observations.items()
    ]
    return {
        "root": repo.resolve().as_posix(),
        "source_ref": f"refs/heads/{branch}",
        "source_head": current_head,
        "target_ref": f"refs/heads/{target_branch}",
        "remote_targets": targets,
        "branch_admissions": dict(branch_admissions),
    }


def _remote_observations(
    *, repo: Path, branch: str, remotes: Mapping[str, str], probe_remote: bool
) -> dict[str, dict[str, object]]:
    """Read declared remote targets independently without pushing."""
    availability = git.remote_availability if probe_remote else git.remote_availability_not_probed
    return {
        key: {
            "availability": availability(repo, remote),
            "sync": git.remote_tracking_sync(repo, branch, remote),
        }
        for key, remote in remotes.items()
    }


def _proposal_branch(root: Path, prefix: str, slug: str) -> str:
    """Return the declared proposal branch only when Git admits its grammar."""
    branch = f"{prefix}{slug}"
    return branch if slug and git.branch_ref_is_valid(root, branch) else ""


def _proposal_admission_gaps(
    *,
    repo: Path,
    target_ref: str,
    current_head: str,
    remotes: Mapping[str, str],
    observed_heads: Mapping[str, str],
    effect_gaps: tuple[str, ...],
) -> tuple[tuple[str, ...], dict[str, dict[str, object]]]:
    reports = {
        peer_id: push_admission_report(
            root=repo,
            target_ref=target_ref,
            pushed_head=current_head,
            remote_head=observed_heads.get(peer_id, "0" * 40),
            remote_name=remote,
        )
        for peer_id, remote in remotes.items()
    }
    gaps = tuple(
        dict.fromkeys(
            (
                *effect_gaps,
                *(
                    f"{gap}:{peer_id}"
                    for peer_id, report in reports.items()
                    for gap in string_sequence(report.get("required_gaps"))
                ),
            )
        )
    )
    return gaps, reports


def _proposal_request_gaps(
    *,
    options: _PublishOptions,
    source_branch: str,
    candidate_branch: str,
    current_head: str,
    proposal_branch: str,
    remotes: Mapping[str, str],
) -> list[str]:
    """Return invocation and source facts required before proposal effects."""
    conditions = (
        (options.expect_head is None, "expect_head_required"),
        (
            source_branch != candidate_branch,
            f"publication_proposal_source_branch_required:{source_branch}:{candidate_branch}",
        ),
        (options.apply and not options.authorize, "authorization_required"),
        (
            options.expect_head is not None and options.expect_head != current_head,
            "expect_head_mismatch",
        ),
        (not options.probe_remote, "publication_proposal_remote_probe_required"),
        (
            not proposal_branch,
            f"publication_proposal_identifier_invalid:{options.proposal or ''}",
        ),
        (not remotes, "publication_proposal_peers_missing"),
    )
    return [gap for blocked, gap in conditions if blocked]


def _proposal_effect_observation(
    *,
    repo: Path,
    options: _PublishOptions,
    proposal_branch: str,
    current_head: str,
    remotes: dict[str, str],
) -> tuple[
    RemotePublicationEffect | None,
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
    tuple[str, ...],
]:
    """Compile one effect and its admission reports from live peer facts."""
    if not (options.probe_remote and proposal_branch and remotes):
        return None, {}, {}, ()
    target_ref = f"refs/heads/{proposal_branch}"
    effect, observations, effect_gaps = observe_remote_publication_effect(
        root=repo,
        source_head=current_head,
        target_ref=target_ref,
        remotes=remotes,
    )
    admission_gaps, reports = _proposal_admission_gaps(
        repo=repo,
        target_ref=target_ref,
        current_head=current_head,
        remotes=remotes,
        observed_heads={
            peer_id: str(observation.get("head") or "0" * 40)
            for peer_id, observation in observations.items()
        },
        effect_gaps=effect_gaps,
    )
    return effect, observations, reports, admission_gaps


def _publish_proposal(
    *,
    repo: Path,
    governance: Mapping[str, object],
    options: _PublishOptions,
    local_verdict: Verdict,
    base_gaps: tuple[str, ...],
    remote_topology: Mapping[str, object],
    remotes: dict[str, str],
    current_head: str,
    source_branch: str,
    candidate_branch: str,
    proposal_branch: str,
    audit: Mapping[str, object],
    independent_verification: Mapping[str, object],
    json_output: bool,
) -> None:
    """Derive or replay one proposal plan, then share one execution path."""
    gaps = list(base_gaps)
    observations: dict[str, dict[str, object]] = {}
    push_admission: dict[str, dict[str, object]] = {}
    request: dict[str, object] = {}
    plan: TransitionPlan | None = None
    effect: RemotePublicationEffect | None = None
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
            effect = remote_publication_effect_from_plan(plan)
        except ValueError as error:
            gaps.append(str(error))
    else:
        gaps.extend(
            _proposal_request_gaps(
                options=options,
                source_branch=source_branch,
                candidate_branch=candidate_branch,
                current_head=current_head,
                proposal_branch=proposal_branch,
                remotes=remotes,
            )
        )
        effect, observations, push_admission, admission_gaps = _proposal_effect_observation(
            repo=repo,
            options=options,
            proposal_branch=proposal_branch,
            current_head=current_head,
            remotes=remotes,
        )
        gaps.extend(admission_gaps)
        if effect is not None:
            plan = compile_remote_publication_request(root=repo, effect=effect)
            gaps.extend(plan.required_gaps)
            if plan.verdict == "pass":
                request = persist_remote_publication_request(repo, plan)

    if effect is not None and effect.source_head != current_head:
        gaps.append("remote_publication_receipt_head_mismatch")
    gaps = list(dict.fromkeys(gaps))
    verdict: Verdict = "block" if gaps or local_verdict != "pass" else "pass"
    execution: dict[str, object] = {"state": "not_applied", "required_gaps": []}
    if options.apply and verdict == "pass" and plan is not None:
        admitted = (
            plan
            if replay
            else load_remote_publication_request(repo, str(request["path"]), str(request["sha256"]))
        )
        execution = apply_remote_publication_effect(root=repo, plan=admitted)
        gaps = list(dict.fromkeys((*gaps, *string_sequence(execution.get("required_gaps")))))
        verdict = "block" if gaps else "pass"
    if effect is not None:
        proposal_branch = effect.targets[0].target_ref.removeprefix("refs/heads/")
    target_ref = effect.targets[0].target_ref if effect is not None else ""
    state = (
        "proposal_published"
        if options.apply and verdict == "pass"
        else "ready_to_publish_proposal"
        if verdict == "pass"
        else "blocked"
    )
    next_action = (
        f"ethos publish --receipt {request['path']} --receipt-sha256 {request['sha256']} "
        f"--apply --authorize --expect-head {current_head} --json"
        if not options.apply and verdict == "pass"
        else ""
        if options.apply and verdict == "pass"
        else "ethos publish --proposal <slug> --probe-remote --expect-head <head> --json"
    )
    effect_digest = effect.digest() if effect is not None else ""
    plan_digest = plan.digest if plan is not None else ""
    decision = admission_decision(
        subject=MutationSubject(
            action="remote.publish",
            resource=target_ref or "refs/heads/proposal/<slug>",
            expected_state={
                "root": repo.resolve().as_posix(),
                "source_head": current_head,
                "target_ref": target_ref,
                "effect_digest": effect_digest,
                "plan_digest": plan_digest,
            },
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="remote_ref_transition",
            identity_basis="immutable_request_receipt" if replay else "configured_push_identity",
            state_bindings=("root", "source_head", "target_ref", "plan_digest", "effect_digest"),
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
                "mode": "proposal_publication_receipt_apply" if replay else "proposal_publication",
                "proposal_branch": proposal_branch,
                "source_head": current_head,
                "remote_push": "applied" if state == "proposal_published" else "not_performed",
                "declared_peer_count": len(effect.targets) if effect is not None else len(remotes),
                "cross_provider_atomicity_claimed": False,
            },
            required_gaps=tuple(gaps),
            next_action=next_action,
            governance_context=dict(governance),
            data={
                "repository_audit": dict(audit),
                "independent_verification": dict(independent_verification),
                "remote_topology": dict(remote_topology),
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
    governance = repository_context(repo)
    current_head = git.current_head(repo)
    proposal_mode = options.proposal is not None or options.receipt is not None
    decision = evaluate_mutation(
        command="publish",
        apply=options.apply and not proposal_mode,
        authorized=options.authorize,
        expect_head=options.expect_head,
        root=repo,
        current_head=current_head,
    )
    audit = repository_audit_after_admission(repo, decision)
    independent_verification = independent_verification_admission_report(
        root=repo,
        action="publish",
        request=independent_verification_request(root=repo, action="publish"),
    )
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    branch = status_payload["branch"]
    release_carrier_gaps = tuple(
        protected_branch_active_change_required_gaps(repo, current_branch=str(branch))
    )
    terminal_gaps = () if decision.verdict == "block" else tuple(proof_gaps(repo, current_head))
    gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + decision.required_gaps
            + release_carrier_gaps
            + tuple(string_sequence(independent_verification.get("required_gaps")))
            + terminal_gaps
        )
    )
    local_verdict = reduce_verdicts(
        decision.verdict,
        report_verdict(audit),
        report_verdict(independent_verification),
        required_gaps=gaps,
    )
    remote_topology = publication_topology(repo, release_config(repo))
    local_topology = _object_mapping(remote_topology.get("local"))
    local_verification_command = str(local_topology.get("verification_command") or "")
    raw_topology_gaps = remote_topology.get("required_gaps", [])
    topology_gaps = (
        tuple(str(gap) for gap in raw_topology_gaps) if isinstance(raw_topology_gaps, list) else ()
    )
    gaps = tuple(dict.fromkeys((*gaps, *topology_gaps)))
    local_verdict = reduce_verdicts(local_verdict, required_gaps=gaps)
    policy = load_branch_role_policy(repo)
    configured_remotes = topology_remotes(remote_topology)
    if proposal_mode:
        proposal_branch = (
            ""
            if options.receipt is not None
            else _proposal_branch(repo, policy.proposal_branch_prefix, options.proposal or "")
        )
        _publish_proposal(
            repo=repo,
            governance=governance,
            options=options,
            local_verdict=local_verdict,
            base_gaps=gaps,
            remote_topology=remote_topology,
            remotes=configured_remotes,
            current_head=current_head,
            source_branch=str(branch),
            candidate_branch=policy.candidate_branch,
            proposal_branch=proposal_branch,
            audit=audit,
            independent_verification=independent_verification,
            json_output=json_output,
        )
        return
    branch_admissions = {
        peer_id: publication_branch_admission(
            remote_topology,
            branch=str(branch),
            role=policy.role_for_branch(str(branch)),
            remote_name=remote,
        )
        for peer_id, remote in configured_remotes.items()
    }
    remote_observations = _remote_observations(
        repo=repo,
        branch=str(branch),
        remotes=configured_remotes,
        probe_remote=options.probe_remote,
    )
    remote_matrix = git.publication_remote_syncs(repo, str(branch), configured_remotes)
    local_ci_fallback = local_ci_fallback_package(
        root=repo,
        current_head=current_head,
        command=local_verification_command,
    )
    publication = publication_readiness(
        branch=str(branch),
        local_ok=local_verdict == "pass",
        policy=policy,
        local_ci_fallback=local_ci_fallback,
        topology=remote_topology,
        remote_observations=remote_observations,
        local_verification_command=local_verification_command,
    )
    publication = publication_with_remote_matrix(
        publication,
        remote_matrix,
        remote_available=any(
            _object_mapping(item.get("availability")).get("available") is True
            for item in remote_observations.values()
        ),
    )
    remote_state = str(publication.get("remote_state") or "deferred")
    remote_push = str(publication.get("remote_push") or "not_performed")
    publish_summary = {
        "mode": "local_readiness",
        "local_readiness": local_verdict == "pass",
        "remote_push": remote_push,
        "remote_publication_state": remote_state,
        "remote_reconciliation_state": str(remote_matrix.get("state") or "pending"),
        "remote_states": {
            key: str(_object_mapping(value.get("availability")).get("state") or "not_probed")
            for key, value in remote_observations.items()
        },
        "remote_sync_states": {
            key: str(_object_mapping(value.get("sync")).get("state") or "not_checked")
            for key, value in remote_observations.items()
        },
        "remote_mutation_allowed": all(
            admission.get("remote_mutation_allowed") is True
            for admission in branch_admissions.values()
        ),
        "hosted_ci_status_claimed": False,
        "independent_verification": str(
            independent_verification.get("evidence_class") or "local_readiness"
        ),
        "proposal_branch": str(publication.get("proposal_branch") or ""),
        "next_publication_action": str(publication.get("next_action") or ""),
    }
    publish_next_action = _publish_next_action(verdict=local_verdict, publication=publication)
    # Read-only tracking synchronization observes an existing remote ref; it never
    # upgrades this no-push command into an executed publication transition.
    publication_verdict: Verdict = "block" if local_verdict == "block" else "unknown"
    result_verdict = publication_verdict if options.apply else local_verdict
    publish_expected_state = _publish_expected_state(
        repo=repo,
        branch=str(branch),
        current_head=current_head,
        publication=publication,
        remote_observations=remote_observations,
        branch_admissions=branch_admissions,
    )
    publish_decision = admission_decision(
        subject=MutationSubject(
            action="remote.publish",
            resource=str(publish_expected_state["target_ref"]),
            expected_state=publish_expected_state,
        ),
        verdict=publication_verdict,
        basis=DecisionBasis(
            enforcement_boundary="remote_ref_transition",
            identity_basis="not_evaluated",
            state_bindings=tuple(publish_expected_state),
            evidence_boundary="local_readiness_and_remote_availability",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref="commitment:publish-admission",
        required_gaps=gaps,
        why=(str(publication.get("remote_state") or "remote_publication_deferred"),),
        next_action=publish_next_action,
    )
    result = EthosResult(
        command="publish",
        verdict=result_verdict,
        state=(
            "local_publish_ready"
            if local_verdict == "pass" and not options.apply
            else "publication_deferred"
            if local_verdict == "pass" and options.apply
            else "blocked"
            if local_verdict == "block"
            else "unknown"
        ),
        summary=publish_summary,
        required_gaps=gaps,
        next_action=publish_next_action,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "release_root_open_spec": {
                "required_gaps": list(release_carrier_gaps),
                "blocking": bool(release_carrier_gaps),
            },
            "independent_verification": independent_verification,
            "remote_push": remote_push,
            "remote_matrix": remote_matrix,
            "remote_topology": remote_topology,
            "publication_branch_admissions": branch_admissions,
            "remote_observations": remote_observations,
            "local_ci_fallback": local_ci_fallback,
            "publication": publication,
            "mutation": mutation_envelope(
                command="publish",
                apply=options.apply,
                authorized=options.authorize,
                expect_head=options.expect_head,
                decision=publish_decision,
            ),
        },
    )
    emit(result, json_output=json_output, enforce=options.apply)

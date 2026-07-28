"""Root land and publish lifecycle commands."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
import ethos.domain.land.closeout as land_core
import ethos.domain.land.publication as land_publication
from ethos.adapters.admission.control.replacement import control_replacement_report
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.landing import apply_candidate_to_accepted
from ethos.adapters.mutation.landing import apply_land_to_candidate
from ethos.adapters.mutation.landing import candidate_base_report
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_readiness_report
from ethos.adapters.openspec.profile import active_change_names
from ethos.adapters.openspec.profile import completed_active_changes_report
from ethos.adapters.openspec.profile import protected_branch_active_change_required_gaps
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import MutationAdmissionRequest
from ethos.contracts.lifecycle.reducer import TransitionDecision
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import context_for_root
from ethos.repository.context import is_product_root
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.output import emit_invalid_adopter_profile
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@dataclass(frozen=True, slots=True)
class _CloseoutPayload:
    repo: Path
    mutation: TransitionRequest
    decision: TransitionDecision
    current_head: str
    audit_root: Path
    audit: dict[str, Any]
    lifecycle: dict[str, Any]
    update: dict[str, object]
    gaps: tuple[str, ...]
    ok: bool
    control_replacement: dict[str, object]


@dataclass(frozen=True, slots=True)
class _LandOptions:
    """CLI options for `ethos land`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    closeout: bool = False
    independent_verification_receipt: Annotated[
        Path | None, Parameter(name="--independent-verification-receipt")
    ] = None


@dataclass(frozen=True, slots=True)
class _PublishOptions:
    """CLI options for `ethos publish`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    probe_remote: Annotated[bool, Parameter(name="--probe-remote")] = False
    remote: Annotated[str | None, Parameter(name="--remote")] = None


_DEFAULT_LAND_OPTIONS = _LandOptions()
_DEFAULT_PUBLISH_OPTIONS = _PublishOptions()


def _gap_tuple(payload: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(string_sequence(payload.get("required_gaps")))


def _first_string(value: object) -> str:
    return next(iter(string_sequence(value)), "")


def _int_value(value: object, *, default: int = 0) -> int:
    """Return an integer from a JSON scalar without trusting arbitrary objects."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _closeout_result(payload: _CloseoutPayload) -> EthosResult:
    mutation_next_actions = land_core.closeout_next_actions(
        ok=payload.ok,
        gaps=payload.gaps,
        current_head=git.current_head(payload.repo),
        state=payload.decision.state,
    )
    return EthosResult(
        command="land",
        ok=payload.ok,
        state=(
            "accepted_current"
            if payload.ok and payload.decision.state == "current"
            else "ready_to_closeout"
            if payload.ok and not payload.mutation.apply
            else "deferred"
            if payload.control_replacement.get("verdict") == "defer"
            else "blocked"
            if payload.gaps
            else str(payload.update.get("state") or payload.mutation.command)
        ),
        required_gaps=payload.gaps,
        next_actions=mutation_next_actions,
        governance_context=context_for_root(payload.audit_root),
        data={
            "repository_audit": payload.audit,
            "openspec_lifecycle": payload.lifecycle,
            "accepted_update": payload.update,
            "control_replacement": payload.control_replacement,
            "closeout_bootstrap": land_core.closeout_bootstrap_package(
                repo=payload.repo, audit_root=payload.audit_root, required_gaps=payload.gaps
            ),
            "mutation": mutation_envelope(
                payload.mutation,
                MutationAdmissionRequest(
                    action="accepted.advance",
                    resource=(
                        f"refs/heads/{load_branch_role_policy(payload.repo).accepted_branch}"
                    ),
                    expected_state=_closeout_expected_state(payload),
                    verdict=(
                        "allow"
                        if payload.ok
                        else "defer"
                        if payload.control_replacement.get("verdict") == "defer"
                        else "block"
                    ),
                    required_gaps=payload.gaps,
                    why=(
                        ("candidate_already_current",)
                        if payload.ok and payload.decision.state == "current"
                        else ()
                    ),
                    next_actions=mutation_next_actions,
                    state=payload.decision.state,
                ),
            ),
        },
    )


def _publish_next_actions(*, ok: bool, publication: dict[str, object]) -> tuple[str, ...]:
    """Return top-level publish actions without hiding publication work."""
    if not ok:
        return ("ethos land --json",)

    actions = string_sequence(publication.get("next_actions"))
    actions.append("ethos status")
    return tuple(dict.fromkeys(actions))


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
        "lease_epoch": _int_value(closeout_support.get("lease_epoch")),
        "lease_expected_head": str(closeout_support.get("lease_expected_head") or ""),
        "lease_expires_at": str(closeout_support.get("lease_expires_at") or ""),
        "lease_payload_sha256": str(closeout_support.get("lease_payload_sha256") or ""),
    }


def _closeout_expected_state(payload: _CloseoutPayload) -> dict[str, object]:
    policy = load_branch_role_policy(payload.repo)
    status_payload = workspace_status(payload.repo, include_foreign_path_scope=False)
    candidate = string_mapping(status_payload.get("candidate"))
    return {
        "root": payload.repo.resolve().as_posix(),
        "accepted_ref": f"refs/heads/{policy.accepted_branch}",
        "accepted_head": payload.current_head,
        "candidate_ref": f"refs/heads/{policy.candidate_branch}",
        "candidate_head": str(candidate.get("head") or ""),
    }


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
    branch_admission: Mapping[str, object],
) -> dict[str, object]:
    target_branch = str(publication.get("proposal_branch") or branch)
    observations = {key: _object_mapping(value) for key, value in remote_observations.items()}
    primary = observations.get("gitlab", {})
    availability = _object_mapping(primary.get("availability"))
    sync = _object_mapping(primary.get("sync"))
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
        "remote": str(availability.get("remote") or ""),
        "observed_remote_ref": str(sync.get("remote_ref") or ""),
        "observed_remote_head": str(sync.get("remote_head") or ""),
        "remote_availability_state": str(availability.get("state") or "not_probed"),
        "remote_sync_state": str(sync.get("state") or "not_checked"),
        "remote_targets": targets,
        "branch_admission": dict(branch_admission),
    }


def _remote_observations(
    *, repo: Path, branch: str, gitlab_remote: str, github_remote: str, probe_remote: bool
) -> dict[str, dict[str, object]]:
    """Read declared remote targets independently without pushing."""
    availability = git.remote_availability if probe_remote else git.remote_availability_not_probed
    return {
        key: {
            "availability": availability(repo, remote),
            "sync": git.remote_tracking_sync(repo, branch, remote),
        }
        for key, remote in {"gitlab": gitlab_remote, "github": github_remote}.items()
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
        return {"verdict": "defer", "required_gaps": list(gaps)}, gaps
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
    request: TransitionRequest,
    current_head: str,
    independent_verification_receipt: Path | None,
) -> EthosResult:
    """Evaluate candidate-to-accepted closeout as one semantic transition."""
    decision = evaluate_closeout_mutation(request, root=repo, current_head=current_head)
    audit_root = land_core.closeout_audit_root(repo, decision)
    audited_candidate_head = _observed_candidate_head(repo, current_head)
    audit = land_core.repository_audit_after_admission(audit_root, decision)
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
        + decision.gaps
        + tuple(string_sequence(lifecycle.get("required_gaps")))
        + control_gaps
    )
    ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"]) and not control_gaps
    update: dict[str, object] = {}
    if ok and request.apply:
        control_replacement, fresh_control_gaps = _stable_control_replacement(
            repo=repo,
            audit_root=audit_root,
            accepted_head=current_head,
            candidate_head=audited_candidate_head,
            independent_verification_receipt=independent_verification_receipt,
        )
        gaps = (*gaps, *fresh_control_gaps)
        ok = not fresh_control_gaps
    if ok and request.apply:
        update = apply_candidate_to_accepted(
            root=repo,
            authorized=request.authorized,
            expect_head=request.expect_head,
            candidate_head=audited_candidate_head,
        )
        gaps = gaps + tuple(string_sequence(update.get("required_gaps")))
        ok = bool(update["ok"])
    return _closeout_result(
        _CloseoutPayload(
            repo=repo,
            mutation=request,
            decision=decision,
            audit_root=audit_root,
            audit=audit,
            lifecycle=lifecycle,
            update=update,
            gaps=gaps,
            ok=ok,
            current_head=current_head,
            control_replacement=control_replacement,
        )
    )


def _candidate_land_result(
    *, repo: Path, request: TransitionRequest, current_head: str
) -> EthosResult:
    """Evaluate work-lane integration into the configured candidate role."""
    governance = context_for_root(repo)
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    closeout_support = string_mapping(status_payload.get("closeout_support"))
    closeout_gaps: tuple[str, ...] = ()
    if status_payload.get("role") == "work_lane" and not closeout_support.get("supported"):
        closeout_gaps = tuple(string_sequence(closeout_support.get("required_gaps")))
    decision = evaluate_mutation(
        request,
        root=repo,
        current_head=current_head,
        status=None if request.apply else status_payload,
    )
    audit = land_core.repository_audit_after_admission(repo, decision)
    lifecycle = completed_active_changes_report(repo)
    archive_gaps = tuple(
        f"openspec_active_change_unarchived:{name}:work_lane"
        for name in active_change_names(repo / "openspec")
    )
    gaps = (
        tuple(string_sequence(audit.get("required_gaps")))
        + decision.gaps
        + closeout_gaps
        + tuple(string_sequence(lifecycle.get("required_gaps")))
        + archive_gaps
    )
    ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"]) and not closeout_gaps
    update: dict[str, object] = {}
    if ok and not archive_gaps and request.apply:
        update = apply_land_to_candidate(
            root=repo,
            authorized=request.authorized,
            expect_head=request.expect_head,
            admitted_decision=decision,
        )
        gaps = gaps + tuple(string_sequence(update.get("required_gaps")))
        ok = bool(update["ok"])
    elif ok and not archive_gaps:
        update = candidate_base_report(root=repo, status=status_payload)
        if not update["ok"]:
            gaps = gaps + tuple(string_sequence(update.get("required_gaps")))
            ok = False
    proof_readiness: dict[str, object] = {}
    if ok and not archive_gaps and not request.apply:
        proof_readiness = proof_readiness_report(repo, current_head)
        gaps = gaps + tuple(string_sequence(proof_readiness.get("required_gaps")))
        ok = not bool(proof_readiness["blocking"])
    ok = ok and not gaps
    state = (
        "ready_to_land"
        if ok and not request.apply
        else "blocked"
        if gaps
        else str(update.get("state") or decision.state)
    )
    mutation_next_actions = land_core.land_next_actions(ok=ok, gaps=gaps, current_head=current_head)
    return EthosResult(
        command="land",
        ok=ok,
        state=state,
        required_gaps=gaps,
        next_actions=mutation_next_actions,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "candidate_update": update,
            "closeout_support": closeout_support,
            "proof_readiness": proof_readiness,
            "mutation": mutation_envelope(
                request,
                MutationAdmissionRequest(
                    action="candidate.integrate",
                    resource=f"refs/heads/{load_branch_role_policy(repo).candidate_branch}",
                    expected_state=_land_expected_state(
                        repo=repo,
                        current_head=current_head,
                        status_payload=status_payload,
                        closeout_support=closeout_support,
                    ),
                    verdict="allow" if ok else "block",
                    required_gaps=gaps,
                    next_actions=mutation_next_actions,
                    state=state,
                ),
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
    if not is_product_root(repo) and profile.state == "invalid":
        emit_invalid_adopter_profile(
            command="land",
            json_output=json_output,
            enforce=options.apply,
        )
        return
    current_head = git.current_head(repo)
    request = TransitionRequest(
        command="closeout" if options.closeout else "land",
        apply=options.apply,
        authorized=options.authorize,
        expect_head=options.expect_head,
    )
    result = (
        _closeout_land_result(
            repo=repo,
            request=request,
            current_head=current_head,
            independent_verification_receipt=options.independent_verification_receipt,
        )
        if options.closeout
        else _candidate_land_result(repo=repo, request=request, current_head=current_head)
    )
    emit(result, json_output=json_output, enforce=options.apply)


@app.command
def publish(
    options: Annotated[_PublishOptions, Parameter(name="*")] = _DEFAULT_PUBLISH_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    repo = resolve_root(root)
    governance = context_for_root(repo)
    current_head = git.current_head(repo)
    decision = evaluate_mutation(
        TransitionRequest(
            command="publish",
            apply=options.apply,
            authorized=options.authorize,
            expect_head=options.expect_head,
        ),
        root=repo,
        current_head=current_head,
    )
    audit = land_core.repository_audit_after_admission(repo, decision)
    independent_verification = independent_verification_admission_report(
        root=repo,
        action="publish",
        request=independent_verification_request(root=repo, action="publish"),
    )
    branch = workspace_status(repo, include_foreign_path_scope=False)["branch"]
    release_carrier_gaps = tuple(
        protected_branch_active_change_required_gaps(repo, current_branch=str(branch))
    )
    terminal_gaps = tuple(proof_gaps(repo, current_head))
    gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + decision.gaps
            + release_carrier_gaps
            + tuple(string_sequence(independent_verification.get("required_gaps")))
            + terminal_gaps
        )
    )
    ok = (
        bool(audit["ok"])
        and decision.ok
        and not release_carrier_gaps
        and bool(independent_verification.get("ok"))
        and not terminal_gaps
    )
    remote_topology = publication_topology(release_config(repo))
    raw_topology_gaps = remote_topology.get("required_gaps", [])
    topology_gaps = (
        tuple(str(gap) for gap in raw_topology_gaps) if isinstance(raw_topology_gaps, list) else ()
    )
    gaps = tuple(dict.fromkeys((*gaps, *topology_gaps)))
    ok = ok and not topology_gaps
    policy = load_branch_role_policy(repo)
    configured_remotes = topology_remotes(remote_topology)
    gitlab_remote = configured_remotes["gitlab"]
    github_remote = configured_remotes["github"]
    branch_admission = publication_branch_admission(
        remote_topology,
        branch=str(branch),
        candidate_branch=str(getattr(policy, "candidate_branch", "candidate/dev")),
        accepted_branch=str(getattr(policy, "accepted_branch", "dev")),
        release_branch=str(getattr(policy, "release_branch", "main")),
        proposal_branch_prefix=str(getattr(policy, "proposal_branch_prefix", "proposal/")),
        remote_name=options.remote or "origin",
    )
    remote_observations = _remote_observations(
        repo=repo,
        branch=str(branch),
        gitlab_remote=gitlab_remote,
        github_remote=github_remote,
        probe_remote=options.probe_remote,
    )
    gitlab_observation = remote_observations["gitlab"]
    remote_availability = _object_mapping(gitlab_observation.get("availability"))
    remote_sync = _object_mapping(gitlab_observation.get("sync"))
    remote_matrix = git.publication_remote_syncs(repo, str(branch))
    local_ci_fallback = land_publication.local_ci_fallback_package(
        remote_availability=remote_availability, root=repo, current_head=current_head
    )
    publication = land_publication.publication_readiness(
        branch=str(branch),
        local_ok=ok,
        policy=policy,
        remote_availability=remote_availability,
        local_ci_fallback=local_ci_fallback,
        topology=remote_topology,
        remote_observations=remote_observations,
    )
    publication = land_publication.publication_with_remote_matrix(
        publication, remote_matrix, remote_available=bool(remote_availability.get("available"))
    )
    remote_state = str(publication.get("remote_state") or "deferred")
    remote_push = str(publication.get("remote_push") or "not_performed")
    remote_availability_state = str(remote_availability.get("state") or "not_probed")
    publish_summary = {
        "mode": "local_readiness",
        "local_readiness": ok,
        "remote_push": remote_push,
        "remote_publication_state": remote_state,
        "remote_availability_state": remote_availability_state,
        "remote_sync_state": str(remote_sync.get("state") or "not_checked"),
        "remote_reconciliation_state": str(remote_matrix.get("state") or "pending"),
        "gitlab_remote_state": str(remote_availability.get("state") or "not_probed"),
        "github_remote_state": str(
            _object_mapping(remote_observations["github"].get("availability")).get("state")
            or "not_probed"
        ),
        "remote_mutation_allowed": bool(branch_admission.get("remote_mutation_allowed")),
        "remote_ahead": _int_value(remote_sync.get("ahead")),
        "remote_behind": _int_value(remote_sync.get("behind")),
        "hosted_ci_status_claimed": False,
        "independent_verification": str(
            independent_verification.get("evidence_class") or "local_readiness"
        ),
        "proposal_branch": str(publication.get("proposal_branch") or ""),
        "next_publication_action": next(iter(string_sequence(publication.get("next_actions"))), ""),
    }
    publish_next_actions = _publish_next_actions(ok=ok, publication=publication)
    # Read-only tracking synchronization observes an existing remote ref; it never
    # upgrades this no-push command into an executed publication transition.
    publication_verdict = "block" if gaps else "defer"
    transition_ok = ok and (not options.apply or publication_verdict == "allow")
    publish_expected_state = _publish_expected_state(
        repo=repo,
        branch=str(branch),
        current_head=current_head,
        publication=publication,
        remote_observations=remote_observations,
        branch_admission=branch_admission,
    )
    result = EthosResult(
        command="publish",
        ok=transition_ok,
        state=(
            "local_publish_ready"
            if ok and not options.apply
            else "publication_deferred"
            if ok and publication_verdict == "defer"
            else "blocked"
            if gaps
            else decision.state
        ),
        summary=publish_summary,
        required_gaps=gaps,
        next_actions=publish_next_actions,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "release_root_open_spec": {
                "required_gaps": list(release_carrier_gaps),
                "blocking": bool(release_carrier_gaps),
            },
            "independent_verification": independent_verification,
            "remote_push": remote_push,
            "remote_availability": remote_availability,
            "remote_sync": remote_sync,
            "remote_matrix": remote_matrix,
            "remote_topology": remote_topology,
            "publication_branch_admission": branch_admission,
            "remote_observations": remote_observations,
            "local_ci_fallback": local_ci_fallback,
            "publication": publication,
            "mutation": mutation_envelope(
                TransitionRequest(
                    command="publish",
                    apply=options.apply,
                    authorized=options.authorize,
                    expect_head=options.expect_head,
                ),
                MutationAdmissionRequest(
                    action="remote.publish",
                    resource=str(publish_expected_state["target_ref"]),
                    expected_state=publish_expected_state,
                    verdict=publication_verdict,
                    required_gaps=gaps,
                    why=(str(publication.get("remote_state") or "remote_publication_deferred"),),
                    next_actions=publish_next_actions,
                    state=remote_state,
                    evidence_boundary="local_readiness_and_remote_availability",
                    enforcement_boundary="remote_ref_transition",
                ),
            ),
        },
    )
    emit(result, json_output=json_output, enforce=options.apply)

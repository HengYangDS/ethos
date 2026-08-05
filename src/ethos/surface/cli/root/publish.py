"""Root publish readiness command."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.profile import protected_branch_active_change_required_gaps
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import repository_audit_after_admission
from ethos.domain.land.publication import local_ci_fallback_package
from ethos.domain.land.publication import publication_readiness
from ethos.domain.land.publication import publication_with_remote_matrix
from ethos.normalization.coercion import integer
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


@dataclass(frozen=True, slots=True)
class _PublishOptions:
    """CLI options for `ethos publish`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    probe_remote: Annotated[bool, Parameter(name="--probe-remote")] = False
    remote: Annotated[str | None, Parameter(name="--remote")] = None


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
    decision = evaluate_mutation(
        command="publish",
        apply=options.apply,
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
    remote_topology = publication_topology(release_config(repo))
    raw_topology_gaps = remote_topology.get("required_gaps", [])
    topology_gaps = (
        tuple(str(gap) for gap in raw_topology_gaps) if isinstance(raw_topology_gaps, list) else ()
    )
    gaps = tuple(dict.fromkeys((*gaps, *topology_gaps)))
    local_verdict = reduce_verdicts(local_verdict, required_gaps=gaps)
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
    local_ci_fallback = local_ci_fallback_package(
        remote_availability=remote_availability, root=repo, current_head=current_head
    )
    publication = publication_readiness(
        branch=str(branch),
        local_ok=local_verdict == "pass",
        policy=policy,
        remote_availability=remote_availability,
        local_ci_fallback=local_ci_fallback,
        topology=remote_topology,
        remote_observations=remote_observations,
    )
    publication = publication_with_remote_matrix(
        publication, remote_matrix, remote_available=bool(remote_availability.get("available"))
    )
    remote_state = str(publication.get("remote_state") or "deferred")
    remote_push = str(publication.get("remote_push") or "not_performed")
    remote_availability_state = str(remote_availability.get("state") or "not_probed")
    publish_summary = {
        "mode": "local_readiness",
        "local_readiness": local_verdict == "pass",
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
        "remote_ahead": integer(remote_sync.get("ahead")),
        "remote_behind": integer(remote_sync.get("behind")),
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
        branch_admission=branch_admission,
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
            "remote_availability": remote_availability,
            "remote_sync": remote_sync,
            "remote_matrix": remote_matrix,
            "remote_topology": remote_topology,
            "publication_branch_admission": branch_admission,
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

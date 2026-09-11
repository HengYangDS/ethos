"""Observe publication admission and report local readiness without remote effects."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.openspec.profile import protected_branch_active_change_required_gaps
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import repository_audit_after_admission
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import repository_context
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_proof_selection
from ethos.repository.release.publication import publication_ref_admission
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Mapping

LOCAL_CI_FALLBACK_EVIDENCE_PATH = Path("build/evidence/local-ci/fallback.json")


def local_ci_fallback_evidence_status(
    repo: Path,
    *,
    current_head: str,
    command: str,
) -> dict[str, object]:
    """Project whether local-ci fallback evidence is bound to the current HEAD."""
    relative = LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix()
    try:
        payload = json.loads((repo / LOCAL_CI_FALLBACK_EVIDENCE_PATH).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _evidence_status("missing", relative, current_head, command)
    except json.JSONDecodeError:
        return _evidence_status("invalid", relative, current_head, command)
    if not isinstance(payload, dict):
        return _evidence_status("invalid", relative, current_head, command)
    evidence_head = str(payload.get("head") or "")
    evidence_command = str(payload.get("command") or "")
    current = (
        bool(current_head)
        and evidence_head == current_head
        and evidence_command == command
        and report_verdict(payload) == "pass"
    )
    return {
        "state": "current" if current else "stale",
        "path": relative,
        "current_head": current_head,
        "evidence_head": evidence_head,
        "verdict": "pass" if current else "block",
        "command": evidence_command,
        "next_action": (
            "local-ci fallback evidence is current at HEAD"
            if current
            else _fallback_action(command)
        ),
    }


def _evidence_status(state: str, path: str, current_head: str, command: str) -> dict[str, object]:
    """Render a missing or invalid fallback-evidence status."""
    return {
        "state": state,
        "path": path,
        "current_head": current_head,
        "evidence_head": "",
        "verdict": "block",
        "next_action": _fallback_action(command)
        if state in {"missing", "not_checked"}
        else _refresh_action(command),
    }


def local_ci_fallback_package(
    *,
    root: Path | None = None,
    current_head: str = "",
    command: str = "",
) -> dict[str, object]:
    """Describe local fallback evidence without claiming hosted CI success."""
    status = (
        local_ci_fallback_evidence_status(
            root,
            current_head=current_head,
            command=command,
        )
        if root
        else _evidence_status(
            "not_checked",
            LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix(),
            current_head,
            command,
        )
    )
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "boundary": "local-ci evidence; hosted CI status unclaimed",
        "hosted_ci_status_claimed": False,
        "command": command,
        "owner_scripts": local_ci_owner_scripts(root=root, command=command),
        "evidence_status": status,
    }


def local_ci_owner_scripts(*, root: Path | None = None, command: str = "") -> list[str]:
    """Project repository scripts invoked by a repository-local command owner."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return []
    if not argv:
        return []
    script = (root or Path.cwd()) / argv[0]
    if script.is_file():
        return list(
            dict.fromkeys(
                re.findall(
                    r"tools/ci/scripts/[A-Za-z0-9_.-]+\.sh",
                    script.read_text(encoding="utf-8"),
                )
            )
        )
    return []


def publication_readiness(
    *, branch: str, local_ok: bool, policy: BranchRolePolicy, **options: object
) -> dict[str, object]:
    """Assemble local readiness and independent no-push remote observations."""
    local_ci_fallback = options.get("local_ci_fallback")
    topology = options.get("topology")
    remote_observations = options.get("remote_observations")
    observations = {key: _object(value) for key, value in _object(remote_observations).items()}
    fallback = (
        local_ci_fallback
        if isinstance(local_ci_fallback, dict)
        else local_ci_fallback_package(command=str(options.get("local_verification_command") or ""))
    )
    fallback_command = str(
        fallback.get("command") or options.get("local_verification_command") or ""
    )
    available = [
        item
        for item in observations.values()
        if _object(item.get("availability")).get("available") is True
    ]
    synchronized = bool(observations) and all(
        _object(item.get("sync")).get("state") == "synchronized" for item in observations.values()
    )
    state = (
        "local_only"
        if not observations
        else "synchronized"
        if synchronized
        else "targets_available"
        if len(available) == len(observations) and len(observations) > 1
        else "target_available"
        if available
        else "deferred"
    )
    evidence = fallback.get("evidence_status")
    action = (
        "remote tracking ref is synchronized; no push was performed"
        if synchronized
        else "run ethos publish --ref <full-ref> --probe-remote --expect-head <head> --json"
        if available
        else str(evidence.get("next_action") or _fallback_action(fallback_command))
        if isinstance(evidence, dict)
        else _fallback_action(fallback_command)
    )
    return {
        "mode": "local_readiness",
        "source_branch": branch,
        "source_role": policy.role_for_branch(branch),
        "remote_push": "not_performed",
        "remote_state": state,
        "remote_topology": topology if isinstance(topology, dict) else {"state": "unspecified"},
        "remote_observations": observations,
        "fallback_evidence": fallback,
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_action": action if local_ok else "resolve local publish readiness gaps",
    }


def _object(value: object) -> dict[str, object]:
    """Return a JSON-object mapping or an empty observation."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _fallback_action(command: str) -> str:
    return (
        f"run {command} as local fallback evidence"
        if command
        else "declare .ethos/release.toml [publication].local_verification_command"
    )


def _refresh_action(command: str) -> str:
    return (
        f"rerun {command} to refresh local fallback evidence"
        if command
        else _fallback_action(command)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationContext:
    """Invocation-local observed publication inputs; never an authorization receipt."""

    root: Path
    governance: dict[str, object]
    head: str
    branch: str
    role_policy: BranchRolePolicy
    topology: dict[str, object]
    remotes: dict[str, str]
    release_tags: tuple[str, ...]
    ref_admissions: dict[str, dict[str, object]]
    proof_admission: dict[str, object]
    audit: dict[str, object]
    independent_verification: dict[str, object]
    release_carrier_gaps: tuple[str, ...]
    required_gaps: tuple[str, ...]
    verdict: Verdict


def _publish_expected_state(
    context: PublicationContext,
    *,
    remote_observations: Mapping[str, object],
    ref_admissions: Mapping[str, object],
) -> dict[str, object]:
    """Bind no-push observations without inventing a proposal target."""
    observations = {key: _object(value) for key, value in remote_observations.items()}
    targets = [
        {
            "id": key,
            "remote": str(_object(data.get("availability")).get("remote") or ""),
            "availability_state": str(
                _object(data.get("availability")).get("state") or "not_probed"
            ),
            "sync_state": str(_object(data.get("sync")).get("state") or "not_checked"),
            "observed_remote_ref": str(_object(data.get("sync")).get("remote_ref") or ""),
            "observed_remote_head": str(_object(data.get("sync")).get("remote_head") or ""),
        }
        for key, data in observations.items()
    ]
    return {
        "root": context.root.resolve().as_posix(),
        "source_ref": f"refs/heads/{context.branch}",
        "source_head": context.head,
        "target_ref": f"refs/heads/{context.branch}",
        "remote_targets": targets,
        "ref_admissions": dict(ref_admissions),
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


def observe_publication(
    repo: Path,
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    target_refs: tuple[str, ...],
) -> PublicationContext:
    """Observe local admission once for readiness or exact remote publication."""
    governance = repository_context(repo)
    current_head = git.current_head(repo)
    decision = evaluate_mutation(
        command="publish",
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        root=repo,
        current_head=current_head,
    )
    audit = repository_audit_after_admission(repo, decision)
    independent_verification = independent_verification_admission_report(
        root=repo,
        action="publish",
        request=independent_verification_request(root=repo, action="publish"),
    )
    branch = (status_payload := workspace_status(repo, include_foreign_path_scope=False))["branch"]
    release_carrier_gaps = tuple(
        protected_branch_active_change_required_gaps(repo, current_branch=str(branch))
    )
    policy = load_branch_role_policy(repo)
    config = release_config(repo)
    remote_topology = publication_topology(repo, config)
    configured_remotes = topology_remotes(remote_topology)
    protected_refs = config.get("protected_refs")
    raw_tags = protected_refs.get("tags") if isinstance(protected_refs, dict) else ()
    release_tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
    ref_admissions = {
        ref: publication_ref_admission(
            remote_topology,
            policy=policy,
            target_ref=ref,
            release_tags=release_tags,
            remote_name=next(iter(configured_remotes.values()), ""),
        )
        for ref in target_refs
    }
    target_roles = tuple(str(item.get("role") or "other") for item in ref_admissions.values())
    proof_selections = {publication_proof_selection(role) for role in target_roles} or {
        publication_proof_selection(str(status_payload["role"]))
    }
    proof_admission = (
        proof_admission_report(
            repo,
            current_head,
            repository_transition=proof_selections == {"repository_transition"},
        )
        if decision.verdict != "block"
        else {
            "verdict": "block",
            "state": "unavailable",
            "selection": "",
            "attestation": {},
            "required_gaps": [],
            "next_action": "",
        }
    )
    gaps = tuple(
        dict.fromkeys(
            (
                *string_sequence(audit.get("required_gaps")),
                *decision.required_gaps,
                *release_carrier_gaps,
                *string_sequence(independent_verification.get("required_gaps")),
                *string_sequence(proof_admission.get("required_gaps")),
                *string_sequence(remote_topology.get("required_gaps")),
            )
        )
    )
    local_verdict = reduce_verdicts(
        decision.verdict,
        report_verdict(audit),
        report_verdict(independent_verification),
        required_gaps=gaps,
    )
    return PublicationContext(
        root=repo,
        governance=governance,
        head=current_head,
        branch=str(branch),
        role_policy=policy,
        topology=remote_topology,
        remotes=configured_remotes,
        release_tags=release_tags,
        ref_admissions=ref_admissions,
        proof_admission=proof_admission,
        audit=audit,
        independent_verification=independent_verification,
        release_carrier_gaps=release_carrier_gaps,
        required_gaps=gaps,
        verdict=local_verdict,
    )


def publication_readiness_result(
    context: PublicationContext,
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    probe_remote: bool,
) -> EthosResult:
    """Return the complete no-push readiness result for any thin transport."""
    repo, branch, current_head = context.root, context.branch, context.head
    policy, remote_topology, configured_remotes = (
        context.role_policy,
        context.topology,
        context.remotes,
    )
    release_tags, local_verdict, gaps = context.release_tags, context.verdict, context.required_gaps
    audit, independent_verification = context.audit, context.independent_verification
    release_carrier_gaps, governance = context.release_carrier_gaps, context.governance
    local_verification_command = str(
        _object(remote_topology.get("local")).get("verification_command") or ""
    )
    ref_admissions = {
        peer_id: publication_ref_admission(
            remote_topology,
            policy=policy,
            target_ref=f"refs/heads/{branch}",
            release_tags=release_tags,
            remote_name=remote,
        )
        for peer_id, remote in configured_remotes.items()
    }
    remote_observations = _remote_observations(
        repo=repo,
        branch=str(branch),
        remotes=configured_remotes,
        probe_remote=probe_remote,
    )
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
    remote_push = str(publication.get("remote_push") or "not_performed")
    publish_summary = {
        "mode": "local_readiness",
        "local_readiness": local_verdict == "pass",
        "remote_push": remote_push,
        "remote_publication_state": str(publication.get("remote_state") or "deferred"),
        "remote_states": {
            key: str(_object(value.get("availability")).get("state") or "not_probed")
            for key, value in remote_observations.items()
        },
        "remote_sync_states": {
            key: str(_object(value.get("sync")).get("state") or "not_checked")
            for key, value in remote_observations.items()
        },
        "remote_mutation_allowed": all(
            admission.get("remote_mutation_allowed") is True
            for admission in ref_admissions.values()
        ),
        "hosted_ci_status_claimed": False,
        "independent_verification": str(
            independent_verification.get("evidence_class") or "local_readiness"
        ),
        "next_publication_action": str(publication.get("next_action") or ""),
    }
    publish_next_action = (
        str(publication.get("next_action") or "")
        if local_verdict == "pass"
        else "ethos land --json"
    )
    # Read-only tracking synchronization observes an existing remote ref; it never
    # upgrades this no-push command into an executed publication transition.
    publication_verdict: Verdict = "block" if local_verdict == "block" else "unknown"
    publish_expected_state = _publish_expected_state(
        context,
        remote_observations=remote_observations,
        ref_admissions=ref_admissions,
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
    return EthosResult(
        command="publish",
        verdict=publication_verdict if apply else local_verdict,
        state=(
            "local_publish_ready"
            if local_verdict == "pass" and not apply
            else "publication_deferred"
            if local_verdict == "pass" and apply
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
            "remote_topology": remote_topology,
            "publication_ref_admissions": ref_admissions,
            "remote_observations": remote_observations,
            "local_ci_fallback": local_ci_fallback,
            "publication": publication,
            "mutation": mutation_envelope(
                command="publish",
                apply=apply,
                authorized=authorized,
                expect_head=expect_head,
                decision=publish_decision,
            ),
        },
    )

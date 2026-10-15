"""Observe invocation-local publication facts and source admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.admission.publication import publication_proof_admission
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.repo.commit.integration import peer_publication_baseline
from ethos.adapters.repo.release import release_publication_head
from ethos.adapters.repo.status.workspace import workspace_status
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
from ethos.repository.release.publication import select_publication_peers
from ethos.repository.release.publication import topology_remotes

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationContext:
    """Invocation-local observed publication inputs; never an authorization receipt."""

    root: Path
    governance: dict[str, object]
    head: str
    proof_head: str
    branch: str
    role_policy: BranchRolePolicy
    topology: dict[str, object]
    remotes: dict[str, str]
    release_tags: tuple[str, ...]
    ref_admissions: dict[str, dict[str, object]]
    proof_admission: dict[str, object]
    audit: dict[str, object]
    independent_verification: dict[str, object]
    required_gaps: tuple[str, ...]
    verdict: Verdict


def observe_publication(
    repo: Path,
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    target_refs: tuple[str, ...],
    peer_ids: tuple[str, ...] = (),
    retire: bool = False,
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
    independent_verification = independent_verification_admission_report(
        root=repo,
        action="publish",
        request=independent_verification_request(root=repo, action="publish"),
    )
    branch = (status_payload := workspace_status(repo, include_foreign_path_scope=False))["branch"]
    policy = load_branch_role_policy(repo)
    config = release_config(repo)
    remote_topology = publication_topology(repo, config)
    configured_remotes = topology_remotes(remote_topology)
    protected = config.get("protected_refs")
    release_tags = tuple(
        string_sequence(protected.get("tags") if isinstance(protected, dict) else None)
    )
    ref_admissions = {
        ref: publication_ref_admission(
            remote_topology,
            policy=policy,
            target_ref=ref,
            release_tags=release_tags,
            remote_name=next(iter(configured_remotes.values()), ""),
            retire=retire,
        )
        for ref in target_refs
    }
    selected_remotes, _ = select_publication_peers(configured_remotes, peer_ids)
    for ref, admission in ref_admissions.items():
        if not ref.startswith("refs/tags/") or not selected_remotes:
            continue
        peer_roles = tuple(
            peer_publication_baseline(repo, target_ref=ref, remote_name=remote)[1]
            for remote in selected_remotes.values()
        )
        role = (
            "object_transport"
            if all(role == "object_transport" for role in peer_roles)
            else "release_publication"
            if "release_publication" in peer_roles or admission["role"] == "release_publication"
            else "other"
        )
        admission.update(role=role, proof_selection=publication_proof_selection(role))
        if role == "object_transport":
            admission["remote_mutation_allowed"] = not remote_topology.get("required_gaps")
    proof_head = current_head
    source_gaps: list[str] = []
    release_refs = tuple(
        ref
        for ref, admission in ref_admissions.items()
        if ref.startswith("refs/tags/") and admission["role"] == "release_publication"
    )
    if release_refs:
        try:
            selected_heads = {
                release_publication_head(repo, ref=ref, new=git.ref_head(repo, ref))
                for ref in release_refs
            }
            if len(selected_heads) == 1 and len(release_refs) == len(target_refs):
                proof_head = selected_heads.pop()
            else:
                source_gaps.append("publication_source_head_ambiguous")
        except (OSError, ValueError) as error:
            source_gaps.append(str(error))
    target_roles = tuple(str(item.get("role") or "other") for item in ref_admissions.values())
    review_only = bool(ref_admissions) and all(
        item["proof_selection"] == "review_object" for item in ref_admissions.values()
    )
    audit = (
        {"verdict": "pass", "state": "review_object", "required_gaps": []}
        if review_only
        else repository_audit_after_admission(repo, decision)
    )
    proof_admission = (
        publication_proof_admission(
            repo, proof_head, target_roles or (str(status_payload["role"]),)
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
                *source_gaps,
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
        proof_head=proof_head,
        branch=str(branch),
        role_policy=policy,
        topology=remote_topology,
        remotes=configured_remotes,
        release_tags=release_tags,
        ref_admissions=ref_admissions,
        proof_admission=proof_admission,
        audit=audit,
        independent_verification=independent_verification,
        required_gaps=gaps,
        verdict=local_verdict,
    )

"""Admit exact review and accepted ref updates through shared Git observations."""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from dataclasses import asdict
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.ref_move_policy import accepted_advance_gaps
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.mutation.proof_admission import unavailable_proof_admission
from ethos.adapters.mutation.publication.retirement import proposal_retirement_report
from ethos.adapters.openspec.observation import active_change_names_in_ref
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.release import accepted_delivery_report
from ethos.adapters.repo.release import publication_source_baseline
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_release_text
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.configuration import release_config
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.configuration import release_role_policy_gaps
from ethos.repository.release.publication import publication_proof_selection
from ethos.repository.release.publication import publication_ref_admission
from ethos.repository.release.publication import publication_ref_role
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import publication_transport_tags

if TYPE_CHECKING:
    from pathlib import Path

_ZERO_OIDS = {"0" * 40, "0" * 64}
_POLICY_PATHS = (".ethos/workspace.toml", ".ethos/release.toml")


def _committed_target_policy(
    root: Path, revision: str
) -> tuple[BranchRolePolicy, tuple[str, ...], tuple[str, ...], list[str]]:
    """Read exact prior declarations without substituting mutable checkout bytes."""
    listed = run_git(
        root,
        "ls-tree",
        "-z",
        revision,
        "--",
        *_POLICY_PATHS,
        text=False,
        check=False,
        observation=True,
    )
    if listed.returncode:
        message = f"publication_policy_unreadable:{revision}"
        raise ValueError(message)
    entries: dict[str, str] = {}
    for record in filter(None, listed.stdout.split(b"\0")):
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            message = f"publication_policy_invalid:{path.decode()}"
            raise ValueError(message)
        entries[path.decode()] = oid.decode("ascii")
    texts = dict(
        zip(entries, (b.decode() for b in read_objects(root, tuple(entries.values()))), strict=True)
    )
    release_text = texts.get(_POLICY_PATHS[1], "")
    policy = strict_branch_role_policy_from_release_text(release_text)
    release = release_config_from_text(release_text)
    protected = release.get("protected_refs", {})
    return (
        policy,
        tuple(protected.get("tags", [])),
        publication_transport_tags(release),
        release_role_policy_gaps(release, policy),
    )


def ref_update_admission_report(
    root: Path,
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    trusted_baseline: str = "",
) -> dict[str, object]:
    """Observe exact ref obligations without accepting a caller-supplied policy override."""
    report, _policy = _ref_update_admission(
        root,
        target_ref=target_ref,
        proposed_head=proposed_head,
        remote_head=remote_head,
        remote_name=remote_name,
        trusted_baseline=trusted_baseline,
    )
    return report


def _ref_update_admission(
    root: Path,
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    trusted_baseline: str = "",
    trusted_baseline_source: str = "",
    accepted_policy_ref: str = "",
    accepted_content: bool = False,
    accepted_source: Mapping[str, object] | None = None,
) -> tuple[dict[str, object], BranchRolePolicy]:
    """Observe destination role, introduced commits and exact OpenSpec tree obligations."""
    if accepted_content:
        commits = accepted_delivery_report(
            root,
            head=accepted_policy_ref,
            proposed=proposed_head,
            target=target_ref,
            remote_head=remote_head,
            remote=remote_name,
            source=accepted_source,
        )
    else:
        commits = commit_range_admission_report(
            root,
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            trusted_baseline=trusted_baseline,
            trusted_baseline_source=trusted_baseline_source,
        )
    local_gaps: list[str] = []
    proposed = str(commits.get("proposed_commit") or "")
    policy_ref = str(commits.get("policy_ref") or commits.get("baseline_commit") or "")
    if commits.get("update_kind") == "delete":
        policy_ref = remote_head
    policy_ref = accepted_policy_ref or policy_ref
    policy, tags, transport_tags = BranchRolePolicy(), (), ()
    policy_known = False
    if policy_ref:
        try:
            policy, tags, transport_tags, _ = _committed_target_policy(root, policy_ref)
            policy_known = True
        except (OSError, UnicodeError, ValueError) as error:
            local_gaps.append(f"publication_policy_invalid:{policy_ref}:{error}")
    if proposed:
        try:
            local_gaps.extend(_committed_target_policy(root, proposed)[-1])
        except (OSError, UnicodeError, ValueError) as error:
            local_gaps.append(f"publication_policy_invalid:{proposed}:{error}")
    ref_valid = (
        run_git(root, "check-ref-format", target_ref, check=False, observation=True).returncode == 0
    )
    if not ref_valid:
        local_gaps.append(f"publication_target_ref_invalid:{target_ref}")
    kind, role, allowed = publication_ref_role(policy, target_ref, tags, transport_tags)
    if policy_known and not allowed:
        local_gaps.append(f"publication_ref_unavailable:{kind}:{role}:{target_ref}")
    intent: dict[str, object] = {"verdict": "pass", "changes": [], "required_gaps": []}
    if proposed:
        intent = active_change_names_in_ref(root, proposed)
    gaps = list(
        dict.fromkeys(
            (
                *string_sequence(commits.get("required_gaps")),
                *local_gaps,
                *string_sequence(intent.get("required_gaps")),
            )
        )
    )
    verdict = reduce_verdicts(
        report_verdict(commits),
        report_verdict(intent),
        "block" if local_gaps else "pass",
        required_gaps=tuple(gaps),
    )
    report = {
        "verdict": verdict,
        "state": "observed"
        if verdict == "pass"
        else "unknown"
        if verdict == "unknown"
        else "blocked",
        "target_ref": target_ref,
        "target_branch": target_ref.removeprefix("refs/heads/") if kind == "branch" else "",
        "proposed_head": proposed_head,
        "proposed_commit": proposed,
        "remote_head": remote_head,
        "remote_name": remote_name,
        "ref_kind": kind,
        "role": role,
        "policy_ref": policy_ref,
        "role_policy": asdict(policy),
        "release_tags": tags,
        "transport_tags": transport_tags,
        "commit_policy_admission": commits,
        "openspec": intent,
        "required_gaps": gaps,
        "satisfies_repository_proof": False,
        "mints_authority": False,
    }
    boundary, why, action = _ref_update_continuation(
        report,
        ref_valid=ref_valid,
        policy_known=policy_known,
        role_allowed=allowed,
    )
    return {
        **report,
        "boundary": boundary,
        "why": why,
        "next_action": shlex.join(("git", "-C", str(root), *action)) if action else "",
    }, policy


def _ref_update_continuation(
    report: Mapping[str, object], *, ref_valid: bool, policy_known: bool, role_allowed: bool
) -> tuple[str, str, tuple[str, ...]]:
    """Select one read-only diagnostic at the first unsatisfied semantic boundary."""
    if report["verdict"] == "pass":
        return (
            "ref_observation",
            "Exact destination obligations are satisfied; no effect is authorized.",
            (),
        )
    target, proposed = str(report["target_ref"]), str(report["proposed_head"])
    commits = cast("Mapping[str, object]", report["commit_policy_admission"])
    if not ref_valid or (
        not commits.get("proposed_commit") and commits.get("update_kind") != "delete"
    ):
        return (
            (
                "target_ref",
                "The destination must be a complete native Git ref.",
                ("check-ref-format", target),
            )
            if not ref_valid
            else (
                "proposed_object",
                "Read the exact proposed object; do not substitute HEAD.",
                ("cat-file", "-t", proposed),
            )
        )
    if not report["policy_ref"] or not policy_known or not role_allowed:
        return (
            (
                "prior_object",
                "Observe the previous ref or select a trusted new-ref baseline.",
                ("ls-remote", str(report["remote_name"])),
            )
            if not report["policy_ref"]
            else (
                "destination_policy",
                "Inspect the exact prior policy before changing the request.",
                ("show", f"{report['policy_ref']}:{_POLICY_PATHS[0]}"),
            )
        )
    intent = cast("Mapping[str, object]", report["openspec"])
    if report_verdict(intent) != "pass":
        return (
            "intent_observation",
            "Required intent-tree facts are unavailable, not an acceptance failure.",
            ("ls-tree", "-r", proposed, "--", "openspec/changes"),
        )
    return (
        "introduced_commits",
        "Inspect only the introduced range under its declared commit policy.",
        ("log", "--format=fuller", f"{commits['baseline_commit']}..{proposed}"),
    )


def publication_proof_admission(
    root: Path,
    head: str,
    roles: tuple[str, ...],
    *,
    observed: object = None,
    attestation_id: str = "",
) -> dict[str, object]:
    """Select the strongest actual target obligation without inventing review proof."""
    selections = {publication_proof_selection(role) for role in roles}
    if selections == {"review_object"}:
        return {
            "verdict": "pass",
            "state": "not_required",
            "selection": "review_object",
            "attestation": {},
            "required_gaps": [],
            "next_action": "",
        }
    repository_transition = "repository_transition" in selections
    selection = "repository_transition" if repository_transition else "current_commitment"
    if (
        isinstance(observed, Mapping)
        and observed.get("selection") == selection
        and (
            not attestation_id
            or (
                isinstance(observed.get("attestation"), Mapping)
                and observed["attestation"].get("id") == attestation_id
            )
        )
    ):
        attestation = observed.get("attestation")
        if observed.get("verdict") != "pass" or (
            isinstance(attestation, Mapping) and attestation.get("commit") == head
        ):
            return dict(observed)
    return proof_admission_report(
        root, head, repository_transition=repository_transition, attestation_id=attestation_id
    )


def push_admission_report(
    *,
    root: Path,
    target_ref: str,
    pushed_head: str,
    **options: object,
) -> dict[str, object]:
    """Enforce role-specific publication without requiring local authoring coordination."""
    repo = root.resolve()
    remote_head, remote_name = (
        str(options.get("remote_head") or ""),
        str(options.get("remote_name") or ""),
    )
    if pushed_head in _ZERO_OIDS:
        return proposal_retirement_report(
            repo, target_ref=target_ref, old=remote_head, remote=remote_name
        )
    current_policy = load_branch_role_policy(repo)
    config = release_config(repo)
    topology = publication_topology(repo, config)
    protected = config.get("protected_refs")
    tags = tuple(string_sequence(protected.get("tags"))) if isinstance(protected, dict) else ()
    preliminary = publication_ref_admission(
        topology,
        policy=current_policy,
        target_ref=target_ref,
        release_tags=tags,
        remote_name=remote_name,
    )
    proof_head = (
        git_stdout(repo, "rev-parse", "--verify", f"{pushed_head}^{{commit}}")
        if preliminary["ref_kind"] == "tag"
        else pushed_head
    )
    branch = target_ref.removeprefix("refs/heads/") if target_ref.startswith("refs/heads/") else ""
    closeout, closeout_gaps, baseline, baseline_source, source = publication_source_baseline(
        repo,
        policy=current_policy,
        branch=branch,
        role=str(preliminary["role"]),
        proof_head=proof_head,
        remote_head=remote_head,
        target_ref=target_ref,
        source_oid=pushed_head,
    )
    accepted_content = False
    observed_proof = options.get("proof_admission")
    role = str(preliminary["role"])
    ordinary_accepted = role == "accepted_root" and (
        remote_head in _ZERO_OIDS or is_ancestor(repo, remote_head, proof_head)
    )
    current_accepted = ordinary_accepted and (
        git_stdout(repo, "rev-parse", current_policy.accepted_branch) == proof_head
    )
    if (current_accepted or role in {"release_root", "release_publication"}) and closeout:
        observed_proof = publication_proof_admission(
            repo,
            proof_head,
            (str(preliminary["role"]),),
            observed=observed_proof,
            attestation_id=str(closeout.get("proof_attestation_id") or ""),
        )
        accepted_content = (
            observed_proof["verdict"] == "pass"
            and not closeout_gaps
            and closeout.get("operation") != "release.promote"
        )
    observed, policy = _ref_update_admission(
        repo,
        target_ref=target_ref,
        proposed_head=pushed_head,
        remote_head=remote_head,
        remote_name=remote_name,
        trusted_baseline=baseline,
        trusted_baseline_source=baseline_source,
        accepted_policy_ref=proof_head if closeout else "",
        accepted_content=accepted_content,
        accepted_source=source,
    )
    role = str(observed["role"])
    ref_admission = publication_ref_admission(
        {**topology, "transport_tags": observed["transport_tags"]},
        policy=policy,
        target_ref=target_ref,
        release_tags=tuple(string_sequence(observed["release_tags"])),
        remote_name=remote_name,
    )
    if policy != current_policy or role != str(preliminary["role"]):
        closeout, closeout_gaps, _baseline, _baseline_source, _source = publication_source_baseline(
            repo,
            policy=policy,
            branch=branch,
            role=role,
            proof_head=proof_head,
            remote_head=remote_head,
            target_ref=target_ref,
            source_oid=pushed_head,
        )
    commits = cast("dict[str, object]", observed["commit_policy_admission"])
    proof = (
        unavailable_proof_admission()
        if ref_admission["enforcement_gaps"]
        else publication_proof_admission(
            repo,
            proof_head,
            (role,),
            observed=observed_proof,
            attestation_id=str((closeout or {}).get("proof_attestation_id") or ""),
        )
    )
    proof_gaps = list(string_sequence(proof.get("required_gaps")))
    repaired = commits.get("update_kind") == "repair"
    if role == "accepted_root" and not repaired and not ordinary_accepted:
        proof_gaps = [gap for gap in proof_gaps if gap.startswith("repository_commitment_")]
    topology_gaps = (
        accepted_advance_gaps(
            repo,
            policy,
            old_value=str(commits.get("integration_baseline") or remote_head),
            new_value=pushed_head,
        )
        if role == "accepted_root" and commits.get("state") != "repaired_history"
        else []
    )
    ref_gaps = list(string_sequence(ref_admission.get("enforcement_gaps")))
    gaps = list(
        dict.fromkeys(
            (
                *ref_gaps,
                *string_sequence(observed.get("required_gaps")),
                *proof_gaps,
                *topology_gaps,
                *closeout_gaps,
            )
        )
    )
    reason = (
        "publication_ref_unavailable"
        if ref_gaps
        else "push_to_protected_role_not_proven"
        if proof_gaps or topology_gaps or closeout_gaps
        else "pushed_commit_policy_not_allowed"
        if commits.get("required_gaps")
        else "publication_intent_not_admitted"
        if observed.get("required_gaps")
        else "push_admitted"
    )
    verdict = reduce_verdicts(
        report_verdict(observed),
        "block" if ref_gaps or proof_gaps or topology_gaps or closeout_gaps else "pass",
        required_gaps=tuple(gaps),
    )
    return {
        **observed,
        "verdict": verdict,
        "state": "admitted"
        if verdict == "pass"
        else "unknown"
        if verdict == "unknown"
        else "blocked",
        "hook": "pre-push",
        "pushed_head": pushed_head,
        "target_branch": branch,
        "publication_ref_admission": ref_admission,
        "proof_admission": proof,
        "accepted_closeout_effect": closeout,
        "decision": {"action": "allow" if verdict == "pass" else "block", "reason": reason},
        "required_gaps": gaps,
        "next_action": str(proof.get("next_action") or ""),
    }

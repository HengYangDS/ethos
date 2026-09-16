"""Admit exact review and accepted ref updates through shared Git observations."""

from __future__ import annotations

import shlex
import tomllib
from collections.abc import Mapping
from dataclasses import asdict
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.ref_move_policy import accepted_advance_gaps
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.mutation.publication.retirement import proposal_retirement_report
from ethos.adapters.openspec.observation import active_change_names_in_ref
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import accepted_closeout_attestation
from ethos.adapters.repo.git_object import read_objects
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.plan import git_effect_from_plan
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

if TYPE_CHECKING:
    from pathlib import Path

_ZERO_OIDS = {"0" * 40, "0" * 64}
_POLICY_PATHS = (".ethos/workspace.toml", ".ethos/release.toml")


def _committed_target_policy(
    root: Path, revision: str
) -> tuple[BranchRolePolicy, tuple[str, ...], list[str]]:
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
    workspace = texts.get(_POLICY_PATHS[0], "")
    values = tomllib.loads(workspace)
    policy = (
        strict_branch_role_policy_from_text(workspace)
        if "branch_roles" in values
        else BranchRolePolicy()
    )
    release = release_config_from_text(texts.get(_POLICY_PATHS[1], ""))
    protected = release.get("protected_refs", {})
    return policy, tuple(protected.get("tags", [])), release_role_policy_gaps(release, policy)


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
) -> tuple[dict[str, object], BranchRolePolicy]:
    """Observe destination role, introduced commits and exact OpenSpec tree obligations."""
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
    policy_ref = str(commits.get("baseline_commit") or "")
    if commits.get("update_kind") == "delete":
        policy_ref = remote_head
    policy_ref = accepted_policy_ref or policy_ref
    policy, tags = BranchRolePolicy(), ()
    policy_known = False
    if policy_ref:
        try:
            policy, tags, _prior_role_gaps = _committed_target_policy(root, policy_ref)
            policy_known = True
        except (OSError, UnicodeError, ValueError) as error:
            local_gaps.append(f"publication_policy_invalid:{policy_ref}:{error}")
    if proposed:
        try:
            _proposed_policy, _proposed_tags, role_gaps = _committed_target_policy(root, proposed)
            local_gaps.extend(role_gaps)
        except (OSError, UnicodeError, ValueError) as error:
            local_gaps.append(f"publication_policy_invalid:{proposed}:{error}")
    ref_valid = (
        run_git(root, "check-ref-format", target_ref, check=False, observation=True).returncode == 0
    )
    if not ref_valid:
        local_gaps.append(f"publication_target_ref_invalid:{target_ref}")
    kind, role, allowed = publication_ref_role(policy, target_ref, tags)
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
        "target_branch": target_ref.removeprefix("refs/heads/"),
        "proposed_head": proposed_head,
        "proposed_commit": proposed,
        "remote_head": remote_head,
        "remote_name": remote_name,
        "ref_kind": kind,
        "role": role,
        "policy_ref": policy_ref,
        "role_policy": asdict(policy),
        "release_tags": tags,
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
    return proof_admission_report(
        root,
        head,
        repository_transition="repository_transition" in selections,
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
        str(options.get("remote_name") or "origin"),
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
    closeout, closeout_gaps, baseline, baseline_source = _accepted_closeout_baseline(
        repo,
        policy=current_policy,
        branch=branch,
        role=str(preliminary["role"]),
        proof_head=proof_head,
        remote_head=remote_head,
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
    )
    role = str(observed["role"])
    ref_admission = publication_ref_admission(
        topology,
        policy=policy,
        target_ref=target_ref,
        release_tags=tuple(string_sequence(observed["release_tags"])),
        remote_name=remote_name,
    )
    if policy != current_policy:
        closeout, closeout_gaps, _baseline, _source = _accepted_closeout_baseline(
            repo,
            policy=policy,
            branch=branch,
            role=role,
            proof_head=proof_head,
            remote_head=remote_head,
        )
    commits = cast("dict[str, object]", observed["commit_policy_admission"])
    selection = publication_proof_selection(role)
    supplied = options.get("proof_admission")
    proof = (
        {
            "verdict": "block",
            "state": "unavailable",
            "selection": "",
            "attestation": {},
            "required_gaps": [],
            "next_action": "",
        }
        if ref_admission["enforcement_gaps"]
        else dict(supplied)
        if isinstance(supplied, Mapping) and supplied.get("selection") == selection
        else publication_proof_admission(repo, proof_head, (role,))
    )
    proof_gaps = list(string_sequence(proof.get("required_gaps")))
    repaired = commits.get("update_kind") == "repair"
    if role == "accepted_root" and not repaired:
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


def _accepted_closeout_baseline(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    role: str,
    proof_head: str,
    remote_head: str,
) -> tuple[dict[str, object], list[str], str, str]:
    """Bind protected publication to its accepted effect and initial-range baseline."""
    required = branch == policy.accepted_branch or (
        remote_head in _ZERO_OIDS and publication_proof_selection(role) == "repository_transition"
    )
    if not required:
        return {}, [], "", ""
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    try:
        closeout = accepted_closeout_attestation(
            repo,
            accepted_ref=accepted_ref,
            candidate_ref=f"refs/heads/{policy.candidate_branch}",
            candidate_head=proof_head,
        )
    except ValueError as error:
        return {}, [str(error)], "", ""
    if closeout is None:
        repair = completed_signature_repair(repo, new=proof_head)
        if repair is not None and accepted_ref in cast("Mapping[str, str]", repair["refs"]):
            return (
                {
                    "attestation_id": repair["attestation_id"],
                    "plan_digest": repair["plan_digest"],
                    "accepted_ref": accepted_ref,
                    "accepted_before": repair["old"],
                    "candidate_head": proof_head,
                    "operation": "commit.identity-replace",
                },
                [],
                "",
                "",
            )
        return {}, ["accepted_closeout_effect_not_attested"], "", ""
    plan, attestation = closeout
    accepted_before = git_effect_from_plan(plan).updates[accepted_ref].expected
    projection = {
        "attestation_id": attestation.id,
        "plan_digest": plan.digest,
        "accepted_ref": accepted_ref,
        "accepted_before": accepted_before,
        "remote_head": remote_head,
        "candidate_head": proof_head,
    }
    return (
        (projection, [], "", "")
        if remote_head not in _ZERO_OIDS
        else (projection, [], accepted_before, "accepted_closeout_effect")
    )

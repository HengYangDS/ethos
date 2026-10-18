"""Admit exact Git integration ranges and proven history-repair replacements."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.admission import commit_policy_for_revision
from ethos.adapters.repo.commit.admission import evaluate_commit_policy
from ethos.adapters.repo.commit.admission import peel_commit
from ethos.adapters.repo.commit.provenance import accepted_provenance
from ethos.adapters.repo.commit.provenance import lane_creation_boundary
from ethos.adapters.repo.commit.signature import repaired_peer_ref_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import observe_commits
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_release_text
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.publication import publication_ref_role
from ethos.repository.release.publication import publication_transport_tags

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.policy.commit import CommitPolicy


def commit_range_admission_report(
    root: Path,
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    trusted_baseline: str = "",
    trusted_baseline_source: str = "",
) -> dict[str, object]:
    """Admit exact introduced objects under the trusted base and candidate policies."""
    repo = root.resolve()
    native_zero = zero_oid(repo)
    report = partial(
        _range_report,
        target_ref=target_ref,
        proposed_head=proposed_head,
        remote_head=remote_head,
        remote_name=remote_name,
        update_kind="create" if remote_head == native_zero else "existing",
    )
    if proposed_head == native_zero:
        return report(update_kind="delete", state="no_range")
    proposed_commit = peel_commit(repo, proposed_head)
    if not proposed_commit:
        return report(
            state="blocked", required_gaps=[f"commit_range_proposed_unreadable:{proposed_head}"]
        )
    baseline, baseline_ref, baseline_source, policy_ref, gap = _baseline(
        repo,
        target_ref=target_ref,
        proposed_commit=proposed_commit,
        remote_head=remote_head,
        remote_name=remote_name,
        trusted_baseline=trusted_baseline,
        trusted_baseline_source=trusted_baseline_source,
        native_zero=native_zero,
    )
    report = partial(
        report,
        proposed_commit=proposed_commit,
        baseline_ref=baseline_ref,
        baseline_source=baseline_source,
        baseline_commit=baseline,
        policy_ref=policy_ref or baseline,
    )
    creation = remote_head == native_zero
    remote_prefix = f"refs/remotes/{remote_name}/"
    repair_ref = (
        f"refs/heads/{baseline_ref.removeprefix(remote_prefix)}"
        if creation and baseline_ref.startswith(remote_prefix)
        else baseline_ref
        if creation
        else target_ref
    )
    repair = (
        repaired_peer_ref_provenance(repo, ref=repair_ref, old=baseline, new=proposed_commit)
        if baseline
        and repair_ref.startswith("refs/heads/")
        and not is_ancestor(repo, baseline, proposed_commit)
        else None
    )
    if gap and not (
        repair is not None and gap.startswith("commit_range_trusted_baseline_not_ancestor:")
    ):
        return report(state="blocked", required_gaps=[gap])
    gap = ""
    if repair is not None and repair["new"] == proposed_commit and not creation:
        revisions = tuple(cast("Mapping[str, str]", repair["mapping"]).values())
        return {
            **report(state="repaired_history", update_kind="repair", revisions=revisions),
            "repair_attestation": repair["attestation_id"],
            **(
                {"repair_attestations": repair["attestation_ids"]}
                if "attestation_ids" in repair
                else {}
            ),
            "signature_verification": "verified_native",
        }
    integration_baseline = str(repair["new"]) if repair is not None else baseline
    revisions = _introduced_commit_revisions(
        repo, proposed_commit=proposed_commit, baseline_commit=integration_baseline
    )
    if revisions is None:
        gap = f"commit_range_unreadable:{baseline}:{proposed_commit}"
    incumbent_revision = policy_ref or integration_baseline
    policies, policy_gap = _range_policies(
        repo, proposed_commit=proposed_commit, baseline_commit=incumbent_revision
    )
    if policy_gap or gap:
        return report(state="blocked", required_gaps=[policy_gap or gap])
    assert revisions is not None
    assert policies is not None
    candidate, incumbent = policies
    violations, gaps = _validate_commit_revisions(
        repo, revisions, policies=tuple(dict.fromkeys(policies)), verify_trust=True
    )
    result = report(
        state="blocked" if gaps else "admitted",
        policy=candidate.projection(),
        revisions=revisions,
        violations=violations,
        required_gaps=gaps,
    )
    result["policy_sources"] = {
        incumbent_revision: incumbent.projection(),
        proposed_commit: candidate.projection(),
    }
    result["signature_verification"] = "required_native"
    if repair is not None:
        result.update(
            update_kind="create" if creation else "repair",
            repair_attestation=repair["attestation_id"],
            repair_replacement=repair["new"],
            integration_baseline=integration_baseline,
            **(
                {"repair_attestations": repair["attestation_ids"]}
                if "attestation_ids" in repair
                else {}
            ),
        )
    return result


def _range_policies(
    repo: Path, *, proposed_commit: str, baseline_commit: str
) -> tuple[tuple[CommitPolicy, CommitPolicy] | None, str]:
    """Compile the candidate and incumbent policies, or name the gap that stops admission."""
    try:
        return (
            commit_policy_for_revision(repo, proposed_commit),
            commit_policy_for_revision(repo, baseline_commit),
        ), ""
    except (TypeError, ValueError) as error:
        return None, str(error)


def validate_replayed_commits(
    root: Path,
    *,
    baseline_commit: str,
    proposed_commit: str,
    policy: CommitPolicy,
) -> list[str]:
    """Admit replay against its trusted baseline and explicitly selected policy."""
    policies = tuple(dict.fromkeys((commit_policy_for_revision(root, baseline_commit), policy)))
    revisions = _introduced_commit_revisions(
        root, proposed_commit=proposed_commit, baseline_commit=baseline_commit
    )
    if revisions is None:
        return [f"commit_range_unreadable:{baseline_commit}:{proposed_commit}"]
    return _validate_commit_revisions(root, revisions, policies=policies, verify_trust=True)[1]


def _validate_commit_revisions(
    root: Path,
    revisions: tuple[str, ...],
    *,
    policies: tuple[CommitPolicy, ...],
    verify_trust: bool = False,
) -> tuple[list[dict[str, object]], list[str]]:
    """Observe one exact sequence and enforce the union of its selected policies."""
    observations = tuple(zip(revisions, observe_commits(root, revisions), strict=True))
    reports = [
        (revision, evaluate_commit_policy(policy, observation, revision))
        for policy in policies
        for revision, observation in observations
    ]
    selected = tuple(
        dict.fromkeys(
            revision
            for revision, report in reports
            if verify_trust and not cast("dict[str, object]", report["signature"])["required_gaps"]
        )
    )
    trust = (
        verify_commit_trust(root, selected[0] if len(selected) == 1 else selected)
        if selected
        else {}
    )
    trust_gaps = cast("list[str]", trust.get("required_gaps", []))
    object_gaps = cast("dict[str, list[str]]", trust.get("object_required_gaps", {}))
    verified = set(selected)
    violations: list[dict[str, object]] = []
    gaps: list[str] = []
    for revision, report in reports:
        commit_gaps = cast("list[str]", report["required_gaps"])
        if (
            revision in verified
            and not cast("dict[str, object]", report["signature"])["required_gaps"]
        ):
            commit_gaps.extend(object_gaps.get(revision, []) if object_gaps else trust_gaps)
        subject = str(cast("dict[str, object]", report["head"]).get("subject") or "")
        if commit_gaps:
            violation: dict[str, object] = {
                "commit": revision,
                "subject": subject,
                "required_gaps": commit_gaps,
            }
            if violation not in violations:
                violations.append(violation)
            gaps.extend(gap for gap in commit_gaps if gap not in gaps)
    return violations, gaps


def _baseline(
    root: Path,
    *,
    target_ref: str,
    proposed_commit: str,
    remote_head: str,
    remote_name: str,
    trusted_baseline: str,
    trusted_baseline_source: str,
    native_zero: str,
) -> tuple[str, str, str, str, str]:
    if not trusted_baseline and target_ref.startswith("refs/tags/"):
        peer_ref, role, peer_gap = peer_publication_baseline(
            root, target_ref=target_ref, remote_name=remote_name
        )
        policy_ref = peel_commit(root, peer_ref) if peer_ref else ""
        if peer_gap or (remote_head == native_zero and role != "object_transport"):
            return (
                "",
                peer_ref,
                "declared_remote_accepted_ref",
                policy_ref,
                peer_gap or f"commit_range_trusted_baseline_required:{target_ref}",
            )
        baseline = policy_ref if remote_head == native_zero else peel_commit(root, remote_head)
        return (
            baseline,
            peer_ref,
            "declared_remote_accepted_ref" if remote_head == native_zero else "remote_head",
            policy_ref,
            "" if baseline else f"commit_range_remote_unreadable:{remote_head}",
        )
    if remote_head != native_zero:
        baseline = peel_commit(root, remote_head)
        return (
            baseline,
            "",
            "remote_head",
            "",
            "" if baseline else f"commit_range_remote_unreadable:{remote_head}",
        )
    baseline_ref = trusted_baseline
    baseline_source = trusted_baseline_source or "explicit_trusted_baseline"
    policy = load_branch_role_policy(root)
    branch = target_ref.removeprefix("refs/heads/")
    if not baseline_ref and branch.startswith(policy.proposal_branch_prefix):
        baseline_ref = f"refs/remotes/{remote_name}/{policy.accepted_branch}"
        baseline_source = "declared_remote_accepted_ref"
    baseline = peel_commit(root, baseline_ref) if baseline_ref else ""
    if not baseline:
        return (
            "",
            baseline_ref,
            baseline_source,
            "",
            f"commit_range_trusted_baseline_unreadable:{baseline_ref}"
            if baseline_ref
            else f"commit_range_trusted_baseline_required:{target_ref}",
        )
    gap = ""
    if not is_ancestor(root, baseline, proposed_commit):
        proposal = branch.startswith(policy.proposal_branch_prefix) and not trusted_baseline
        birth = _accepted_lane_birth(root, proposed_commit) if proposal else ""
        if birth:
            return birth, "", "native_lane_birth_accepted_provenance", "", ""
        gap = f"commit_range_trusted_baseline_not_ancestor:{baseline}:{proposed_commit}"
    return baseline, baseline_ref, baseline_source, "", gap


def _accepted_lane_birth(root: Path, proposed_commit: str) -> str:
    """Select a historical lane's own birth only when it was an originally accepted head.

    The native lane.start effect observes where the lane began; the original
    candidate.accept provenance of that exact commit is what makes it a trusted baseline.
    """
    policy = load_branch_role_policy(root)
    try:
        birth = lane_creation_boundary(root, proposed_commit)
        accepted = birth and accepted_provenance(
            root,
            accepted_ref=f"refs/heads/{policy.accepted_branch}",
            candidate_ref=f"refs/heads/{policy.candidate_branch}",
            head=birth,
        )
    except ValueError:
        return ""
    return birth if accepted else ""


def peer_publication_baseline(
    root: Path, *, target_ref: str, remote_name: str
) -> tuple[str, str, str]:
    """Resolve a tag's destination policy from the same peer's accepted root."""
    namespace = f"refs/remotes/{remote_name}/"
    selected = run_git(
        root,
        "symbolic-ref",
        "--quiet",
        f"{namespace}HEAD",
        check=False,
        observation=True,
    )
    root_ref = selected.stdout.strip()
    if selected.returncode or not root_ref.startswith(namespace):
        return "", "other", f"commit_range_trusted_baseline_required:{target_ref}"
    try:
        root_policy = strict_branch_role_policy_from_release_text(
            committed_file_text(root, root_ref, ".ethos/release.toml")
        )
        if root_ref.removeprefix(namespace) not in root_policy.protected_branches:
            return "", "other", f"commit_range_peer_root_not_protected:{root_ref}"
        baseline_ref = f"{namespace}{root_policy.accepted_branch}"
        baseline = peel_commit(root, baseline_ref)
        if not baseline:
            return baseline_ref, "other", f"commit_range_trusted_baseline_unreadable:{baseline_ref}"
        policy = strict_branch_role_policy_from_release_text(
            committed_file_text(root, baseline, ".ethos/release.toml")
        )
        if policy.accepted_branch != root_policy.accepted_branch:
            return "", "other", f"commit_range_peer_accepted_role_mismatch:{baseline_ref}"
        declaration = release_config_from_text(
            committed_file_text(root, baseline, ".ethos/release.toml")
        )
        _, role, allowed = publication_ref_role(
            policy,
            target_ref,
            tuple(declaration.get("protected_refs", {}).get("tags", ())),
            publication_transport_tags(declaration),
        )
    except (UnicodeError, ValueError) as error:
        return root_ref, "other", f"commit_range_peer_policy_invalid:{root_ref}:{error}"
    return (
        (baseline_ref, role, "")
        if allowed
        else (baseline_ref, role, f"commit_range_trusted_baseline_required:{target_ref}")
    )


def _introduced_commit_revisions(
    root: Path,
    *,
    proposed_commit: str,
    baseline_commit: str,
) -> tuple[str, ...] | None:
    """Return the oldest-first commits newly reachable from one exact baseline."""
    completed = run_git(
        root,
        "rev-list",
        "--reverse",
        "--topo-order",
        proposed_commit,
        "--not",
        baseline_commit,
        check=False,
        observation=True,
    )
    return tuple(completed.stdout.splitlines()) if completed.returncode == 0 else None


def _range_report(
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    update_kind: str,
    state: str,
    proposed_commit: str = "",
    baseline_commit: str = "",
    baseline_ref: str = "",
    baseline_source: str = "",
    policy_ref: str = "",
    policy: dict[str, object] | None = None,
    revisions: tuple[str, ...] = (),
    violations: list[dict[str, object]] | None = None,
    required_gaps: list[str] | None = None,
) -> dict[str, object]:
    gaps = required_gaps or []
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "target_ref": target_ref,
        "remote_name": remote_name,
        "update_kind": update_kind,
        "proposed_head": proposed_head,
        "remote_head": remote_head,
        "proposed_commit": proposed_commit,
        "baseline_commit": baseline_commit,
        "baseline_ref": baseline_ref,
        "baseline_source": baseline_source,
        "policy_ref": policy_ref,
        "policy": policy,
        "revisions": list(revisions),
        "checked_commit_count": len(revisions),
        "violations": violations or [],
        "required_gaps": gaps,
    }

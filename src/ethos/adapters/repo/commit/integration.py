"""Admit exact Git integration ranges and proven history-repair replacements."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.admission import commit_policy_for_revision
from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.commit.admission import peel_commit
from ethos.adapters.repo.commit.signature import repaired_peer_ref_provenance
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.branch.roles import load_branch_role_policy

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
    baseline, baseline_ref, baseline_source, gap = _baseline(
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
    )
    if gap:
        return report(state="blocked", required_gaps=[gap])
    report = partial(report, baseline_commit=baseline)
    repair = repaired_peer_ref_provenance(repo, ref=target_ref, old=baseline, new=proposed_commit)
    if repair is not None and repair["new"] == proposed_commit:
        revisions = tuple(cast("Mapping[str, str]", repair["mapping"]).values())
        return {
            **report(state="repaired_history", update_kind="repair", revisions=revisions),
            "repair_attestation": repair["attestation_id"],
            "signature_verification": "verified_native",
        }
    integration_baseline = str(repair["new"]) if repair is not None else baseline
    revisions = _introduced_commit_revisions(
        repo, proposed_commit=proposed_commit, baseline_commit=integration_baseline
    )
    if revisions is None:
        gap = f"commit_range_unreadable:{baseline}:{proposed_commit}"
    try:
        candidate = commit_policy_for_revision(repo, proposed_commit)
        incumbent = commit_policy_for_revision(repo, integration_baseline)
    except (TypeError, ValueError) as error:
        gap = str(error)
        candidate = incumbent = None
    if gap:
        return report(state="blocked", required_gaps=[gap])
    assert revisions is not None
    violations: list[dict[str, object]] = []
    gaps: list[str] = []
    policies = tuple(dict.fromkeys(policy for policy in (candidate, incumbent) if policy))
    for policy in policies:
        found, failed = _validate_commit_revisions(
            repo, revisions, policy=policy, verify_trust=True
        )
        violations.extend(item for item in found if item not in violations)
        gaps.extend(gap for gap in failed if gap not in gaps)
    result = report(
        state="blocked" if gaps else "admitted",
        policy=candidate.projection() if candidate else None,
        revisions=revisions,
        violations=violations,
        required_gaps=gaps,
    )
    result["policy_sources"] = {
        integration_baseline: incumbent.projection() if incumbent else None,
        proposed_commit: candidate.projection() if candidate else None,
    }
    result["signature_verification"] = (
        "required_native" if any(policy.signing_required for policy in policies) else "not_required"
    )
    if repair is not None:
        result.update(
            update_kind="repair",
            repair_attestation=repair["attestation_id"],
            repair_replacement=repair["new"],
            integration_baseline=integration_baseline,
        )
    return result


def validate_replayed_commits(
    root: Path,
    *,
    baseline_commit: str,
    proposed_commit: str,
    policy: CommitPolicy | None,
) -> list[str]:
    """Admit replay against its trusted baseline and explicitly selected policy."""
    policies = tuple(
        dict.fromkeys(
            item for item in (commit_policy_for_revision(root, baseline_commit), policy) if item
        )
    )
    if not policies:
        return []
    revisions = _introduced_commit_revisions(
        root, proposed_commit=proposed_commit, baseline_commit=baseline_commit
    )
    if revisions is None:
        return [f"commit_range_unreadable:{baseline_commit}:{proposed_commit}"]
    return list(
        dict.fromkeys(
            gap
            for selected in policies
            for gap in _validate_commit_revisions(
                root, revisions, policy=selected, verify_trust=True
            )[1]
        )
    )


def _validate_commit_revisions(
    root: Path,
    revisions: tuple[str, ...],
    *,
    policy: CommitPolicy | None,
    verify_trust: bool = False,
) -> tuple[list[dict[str, object]], list[str]]:
    """Validate one already-derived oldest-first commit sequence."""
    if policy is None:
        return [], []
    violations: list[dict[str, object]] = []
    gaps: list[str] = []
    for revision in revisions:
        report = commit_policy_report(root, policy, revision, verify_trust=verify_trust)
        commit_gaps = cast("list[str]", report["required_gaps"])
        subject = str(cast("dict[str, object]", report["head"]).get("subject") or "")
        if commit_gaps:
            violations.append(
                {"commit": revision, "subject": subject, "required_gaps": commit_gaps}
            )
            gaps.extend(commit_gaps)
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
) -> tuple[str, str, str, str]:
    if remote_head != native_zero:
        baseline = peel_commit(root, remote_head)
        return (
            baseline,
            "",
            "remote_head",
            "" if baseline else f"commit_range_remote_unreadable:{remote_head}",
        )
    baseline_ref = trusted_baseline
    baseline_source = trusted_baseline_source or "explicit_trusted_baseline"
    policy = load_branch_role_policy(root)
    branch = target_ref.removeprefix("refs/heads/")
    if not baseline_ref and branch.startswith(policy.proposal_branch_prefix):
        baseline_ref = f"refs/remotes/{remote_name}/{policy.accepted_branch}"
        baseline_source = "declared_remote_accepted_ref"
    if not baseline_ref:
        return (
            "",
            "",
            "",
            f"commit_range_trusted_baseline_required:{target_ref}",
        )
    baseline = peel_commit(root, baseline_ref)
    if not baseline:
        return (
            "",
            baseline_ref,
            baseline_source,
            f"commit_range_trusted_baseline_unreadable:{baseline_ref}",
        )
    if not is_ancestor(root, baseline, proposed_commit):
        return (
            baseline,
            baseline_ref,
            baseline_source,
            f"commit_range_trusted_baseline_not_ancestor:{baseline}:{proposed_commit}",
        )
    return baseline, baseline_ref, baseline_source, ""


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
        "policy": policy,
        "revisions": list(revisions),
        "checked_commit_count": len(revisions),
        "violations": violations or [],
        "required_gaps": gaps,
    }

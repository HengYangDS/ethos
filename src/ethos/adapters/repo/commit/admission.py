"""Observe and admit prospective and existing repository commits."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import observe_commit
from ethos.adapters.repo.git_object import verify_commit_trust
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.policy.commit import commit_policy_from_text

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.policy.commit import CommitPolicy

_POLICY_PATH = ".ethos/workspace.toml"


def indexed_commit_policy(root: Path) -> CommitPolicy | None:
    """Compile commit policy from the exact prospective Git index tree."""
    listed = run_git(
        root,
        "ls-files",
        "--stage",
        "-z",
        "--",
        _POLICY_PATH,
        check=False,
        observation=True,
        text=False,
    )
    if listed.returncode != 0:
        message = "commit_policy_index_unreadable"
        raise ValueError(message)
    records = tuple(record for record in listed.stdout.split(b"\0") if record)
    if not records:
        return None
    if len(records) != 1:
        message = "commit_policy_index_unmerged"
        raise ValueError(message)
    metadata, separator, path = records[0].partition(b"\t")
    fields = metadata.split()
    if separator != b"\t" or path != _POLICY_PATH.encode() or len(fields) != 3:
        message = "commit_policy_index_invalid"
        raise ValueError(message)
    mode, object_id, stage = fields
    if stage != b"0":
        message = "commit_policy_index_unmerged"
        raise ValueError(message)
    if mode not in {b"100644", b"100755"}:
        message = "commit_policy_index_invalid"
        raise ValueError(message)
    return commit_policy_from_text(
        _blob_text(root, object_id.decode("ascii"), gap="commit_policy_index_unreadable")
    )


def commit_message_report(root: Path, message_file: Path) -> dict[str, object]:
    """Validate the final commit subject against the prospective index policy."""
    path = message_file if message_file.is_absolute() else root / message_file
    try:
        subject = path.read_text(encoding="utf-8").partition("\n")[0]
    except (OSError, UnicodeError):
        return _blocked("commit_message_unreadable")
    policy = indexed_commit_policy(root)
    if policy is None:
        return _passed("policy_not_declared")
    if gap := commit_subject_gap(policy, subject):
        return _blocked(gap)
    return _passed("subject_admitted")


def commit_subject_gap(
    policy: CommitPolicy | None,
    subject: str,
    *,
    revision: str = "",
) -> str:
    """Return the canonical subject-policy gap for one prospective or existing commit."""
    first_line = subject.partition("\n")[0]
    if policy is None or policy.accepts_subject(first_line):
        return ""
    coordinate = f"{revision}:" if revision else ""
    return f"commit_subject_invalid:{coordinate}{first_line}"


def head_commit_policy_report(root: Path, policy: CommitPolicy) -> dict[str, object]:
    """Evaluate current HEAD facts through the shared commit-policy validator."""
    observation = observe_commit(root)
    object_oid = str(observation.get("object_oid") or "")
    subject = str(observation.get("subject") or "")
    head = {
        key: observation.get(key, {}) for key in ("object_oid", "subject", "author", "committer")
    }
    gaps = [str(gap) for gap in cast("list[object]", observation.get("required_gaps", []))]
    if not gaps and (gap := commit_subject_gap(policy, subject, revision=object_oid)):
        gaps.append(gap)
    signature = _signature_policy_report(
        policy,
        object_oid,
        cast("dict[str, object]", observation.get("signature", {})),
    )
    gaps.extend(cast("list[str]", signature["required_gaps"]))
    return {
        "verdict": "block" if gaps else "pass",
        "state": str(observation.get("state") or "unknown"),
        "head": head,
        "signature": signature,
        "required_gaps": gaps,
    }


def commit_range_admission_report(
    root: Path,
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    trusted_baseline: str = "",
    trusted_baseline_source: str = "",
    verify_trust: bool = False,
) -> dict[str, object]:
    """Validate the commits introduced by one exact proposed ref update."""
    repo = root.resolve()
    native_zero = zero_oid(repo)
    if proposed_head == native_zero:
        return _range_report(
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            update_kind="delete",
            state="no_range",
        )
    proposed_commit = _peel_commit(repo, proposed_head)
    if not proposed_commit:
        return _range_blocked(
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            update_kind="create" if remote_head == native_zero else "existing",
            gap=f"commit_range_proposed_unreadable:{proposed_head}",
        )
    baseline, baseline_ref, baseline_source, baseline_gap = _baseline(
        repo,
        target_ref=target_ref,
        proposed_commit=proposed_commit,
        remote_head=remote_head,
        remote_name=remote_name,
        trusted_baseline=trusted_baseline,
        trusted_baseline_source=trusted_baseline_source,
        native_zero=native_zero,
    )
    update_kind = "create" if remote_head == native_zero else "existing"
    if baseline_gap:
        return _range_blocked(
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            proposed_commit=proposed_commit,
            baseline_ref=baseline_ref,
            baseline_source=baseline_source,
            update_kind=update_kind,
            gap=baseline_gap,
        )
    try:
        policy = _committed_policy(repo, proposed_commit)
    except (TypeError, ValueError) as error:
        return _range_blocked(
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            proposed_commit=proposed_commit,
            baseline_commit=baseline,
            baseline_ref=baseline_ref,
            baseline_source=baseline_source,
            update_kind=update_kind,
            gap=str(error),
        )
    revisions = introduced_commit_revisions(
        repo,
        proposed_commit=proposed_commit,
        baseline_commit=baseline,
    )
    if revisions is None:
        return _range_blocked(
            target_ref=target_ref,
            proposed_head=proposed_head,
            remote_head=remote_head,
            remote_name=remote_name,
            proposed_commit=proposed_commit,
            baseline_commit=baseline,
            baseline_ref=baseline_ref,
            baseline_source=baseline_source,
            update_kind=update_kind,
            gap=f"commit_range_unreadable:{baseline}:{proposed_commit}",
        )
    violations, gaps = validate_commit_revisions(
        repo,
        revisions,
        policy=policy,
        verify_trust=verify_trust,
    )
    return _range_report(
        target_ref=target_ref,
        proposed_head=proposed_head,
        remote_head=remote_head,
        remote_name=remote_name,
        proposed_commit=proposed_commit,
        baseline_commit=baseline,
        baseline_ref=baseline_ref,
        baseline_source=baseline_source,
        update_kind=update_kind,
        state="blocked" if gaps else "admitted",
        policy=policy.projection() if policy else None,
        revisions=revisions,
        violations=violations,
        required_gaps=gaps,
    )


def validate_commit_revisions(
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
        observation = observe_commit(root, revision)
        commit_gaps = [
            str(gap) for gap in cast("list[object]", observation.get("required_gaps", []))
        ]
        subject = str(observation.get("subject") or "")
        if not commit_gaps and (gap := commit_subject_gap(policy, subject, revision=revision)):
            commit_gaps.append(gap)
        signature = _signature_policy_report(
            policy,
            revision,
            cast("dict[str, object]", observation.get("signature", {})),
        )
        commit_gaps.extend(cast("list[str]", signature["required_gaps"]))
        if verify_trust and policy.signing_required and not commit_gaps:
            trust = verify_commit_trust(root, revision)
            commit_gaps.extend(
                str(gap) for gap in cast("list[object]", trust.get("required_gaps", []))
            )
        if commit_gaps:
            violations.append(
                {"commit": revision, "subject": subject, "required_gaps": commit_gaps}
            )
            gaps.extend(commit_gaps)
    return violations, gaps


def _signature_policy_report(
    policy: CommitPolicy,
    revision: str,
    facts: dict[str, object],
) -> dict[str, object]:
    present = facts.get("present") is True
    observed_format = str(facts.get("format") or "")
    gaps: list[str] = []
    state = "not_required"
    if policy.signing_required and not present:
        state = "missing"
        gaps.append(f"commit_signature_missing:{revision}")
    elif policy.signing_required and observed_format != policy.signing_format:
        state = "format_mismatch"
        gaps.append(
            "commit_signature_format_mismatch:"
            f"{revision}:expected={policy.signing_format}:"
            f"observed={observed_format or 'unknown'}"
        )
    elif policy.signing_required:
        state = "present"
    return {
        "verdict": "block" if gaps else "pass",
        "required": policy.signing_required,
        "state": state,
        "present": present,
        "format": observed_format,
        "required_gaps": gaps,
    }


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
        baseline = _peel_commit(root, remote_head)
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
    baseline = _peel_commit(root, baseline_ref)
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


def _peel_commit(root: Path, revision: str) -> str:
    completed = run_git(
        root,
        "rev-parse",
        "--verify",
        f"{revision}^{{commit}}",
        check=False,
        observation=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _committed_policy(root: Path, proposed_commit: str) -> CommitPolicy | None:
    listed = run_git(
        root,
        "ls-tree",
        "-z",
        proposed_commit,
        "--",
        _POLICY_PATH,
        check=False,
        observation=True,
        text=False,
    )
    if listed.returncode != 0:
        message = f"commit_policy_projection_unreadable:{proposed_commit}"
        raise ValueError(message)
    records = tuple(record for record in listed.stdout.split(b"\0") if record)
    if not records:
        return None
    if len(records) != 1:
        message = f"commit_policy_projection_invalid:{proposed_commit}"
        raise ValueError(message)
    metadata, separator, path = records[0].partition(b"\t")
    fields = metadata.split()
    if (
        separator != b"\t"
        or path != _POLICY_PATH.encode()
        or len(fields) != 3
        or fields[0] not in {b"100644", b"100755"}
        or fields[1] != b"blob"
    ):
        message = f"commit_policy_projection_invalid:{proposed_commit}"
        raise ValueError(message)
    return commit_policy_from_text(
        _blob_text(
            root,
            fields[2].decode("ascii"),
            gap=f"commit_policy_projection_unreadable:{proposed_commit}",
        )
    )


def _blob_text(root: Path, object_id: str, *, gap: str) -> str:
    completed = run_git(
        root,
        "cat-file",
        "blob",
        object_id,
        check=False,
        observation=True,
        text=False,
    )
    if completed.returncode != 0:
        raise ValueError(gap)
    try:
        return completed.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(gap) from error


def introduced_commit_revisions(
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


def _range_blocked(
    *,
    target_ref: str,
    proposed_head: str,
    remote_head: str,
    remote_name: str,
    update_kind: str,
    gap: str,
    proposed_commit: str = "",
    baseline_commit: str = "",
    baseline_ref: str = "",
    baseline_source: str = "",
) -> dict[str, object]:
    return _range_report(
        target_ref=target_ref,
        proposed_head=proposed_head,
        remote_head=remote_head,
        remote_name=remote_name,
        proposed_commit=proposed_commit,
        baseline_commit=baseline_commit,
        baseline_ref=baseline_ref,
        baseline_source=baseline_source,
        update_kind=update_kind,
        state="blocked",
        required_gaps=[gap],
    )


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


def _passed(state: str) -> dict[str, object]:
    return {"verdict": "pass", "state": state, "hook": "commit-msg", "required_gaps": []}


def _blocked(gap: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "hook": "commit-msg",
        "required_gaps": [gap],
    }

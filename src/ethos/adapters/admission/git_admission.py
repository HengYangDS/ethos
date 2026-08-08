from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import commit_contained_in
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commit_identity import equivalent_commit_identity
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from ethos.contracts.admission import HookAdmissionRequest

HOOK_LAYERS = {
    name: {"timing": timing, "duty": duty, "fallback": fallback}
    for name, timing, duty, fallback in (
        ("context", "before_target_resolution", "refresh_repository_truth", False),
        ("pre-tool", "before_write_capable_tool", "block_unadmitted_tracked_writes", False),
        ("pre-run", "before_shell_command", "classify_mutation_risk", False),
        ("post-write", "after_write", "fuse_on_unexpected_mutation", False),
        ("git", "commit_or_push", "deterministic_local_fallback", True),
        ("ci", "hosted_pipeline", "integration_and_release_proof", True),
    )
}
_NO_RECONCILIATION = ReconciliationObservation()
_ZERO_OIDS = {"0" * 40, "0" * 64}


def hook_admission_report(request: HookAdmissionRequest) -> dict[str, object]:
    """Evaluate a hook-layer request against the current checkout state."""
    normalized = request.layer.strip().lower().replace("_", "-")
    repo = Path(request.root).resolve()
    status = workspace_status(repo, include_foreign_path_scope=False)
    targets = [
        path
        if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
        else repo / path
        for path in map(Path, request.paths)
    ]
    expected_root = Path(request.expected_root) if request.expected_root else None
    editor_root = Path(request.editor_root) if request.editor_root else None
    base: dict[str, object] = {"verdict": "pass", "state": "admitted", "layer": normalized}
    base.update(hook=HOOK_LAYERS.get(normalized, {}), target_root=repo.as_posix())
    base.update(expected_root=(expected_root or repo).resolve().as_posix())
    base.update(role=status["role"], branch=status["branch"])
    base.update(editor_root=editor_root.resolve().as_posix() if editor_root else "")
    base.update(target_paths=[path.as_posix() for path in targets])
    base.update(decision={"action": "allow", "reason": "hook_admitted"}, required_gaps=[])
    if normalized not in HOOK_LAYERS:
        return _verdict(base, "block", "blocked", "block", "hook_layer_invalid")
    report: dict[str, object] | None = None
    if normalized == "context":
        mismatch = expected_root is not None and expected_root.resolve() != repo
        report = _verdict(
            base,
            "block" if mismatch else "pass",
            "blocked" if mismatch else "refreshed",
            "block" if mismatch else "allow",
            "hook_context_root_mismatch" if mismatch else "context_refreshed",
            None if mismatch else (),
        )
    elif normalized == "pre-tool":
        if status["role"] in PROTECTED_WRITE_ROLES and not targets:
            report = _verdict(
                base,
                "block",
                "blocked",
                "block",
                "protected_root_pretool_paths_required",
            )
    elif normalized == "pre-run":
        report = _pre_run_report(base, request.command, targets)
    elif normalized == "post-write":
        report = _post_write_report(base, repo, targets)
    else:
        base["fallback"] = True
        report = _verdict(base, "pass", "fallback", "allow", "fallback_hook_layer", ())
    if report is None:
        report = _prewrite_report(
            base,
            repo=repo,
            paths=targets,
            editor_root=editor_root,
            require_editor_root=request.require_editor_root,
        )
    return report


def _pre_run_report(
    base: dict[str, object], command: str, targets: list[Path]
) -> dict[str, object] | None:
    stash = git_stash_policy(command)
    risk = command_risk(command)
    base.update(command=command, command_risk=risk, git_stash_policy=stash)
    if risk.get("unclassifiable") is True:
        return _verdict(base, "block", "blocked", "block", "shell_command_unclassifiable")
    if stash["forbidden"] is True:
        return _verdict(base, "block", "blocked", "block", "git_stash_forbidden")
    if risk["tracked_mutation_risk"] is not True:
        return _verdict(base, "pass", "admitted", "allow", "command_observe_only", ())
    return (
        None
        if targets
        else _verdict(base, "block", "blocked", "block", "hook_prerun_paths_required")
    )


def push_admission_report(
    *,
    root: Path,
    target_ref: str,
    pushed_head: str,
    **options: object,
) -> dict[str, object]:
    """Admit a push only when its branch, identity, proof, and topology agree."""
    remote_head = str(options.get("remote_head") or "")
    remote_name = str(options.get("remote_name") or "origin")
    supplied = options.get("reconciliation", _NO_RECONCILIATION)
    reconciliation = (
        supplied if isinstance(supplied, ReconciliationObservation) else _NO_RECONCILIATION
    )
    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = target_ref.removeprefix("refs/heads/")
    role = policy.role_for_branch(branch)
    topology = publication_topology(repo, release_config(repo))
    branch_admission = publication_branch_admission(
        topology,
        branch=branch,
        candidate_branch=policy.candidate_branch,
        accepted_branch=policy.accepted_branch,
        release_branch=policy.release_branch,
        proposal_branch_prefix=policy.proposal_branch_prefix,
        remote_name=remote_name,
    )
    branch_gaps = list(cast("list[str]", branch_admission["enforcement_gaps"]))
    reconcile = (
        replace(
            reconciliation,
            proposal_branch=branch if role == "proposal_lane" else reconciliation.proposal_branch,
        )
        if (role == "proposal_lane" and remote_head in _ZERO_OIDS)
        or (role in PROTECTED_WRITE_ROLES and reconciliation.receipt_path)
        else _NO_RECONCILIATION
    )
    identity = push_identity_policy_report(
        repo,
        pushed_head,
        remote_head,
        f"{remote_name}/{policy.accepted_branch}"
        if role == "proposal_lane" and remote_head in _ZERO_OIDS
        else "",
        reconciliation=reconcile,
    )
    identity_gaps = list(cast("list[str]", identity["required_gaps"]))
    base: dict[str, object] = {"verdict": "pass", "state": "admitted", "hook": "pre-push"}
    base.update(target_ref=target_ref, target_branch=branch, role=role, remote_name=remote_name)
    base.update(pushed_head=pushed_head, remote_head=remote_head)
    base.update(
        publication_branch_admission=branch_admission,
        identity_policy=identity,
    )
    base.update(decision={"action": "allow", "reason": "push_admitted"}, required_gaps=[])
    if role in PROTECTED_WRITE_ROLES and not branch_gaps:
        proof_gap_list = proof_gaps(repo, pushed_head)
    else:
        proof_gap_list = []
    topology_gaps = (
        accepted_advance_gaps(repo, policy, old_value=remote_head, new_value=pushed_head)
        if branch == policy.accepted_branch
        else []
    )
    local_protected_head = (
        git_stdout(repo, "rev-parse", "--verify", "--quiet", branch)
        if branch in policy.protected_branches
        else ""
    )
    local_closeout_gaps = (
        []
        if branch not in policy.protected_branches or local_protected_head == pushed_head
        else [f"push_to_protected_role_not_proven:local_ref_mismatch:{branch}"]
    )
    gaps = list(
        dict.fromkeys(
            (
                *branch_gaps,
                *identity_gaps,
                *proof_gap_list,
                *topology_gaps,
                *local_closeout_gaps,
            )
        )
    )
    if not gaps:
        return base
    reason = (
        "publication_candidate_branch_remote_forbidden"
        if branch == policy.candidate_branch and branch_gaps
        else "publication_remote_branch_forbidden"
        if any(gap.startswith("publication_remote_branch_forbidden:") for gap in branch_gaps)
        else "publication_remote_name_missing"
        if "publication_remote_name_missing" in branch_gaps
        else "publication_remote_target_unknown"
        if any(gap.startswith("publication_remote_target_unknown:") for gap in branch_gaps)
        else "push_to_protected_role_not_proven"
        if proof_gap_list or topology_gaps or local_closeout_gaps
        else "pushed_commit_identity_not_allowed"
    )
    return _verdict(base, "block", "blocked", "block", reason, gaps)


def accepted_advance_gaps(
    repo: Path,
    policy: BranchRolePolicy,
    *,
    old_value: str,
    new_value: str,
) -> list[str]:
    """Return candidate-head and fast-forward gaps for an accepted advance."""
    candidate = policy.candidate_branch
    identity_replacement = equivalent_commit_identity(repo, old_value, new_value)
    contained = commit_contained_in(repo, new_value, candidate)
    candidate_head = git_stdout(repo, "rev-parse", "--verify", "--quiet", candidate)
    gaps = (
        []
        if new_value == candidate_head and (identity_replacement or contained)
        else ["accepted_ref_move_not_candidate_head"]
        if contained
        else ["accepted_advance_not_candidate_validated"]
    )
    if (
        not identity_replacement
        and old_value not in _ZERO_OIDS
        and not commit_contained_in(repo, old_value, new_value)
    ):
        gaps.append("accepted_ref_move_not_fast_forward")
    return gaps


def _prepared_ref_intent_gaps(
    *,
    repo: Path,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    missing_gap: str,
) -> list[str]:
    intent = claim_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=update,
        operation=operation,
        phase="prepared",
    )
    gap = str(intent["gap"] or "")
    return [missing_gap if gap == "ref_intent_missing" else gap] if gap else []


def resolve_ref_move_policy(
    repo: Path, ref_name: str, old_value: str, new_value: str
) -> BranchRolePolicy:
    """Resolve the strict policy that governs one ref transition.

    The incumbent strict policy remains authoritative. When it predates the
    current schema, the promoted strict policy performs the one-control
    bootstrap. No legacy policy parser participates in admission.
    """
    branch = ref_name.removeprefix("refs/heads/")
    policy = _strict_ref_policy(repo, old_value)
    if policy is None:
        policy = _strict_ref_policy(repo, new_value)
    if policy is None:
        for revision in (old_value, new_value):
            if revision not in _ZERO_OIDS:
                profile = load_repository_profile(repo, tree_ref=revision)
                if profile.state == "valid" and profile.declaration is not None:
                    policy = BranchRolePolicy()
                    break
    if policy is None:
        policy = _absorbed_ref_deletion_policy(repo, branch, old_value, new_value)
    if policy is None:
        message = "ref_move_policy_unavailable"
        raise ValueError(message)
    if branch != policy.release_branch:
        return policy
    accepted_head = git_stdout(repo, "rev-parse", policy.accepted_branch)
    accepted_policy = _strict_ref_policy(repo, accepted_head)
    if accepted_policy is None:
        return policy
    return (
        accepted_policy if accepted_policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF else policy
    )


def _absorbed_ref_deletion_policy(
    repo: Path, branch: str, old_value: str, new_value: str
) -> BranchRolePolicy | None:
    """Resolve current strict policy for one exact legacy absorbed-ref deletion."""
    if new_value not in _ZERO_OIDS or old_value in _ZERO_OIDS:
        return None
    current_policy = load_branch_role_policy(repo)
    accepted_head = git_stdout(repo, "rev-parse", current_policy.accepted_branch)
    accepted_policy = _strict_ref_policy(repo, accepted_head)
    if (
        accepted_policy is None
        or git_stdout(repo, "rev-parse", "HEAD") != accepted_head
        or accepted_policy.role_for_branch(branch) != "work_lane"
        or not is_ancestor(repo, old_value, accepted_head)
    ):
        return None
    intent = claim_ref_intent(
        root=repo,
        ref_name=f"refs/heads/{branch}",
        update=GitRefUpdate(expected=old_value, desired=new_value),
        operation="lane.retire",
        phase="prepared",
    )
    return accepted_policy if intent.get("present") and not intent.get("gap") else None


def _strict_ref_policy(repo: Path, revision: str) -> BranchRolePolicy | None:
    if revision in _ZERO_OIDS:
        return None
    try:
        return strict_branch_role_policy_from_text(
            committed_file_text(repo, revision, ".ethos/workspace.toml")
        )
    except (TypeError, ValueError):
        return None


def ref_move_admission_report(
    *,
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
    phase: str = "prepared",
) -> dict[str, object]:
    """Admit a local ref move only through the protected candidate train."""
    repo = root.resolve()
    try:
        policy = resolve_ref_move_policy(repo, ref_name, old_value, new_value)
    except (ValueError, TypeError):
        branch = ref_name.removeprefix("refs/heads/")
        return {
            "verdict": "block",
            "state": "blocked",
            "hook": "reference-transaction",
            "ref": ref_name,
            "branch": branch,
            "old_value": old_value,
            "new_value": new_value,
            "decision": {"action": "block", "reason": "ref_move_policy_unavailable"},
            "required_gaps": ["ref_move_policy_unavailable"],
        }
    branch = ref_name.removeprefix("refs/heads/")
    base: dict[str, object] = {"verdict": "pass", "state": "admitted"}
    base.update(hook="reference-transaction", ref=ref_name, branch=branch)
    base.update(phase=phase, old_value=old_value, new_value=new_value)
    base.update(decision={"action": "allow", "reason": "ref_move_admitted"}, required_gaps=[])
    if new_value == old_value:
        return base
    mirror = branch == policy.release_branch and policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    operation = (
        "commit.identity-replace"
        if branch in {policy.candidate_branch, policy.accepted_branch}
        and equivalent_commit_identity(repo, old_value, new_value)
        else "release.mirror"
        if mirror
        else "candidate.accept"
        if branch == policy.accepted_branch
        else "candidate.bootstrap"
        if branch == policy.candidate_branch and old_value in _ZERO_OIDS
        else "candidate.refresh"
        if branch == policy.candidate_branch
        and commit_contained_in(repo, new_value, policy.accepted_branch)
        else "candidate.integrate"
        if branch == policy.candidate_branch
        else "lane.retire"
        if branch.startswith(policy.work_branch_prefix) and new_value in _ZERO_OIDS
        else "lane.import"
        if branch.startswith(policy.work_branch_prefix) and old_value in _ZERO_OIDS
        else ""
    )
    if phase in {"committed", "aborted"} and operation:
        intent = claim_ref_intent(
            root=repo,
            ref_name=ref_name,
            update=GitRefUpdate(expected=old_value, desired=new_value),
            operation=operation,
            phase=phase,
        )
        if gap := str(intent["gap"] or ""):
            return _verdict(
                base,
                "block",
                "repair_required" if phase == "committed" else "blocked",
                "block",
                f"ref_intent_{phase}_failed",
                [gap],
            )
        base["decision"] = {"action": "allow", "reason": f"ref_intent_{phase}"}
        return base
    if mirror or branch == policy.accepted_branch:
        gaps = [
            *accepted_advance_gaps(repo, policy, old_value=old_value, new_value=new_value),
            *proof_gaps(repo, new_value),
        ]
        if not gaps:
            gaps.extend(
                _prepared_ref_intent_gaps(
                    repo=repo,
                    ref_name=ref_name,
                    update=GitRefUpdate(expected=old_value, desired=new_value),
                    operation=operation,
                    missing_gap=(
                        "release_mirror_ref_move_no_ref_intent"
                        if mirror
                        else "accepted_ref_move_no_ref_intent"
                    ),
                )
            )
        reason = (
            "release_mirror_ref_move_bypasses_accepted_closeout"
            if mirror
            else "accepted_ref_move_bypasses_candidate_train"
        )
    elif branch == policy.candidate_branch:
        if commit_contained_in(repo, new_value, policy.accepted_branch):
            gaps = []
        else:
            gaps = proof_gaps(repo, new_value)
        if not gaps:
            gaps.extend(
                _prepared_ref_intent_gaps(
                    repo=repo,
                    ref_name=ref_name,
                    update=GitRefUpdate(expected=old_value, desired=new_value),
                    operation=operation,
                    missing_gap="candidate_ref_move_no_ref_intent",
                )
            )
        reason = "protected_ref_move_not_proven"
    else:
        return base
    return _verdict(base, "block", "blocked", "block", reason, gaps) if gaps else base


def _prewrite_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
) -> dict[str, object]:
    admission = prewrite_guard(
        root=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )
    base.update(admission=admission, role=admission["role"], branch=admission["branch"])
    verdict = report_verdict(admission)
    if verdict == "pass":
        return _verdict(base, "pass", "admitted", "allow", "prewrite_admitted", ())
    gaps = [str(gap) for gap in cast("list[object]", admission.get("required_gaps", []))]
    reason = str(admission.get("error") or (gaps[0] if gaps else "prewrite_unknown"))
    blocked = _verdict(
        base,
        verdict,
        "unknown" if verdict == "unknown" else "blocked",
        "block",
        reason,
        gaps,
    )
    blocked["next_action"] = _prewrite_block_next_action(admission)
    return blocked


def _post_write_report(
    base: dict[str, object], repo: Path, expected_paths: list[Path]
) -> dict[str, object]:
    status = workspace_status(repo)
    changed = string_sequence(status.get("changed_paths"))
    expected = {_relative(repo, path) for path in expected_paths}
    unexpected = [path for path in changed if not expected or path not in expected]
    base.update(role=status["role"], branch=status["branch"], changed_paths=changed)
    base["unexpected_paths"] = unexpected
    if status["role"] in PROTECTED_WRITE_ROLES and changed:
        return _verdict(base, "block", "fused", "fuse", "post_write_protected_root_dirty")
    if unexpected:
        return _verdict(base, "block", "fused", "fuse", "post_write_unexpected_path")
    return _verdict(base, "pass", "admitted", "allow", "post_write_expected_paths_clean", ())


def _relative(root: Path, path: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    try:
        return resolved.resolve().relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _prewrite_block_next_action(admission: dict[str, object]) -> str:
    lease = admission.get("work_lane_lease")
    reason = str(lease.get("reason") or "") if isinstance(lease, dict) else ""
    if reason.startswith("lease_holder_mismatch:"):
        holder = str(lease.get("holder_ref") or "").strip() if isinstance(lease, dict) else ""
        return (
            f"set ETHOS_ACTOR={holder} and rerun the blocked command, or obtain handoff"
            if holder
            else "set ETHOS_ACTOR to the current holder_ref or obtain handoff"
        )
    if reason.startswith("work_lane_missing_lease:"):
        return (
            "ethos lane start <name> --commitment <commitment.toml> "
            "--holder-ref <holder-ref> --apply --json"
        )
    return "ethos lane prewrite <path>"


def _verdict(
    base: dict[str, object],
    verdict: Verdict,
    state: str,
    action: str,
    reason: str,
    gaps: list[str] | tuple[()] | None = None,
) -> dict[str, object]:
    required = [reason] if gaps is None else list(gaps)
    base.update(
        verdict=close_verdict(verdict, tuple(required)),
        state=state,
        decision={"action": action, "reason": reason},
    )
    base["required_gaps"] = required
    return base

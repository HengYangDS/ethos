from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.core as mutation_core
from ethos.adapters.admission.closeout_intent.core import MarkerExpectation
from ethos.adapters.admission.closeout_intent.core import consume_closeout_intent
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import commit_contained_in
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.core import workspace_status
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.core import string_sequence
from ethos.repository.policy.gates import gate_policy_digest
from ethos.repository.release.core import release_config
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from ethos.contracts.admission import HookAdmissionRequest
    from ethos.contracts.branch.roles import BranchRolePolicy

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
_ZERO_OID = "0" * 40


def hook_admission_report(request: HookAdmissionRequest) -> dict[str, object]:
    """Evaluate a hook-layer request against the current checkout state."""
    normalized = request.layer.strip().lower().replace("_", "-")
    normalized = normalized if normalized in HOOK_LAYERS else "pre-tool"
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
    base: dict[str, object] = {"ok": True, "state": "admitted", "layer": normalized}
    base.update(hook=HOOK_LAYERS[normalized], target_root=repo.as_posix())
    base.update(expected_root=(expected_root or repo).resolve().as_posix())
    base.update(role=status["role"], branch=status["branch"])
    base.update(editor_root=editor_root.resolve().as_posix() if editor_root else "")
    base.update(target_paths=[path.as_posix() for path in targets])
    base.update(decision={"action": "allow", "reason": "hook_admitted"}, required_gaps=[])
    report: dict[str, object] | None = None
    if normalized == "context":
        mismatch = expected_root is not None and expected_root.resolve() != repo
        report = _verdict(
            base,
            "blocked" if mismatch else "refreshed",
            "block" if mismatch else "allow",
            "hook_context_root_mismatch" if mismatch else "context_refreshed",
            None if mismatch else (),
        )
    elif normalized == "pre-tool":
        if status["role"] in PROTECTED_WRITE_ROLES and not targets:
            report = _verdict(base, "blocked", "block", "protected_root_pretool_paths_required")
    elif normalized == "pre-run":
        command = request.command
        stash_policy = git_stash_policy(command)
        risk = command_risk(command, role=str(base["role"]))
        base.update(command=command, command_risk=risk, git_stash_policy=stash_policy)
        if stash_policy["forbidden"] is True:
            report = _verdict(base, "blocked", "block", "git_stash_forbidden")
        elif risk["tracked_mutation_risk"] is not True:
            report = _verdict(base, "admitted", "allow", "command_observe_only", ())
        elif not targets:
            report = _verdict(base, "blocked", "block", "hook_prerun_paths_required")
    elif normalized == "post-write":
        report = _post_write_report(base, repo, targets)
    else:
        base["fallback"] = True
        report = _verdict(base, "fallback", "allow", "fallback_hook_layer", ())
    if report is None:
        report = _prewrite_report(
            base,
            repo=repo,
            paths=targets,
            editor_root=editor_root,
            require_editor_root=request.require_editor_root,
        )
    return report


def push_admission_report(
    *,
    root: Path,
    target_ref: str,
    pushed_head: str,
    campaign_publication: dict[str, object] | None = None,
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
    topology = publication_topology(release_config(repo))
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
        if (role == "proposal_lane" and remote_head == _ZERO_OID)
        or (role in PROTECTED_WRITE_ROLES and reconciliation.receipt_path)
        else _NO_RECONCILIATION
    )
    identity = push_identity_policy_report(
        repo,
        pushed_head,
        remote_head,
        f"{remote_name}/{policy.accepted_branch}"
        if role == "proposal_lane" and remote_head == _ZERO_OID
        else "",
        reconciliation=reconcile,
    )
    identity_gaps = list(cast("list[str]", identity["required_gaps"]))
    base: dict[str, object] = {"ok": True, "state": "admitted", "hook": "pre-push"}
    base.update(target_ref=target_ref, target_branch=branch, role=role, remote_name=remote_name)
    base.update(pushed_head=pushed_head, remote_head=remote_head)
    base.update(
        publication_branch_admission=branch_admission,
        identity_policy=identity,
        campaign_publication=campaign_publication or {},
    )
    base.update(decision={"action": "allow", "reason": "push_admitted"}, required_gaps=[])
    proof_gaps = (
        mutation_core.proof_gaps(repo, pushed_head)
        if role in PROTECTED_WRITE_ROLES and not branch_gaps
        else []
    )
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
    campaign_gaps = (
        string_sequence(campaign_publication.get("required_gaps"), drop_empty=True)
        if role in PROTECTED_WRITE_ROLES and campaign_publication
        else []
    )
    gaps = list(
        dict.fromkeys(
            (
                *campaign_gaps,
                *branch_gaps,
                *identity_gaps,
                *proof_gaps,
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
        if proof_gaps or topology_gaps or local_closeout_gaps
        else "campaign_publication_not_terminal"
        if campaign_gaps
        else "pushed_commit_identity_not_allowed"
    )
    return _verdict(base, "blocked", "block", reason, gaps)


def _proof_evidence_digest(root: Path, head: str) -> str:
    record = executed_proof_record(root, head)
    return str(record.get("evidence_digest", "")) if isinstance(record, dict) else ""


def accepted_advance_gaps(
    repo: Path,
    policy: BranchRolePolicy,
    *,
    old_value: str,
    new_value: str,
) -> list[str]:
    """Return candidate-head and fast-forward gaps for an accepted advance."""
    candidate = policy.candidate_branch
    contained = commit_contained_in(repo, new_value, candidate)
    candidate_head = git_stdout(repo, "rev-parse", "--verify", "--quiet", candidate)
    gaps = (
        []
        if contained and new_value == candidate_head
        else ["accepted_ref_move_not_candidate_head"]
        if contained
        else ["accepted_advance_not_candidate_validated"]
    )
    if old_value not in (_ZERO_OID, "") and not commit_contained_in(repo, old_value, new_value):
        gaps.append("accepted_ref_move_not_fast_forward")
    return gaps


def ref_move_admission_report(
    *,
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
) -> dict[str, object]:
    """Admit a local ref move only through the protected candidate train."""
    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = ref_name.removeprefix("refs/heads/")
    base: dict[str, object] = {"ok": True, "state": "admitted"}
    base.update(hook="reference-transaction", ref=ref_name, branch=branch)
    base.update(old_value=old_value, new_value=new_value)
    base.update(decision={"action": "allow", "reason": "ref_move_admitted"}, required_gaps=[])
    if new_value in (_ZERO_OID, "") or new_value == old_value:
        return base
    candidate_policy = branch_role_policy_from_text(
        committed_file_text(repo, policy.candidate_branch, ".ethos/workspace.toml")
    )
    mirror = (
        branch == candidate_policy.release_branch
        and candidate_policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    )
    if mirror or branch == policy.accepted_branch:
        move_policy = candidate_policy if mirror else policy
        gaps = [
            *accepted_advance_gaps(repo, move_policy, old_value=old_value, new_value=new_value),
            *mutation_core.proof_gaps(repo, new_value),
        ]
        intent = consume_closeout_intent(
            root=repo,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
            expect=MarkerExpectation(
                evidence_digest=_proof_evidence_digest(repo, new_value),
                gate_policy_digest=gate_policy_digest(repo, tree_ref=new_value),
            ),
        )
        if intent["gap"]:
            gap = str(intent["gap"])
            gaps.append(
                gap.replace("accepted_ref_move", "release_mirror_ref_move") if mirror else gap
            )
        reason = (
            "release_mirror_ref_move_bypasses_accepted_closeout"
            if mirror
            else "accepted_ref_move_bypasses_candidate_train"
        )
    elif branch == policy.candidate_branch:
        gaps = (
            []
            if commit_contained_in(repo, new_value, policy.accepted_branch)
            else mutation_core.proof_gaps(repo, new_value)
        )
        reason = "protected_ref_move_not_proven"
    else:
        return base
    return _verdict(base, "blocked", "block", reason, gaps) if gaps else base


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
    if admission["ok"] is True:
        return _verdict(base, "admitted", "allow", "prewrite_admitted", ())
    blocked = _verdict(base, "blocked", "block", str(admission["error"]))
    blocked["next_actions"] = _prewrite_block_next_actions(admission)
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
        return _verdict(base, "fused", "fuse", "post_write_protected_root_dirty")
    if unexpected:
        return _verdict(base, "fused", "fuse", "post_write_unexpected_path")
    return _verdict(base, "admitted", "allow", "post_write_expected_paths_clean", ())


def _relative(root: Path, path: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    try:
        return resolved.resolve().relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _prewrite_block_next_actions(admission: dict[str, object]) -> list[str]:
    lease = admission.get("work_lane_lease")
    reason = str(lease.get("reason") or "") if isinstance(lease, dict) else ""
    if reason.startswith("lease_holder_mismatch:"):
        holder = str(lease.get("holder_ref") or "").strip() if isinstance(lease, dict) else ""
        return (
            [
                f"set ETHOS_ACTOR={holder} and rerun the blocked command, or obtain handoff",
                "ethos lane prewrite <path>",
            ]
            if holder
            else ["set ETHOS_ACTOR to the current holder_ref or obtain handoff"]
        )
    if reason.startswith("work_lane_missing_lease:"):
        return ["ethos lane start <name> --holder-ref <holder-ref> --apply --json"]
    return ["ethos lane prewrite <path>"]


def _verdict(
    base: dict[str, object],
    state: str,
    action: str,
    reason: str,
    gaps: list[str] | tuple[()] | None = None,
) -> dict[str, object]:
    required = [reason] if gaps is None else list(gaps)
    base.update(ok=not required, state=state, decision={"action": action, "reason": reason})
    base["required_gaps"] = required
    return base

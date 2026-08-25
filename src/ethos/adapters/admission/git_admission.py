from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.identity import commit_contained_in
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_move_policy import accepted_advance_gaps
from ethos.adapters.admission.ref_move_policy import prepared_ref_intent_gaps
from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.remediation.guidance import prewrite_next_action
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_attestation import accepted_closeout_attestation
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_proof_selection
from ethos.repository.release.publication import publication_ref_admission
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
    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = target_ref.removeprefix("refs/heads/") if target_ref.startswith("refs/heads/") else ""
    config = release_config(repo)
    protected_refs = config.get("protected_refs")
    raw_tags = protected_refs.get("tags") if isinstance(protected_refs, dict) else ()
    release_tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
    topology = publication_topology(repo, config)
    ref_admission = publication_ref_admission(
        topology,
        policy=policy,
        target_ref=target_ref,
        release_tags=release_tags,
        remote_name=remote_name,
    )
    role = str(ref_admission["role"])
    ref_kind = str(ref_admission["ref_kind"])
    ref_gaps = list(cast("list[str]", ref_admission["enforcement_gaps"]))
    identity = push_identity_policy_report(
        repo,
        pushed_head,
        remote_head,
        f"{remote_name}/{policy.accepted_branch}"
        if role == "proposal_lane" and remote_head in _ZERO_OIDS
        else "",
    )
    identity_gaps = list(cast("list[str]", identity["required_gaps"]))
    base: dict[str, object] = {"verdict": "pass", "state": "admitted", "hook": "pre-push"}
    base.update(
        target_ref=target_ref,
        target_branch=branch,
        ref_kind=ref_kind,
        role=role,
        remote_name=remote_name,
    )
    base.update(pushed_head=pushed_head, remote_head=remote_head)
    base.update(
        publication_ref_admission=ref_admission,
        identity_policy=identity,
    )
    base.update(decision={"action": "allow", "reason": "push_admitted"}, required_gaps=[])
    proof_head = (
        git_stdout(repo, "rev-parse", "--verify", f"{pushed_head}^{{commit}}")
        if ref_kind == "tag"
        else pushed_head
    )
    source_gaps = (
        list(_release_publication_source_gaps(repo, policy=policy, peeled_commit=proof_head))
        if role == "release_publication" and proof_head
        else []
    )
    supplied_proof = options.get("proof_admission")
    proof_admission = (
        dict(supplied_proof)
        if isinstance(supplied_proof, Mapping)
        else proof_admission_report(
            repo,
            proof_head,
            repository_transition=publication_proof_selection(role) == "repository_transition",
        )
        if not ref_gaps and proof_head
        else {
            "verdict": "block",
            "state": "unavailable",
            "selection": "",
            "attestation": {},
            "required_gaps": [],
            "next_action": "",
        }
    )
    reported_proof_gaps = list(cast("list[str]", proof_admission["required_gaps"]))
    proof_gap_list = (
        [gap for gap in reported_proof_gaps if gap.startswith("repository_commitment_")]
        if branch == policy.accepted_branch
        else reported_proof_gaps
    )
    base["proof_admission"] = proof_admission
    topology_gaps = (
        accepted_advance_gaps(repo, policy, old_value=remote_head, new_value=pushed_head)
        if branch == policy.accepted_branch
        else []
    )
    accepted_closeout: dict[str, object] = {}
    closeout_gaps: list[str] = []
    if branch == policy.accepted_branch:
        try:
            closeout = accepted_closeout_attestation(
                repo,
                accepted_ref=target_ref,
                candidate_ref=f"refs/heads/{policy.candidate_branch}",
                candidate_head=pushed_head,
            )
        except ValueError as error:
            closeout_gaps.append(str(error))
        else:
            if closeout is None:
                closeout_gaps.append("accepted_closeout_effect_not_attested")
            else:
                plan, attestation = closeout
                accepted_closeout = {
                    "attestation_id": attestation.id,
                    "plan_digest": plan.digest,
                    "accepted_ref": target_ref,
                    "accepted_before": git_effect_from_plan(plan).updates[target_ref].expected,
                    "remote_head": remote_head,
                    "candidate_head": pushed_head,
                }
    base["accepted_closeout_effect"] = accepted_closeout
    gaps = list(
        dict.fromkeys(
            (
                *ref_gaps,
                *identity_gaps,
                *source_gaps,
                *proof_gap_list,
                *topology_gaps,
                *closeout_gaps,
            )
        )
    )
    base["next_action"] = str(proof_admission.get("next_action") or "")
    if not gaps:
        return base
    reason = (
        "publication_ref_unavailable"
        if any(gap.startswith("publication_ref_unavailable:") for gap in ref_gaps)
        else "publication_remote_name_missing"
        if "publication_remote_name_missing" in ref_gaps
        else "publication_remote_target_unknown"
        if any(gap.startswith("publication_remote_target_unknown:") for gap in ref_gaps)
        else "push_to_protected_role_not_proven"
        if proof_gap_list or topology_gaps or closeout_gaps
        else "pushed_commit_identity_not_allowed"
    )
    return _verdict(base, "block", "blocked", "block", reason, gaps)


def _release_publication_source_gaps(
    root: Path,
    *,
    policy: BranchRolePolicy,
    peeled_commit: str,
) -> tuple[str, ...]:
    """Require a release tag to project one current accepted product head."""
    product_heads = {
        head
        for branch in (policy.accepted_branch, policy.release_branch)
        if branch
        and (
            head := git_stdout(
                root,
                "rev-parse",
                "--verify",
                "--quiet",
                f"refs/heads/{branch}^{{commit}}",
            )
        )
    }
    return () if peeled_commit in product_heads else ("release_publication_source_not_current",)


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
        "release.mirror"
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
                prepared_ref_intent_gaps(
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
                prepared_ref_intent_gaps(
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
    blocked["next_action"] = str(admission.get("next_action") or prewrite_next_action(admission))
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

"""Admit native ref effects and optional write-capable tool requests."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import committed_ref_intent
from ethos.adapters.admission.ref_move_policy import accepted_advance_gaps
from ethos.adapters.admission.ref_move_policy import prepared_ref_intent_gaps
from ethos.adapters.admission.ref_move_policy import ref_transition_operation
from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.adapters.admission.ref_move_policy import signature_repair_ref_report
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.release import declared_release_tag
from ethos.adapters.repo.release import release_ref_subject
from ethos.adapters.repo.release import release_selection_command
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
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


def hook_admission_report(
    request: HookAdmissionRequest,
    *,
    selected_runtime: SelectedRuntime | None = None,
) -> dict[str, object]:
    """Evaluate a hook-layer request against the current checkout state."""
    normalized = request.layer.strip().lower().replace("_", "-")
    repo = Path(request.root).resolve()
    prewrite = import_module("ethos.adapters.admission.prewrite")
    status = workspace_status(
        repo,
        include_foreign_path_scope=False,
        selected_runtime=selected_runtime,
    )
    targets = [
        path
        if path.is_absolute() or prewrite.has_invalid_path_token_character(path.as_posix())
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
            selected_runtime=selected_runtime,
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


def ref_move_admission_report(
    *,
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
    phase: str = "prepared",
) -> dict[str, object]:
    """Admit one exact local ref transition through its declared lifecycle owner."""
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
    repair = signature_repair_ref_report(repo, ref_name, old_value, new_value, phase=phase)
    if repair is not None:
        return repair
    mirror = branch == policy.release_branch and policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    operation = ref_transition_operation(repo, policy, ref_name, old_value, new_value)
    if phase in {"committed", "aborted"} and operation:
        return _terminal_ref_report(repo, base, ref_name, old_value, new_value, phase, operation)
    if operation in {"release.promote", "release.tag"}:
        return _release_move_report(repo, base, ref_name, old_value, new_value, operation)
    if mirror or branch == policy.accepted_branch:
        _, proof_required = proof_for_repository_transition(repo, new_value)
        gaps = [
            *accepted_advance_gaps(repo, policy, old_value=old_value, new_value=new_value),
            *proof_required,
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
        gaps = _candidate_move_gaps(
            repo, ref_name, old_value, new_value, operation, policy.accepted_branch
        )
        reason = "protected_ref_move_not_proven"
    elif operation == "lane.retire":
        gaps = prepared_ref_intent_gaps(
            repo=repo,
            ref_name=ref_name,
            update=GitRefUpdate(expected=old_value, desired=new_value),
            operation=operation,
            missing_gap="retirement_ref_move_no_ref_intent",
        )
        reason = "retirement_ref_move_not_admitted"
    else:
        gaps, reason = [], "ref_move_admitted"
    return _ref_result(base, reason, gaps)


def _prewrite_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
    selected_runtime: SelectedRuntime | None,
) -> dict[str, object]:
    admission = import_module("ethos.adapters.admission.prewrite").prewrite_guard(
        root=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
        selected_runtime=selected_runtime,
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
    blocked["next_action"] = str(admission.get("next_action") or "")
    blocked["user_decision_required"] = bool(admission.get("user_decision_required", False))
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


def _release_move_gaps(repo: Path, ref: str, old: str, new: str, operation: str) -> list[str]:
    """Conjoin accepted source, current proof and exact executor intent."""
    reversing = (
        new in _ZERO_OIDS
        if operation == "release.tag"
        else is_ancestor(repo, new, old) and new != old
    )
    forward = None
    try:
        if reversing:
            head = release_ref_subject(repo, ref=ref, old=new, new=old)
            forward = committed_ref_intent(
                root=repo, operation=operation, desired=old, ref_name=ref
            )
            if forward.get("gap") or forward.get("old_value") != new:
                return ["release_compensation_forward_intent_missing"]
        else:
            head = release_ref_subject(repo, ref=ref, old=old, new=new)
    except (OSError, TypeError, ValueError) as error:
        return [str(error)]
    _, gaps = proof_for_repository_transition(repo, head)
    if gaps:
        return gaps
    intent = claim_ref_intent(
        root=repo,
        ref_name=ref,
        update=GitRefUpdate(expected=old, desired=new),
        operation=operation,
        phase="prepared",
        plan_digest=str(forward["plan_digest"]) if forward else None,
    )
    gap = str(intent.get("gap") or "")
    return ["release_ref_move_no_ref_intent" if gap == "ref_intent_missing" else gap] if gap else []


def _release_move_report(
    repo: Path, base: dict[str, object], ref: str, old: str, new: str, operation: str
) -> dict[str, object]:
    if operation == "release.tag":
        policy = load_branch_role_policy(repo)
        if not declared_release_tag(repo, ref_head(repo, policy.accepted_branch), ref):
            return base
    gaps = _release_move_gaps(repo, ref, old, new, operation)
    if operation == "release.tag" and gaps == ["release_ref_move_no_ref_intent"]:
        policy = load_branch_role_policy(repo)
        base["next_action"] = release_selection_command(
            repo,
            head=ref_head(repo, policy.accepted_branch),
            previous=ref_head(repo, policy.release_branch),
            tag=ref.removeprefix("refs/tags/"),
        )
    return (
        _verdict(base, "block", "blocked", "block", "release_ref_move_not_admitted", gaps)
        if gaps
        else base
    )


def _terminal_ref_report(
    repo: Path,
    base: dict[str, object],
    ref: str,
    old: str,
    new: str,
    phase: str,
    operation: str,
) -> dict[str, object]:
    """Observe the terminal native intent without duplicating subject admission."""
    intent = claim_ref_intent(
        root=repo,
        ref_name=ref,
        update=GitRefUpdate(expected=old, desired=new),
        operation=operation,
        phase=cast('Literal["committed", "aborted"]', phase),
    )
    gap = str(intent["gap"] or "")
    base["decision"] = {"action": "allow", "reason": f"ref_intent_{phase}"}
    return (
        _verdict(
            base,
            "block",
            "repair_required" if phase == "committed" else "blocked",
            "block",
            f"ref_intent_{phase}_failed",
            [gap],
        )
        if gap
        else base
    )


def _ref_result(base: dict[str, object], reason: str, gaps: list[str]) -> dict[str, object]:
    return _verdict(base, "block", "blocked", "block", reason, gaps) if gaps else base


def _candidate_move_gaps(
    repo: Path, ref: str, old: str, new: str, operation: str, accepted: str
) -> list[str]:
    gaps = [] if is_ancestor(repo, new, accepted) else proof_gaps(repo, new)
    return gaps or prepared_ref_intent_gaps(
        repo=repo,
        ref_name=ref,
        update=GitRefUpdate(expected=old, desired=new),
        operation=operation,
        missing_gap="candidate_ref_move_no_ref_intent",
    )

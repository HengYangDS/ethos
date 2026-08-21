from __future__ import annotations

import os
from pathlib import Path

from ethos.adapters.admission.lease_binding import lease_binding_reason
from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.mutation.remediation.guidance import archive_recovery_command
from ethos.adapters.mutation.remediation.guidance import prewrite_next_action
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.generation.prewrite import prepared_start_prewrite_authority
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_effect import archive_prewrite_authority
from ethos.adapters.openspec.lifecycle.archive_effect import archive_prewrite_recovery
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.repo.runtime.binding import runtime_binding_check
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.contracts.branch.roles import ROLE_DETACHED
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_mapping

_STATE_BINDINGS = ("root", "role", "branch", "paths", "lease_id", "epoch", "head")
_SCOPE_LIST_FIELDS = (
    "changed_paths",
    "material_patterns",
    "material_paths",
    "changes",
    "covered_paths",
    "uncovered_paths",
    "required_gaps",
    "advisory_gaps",
)


def has_invalid_path_token_character(text: str) -> bool:
    return any(character.isspace() or not character.isprintable() for character in text)


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
    patch: str = "",
) -> dict[str, object]:
    status = _prewrite_status(root)
    status_role, status_branch = str(status["role"]), str(status["branch"])
    effective = _effective_write_context(root=root, role=status_role, branch=status_branch)
    runtime_check = runtime_binding_check(status)
    checked = [_check_path(root=root, path=path, role=effective["role"]) for path in paths]
    tracked = any(path["tracked_candidate"] for path in checked)
    requested = tuple(
        str(path["relative_path"])
        for path in checked
        if path["tracked_candidate"] is True and path["relative_path"]
    )
    lease = _work_lane_lease_check(
        root=root, status=status, effective=effective, tracked_write_requested=tracked
    )
    profile_enabled = openspec_profile_enabled(root)
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    prepared_authority = None
    if tracked and profile_enabled:
        prepared_authority = archive_prewrite_authority(
            root, changed_paths=requested, branch=effective["branch"], actor=actor
        )
    if prepared_authority is None and tracked and profile_enabled:
        prepared_authority = prepared_start_prewrite_authority(
            root, changed_paths=requested, branch=effective["branch"], actor=actor
        )
    archive_recovery = (
        archive_prewrite_recovery(
            root,
            changed_paths=requested,
            branch=effective["branch"],
        )
        if prepared_authority is None
        and tracked
        and profile_enabled
        and lease.get("verdict") != "pass"
        else None
    )
    authority = prepared_authority or lease
    profile_adapter: dict[str, object] = {}
    prepared_scope = authority.get("material_scope")
    if isinstance(prepared_scope, dict):
        scope = string_mapping(prepared_scope)
    elif lease.get("required") is True:
        scope = _commitment_scope(root, requested, lease)
    elif archive_recovery is not None:
        scope = dict(archive_recovery.material_scope)
    elif profile_enabled:
        profile_adapter = openspec_governance_report(
            root,
            lifecycle=True,
            changed_paths=requested,
            require_workspace=False,
        )
        scope = _openspec_scope(profile_adapter)
    else:
        scope = _commitment_scope(root, requested, lease)
    editor = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked,
    )
    patch_report = patch_admission(
        root=root,
        requested_paths=requested,
        baseline_head=str(authority.get("expected_head") or ""),
        patch=patch,
    )
    blocked = [path for path in checked if path["allowed"] is False]
    gaps = _gaps(runtime_check, authority, editor, patch_report, scope, blocked)
    verdict = reduce_verdicts(
        report_verdict(runtime_check),
        "block" if blocked else "pass",
        report_verdict(authority),
        report_verdict(editor),
        report_verdict(patch_report),
        report_verdict(scope),
        required_gaps=tuple(gaps),
    )
    decision = _prewrite_decision(root, effective, checked, authority, verdict, tuple(gaps))
    next_action = (
        ""
        if verdict == "pass"
        else archive_recovery_command(
            archive_recovery.change,
            archive_recovery.expected_head,
        )
        if archive_recovery is not None
        else prewrite_next_action({"work_lane_lease": lease, "editor_root": editor})
    )
    return {
        "verdict": decision.verdict,
        "error": gaps[0] if gaps else "",
        "role": effective["role"],
        "branch": effective["branch"],
        "status_role": status_role,
        "status_branch": status_branch,
        "effective_context": effective,
        "runtime_binding": runtime_check,
        "work_lane_lease": lease,
        "mutation_authority": authority,
        "editor_root": editor,
        "patch_admission": patch_report,
        **({"profile_adapter": profile_adapter} if profile_adapter else {}),
        "material_scope": scope,
        "paths": checked,
        "blocked_paths": blocked,
        "request_binding": decision.subject.model_dump(mode="json"),
        "decision": decision.to_payload(),
        "required_gaps": gaps,
        "next_action": next_action,
    }


def _prewrite_status(root: Path) -> dict[str, object]:
    top = git_stdout(root, "rev-parse", "--show-toplevel")
    repo = Path(top).resolve() if top else root
    if not top:
        return {
            "root": str(root),
            "branch": "untracked",
            "role": "other",
            "runtime_binding": runtime_binding(repo),
            "worktrees": [],
        }
    policy = load_branch_role_policy(repo)
    branch = current_branch(repo)
    return {
        "root": str(root),
        "branch": branch,
        "role": policy.role_for_branch(branch) if branch else ROLE_DETACHED,
        "runtime_binding": runtime_binding(repo),
        "worktrees": worktree_records(repo, current_path=repo, policy=policy),
    }


def _effective_write_context(*, root: Path, role: str, branch: str) -> dict[str, str]:
    rebase_branch = _rebase_head_branch(root) if role == ROLE_DETACHED else ""
    is_work_rebase = bool(
        rebase_branch
        and load_branch_role_policy(root).role_for_branch(rebase_branch) == ROLE_WORK_LANE
    )
    return {
        "role": ROLE_WORK_LANE if is_work_rebase else role,
        "branch": rebase_branch if is_work_rebase else branch,
        "source": "git_rebase_head_name" if is_work_rebase else "prewrite_context",
        "rebase_head_name": rebase_branch,
    }


def _rebase_head_branch(root: Path) -> str:
    git_dir = Path(git_stdout(root, "rev-parse", "--git-path", ".") or ".git")
    git_dir = git_dir if git_dir.is_absolute() else root / git_dir
    head = next(
        filter(
            Path.exists,
            (git_dir / "rebase-merge/head-name", git_dir / "rebase-apply/head-name"),
        ),
        None,
    )
    return head.read_text(encoding="utf-8").strip().removeprefix("refs/heads/") if head else ""


def _work_lane_lease_check(
    *,
    root: Path,
    status: dict[str, object],
    effective: dict[str, str],
    tracked_write_requested: bool,
) -> dict[str, object]:
    role, branch, source = effective["role"], effective["branch"], effective["source"]
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if role != ROLE_WORK_LANE or not tracked_write_requested:
        return _lease_report(branch, actor, {}, ("pass", False, "not_required"))
    lease = _work_lane_lease(root=root, status=status, branch=branch)
    lease_state = str(lease.get("lease_state") or "missing")
    if lease_state != "valid" or not lease.get("holder_ref"):
        reason = {
            "unknown": f"work_lane_lease_unknown:{branch}",
            "expired": f"work_lane_lease_expired:{branch}",
        }.get(lease_state, f"work_lane_missing_lease:{branch}")
        return _lease_report(
            branch,
            actor,
            lease,
            ("unknown" if lease_state == "unknown" else "block", True, reason),
        )
    current = git_stdout(root, "rev-parse", "HEAD")
    binding = (
        git_stdout(root, "rev-parse", "--verify", f"refs/heads/{branch}")
        if source == "git_rebase_head_name"
        else current
    )
    reason = lease_binding_reason(
        root=root,
        branch=branch,
        lease=lease,
        actor=actor,
        current_head=binding,
        commitment_loader=load_lease_bound_commitment,
    )
    return _lease_report(
        branch,
        actor,
        lease,
        ("block" if reason else "pass", True, reason or "matched"),
        observed=(
            current,
            binding,
            "rebase_branch_ref" if source == "git_rebase_head_name" else "head",
        ),
    )


def _lease_report(
    branch: str,
    actor: str,
    lease: dict[str, object],
    result: tuple[Verdict, bool, str],
    *,
    observed: tuple[str, str, str] | None = None,
) -> dict[str, object]:
    verdict, required, reason = result
    report: dict[str, object] = {
        "verdict": verdict,
        "required": required,
        "branch": branch,
        "holder_ref": str(lease.get("holder_ref") or ""),
        "invocation_holder_ref": actor,
        "lease_id": str(lease.get("lease_id") or ""),
        "epoch": integer_value(lease.get("epoch")),
        "expected_head": str(lease.get("expected_head") or ""),
        "expected_tree": str(lease.get("expected_tree") or ""),
        "base_commitment_path": str(lease.get("base_commitment_path") or ""),
        "base_commitment_bytes_sha256": str(lease.get("base_commitment_bytes_sha256") or ""),
        "base_commitment_digest": str(lease.get("base_commitment_digest") or ""),
    }
    if observed:
        report.update(current_head=observed[0], binding_head=observed[1], head_source=observed[2])
    report["reason"] = reason
    return report


def _work_lane_lease(*, root: Path, status: dict[str, object], branch: str) -> dict[str, object]:
    current_path = Path(str(status.get("root") or root)).resolve()
    return leases_by_branch(current_path).get(branch, {})


def _prewrite_decision(
    root: Path,
    effective: dict[str, str],
    checked_paths: list[dict[str, object]],
    lease_check: dict[str, object],
    verdict: Verdict,
    gaps: tuple[str, ...],
) -> AdmissionDecision:
    branch, role = effective["branch"], effective["role"]
    paths = tuple(
        str(item.get("relative_path") or item.get("path") or "") for item in checked_paths
    )
    return AdmissionDecision(
        verdict=verdict,
        subject=MutationSubject(
            action="lane.prewrite",
            resource=f"{branch}:{','.join(paths)}",
            expected_state={
                "root": root.resolve().as_posix(),
                "role": role,
                "branch": branch,
                "paths": list(paths),
                "holder_ref": str(lease_check.get("holder_ref") or ""),
                "lease_id": str(lease_check.get("lease_id") or ""),
                "epoch": integer_value(lease_check.get("epoch")),
                "head": str(lease_check.get("expected_head") or ""),
            },
        ),
        policy_refs=("commitment:tracked-write-admission",),
        evidence_refs=("evidence:current-worktree-and-lease-observation",),
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="holder_ref_equality" if lease_check.get("required") else "not_required",
            state_bindings=_STATE_BINDINGS,
            evidence_boundary="current_local_observation",
            verifier_provenance="current_worktree_runner",
            time_basis="evaluation_time",
        ),
        why=(
            gaps[0]
            if gaps
            else "request_matches_current_local_state"
            if verdict == "pass"
            else "required_fact_unverified",
        ),
        next_action="repair_required_gap" if verdict != "pass" else "",
        required_gaps=gaps,
    )


def _editor_root_check(
    *, root: Path, editor_root: Path | None, require_editor_root: bool
) -> dict[str, object]:
    expected = root.resolve()
    actual = editor_root.resolve() if editor_root else None
    matched = actual == expected or (actual is None and not require_editor_root)
    reason = (
        "matched"
        if actual == expected
        else "editor_root_mismatch"
        if actual
        else "editor_root_missing"
        if require_editor_root
        else "not_checked"
    )
    return {
        "verdict": "pass" if matched else "block",
        "required": require_editor_root,
        "expected": expected.as_posix(),
        "actual": actual.as_posix() if actual else "",
        "reason": reason,
    }


def _check_path(*, root: Path, path: Path, role: str) -> dict[str, object]:
    text = path.as_posix()
    if has_invalid_path_token_character(text):
        reason = (
            "path_invalid_control_character"
            if any(not character.isprintable() for character in text)
            else "path_invalid_whitespace"
        )
        return _path_report(text, reason=reason)
    root_path = root.resolve()
    resolved = (path if path.is_absolute() else root_path / path).resolve()
    try:
        relative = resolved.relative_to(root_path).as_posix()
    except ValueError:
        return _path_report(resolved.as_posix(), reason="path_outside_worktree")
    topology = path_policy_from_declaration(
        relative,
        load_generated_artifact_topology_declaration(
            root_path / "system/policies/generated-artifact-topology.toml"
        ),
    )
    ignored = _is_ignored(root_path, relative)
    tracked = not ignored
    if topology["decision"] == "deny":
        return _path_report(
            resolved.as_posix(),
            relative_path=relative,
            ignored=ignored,
            tracked_candidate=tracked,
            reason=str(topology.get("required_gap") or "generated_artifact_topology_denied"),
        )
    protected = role in PROTECTED_WRITE_ROLES and tracked
    return _path_report(
        resolved.as_posix(),
        relative_path=relative,
        ignored=ignored,
        tracked_candidate=tracked,
        allowed=not protected,
        reason="protected_lane_tracked_write" if protected else "allowed",
    )


def _path_report(path: str, *, reason: str, **details: object) -> dict[str, object]:
    return {
        "path": path,
        "relative_path": "",
        "ignored": False,
        "tracked_candidate": False,
        "allowed": False,
        "reason": reason,
        **details,
    }


def _is_ignored(root: Path, relative_path: str) -> bool:
    return run_git(root, "check-ignore", "-q", "--", relative_path, check=False).returncode == 0


def _gaps(
    runtime_check: dict[str, object],
    lease_check: dict[str, object],
    editor_check: dict[str, object],
    patch_admission: dict[str, object],
    material_scope: dict[str, object],
    blocked_paths: list[dict[str, object]],
) -> list[str]:
    scope_gaps = material_scope.get("required_gaps")
    checks = (
        str(runtime_check["reason"]) if report_verdict(runtime_check) != "pass" else "",
        _blocked_path_error(blocked_paths),
        str(lease_check["reason"]) if report_verdict(lease_check) != "pass" else "",
        str(editor_check["reason"]) if report_verdict(editor_check) != "pass" else "",
        str(patch_admission["reason"]) if report_verdict(patch_admission) != "pass" else "",
        str(scope_gaps[0]) if isinstance(scope_gaps, list) and scope_gaps else "",
    )
    return list(dict.fromkeys(error for error in checks if error))


def _blocked_path_error(blocked_paths: list[dict[str, object]]) -> str:
    reasons = {str(path["reason"]) for path in blocked_paths}
    priority = (
        ("path_invalid_control_character", "prewrite_path_invalid_control_character"),
        ("path_invalid_whitespace", "prewrite_path_invalid_whitespace"),
        ("path_outside_worktree", "prewrite_path_outside_worktree"),
    )
    explicit = next((gap for reason, gap in priority if reason in reasons), "")
    residual = next((reason for reason in reasons if reason != "protected_lane_tracked_write"), "")
    return explicit or residual or ("protected_lane_prewrite_blocked" if blocked_paths else "")


def _openspec_scope(report: dict[str, object]) -> dict[str, object]:
    """Return scope projected by the optional ETHOS self-profile adapter."""
    lifecycle = report.get("lifecycle")
    scope = lifecycle.get("scope_binding") if isinstance(lifecycle, dict) else None
    if isinstance(scope, dict):
        return string_mapping(scope)
    return {
        "verdict": "unknown",
        "state": "not_available",
        **{key: [] for key in _SCOPE_LIST_FIELDS},
        "required_gaps": ["openspec_scope_unavailable"],
    }


def _commitment_scope(
    root: Path, requested: tuple[str, ...], lease: dict[str, object]
) -> dict[str, object]:
    """Evaluate generic writes against the selected Commitment scope."""
    lease_verdict = report_verdict(lease)
    if lease.get("required") is True and lease_verdict != "pass":
        return {
            "verdict": lease_verdict,
            "state": "not_available",
            "required_gaps": [str(lease.get("reason") or "commitment_scope_unavailable")],
        }
    try:
        commitment = (
            load_lease_bound_commitment(root, lease=lease)
            if lease.get("required") is True
            else load_commitment(root)
        )
    except ValueError as exc:
        return {"verdict": "block", "state": "invalid", "required_gaps": [str(exc)]}
    uncovered = [
        path
        for path in requested
        if not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
    ]
    return {
        "verdict": "block" if uncovered else "pass",
        "state": "uncovered" if uncovered else "covered" if requested else "no_paths",
        "changed_paths": list(requested),
        "material_patterns": list(commitment.scope),
        "material_paths": list(requested),
        "uncovered_paths": uncovered,
        "required_gaps": [f"commitment_scope_uncovered:{path}" for path in uncovered],
    }

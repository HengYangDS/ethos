from __future__ import annotations

import os
from fnmatch import fnmatchcase
from pathlib import Path

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.binding import runtime_binding
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
from ethos.normalization.coercion import string_mapping
from ethos.repository.profile import profile_gate_registry

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
    role = effective["role"]
    runtime_check = runtime_binding_check(status)
    checked = [_check_path(root=root, path=path, role=role) for path in paths]
    tracked = any(path["tracked_candidate"] for path in checked)
    requested = tuple(
        str(path["relative_path"])
        for path in checked
        if path["tracked_candidate"] is True and path["relative_path"]
    )
    lease = _work_lane_lease_check(
        root=root, status=status, effective=effective, tracked_write_requested=tracked
    )
    profile_adapter: dict[str, object] = {}
    if openspec_profile_enabled(root):
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
        baseline_head=str(lease.get("expected_head") or ""),
        patch=patch,
    )
    blocked = [path for path in checked if path["allowed"] is False]
    gaps = _gaps(runtime_check, lease, editor, patch_report, scope, blocked)
    verdict = reduce_verdicts(
        report_verdict(runtime_check),
        "block" if blocked else "pass",
        report_verdict(lease),
        report_verdict(editor),
        report_verdict(patch_report),
        report_verdict(scope),
        required_gaps=tuple(gaps),
    )
    decision = _prewrite_decision(root, effective, checked, lease, verdict, tuple(gaps))
    return {
        "verdict": decision.verdict,
        "error": gaps[0] if gaps else "",
        "role": role,
        "branch": effective["branch"],
        "status_role": status_role,
        "status_branch": status_branch,
        "effective_context": effective,
        "runtime_binding": runtime_check,
        "work_lane_lease": lease,
        "editor_root": editor,
        "patch_admission": patch_report,
        **({"profile_adapter": profile_adapter} if profile_adapter else {}),
        "material_scope": scope,
        "paths": checked,
        "blocked_paths": blocked,
        "request_binding": decision.subject.model_dump(mode="json"),
        "decision": decision.to_payload(),
        "required_gaps": gaps,
    }


def _prewrite_status(root: Path) -> dict[str, object]:
    top = git_stdout(root, "rev-parse", "--show-toplevel")
    if not top:
        return {
            "root": str(root),
            "branch": "untracked",
            "role": "other",
            "runtime_binding": runtime_binding(root),
            "worktrees": [],
        }
    policy = load_branch_role_policy(repo := Path(top).resolve())
    branch = current_branch(repo)
    role = policy.role_for_branch(branch) if branch else ROLE_DETACHED
    return {
        "root": str(root),
        "branch": branch,
        "role": role,
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
    holder = str(lease.get("holder_ref") or "")
    if lease_state != "valid" or not holder:
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
    binding, binding_source = (
        (
            git_stdout(root, "rev-parse", "--verify", f"refs/heads/{branch}"),
            "rebase_branch_ref",
        )
        if source == "git_rebase_head_name"
        else (current, "head")
    )
    reason = _lease_binding_reason(
        root=root,
        branch=branch,
        lease=lease,
        actor=actor,
        current_head=binding,
    )
    return _lease_report(
        branch,
        actor,
        lease,
        ("block" if reason else "pass", True, reason or "matched"),
        observed=(current, binding, binding_source),
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
        "base_commitment_digest": str(lease.get("base_commitment_digest") or ""),
    }
    if observed:
        report.update(current_head=observed[0], binding_head=observed[1], head_source=observed[2])
    report["reason"] = reason
    return report


def _work_lane_lease(*, root: Path, status: dict[str, object], branch: str) -> dict[str, object]:
    current_path = Path(str(status.get("root") or root)).resolve()
    return leases_by_branch(current_path).get(branch, {})


def _lease_binding_reason(
    *, root: Path, branch: str, lease: dict[str, object], actor: str, current_head: str
) -> str:
    expected_head = str(lease.get("expected_head") or "")
    commitment_reason = ""
    try:
        load_lease_bound_commitment(root, lease=lease)
    except ValueError as exc:
        reason = str(exc)
        commitment_reason = f"{reason}:{branch}" if reason.startswith("lease_base_") else reason
    checks = (
        (
            actor != str(lease.get("holder_ref") or ""),
            f"lease_holder_mismatch:{branch}",
        ),
        (
            not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1,
            f"lease_generation_missing:{branch}",
        ),
        (
            expected_head != current_head,
            f"lease_head_stale:{branch}",
        ),
        (bool(commitment_reason), commitment_reason),
    )
    return next((reason for failed, reason in checks if failed), "")


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


def runtime_binding_check(status: dict[str, object]) -> dict[str, object]:
    binding = status.get("runtime_binding")
    available = isinstance(binding, dict)
    binding = binding if available else {}
    audit = str(binding.get("audit_root") or "")
    runner = str(binding.get("runner_source_root") or "")
    schema = str(binding.get("schema_source_root") or "")
    checkout_binding_required = bool(audit and profile_gate_registry(Path(audit)))
    runner_matches = binding.get("runner_matches_audit_root") is True
    schema_matches = binding.get("schema_matches_audit_root") is True
    common_runtime = binding.get("state") == "bound_to_common_runtime"
    verdict: Verdict = (
        "unknown"
        if not available
        else "pass"
        if not checkout_binding_required or (schema_matches and (runner_matches or common_runtime))
        else "block"
    )
    return {
        "verdict": verdict,
        "reason": (
            "runtime_binding_unavailable"
            if not available
            else "matched"
            if verdict == "pass"
            else "root_binding_mismatch"
        ),
        "audit_root": audit,
        "runner_source_root": runner,
        "schema_source_root": schema,
        "checkout_binding_required": checkout_binding_required,
        "runner_matches_audit_root": runner_matches,
        "schema_matches_audit_root": schema_matches,
        "runner_matches_common_runtime": common_runtime,
    }


def _editor_root_check(
    *, root: Path, editor_root: Path | None, require_editor_root: bool
) -> dict[str, object]:
    expected = root.resolve()
    actual = editor_root.resolve() if editor_root else None
    verdict: Verdict = (
        "pass" if actual == expected or (actual is None and not require_editor_root) else "block"
    )
    if actual == expected:
        reason = "matched"
    elif actual:
        reason = "editor_root_mismatch"
    else:
        reason = "editor_root_missing" if require_editor_root else "not_checked"
    return {
        "verdict": verdict,
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
    reasons = [str(path["reason"]) for path in blocked_paths]
    priority = (
        ("path_invalid_control_character", "prewrite_path_invalid_control_character"),
        ("path_invalid_whitespace", "prewrite_path_invalid_whitespace"),
        ("path_outside_worktree", "prewrite_path_outside_worktree"),
    )
    return next(
        (gap for reason, gap in priority if reason in reasons),
        next(
            (reason for reason in reasons if reason != "protected_lane_tracked_write"),
            "protected_lane_prewrite_blocked" if blocked_paths else "",
        ),
    )


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
        if not any(_scope_matches(path, pattern) for pattern in commitment.scope)
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


def _scope_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return pattern == "**" or fnmatchcase(path, pattern)

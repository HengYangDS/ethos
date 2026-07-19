from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import cast

from ethos.adapters.openspec.core import openspec_governance_report
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import git_stdout_checked
from ethos.adapters.repo.runtime.core import runtime_binding
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import current_branch
from ethos.adapters.repo.status.core import worktree_records
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.admission import DecisionBasis
from ethos_core.contracts.admission import MutationSubject
from ethos_core.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos_core.contracts.branch.roles import ROLE_DETACHED
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

_CONTROL_CHARACTER_UPPER_BOUND = 32
_DELETE_CONTROL_CODE_POINT = 127
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


def has_path_whitespace(text: str) -> bool:
    """Return whether a path token contains ambiguous whitespace."""
    return any(character.isspace() for character in text)


def has_invalid_path_token_character(text: str) -> bool:
    """Return whether a path token is unsafe as one mutation subject."""
    return has_control_character(text) or has_path_whitespace(text)


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
) -> dict[str, object]:
    status = _prewrite_status(root)
    status_role, status_branch = str(status["role"]), str(status["branch"])
    effective = _effective_write_context(root=root, role=status_role, branch=status_branch)
    role = effective["role"]
    runtime_check = _runtime_binding_check(status)
    checked = [_check_path(root=root, path=path, role=role) for path in paths]
    tracked = any(path["tracked_candidate"] for path in checked)
    requested = tuple(
        str(path["relative_path"])
        for path in checked
        if path["tracked_candidate"] is True and path["relative_path"]
    )
    lifecycle = openspec_governance_report(root, lifecycle=True, changed_paths=requested)
    scope = _material_scope_from_lifecycle(lifecycle)
    lease = _work_lane_lease_check(
        root=root, status=status, effective=effective, tracked_write_requested=tracked
    )
    editor = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked,
    )
    blocked = [path for path in checked if path["allowed"] is False]
    error = _error(runtime_check, lease, editor, scope, blocked)
    decision = _prewrite_decision(
        root=root,
        branch=effective["branch"],
        role=role,
        checked_paths=checked,
        lease_check=lease,
        error=error,
    )
    report: dict[str, object] = {"ok": not error, "error": error, "role": role}
    report.update(branch=effective["branch"], status_role=status_role, status_branch=status_branch)
    report.update(effective_context=effective, runtime_binding=runtime_check, work_lane_lease=lease)
    report.update(editor_root=editor, openspec_lifecycle=lifecycle, material_scope=scope)
    report.update(paths=checked, blocked_paths=blocked)
    report.update(request_binding=decision.subject.model_dump(mode="json"))
    report.update(decision=decision.to_payload(), required_gaps=[error] if error else [])
    return report


def _prewrite_status(root: Path) -> dict[str, object]:
    try:
        repo = Path(git_stdout_checked(root, "rev-parse", "--show-toplevel")).resolve()
    except (OSError, subprocess.CalledProcessError):
        return {
            "root": str(root),
            "branch": "untracked",
            "role": "other",
            "runtime_binding": runtime_binding(root),
            "worktrees": [],
        }
    policy = load_branch_role_policy(repo)
    branch = current_branch(repo)
    return {
        "root": str(root),
        "branch": branch,
        "role": policy.role_for_branch(branch),
        "runtime_binding": runtime_binding(repo),
        "worktrees": worktree_records(repo, current_path=repo, policy=policy),
    }


def _effective_write_context(*, root: Path, role: str, branch: str) -> dict[str, str]:
    rebase_branch = _rebase_head_branch(root) if role == ROLE_DETACHED else ""
    rebase_role = (
        load_branch_role_policy(root).role_for_branch(rebase_branch) if rebase_branch else ""
    )
    is_work_rebase = role == ROLE_DETACHED and rebase_role == ROLE_WORK_LANE
    return {
        "role": ROLE_WORK_LANE if is_work_rebase else role,
        "branch": rebase_branch if is_work_rebase else branch,
        "source": "git_rebase_head_name" if is_work_rebase else "prewrite_context",
        "rebase_head_name": rebase_branch,
    }


def _rebase_head_branch(root: Path) -> str:
    git_dir = _git_path(root)
    for state_dir in ("rebase-merge", "rebase-apply"):
        head_name = git_dir / state_dir / "head-name"
        if head_name.exists():
            return head_name.read_text(encoding="utf-8").strip().removeprefix("refs/heads/")
    return ""


def _git_path(root: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--git-path", "."],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return root / ".git"
    path = Path(completed.stdout.strip())
    return path if path.is_absolute() else root / path


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
        return _lease_report(branch, actor, {}, ok=True, required=False, reason="not_required")
    lease = _work_lane_lease(root=root, status=status, branch=branch)
    holder = str(lease.get("holder_ref") or "")
    if not holder:
        return _lease_report(
            branch,
            actor,
            lease,
            ok=False,
            required=True,
            reason=f"work_lane_missing_lease:{branch}",
        )
    current = _current_head(root)
    binding, binding_source = _binding_head(
        root=root, branch=branch, head_source=source, current_head=current
    )
    reason = _lease_binding_reason(branch=branch, lease=lease, actor=actor, current_head=binding)
    return _lease_report(
        branch,
        actor,
        lease,
        ok=not reason,
        required=True,
        reason=reason or "matched",
        observed=(current, binding, binding_source),
    )


def _lease_report(  # noqa: PLR0913, RUF100 - exact lease binding dimensions
    branch: str,
    actor: str,
    lease: dict[str, object],
    *,
    ok: bool,
    required: bool,
    reason: str,
    observed: tuple[str, str, str] | None = None,
) -> dict[str, object]:
    report: dict[str, object] = {"ok": ok, "required": required, "branch": branch}
    report.update(holder_ref=str(lease.get("holder_ref") or ""), invocation_holder_ref=actor)
    report.update(
        lease_id=str(lease.get("lease_id") or ""), epoch=integer_value(lease.get("epoch"))
    )
    report["expected_head"] = str(lease.get("expected_head") or "")
    if observed:
        report.update(current_head=observed[0], binding_head=observed[1], head_source=observed[2])
    report["reason"] = reason
    return report


def _work_lane_lease(*, root: Path, status: dict[str, object], branch: str) -> dict[str, object]:
    current_path = Path(str(status.get("root") or root)).resolve()
    worktrees = cast("list[dict[str, str]]", status["worktrees"])
    return leases_by_branch(worktrees, current_path=current_path).get(branch, {})


def _lease_binding_reason(
    *, branch: str, lease: dict[str, object], actor: str, current_head: str
) -> str:
    checks = (
        (
            str(lease.get("normalization_state") or "") != "normalized",
            f"lane_lease_legacy_ambiguous:{branch}",
        ),
        (actor != str(lease.get("holder_ref") or ""), f"lease_holder_mismatch:{branch}"),
        (
            not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1,
            f"lease_generation_missing:{branch}",
        ),
        (str(lease.get("expected_head") or "") != current_head, f"lease_head_stale:{branch}"),
    )
    return next((reason for failed, reason in checks if failed), "")


def _current_head(root: Path) -> str:
    return git_stdout(root, "rev-parse", "HEAD")


def _binding_head(
    *, root: Path, branch: str, head_source: str, current_head: str
) -> tuple[str, str]:
    if head_source != "git_rebase_head_name":
        return current_head, "head"
    return git_stdout(root, "rev-parse", "--verify", f"refs/heads/{branch}"), "rebase_branch_ref"


def _prewrite_decision(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    role: str,
    checked_paths: list[dict[str, object]],
    lease_check: dict[str, object],
    error: str,
) -> AdmissionDecision:
    paths = tuple(
        str(item.get("relative_path") or item.get("path") or "") for item in checked_paths
    )
    state = {
        "root": root.resolve().as_posix(),
        "role": role,
        "branch": branch,
        "paths": list(paths),
    }
    state.update(holder_ref=str(lease_check.get("holder_ref") or ""))
    state.update(
        lease_id=str(lease_check.get("lease_id") or ""),
        epoch=integer_value(lease_check.get("epoch")),
    )
    state["head"] = str(lease_check.get("expected_head") or "")
    return AdmissionDecision(
        verdict="block" if error else "allow",
        subject=MutationSubject(
            action="lane.prewrite", resource=f"{branch}:{','.join(paths)}", expected_state=state
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
        why=(error or "request_matches_current_local_state",),
        next=(("repair_required_gap",) if error else ()),
        required_gaps=((error,) if error else ()),
    )


def _runtime_binding_check(status: dict[str, object]) -> dict[str, object]:
    binding = status.get("runtime_binding")
    if not isinstance(binding, dict):
        return {
            "ok": True,
            "reason": "runtime_binding_unavailable",
            "audit_root": "",
            "runner_source_root": "",
            "schema_source_root": "",
            "product_audit_root": False,
        }
    audit = str(binding.get("audit_root") or "")
    runner = str(binding.get("runner_source_root") or "")
    schema = str(binding.get("schema_source_root") or "")
    product = bool(audit) and (Path(audit) / "packages/ethos/src/ethos/__init__.py").exists()
    runner_matches = binding.get("runner_matches_audit_root") is True
    schema_matches = binding.get("schema_matches_audit_root") is True
    ok = not product or (runner_matches and schema_matches)
    report: dict[str, object] = {"ok": ok, "reason": "matched" if ok else "root_binding_mismatch"}
    report.update(audit_root=audit, runner_source_root=runner, schema_source_root=schema)
    report.update(product_audit_root=product, runner_matches_audit_root=runner_matches)
    report["schema_matches_audit_root"] = schema_matches
    return report


def _editor_root_check(
    *, root: Path, editor_root: Path | None, require_editor_root: bool
) -> dict[str, object]:
    expected = root.resolve()
    actual = editor_root.resolve() if editor_root else None
    ok = actual == expected if actual else not require_editor_root
    return {
        "ok": ok,
        "required": require_editor_root,
        "expected": expected.as_posix(),
        "actual": actual.as_posix() if actual else "",
        "reason": "matched"
        if actual == expected
        else "editor_root_missing"
        if require_editor_root and not actual
        else "editor_root_mismatch"
        if actual
        else "not_checked",
    }


def _check_path(*, root: Path, path: Path, role: str) -> dict[str, object]:
    text = path.as_posix()
    if has_control_character(text):
        return _path_report(text, reason="path_invalid_control_character")
    if has_path_whitespace(text):
        return _path_report(text, reason="path_invalid_whitespace")
    root_path = root.resolve()
    resolved = (path if path.is_absolute() else root_path / path).resolve()
    try:
        relative = resolved.relative_to(root_path).as_posix()
    except ValueError:
        return _path_report(resolved.as_posix(), reason="path_outside_worktree")
    ignored = _is_ignored(root_path, relative)
    tracked = not ignored
    protected = role in PROTECTED_WRITE_ROLES and tracked
    return _path_report(
        resolved.as_posix(),
        relative=relative,
        ignored=ignored,
        tracked=tracked,
        allowed=not protected,
        reason="protected_lane_tracked_write" if protected else "allowed",
    )


def _path_report(  # noqa: PLR0913, RUF100 - exact path admission dimensions
    path: str,
    *,
    reason: str,
    relative: str = "",
    ignored: bool = False,
    tracked: bool = False,
    allowed: bool = False,
) -> dict[str, object]:
    return {
        "path": path,
        "relative_path": relative,
        "ignored": ignored,
        "tracked_candidate": tracked,
        "allowed": allowed,
        "reason": reason,
    }


def has_control_character(text: str) -> bool:
    """Return whether a path token contains unsafe control bytes."""
    return any(
        ord(character) < _CONTROL_CHARACTER_UPPER_BOUND
        or ord(character) == _DELETE_CONTROL_CODE_POINT
        for character in text
    )


def _is_ignored(root: Path, relative_path: str) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", "--", relative_path], cwd=root, check=False
        ).returncode
        == 0
    )


def _error(
    runtime_check: dict[str, object],
    lease_check: dict[str, object],
    editor_check: dict[str, object],
    material_scope: dict[str, object],
    blocked_paths: list[dict[str, object]],
) -> str:
    scope_gaps = material_scope.get("required_gaps")
    checks = (
        str(runtime_check["reason"]) if runtime_check["ok"] is not True else "",
        _blocked_path_error(blocked_paths),
        str(lease_check["reason"]) if lease_check["ok"] is not True else "",
        str(editor_check["reason"]) if editor_check["ok"] is not True else "",
        str(scope_gaps[0]) if isinstance(scope_gaps, list) and scope_gaps else "",
    )
    return next((error for error in checks if error), "")


def _blocked_path_error(blocked_paths: list[dict[str, object]]) -> str:
    reasons = {str(path["reason"]) for path in blocked_paths}
    priority = (
        ("path_invalid_control_character", "prewrite_path_invalid_control_character"),
        ("path_invalid_whitespace", "prewrite_path_invalid_whitespace"),
        ("path_outside_worktree", "prewrite_path_outside_worktree"),
    )
    return next(
        (gap for reason, gap in priority if reason in reasons),
        "protected_lane_prewrite_blocked" if blocked_paths else "",
    )


def _material_scope_from_lifecycle(report: dict[str, object]) -> dict[str, object]:
    """Return the canonical scope read model projected by OpenSpec lifecycle."""
    lifecycle = report.get("lifecycle")
    scope = lifecycle.get("scope_binding") if isinstance(lifecycle, dict) else None
    if isinstance(scope, dict):
        return cast("dict[str, object]", scope)
    empty = {key: [] for key in _SCOPE_LIST_FIELDS}
    return {"ok": True, "state": "not_available", **empty}

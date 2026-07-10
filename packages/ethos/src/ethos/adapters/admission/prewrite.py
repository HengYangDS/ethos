from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.admission import DecisionBasis
from ethos_core.contracts.admission import MutationSubject
from ethos_core.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos_core.contracts.branch.roles import ROLE_DETACHED
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

_CONTROL_CHARACTER_UPPER_BOUND = 32
_DELETE_CONTROL_CODE_POINT = 127


def has_path_whitespace(text: str) -> bool:
    """Return whether a path token contains whitespace and is therefore ambiguous."""
    return any(character.isspace() for character in text)


def has_invalid_path_token_character(text: str) -> bool:
    """Return whether a path token is unsafe to join or admit as a single subject."""
    return has_control_character(text) or has_path_whitespace(text)


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
) -> dict[str, object]:
    status = workspace_status(root)
    status_role = str(status["role"])
    status_branch = str(status["branch"])
    effective = _effective_write_context(root=root, role=status_role, branch=status_branch)
    role = effective["role"]
    runtime_check = _runtime_binding_check(status)
    checked_paths = [_check_path(root=root, path=path, role=role) for path in paths]
    tracked_write_requested = any(path["tracked_candidate"] for path in checked_paths)
    lease_check = _work_lane_lease_check(
        root=root,
        status=status,
        role=role,
        branch=effective["branch"],
        tracked_write_requested=tracked_write_requested,
    )
    editor_check = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked_write_requested,
    )
    blocked_paths = [path for path in checked_paths if path["allowed"] is False]
    error = _error(
        runtime_check=runtime_check,
        lease_check=lease_check,
        editor_check=editor_check,
        blocked_paths=blocked_paths,
    )
    decision = _prewrite_decision(
        root=root,
        branch=effective["branch"],
        role=role,
        checked_paths=checked_paths,
        lease_check=lease_check,
        error=error,
    )
    return {
        "ok": error == "",
        "error": error,
        "role": role,
        "branch": effective["branch"],
        "status_role": status_role,
        "status_branch": status_branch,
        "effective_context": effective,
        "runtime_binding": runtime_check,
        "work_lane_lease": lease_check,
        "editor_root": editor_check,
        "paths": checked_paths,
        "blocked_paths": blocked_paths,
        "request_binding": decision.subject.model_dump(mode="json"),
        "decision": decision.to_payload(),
        "required_gaps": [error] if error else [],
    }


def _effective_write_context(*, root: Path, role: str, branch: str) -> dict[str, str]:
    """Return the write-admission context for hook-time Git lifecycle states.

    A sanctioned ``git rebase`` temporarily detaches HEAD while replaying commits from
    the original branch. The repository's truth is still the same Work Lane when
    Git's rebase metadata says ``head-name = refs/heads/work/...``. Treat that narrow
    lifecycle state as the original Work Lane so the pre-commit fallback hook keeps
    checking paths instead of blocking ETHOS' own ``lane refresh-base`` transition.
    Other detached states remain protected and fail closed.
    """
    if role != ROLE_DETACHED:
        return {
            "role": role,
            "branch": branch,
            "source": "workspace_status",
            "rebase_head_name": "",
        }
    rebase_branch = _rebase_head_branch(root)
    policy = load_branch_role_policy(root)
    rebase_role = policy.role_for_branch(rebase_branch)
    if rebase_role != ROLE_WORK_LANE:
        return {
            "role": role,
            "branch": branch,
            "source": "workspace_status",
            "rebase_head_name": rebase_branch,
        }
    return {
        "role": ROLE_WORK_LANE,
        "branch": rebase_branch,
        "source": "git_rebase_head_name",
        "rebase_head_name": rebase_branch,
    }


def _rebase_head_branch(root: Path) -> str:
    git_dir = _git_path(root)
    for state_dir in ("rebase-merge", "rebase-apply"):
        head_name = git_dir / state_dir / "head-name"
        if not head_name.exists():
            continue
        value = head_name.read_text(encoding="utf-8").strip()
        return value.removeprefix("refs/heads/")
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
    role: str,
    branch: str,
    tracked_write_requested: bool,
) -> dict[str, object]:
    if role != ROLE_WORK_LANE or not tracked_write_requested:
        return {
            "ok": True,
            "required": False,
            "branch": branch,
            "holder_ref": "",
            "invocation_holder_ref": os.environ.get("ETHOS_ACTOR", "").strip(),
            "lease_id": "",
            "epoch": 0,
            "expected_head": "",
            "reason": "not_required",
        }
    lease = _work_lane_lease(root=root, status=status, branch=branch)
    holder_ref = str(lease.get("holder_ref") or "")
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if not holder_ref:
        return {
            "ok": False,
            "required": True,
            "branch": branch,
            "holder_ref": "",
            "invocation_holder_ref": actor,
            "lease_id": str(lease.get("lease_id") or ""),
            "epoch": int(lease.get("epoch") or 0),
            "expected_head": str(lease.get("expected_head") or ""),
            "reason": f"work_lane_missing_lease:{branch}",
        }
    current_head = _current_head(root)
    reason = _lease_binding_reason(
        branch=branch,
        lease=lease,
        actor=actor,
        current_head=current_head,
    )
    if reason:
        return {
            "ok": False,
            "required": True,
            "branch": branch,
            "holder_ref": holder_ref,
            "invocation_holder_ref": actor,
            "lease_id": str(lease.get("lease_id") or ""),
            "epoch": int(lease.get("epoch") or 0),
            "expected_head": str(lease.get("expected_head") or ""),
            "current_head": current_head,
            "reason": reason,
        }
    return {
        "ok": True,
        "required": True,
        "branch": branch,
        "holder_ref": holder_ref,
        "invocation_holder_ref": actor,
        "lease_id": str(lease.get("lease_id") or ""),
        "epoch": int(lease.get("epoch") or 0),
        "expected_head": str(lease.get("expected_head") or ""),
        "current_head": current_head,
        "reason": "matched",
    }


def _work_lane_lease(*, root: Path, status: dict[str, object], branch: str) -> dict[str, object]:
    current_path = Path(str(status.get("root") or root)).resolve()
    leases = leases_by_branch(cast_worktrees(status.get("worktrees")), current_path=current_path)
    return leases.get(branch, {})


def _lease_binding_reason(
    *, branch: str, lease: dict[str, object], actor: str, current_head: str
) -> str:
    if str(lease.get("normalization_state") or "") != "normalized":
        return f"lane_lease_legacy_ambiguous:{branch}"
    if actor != str(lease.get("holder_ref") or ""):
        return f"lease_holder_mismatch:{branch}"
    if not str(lease.get("lease_id") or "") or int(lease.get("epoch") or 0) < 1:
        return f"lease_generation_missing:{branch}"
    if str(lease.get("expected_head") or "") != current_head:
        return f"lease_head_stale:{branch}"
    return ""


def _current_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _prewrite_decision(
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
    expected_state = {
        "root": root.resolve().as_posix(),
        "role": role,
        "branch": branch,
        "paths": list(paths),
        "holder_ref": str(lease_check.get("holder_ref") or ""),
        "lease_id": str(lease_check.get("lease_id") or ""),
        "epoch": int(lease_check.get("epoch") or 0),
        "head": str(lease_check.get("expected_head") or ""),
    }
    return AdmissionDecision(
        verdict="block" if error else "allow",
        subject=MutationSubject(
            action="lane.prewrite",
            resource=f"{branch}:{','.join(paths)}",
            expected_state=expected_state,
        ),
        policy_refs=("commitment:tracked-write-admission",),
        evidence_refs=("evidence:current-worktree-and-lease-observation",),
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="holder_ref_equality" if lease_check.get("required") else "not_required",
            state_bindings=(
                "root",
                "role",
                "branch",
                "paths",
                "lease_id",
                "epoch",
                "head",
            ),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_worktree_runner",
            time_basis="evaluation_time",
        ),
        why=((error,) if error else ("request_matches_current_local_state",)),
        next=(("repair_required_gap",) if error else ()),
        required_gaps=((error,) if error else ()),
    )


def cast_worktrees(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        result.append({str(key): str(val) for key, val in item.items()})
    return result


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
    audit_root = str(binding.get("audit_root") or "")
    runner_source_root = str(binding.get("runner_source_root") or "")
    schema_source_root = str(binding.get("schema_source_root") or "")
    product_audit_root = (
        bool(audit_root)
        and (Path(audit_root) / "packages" / "ethos" / "src" / "ethos" / "__init__.py").exists()
    )
    runner_matches = binding.get("runner_matches_audit_root") is True
    schema_matches = binding.get("schema_matches_audit_root") is True
    ok = (not product_audit_root) or (runner_matches and schema_matches)
    reason = "matched" if ok else "root_binding_mismatch"
    return {
        "ok": ok,
        "reason": reason,
        "audit_root": audit_root,
        "runner_source_root": runner_source_root,
        "schema_source_root": schema_source_root,
        "product_audit_root": product_audit_root,
        "runner_matches_audit_root": runner_matches,
        "schema_matches_audit_root": schema_matches,
    }


def _editor_root_check(
    *,
    root: Path,
    editor_root: Path | None,
    require_editor_root: bool,
) -> dict[str, object]:
    expected = root.resolve()
    if editor_root is None:
        return {
            "ok": not require_editor_root,
            "required": require_editor_root,
            "expected": expected.as_posix(),
            "actual": "",
            "reason": "editor_root_missing" if require_editor_root else "not_checked",
        }
    actual = editor_root.resolve()
    return {
        "ok": actual == expected,
        "required": require_editor_root,
        "expected": expected.as_posix(),
        "actual": actual.as_posix(),
        "reason": "matched" if actual == expected else "editor_root_mismatch",
    }


def _check_path(*, root: Path, path: Path, role: str) -> dict[str, object]:
    path_text = path.as_posix()
    if has_control_character(path_text):
        return {
            "path": path_text,
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": "path_invalid_control_character",
        }
    if has_path_whitespace(path_text):
        return {
            "path": path_text,
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": "path_invalid_whitespace",
        }
    root_path = root.resolve()
    resolved = (path if path.is_absolute() else root_path / path).resolve()
    try:
        relative_path = resolved.relative_to(root_path).as_posix()
    except ValueError:
        return {
            "path": resolved.as_posix(),
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": "path_outside_worktree",
        }
    ignored = _is_ignored(root_path, relative_path)
    tracked_candidate = not ignored
    protected = role in PROTECTED_WRITE_ROLES and tracked_candidate
    return {
        "path": resolved.as_posix(),
        "relative_path": relative_path,
        "ignored": ignored,
        "tracked_candidate": tracked_candidate,
        "allowed": not protected,
        "reason": "protected_lane_tracked_write" if protected else "allowed",
    }


def has_control_character(text: str) -> bool:
    """Return whether a path token contains shell/log unsafe control bytes."""
    return any(
        ord(character) < _CONTROL_CHARACTER_UPPER_BOUND
        or ord(character) == _DELETE_CONTROL_CODE_POINT
        for character in text
    )


def _is_ignored(root: Path, relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative_path],
        cwd=root,
        check=False,
    )
    return completed.returncode == 0


def _error(
    *,
    runtime_check: dict[str, object],
    lease_check: dict[str, object],
    editor_check: dict[str, object],
    blocked_paths: list[dict[str, object]],
) -> str:
    error = ""
    if runtime_check["ok"] is not True:
        error = str(runtime_check["reason"])
    else:
        error = _blocked_path_error(blocked_paths)
    if not error and lease_check["ok"] is not True:
        error = str(lease_check["reason"])
    if not error and editor_check["ok"] is not True:
        error = str(editor_check["reason"])
    return error


def _blocked_path_error(blocked_paths: list[dict[str, object]]) -> str:
    reasons = {str(path["reason"]) for path in blocked_paths}
    if "path_invalid_control_character" in reasons:
        return "prewrite_path_invalid_control_character"
    if "path_invalid_whitespace" in reasons:
        return "prewrite_path_invalid_whitespace"
    if "path_outside_worktree" in reasons:
        return "prewrite_path_outside_worktree"
    if blocked_paths:
        return "protected_lane_prewrite_blocked"
    return ""

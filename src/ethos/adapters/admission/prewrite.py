"""Fresh repository write admission over authority, origin and exact effects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.admission.current.resolution import non_openspec_prewrite_scope
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.admission.patch_admission import patch_repair_action
from ethos.adapters.admission.patch_admission import profile_repair_scope
from ethos.adapters.admission.patch_admission import revalidate_staged_admission
from ethos.adapters.admission.patch_admission import staged_artifact_admission
from ethos.adapters.admission.paths import check_write_paths
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.root_repair import supporting_relocation_scope
from ethos.adapters.openspec.relocation import active_change_relocation_scope
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.runtime.binding import runtime_binding
from ethos.adapters.repo.runtime.binding import runtime_binding_check
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_DETACHED
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_mapping
from ethos.repository.profile import INVALID_PROFILE_ERROR

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.adapters.admission.current.authority import CurrentAuthority
    from ethos.adapters.repo.runtime.selection import SelectedRuntime

_STATE_BINDINGS = ("root", "role", "branch", "paths", "holder_ref", "generation", "head")


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
    patch: str = "",
    staged: bool = False,
    index_env: Mapping[str, str] | None = None,
    selected_runtime: SelectedRuntime | None = None,
    require_workspace: bool = False,
) -> dict[str, object]:
    status = _prewrite_status(root, selected_runtime=selected_runtime)
    status_role, status_branch = str(status["role"]), str(status["branch"])
    effective = _effective_write_context(root=root, role=status_role, branch=status_branch)
    runtime_check = runtime_binding_check(status)
    staged_report = (
        staged_artifact_admission(root, git_stdout(root, "rev-parse", "HEAD"), index_env=index_env)
        if staged
        else None
    )
    checked, origin_gap = check_write_paths(
        root, paths, effective["role"], effect_report=staged_report
    )
    tracked = any(path["tracked_candidate"] for path in checked)
    requested = tuple(
        str(path["relative_path"])
        for path in checked
        if path["tracked_candidate"] is True and path["relative_path"]
    )
    current_authority = observe_current_authority(
        root=root,
        branch=effective["branch"],
        actor=os.environ.get("ETHOS_ACTOR", "").strip(),
        required=effective["role"] == ROLE_WORK_LANE and tracked,
        head_source="rebase_branch_ref"
        if effective["source"] == "git_rebase_head_name"
        else "head",
    )
    authority = current_authority.projection()
    editor = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked,
    )
    patch_report = (
        staged_report
        if staged_report is not None
        else patch_admission(
            root=root,
            requested_paths=requested,
            baseline_head=str(authority.get("current_head") or ""),
            patch=patch,
        )
    )
    if (
        origin_gap.startswith("projection_ownership_unknown:")
        and patch
        and report_verdict(patch_report) == "pass"
    ):
        checked, origin_gap = check_write_paths(
            root, paths, effective["role"], effect_report=patch_report
        )
    if origin_gap:
        patch_report.update(verdict="unknown", reason=origin_gap)
    scope, official, profile_invalid = _prewrite_material_scope(
        root,
        effective=effective,
        requested=requested,
        current_authority=current_authority,
        patch_report=patch_report,
        require_workspace=require_workspace,
    )
    patch_report = revalidate_staged_admission(root, patch_report, index_env=index_env)
    _apply_path_effects(checked, patch_report, patch_supplied=bool(patch) or staged)
    blocked = [path for path in checked if path["allowed"] is False]
    gaps = _gaps(runtime_check, authority, editor, patch_report, scope, blocked)
    if profile_invalid and gaps:
        gaps = list(dict.fromkeys([INVALID_PROFILE_ERROR, *gaps]))
    verdict = reduce_verdicts(
        report_verdict(runtime_check),
        "block" if blocked else "pass",
        report_verdict(authority),
        report_verdict(editor),
        report_verdict(patch_report),
        report_verdict(scope),
        required_gaps=tuple(gaps),
    )
    decision = _prewrite_decision(
        root,
        effective,
        checked,
        authority,
        verdict,
        tuple(gaps),
        index_tree=str(patch_report.get("index_tree") or ""),
    )
    next_action = str(scope.get("next_action") or "")
    user_decision_required = bool(scope.get("user_decision_required", False))
    if verdict != "pass":
        if report_verdict(authority) != "pass":
            next_action, user_decision_required = current_authority.recovery(root)
        if not next_action and report_verdict(scope) != "pass":
            next_action = str(scope.get("next_action") or "")
            user_decision_required = bool(scope.get("user_decision_required", False))
        if not next_action and editor.get("reason") == "editor_root_missing":
            next_action = (
                f"ethos lane prewrite <path> --editor-root {editor['expected']} "
                "--require-editor-root --json"
            )
        if not next_action:
            next_action = next((str(path["repair"]) for path in blocked if path.get("repair")), "")
        if not next_action:
            next_action = patch_repair_action(root, requested, patch_report)
    return {
        "verdict": decision.verdict,
        "error": gaps[0] if gaps else "",
        "role": effective["role"],
        "branch": effective["branch"],
        "status_role": status_role,
        "status_branch": status_branch,
        "effective_context": effective,
        "runtime_binding": runtime_check,
        "work_lane_lease": authority,
        "mutation_authority": authority,
        "editor_root": editor,
        "patch_admission": patch_report,
        "material_scope": scope,
        "openspec": official,
        "paths": checked,
        "blocked_paths": blocked,
        "request_binding": decision.subject.model_dump(mode="json"),
        "decision": decision.to_payload(),
        "required_gaps": gaps,
        "next_action": next_action,
        "user_decision_required": user_decision_required,
    }


def _prewrite_material_scope(
    root: Path,
    *,
    effective: dict[str, str],
    requested: tuple[str, ...],
    current_authority: CurrentAuthority,
    patch_report: dict[str, object],
    require_workspace: bool,
) -> tuple[dict[str, object], dict[str, object], bool]:
    """Resolve current intent or an exact native carrier recovery."""
    try:
        profile_enabled = openspec_profile_enabled(root)
    except ValueError as error:
        if str(error) != INVALID_PROFILE_ERROR:
            raise
        profile_enabled = None
    if profile_enabled is None:
        scope = profile_repair_scope(
            root, role=effective["role"], requested_paths=requested, report=patch_report
        )
        return scope, {"verdict": "unknown", "required_gaps": [INVALID_PROFILE_ERROR]}, True
    if not profile_enabled:
        scope = non_openspec_prewrite_scope(requested)
        return scope, {"verdict": "pass", "change": None, "required_gaps": []}, False
    repair = active_change_relocation_scope(
        root, role=effective["role"], requested_paths=requested, report=patch_report
    )
    if repair:
        return repair, string_mapping(repair["openspec"]), False
    resolution = resolve_current_resolution(
        root,
        status={
            "role": effective["role"],
            "head": current_authority.current_head,
            "changed_paths": list(requested),
        },
        authority=current_authority,
        changed=False,
        prewrite_paths=requested,
        staged_tree_ref=str(patch_report["index_tree"]) if patch_report.get("index_tree") else None,
        require_workspace=require_workspace,
    )
    scope = resolution.scope_report(requested)
    if patch_report.get("profile_metadata_repair") is True and resolution.required_gaps:
        scope = profile_repair_scope(
            root, role=effective["role"], requested_paths=requested, report=patch_report
        )
    if resolution.required_gaps and patch_report.get("openspec_root_repair"):
        scope = (
            supporting_relocation_scope(
                role=effective["role"],
                requested_paths=requested,
                repair=patch_report["openspec_root_repair"],
                official=resolution.openspec,
            )
            or scope
        )
    return scope, resolution.openspec, False


def _apply_path_effects(
    checked: list[dict[str, object]],
    report: dict[str, object],
    *,
    patch_supplied: bool,
) -> None:
    """Annotate path observations without confusing absent files with deletions."""
    effects = report.get("effects")
    for item in checked:
        relative = str(item["relative_path"])
        item["effect"] = (
            effects.get(relative, "unspecified") if isinstance(effects, dict) else "unspecified"
        )
        if item.get("origin") == "projection" and not patch_supplied and item["allowed"]:
            item.update(allowed=False, reason=f"generated_projection_patch_required:{relative}")


def _prewrite_status(
    root: Path,
    *,
    selected_runtime: SelectedRuntime | None = None,
) -> dict[str, object]:
    top = git_stdout(root, "rev-parse", "--show-toplevel")
    repo = Path(top).resolve() if top else root
    if not top:
        return {
            "root": str(root),
            "branch": "untracked",
            "role": "other",
            "runtime_binding": runtime_binding(repo, selected_runtime=selected_runtime),
        }
    policy = load_branch_role_policy(repo)
    branch = current_branch(repo)
    return {
        "root": str(root),
        "branch": branch,
        "role": policy.role_for_branch(branch) if branch else ROLE_DETACHED,
        "runtime_binding": runtime_binding(repo, selected_runtime=selected_runtime),
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


def _prewrite_decision(
    root: Path,
    effective: dict[str, str],
    checked_paths: list[dict[str, object]],
    lease_check: dict[str, object],
    verdict: Verdict,
    gaps: tuple[str, ...],
    *,
    index_tree: str = "",
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
                "generation": integer_value(lease_check.get("generation")),
                "head": str(lease_check.get("current_head") or ""),
                **({"index_tree": index_tree} if index_tree else {}),
            },
        ),
        policy_refs=("commitment:tracked-write-admission",),
        evidence_refs=("evidence:current-worktree-and-lease-observation",),
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="holder_ref_equality" if lease_check.get("required") else "not_required",
            state_bindings=(*_STATE_BINDINGS, "index_tree") if index_tree else _STATE_BINDINGS,
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
        str(lease_check["reason"]) if report_verdict(lease_check) != "pass" else "",
        str(runtime_check["reason"]) if report_verdict(runtime_check) != "pass" else "",
        _blocked_path_error(blocked_paths),
        str(editor_check["reason"]) if report_verdict(editor_check) != "pass" else "",
        str(patch_admission["reason"]) if report_verdict(patch_admission) != "pass" else "",
        str(scope_gaps[0]) if isinstance(scope_gaps, list) and scope_gaps else "",
    )
    repair_gaps = (
        scope_gaps[1:]
        if material_scope.get("state") == "profile_repair" and isinstance(scope_gaps, list)
        else []
    )
    return list(dict.fromkeys(error for error in (*checks, *repair_gaps) if error))


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

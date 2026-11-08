"""Compose transport-independent repository observations and continuations."""

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.mutation.branch_roles import pending_role_rebindings
from ethos.adapters.mutation.branch_roles import rebinding_command
from ethos.adapters.mutation.branch_roles import rebinding_gaps
from ethos.adapters.mutation.lane_lifecycle.candidate_projection import bootstrap_candidate
from ethos.adapters.openspec.cli import OFFICIAL_PACKAGE_SPEC
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.lifecycle.report import openspec_official_cli
from ethos.adapters.openspec.selection import selected_change
from ethos.adapters.repo.hook.observation import commit_policy_enforcement
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.application.catalog import catalog_operation
from ethos.application.land.closeout import closeout_command_from_status
from ethos.application.peer_identity import peer_identity_status
from ethos.contracts.branch.roles import LIFECYCLE_COMMIT_ROLES
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.outcome import Outcome
from ethos.contracts.verdict import report_verdict
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.normalization.coercion import string_sequence
from ethos.repository.context import repository_context
from ethos.result import EthosResult

# Under two hours left, the Lease outlasts no loaded full proof, so status points at its renewal.
_RENEWAL_THRESHOLD_SECONDS = 2 * 60 * 60


def _count(value: object) -> int:
    return len(value) if isinstance(value, list | tuple) else 0


def lease_summary(
    authority: Mapping[str, object], *, role: str, now: datetime
) -> dict[str, object]:
    """Name a Work Lane's Lease generation, expiry and seconds left; nothing for other roles."""
    generation, expires_at = authority.get("generation"), str(authority.get("expires_at") or "")
    if role != ROLE_WORK_LANE or not isinstance(generation, int) or generation < 1:
        return {}
    try:
        left = int((datetime.fromisoformat(expires_at) - now).total_seconds())
    except ValueError:
        return {}
    return {
        "lease_generation": generation,
        "lease_expires_at": expires_at,
        "lease_seconds_left": left,
    }


def renewal_action(summary: Mapping[str, object], *, root: Path) -> str:
    """Point at the renewal preview under two hours left, and at resumption once expired."""
    left = summary.get("lease_seconds_left")
    if not isinstance(left, int) or left >= _RENEWAL_THRESHOLD_SECONDS:
        return ""
    verb = "renew" if left > 0 else "resume"
    return f"ethos lane lease {verb} --root {root.as_posix()}"


@catalog_operation("status")
def inspect_repository(root: Path, *, change: str | None = None) -> EthosResult:
    """Inspect bounded truth, authority, gaps, coordination, and next action."""
    with selected_change(change):
        repo = root.resolve()
        runtime = hook_runtime_binding(repo)
        observed, authority = workspace_status_observation(
            repo, include_foreign_path_scope=False, hook_binding=runtime
        )
        resolution = (
            resolve_current_resolution(
                repo,
                status=observed,
                authority=authority,
            )
            if observed.get("role") == ROLE_WORK_LANE
            else None
        )
        generation_scope = resolution.scope if resolution is not None else CurrentScope(())
        validation = workspace_status_validation(repo, observed)
        landing = cast("dict[str, object]", observed.get("landing_readiness") or {})
        generation_gaps = (
            ()
            if "candidate_base_stale" in string_sequence(landing.get("required_gaps"))
            else generation_scope.gaps
        )
        gaps = tuple(
            dict.fromkeys(
                (
                    *string_sequence(observed.get("required_gaps")),
                    *workspace_status_validation_gaps(validation),
                    *(resolution.required_gaps if resolution is not None else generation_gaps),
                    *(
                        ("change_scope_exceeded",)
                        if any(item.state == "uncovered" for item in generation_scope.attributions)
                        else ()
                    ),
                )
            )
        )
        foreign = cast("list[dict[str, object]]", observed.get("foreign_work_lanes") or [])
        unbound = cast("list[dict[str, object]]", observed.get("unbound_work_lane_refs") or [])
        coordination_gaps = string_sequence(observed.get("coordination_gaps"))
        authority_projection = authority.projection() if authority is not None else {}
        lease = lease_summary(
            authority_projection, role=str(observed.get("role") or ""), now=datetime.now(UTC)
        )
        commit_policy = commit_policy_enforcement(
            repo, runtime, signer_required=observed.get("role") in LIFECYCLE_COMMIT_ROLES
        )
        runtime_gaps = string_sequence(runtime["required_gaps"]) if runtime["required"] else ()
        commit_policy_gaps = string_sequence(commit_policy.get("required_gaps"))
        # Worktrees left on renamed legacy role refs come first: every other route reads them.
        rebinding = pending_role_rebindings(repo)
        rebinding_action = (
            rebinding_command(repo, rebinding, str(observed.get("head") or "")) if rebinding else ""
        )
        gaps = tuple(
            dict.fromkeys((*gaps, *rebinding_gaps(rebinding), *runtime_gaps, *commit_policy_gaps))
        )
        data = {
            "root": observed.get("root", ""),
            "branch": observed.get("branch", ""),
            "head": observed.get("head", ""),
            "role": observed.get("role", ""),
            "dirty": bool(observed.get("dirty")),
            "changed_path_count": _count(observed.get("changed_paths")),
            "selected_carrier": generation_scope.selected_carrier,
            "path_attributions": list(generation_scope.attribution_projection()),
            "authority": authority_projection,
            "landing_readiness": {
                "state": landing.get("state", ""),
                "required_gaps": string_sequence(landing.get("required_gaps")),
                "next_action": landing.get("next_action", ""),
            },
            "hook_runtime": runtime,
            "commit_policy_enforcement": commit_policy,
            "coordination": {
                "detail_state": "deferred",
                "blocking": any(gap.startswith("coordination_gap:") for gap in gaps),
                "foreign_work_lane_count": len(foreign),
                "unbound_work_lane_count": len(unbound),
                "missing_lease_count": sum(
                    lane.get("lease_state") == "missing" for lane in foreign
                ),
                "advisory_count": len(coordination_gaps),
                "required_count": sum(gap.startswith("coordination_gap:") for gap in gaps),
            },
        }
        compact_coordination = data["coordination"]
        # Validation and the current resolution declare their own class; the other gaps block.
        owned = Outcome.of(
            report_verdict(validation), *workspace_status_validation_gaps(validation)
        )
        if resolution is not None:
            owned = owned.combine(Outcome.of(resolution.verdict, *resolution.required_gaps))
        unowned = Outcome.of("pass", *(gap for gap in gaps if gap not in owned.gaps))
        verdict = owned.combine(unowned).verdict
        closeout_action = closeout_command_from_status(repo, observed)
        stage_gates = cast("dict[str, object]", observed.get("stage_gates") or {})
        stage_action = str(stage_gates.get("next_action") or "")
        scope_exceeded = any(item.state == "uncovered" for item in generation_scope.attributions)
        runtime_action = runtime["next_action"] if runtime_gaps else ""
        commit_policy_action = str(commit_policy.get("next_action") or "")
        candidate_action = ""
        candidate_decision = False
        if (
            observed.get("role") == ROLE_ACCEPTED_ROOT
            and not observed.get("dirty")
            and {"candidate_branch_missing", "candidate_worktree_missing"}.intersection(gaps)
        ):
            candidate_report = bootstrap_candidate(
                root=repo, expect_head=str(observed.get("head") or ""), observed_status=observed
            )
            candidate_action = str(candidate_report.get("next_action") or "")
            candidate_decision = bool(candidate_report.get("user_decision_required"))
        next_action = rebinding_action or (
            resolution.next_action
            if resolution is not None
            and (resolution.authority is None or resolution.authority.verdict != "pass")
            else candidate_action
            or runtime_action
            or commit_policy_action
            or renewal_action(lease, root=repo)
            or closeout_action
            or (
                "repair the selected Commitment scope for the uncovered current-generation paths"
                if scope_exceeded
                else resolution.next_action
                if resolution is not None and resolution.next_action
                else stage_action
            )
            or ("ethos lane status --json" if foreign or unbound else "")
        )
        user_decision_required = (
            candidate_decision
            if candidate_action and next_action == candidate_action
            else False
            if next_action in {runtime_action, commit_policy_action} and next_action
            else resolution.user_decision_required
            if resolution is not None and resolution.next_action
            else bool(stage_gates.get("user_decision_required", False))
            if next_action == stage_action
            else False
        )
        return EthosResult(
            command="status",
            verdict=verdict,
            state=(
                "blocked"
                if verdict == "block"
                else "unknown"
                if verdict == "unknown"
                else "dirty"
                if data["dirty"]
                else "ready"
            ),
            summary={
                key: data[key] for key in ("root", "branch", "role", "dirty", "changed_path_count")
            }
            | {
                "foreign_work_lane_count": compact_coordination["foreign_work_lane_count"],
                "unbound_work_lane_count": compact_coordination["unbound_work_lane_count"],
                "missing_lease_count": compact_coordination["missing_lease_count"],
                "coordination_detail_state": compact_coordination["detail_state"],
                "coordination_advisory_count": compact_coordination["advisory_count"],
                "coordination_blocking": compact_coordination["blocking"],
            }
            | lease
            | {"peer_identity_advisories": peer_identity_status(repo)},
            diagnostics=(validation,),
            required_gaps=gaps,
            next_action=next_action,
            user_decision_required=user_decision_required,
            governance_context=repository_context(repo)
            | {
                "official_openspec": openspec_official_cli(
                    package=OFFICIAL_PACKAGE_SPEC,
                    base_command=openspec_base_command(execution_probe=False),
                )
            },
            data=data,
        )

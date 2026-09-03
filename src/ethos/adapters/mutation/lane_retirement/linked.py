from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_retirement.linked_effect import linked_retirement_plan
from ethos.adapters.mutation.lane_retirement.observation import output
from ethos.adapters.mutation.lane_retirement.operation import apply_operation
from ethos.adapters.mutation.lane_retirement.operation import persist_operation
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.retirement import RetirementOperation
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.verdict import Verdict


class LinkedRetirementRequest(BaseModel):
    """Exact request for one linked Work Lane retirement transition."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, strict=True, extra="forbid")

    branch: str | None = None
    path: str | None = None
    expect_head: str | None = None
    absorbed_by: str = ""
    reason: str = ""
    authorize: bool = False
    apply: bool = False


def compile_retirement_operation(
    control_root: Path,
    *,
    mode: Literal["landed", "superseded"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority: dict[str, object],
    accepted_head: str,
    reason: str,
) -> RetirementOperation:
    """Compile one immutable linked retirement request from admitted facts."""
    actor = effects.actor_ref()
    execution_root, plan = linked_retirement_plan(
        control_root,
        lane,
        accepted=(policy.accepted_branch, accepted_head),
        authority=authority,
        mode=mode,
        actor=actor,
        worktree_clean=True,
    )
    branch = str(lane["branch"])
    lease_state = str(lane.get("lease_state") or "missing")
    target_lease = (
        lease_generation(
            {**cast("dict[str, object]", lane.get("lease") or {}), "lane_ref": branch}
        )
        if lease_state != "missing"
        else {}
    )
    recovery_required = bool(lane.get("recovery_required"))
    return RetirementOperation(
        repository_common_dir=Path(git_common_dir(control_root)).resolve().as_posix(),
        repository_identity=repository_identity(control_root, tree_ref=str(lane["head"])),
        control_root=control_root.resolve().as_posix(),
        execution_root=execution_root.resolve().as_posix(),
        mode=mode,
        branch=branch,
        head=str(lane["head"]),
        tree=current_tree(control_root, str(lane["head"])),
        accepted_branch=policy.accepted_branch,
        accepted_head=accepted_head,
        worktree_path=str(lane.get("path") or ""),
        worktree_initial="unbound" if recovery_required else "linked",
        lease_state=cast("Literal['valid', 'expired', 'missing']", lease_state),
        lease=target_lease,
        authority={
            "kind": "successor" if authority.get("branch") != lane.get("branch") else "owner",
            "actor": actor,
            "branch": str(authority.get("branch") or ""),
            "head": str(authority.get("head") or ""),
        },
        reason={
            "code": "accepted-absorption" if mode == "landed" else "successor-absorption",
            "summary": reason or f"{mode} Work Lane retirement",
        },
        git_plan=plan.model_dump(mode="json"),
    )


def retire_linked_work_lane(
    *,
    root: Path,
    mode: Literal["landed", "superseded"],
    request: LinkedRetirementRequest,
) -> dict[str, object]:
    """Plan or execute one holder-bound linked-lane retirement."""
    repo = repository_root(root)
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    policy = load_branch_role_policy(repo)
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    accepted_head = output(repo, "rev-parse", policy.accepted_branch) or ""
    control_root = effects.control_root(worktrees, repo)
    leases = leases_by_branch(repo)
    lanes, lane = _retirement_target(
        repo=repo,
        policy=policy,
        worktrees=worktrees,
        leases=leases,
        request=request,
        mode=mode,
        branch=branch,
        accepted_head=accepted_head,
    )
    successor = (
        _leased_successor(
            repo=repo,
            policy=policy,
            worktrees=worktrees,
            leases=leases,
            target_branch=branch,
            absorbed_by=absorbed_by,
            accepted_head=accepted_head,
        )
        if mode == "superseded" and absorbed_by != accepted_head
        else {}
    )
    authority = successor or lane
    gaps = (
        _landed_gaps(
            branch=branch,
            request=request,
            lanes=lanes,
        )
        if mode == "landed"
        else _superseded_gaps(
            repo=repo,
            policy=policy,
            request=request,
            lane=lane,
            successor=successor,
            accepted_head=accepted_head,
        )
    )
    gaps.extend(
        _effect_readiness_gaps(
            repo,
            control_root,
            mode=mode,
            policy=policy,
            lane=lane,
            authority=authority,
            accepted_head=accepted_head,
            required_gaps=gaps,
            apply=request.apply,
        )
    )
    required_gaps = sorted(set(gaps))

    verdict = _retirement_verdict(required_gaps)
    if lane:
        lane = {**lane, "retire_ready": not required_gaps, "required_gaps": required_gaps}

    state = "planned" if mode == "landed" else "ready_to_retire_superseded"
    if verdict != "pass":
        state = "blocked" if verdict == "block" else "unknown"

    def mutation(current_gaps: list[str]) -> dict[str, object]:
        required_holder = effects.holder_ref(authority)
        gaps = tuple(sorted(set(current_gaps)))
        current_verdict = _retirement_verdict(gaps)
        expected_state = {
            "ref": f"refs/heads/{branch}" if branch else "",
            "head": (request.expect_head or "").strip(),
            "path": (request.path or "").strip(),
            "invocation_holder_ref": effects.actor_ref(),
            "required_holder_ref": required_holder,
            "authority_branch": authority.get("branch", ""),
            "authority_head": authority.get("head", ""),
            "accepted_head": accepted_head,
            "lease": authority.get("lease", {}),
            "target_lease": lane.get("lease", {}),
            **({"absorbed_by": absorbed_by, "reason": reason} if mode == "superseded" else {}),
        }
        decision = admission_decision(
            subject=MutationSubject(
                action=f"lane.retire.{mode}",
                resource=f"refs/heads/{branch}" if branch else "work-lane",
                expected_state=expected_state,
            ),
            verdict=current_verdict,
            basis=DecisionBasis(
                enforcement_boundary=(
                    "sqlite_generation_lock_and_git_ref_transaction"
                    if required_holder
                    else "git_ref_and_worktree_transition"
                ),
                identity_basis="exact_lease_generation" if required_holder else "not_evaluated",
                state_bindings=tuple(expected_state),
                evidence_boundary="current_git_lane_and_lease_observation",
                verifier_provenance="current_runner",
                time_basis="evaluation_time",
            ),
            policy_ref=(
                "openspec/specs/repository-governance/spec.md"
                "#linked-work-lane-retirement-has-one-exact-effect"
                if mode == "landed"
                else "commitment:lane-retire-superseded-admission"
            ),
            required_gaps=gaps,
            why=("ready",) if current_verdict == "pass" else (),
        )
        return mutation_envelope(
            command=f"lane-retire-{mode}",
            apply=request.apply,
            authorized=request.authorize,
            expect_head=request.expect_head,
            decision=decision,
        )

    report: dict[str, object] = {
        "verdict": verdict,
        "state": state,
        "branch": branch,
        "mutation": mutation(required_gaps),
        "required_gaps": required_gaps,
        **({"lanes": lanes} if mode == "landed" else {"lane": lane}),
    }
    report |= _continuation(
        repo,
        mode=mode,
        request=request,
        report=report,
        authority=authority,
    )
    if required_gaps:
        return report
    if not request.apply:
        return report

    operation = compile_retirement_operation(
        cast("Path", control_root),
        mode=mode,
        policy=policy,
        lane=lane,
        authority=authority,
        accepted_head=accepted_head,
        reason=reason,
    )
    receipt = persist_operation(cast("Path", control_root), operation)
    effect = apply_operation(
        cast("Path", control_root),
        operation,
        request_receipt=receipt,
        apply=True,
    )
    effect_gaps = string_sequence(effect.get("required_gaps"))
    return report | effect | {"receipt": receipt, "mutation": mutation(effect_gaps)}


def _continuation(
    repo: Path,
    *,
    mode: Literal["landed", "superseded"],
    request: LinkedRetirementRequest,
    report: dict[str, object],
    authority: dict[str, object],
) -> dict[str, object]:
    """Return the sole public continuation owned by linked retirement."""
    gaps = tuple(string_sequence(report.get("required_gaps")))
    holder = effects.holder_ref(authority)
    if "foreign_work_lane_retire_authority_required" in gaps and holder:
        return {
            "next_action": f"export ETHOS_ACTOR={shlex.quote(holder)}",
            "user_decision_required": True,
        }
    if gaps:
        return {
            "next_action": f"ethos lane status --root {shlex.quote(repo.as_posix())} --json",
            "user_decision_required": "authorization_required" in gaps,
        }
    if request.apply:
        return {
            "next_action": f"ethos status --root {shlex.quote(repo.as_posix())} --json",
            "user_decision_required": False,
        }
    parts = ["ethos", "lane", "retire", mode]
    for option, value in (
        ("--branch", request.branch),
        ("--path", request.path if mode == "superseded" else None),
        ("--expect-head", request.expect_head),
        ("--absorbed-by", request.absorbed_by if mode == "superseded" else None),
        ("--reason", request.reason if mode == "superseded" else None),
    ):
        if value:
            parts.extend((option, shlex.quote(value)))
    parts.extend(("--authorize", "--apply", "--root", shlex.quote(repo.as_posix()), "--json"))
    return {"next_action": " ".join(parts), "user_decision_required": True}


def _retirement_target(
    *,
    repo: Path,
    policy: BranchRolePolicy,
    worktrees: list[dict[str, object]],
    leases: dict[str, dict[str, object]],
    request: LinkedRetirementRequest,
    mode: Literal["landed", "superseded"],
    branch: str,
    accepted_head: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    candidates = [
        item
        for item in worktrees
        if item["role"] == ROLE_WORK_LANE
        and ((mode == "landed" and request.branch is None) or item["branch"] == branch)
    ]
    lanes = [
        _with_archive_absorption(
            repo,
            effects.lane(repo, item, leases, accepted_head=accepted_head, mode=mode),
            accepted_head,
        )
        for item in candidates
    ]
    if lanes or mode == "landed":
        return lanes, lanes[0] if lanes else {}
    lane = _unbound_retirement_target(
        policy=policy,
        worktrees=worktrees,
        leases=leases,
        branch=branch,
        path=(request.path or "").strip(),
        head=(output(repo, "rev-parse", "--verify", branch) or "") if branch else "",
    )
    return lanes, _with_archive_absorption(repo, lane, accepted_head) if lane else {}


def _unbound_retirement_target(
    *,
    policy: BranchRolePolicy,
    worktrees: list[dict[str, object]],
    leases: dict[str, dict[str, object]],
    branch: str,
    path: str,
    head: str,
) -> dict[str, object]:
    """Compile one exact unbound source without recreating its worktree."""
    if not path:
        return {}
    target = Path(path)
    lease = leases.get(branch, {})
    lease_state = str(lease.get("lease_state") or "missing")
    gaps = _unbound_path_gaps(target, worktrees)
    gaps.extend(
        gap
        for failed, gap in (
            (policy.role_for_branch(branch) != ROLE_WORK_LANE, "superseded_retire_not_work_lane"),
            (not head, "superseded_retire_branch_not_found"),
            (lease_state == "unknown", f"work_lane_lease_unknown:{branch}"),
            (lease_state == "expired", f"work_lane_lease_expired:{branch}"),
            (
                lease_state not in {"valid", "unknown", "expired"},
                f"work_lane_missing_lease:{branch}",
            ),
        )
        if failed
    )
    return {
        "branch": branch,
        "path": target.as_posix(),
        "head": head,
        "lease": {key: value for key, value in lease_generation(lease).items() if key != "lane_ref"}
        | {"mints_authority": False},
        "lease_state": lease_state,
        "recovery_required": True,
        "retire_ready": not gaps,
        "required_gaps": sorted(set(gaps)),
    }


def _unbound_path_gaps(target: Path, worktrees: list[dict[str, object]]) -> list[str]:
    if not target.is_absolute():
        return ["retirement_recovery_path_not_absolute"]
    if target.exists() or target.is_symlink():
        return ["retirement_recovery_path_collision"]
    resolved = target.resolve()
    registered = any(
        path and Path(path).resolve() == resolved
        for row in worktrees
        if (path := str(row.get("path") or ""))
    )
    return ["retirement_recovery_path_registered"] if registered else []


def _retirement_verdict(gaps: list[str] | tuple[str, ...]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


def _effect_readiness_gaps(
    repo: Path,
    control_root: Path | None,
    *,
    mode: Literal["landed", "superseded"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority: dict[str, object],
    accepted_head: str,
    required_gaps: list[str],
    apply: bool,
) -> list[str]:
    if apply and control_root is None:
        return ["retirement_control_root_unavailable"]
    if required_gaps or control_root is None:
        return []
    return effects.effect_gaps(
        repo,
        control_root,
        mode=mode,
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head=accepted_head,
    )


def _with_archive_absorption(
    repo: Path, lane: dict[str, object], accepted_head: str
) -> dict[str, object]:
    mapping = effects.archived_carrier_absorption(
        repo,
        head=str(lane.get("head") or ""),
        accepted_head=accepted_head,
    )
    return {**lane, **({"archive_absorption": mapping} if mapping else {})}


def _landed_gaps(
    *,
    branch: str,
    request: LinkedRetirementRequest,
    lanes: list[dict[str, object]],
) -> list[str]:
    gaps = [
        gap
        for failed, gap in (
            (request.branch is not None and not lanes, "retire_branch_not_found"),
            (request.apply and not branch, "retire_branch_required"),
            (request.apply and not request.authorize, "authorization_required"),
        )
        if failed
    ]
    if branch and lanes:
        gaps.extend(map(str, cast("list[object]", lanes[0]["required_gaps"])))
        gaps.extend(effects.holder_gaps(lanes[0]))
        expected = (request.expect_head or "").strip()
        if request.apply and not expected:
            gaps.append("expect_head_required")
        elif request.apply and expected != str(lanes[0]["head"]):
            gaps.append("expect_head_mismatch")
    return gaps


def _superseded_gaps(
    *,
    repo: Path,
    policy: BranchRolePolicy,
    request: LinkedRetirementRequest,
    lane: dict[str, object],
    successor: dict[str, object],
    accepted_head: str,
) -> list[str]:
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    gaps = _superseded_target_gaps(repo, policy, branch, lane)
    if lane:
        gaps.extend(_source_lane_gaps(lane, branch=branch, successor=successor))
        gaps.extend(effects.holder_gaps(successor or lane))
    if successor:
        gaps.extend(string_sequence(successor.get("required_gaps")))
    gaps.extend(
        gap
        for failed, gap in (
            (not reason, "retire_reason_required"),
            (not accepted_head, "accepted_head_unavailable"),
            (not absorbed_by, "absorbed_by_required"),
            (
                bool(absorbed_by and absorbed_by != accepted_head and not successor),
                "absorbed_by_not_current_authority_head",
            ),
            (request.apply and not request.authorize, "authorization_required"),
        )
        if failed
    )
    head = str(lane.get("head") or "")
    if gap := _absorption_gap(
        repo,
        source_head=head,
        absorbed_by=absorbed_by,
        accepted_head=accepted_head,
        successor=successor,
        lane=lane,
    ):
        gaps.append(gap)
    expected = (request.expect_head or "").strip()
    if not expected:
        gaps.append("expect_head_required")
    elif head and expected != head:
        gaps.append("expect_head_mismatch")
    return gaps


def _superseded_target_gaps(
    repo: Path,
    policy: BranchRolePolicy,
    branch: str,
    lane: dict[str, object],
) -> list[str]:
    if not branch:
        return ["superseded_retire_branch_required"]
    if output(repo, "rev-parse", "--verify", branch) is None:
        return ["superseded_retire_branch_not_found"]
    if policy.role_for_branch(branch) != ROLE_WORK_LANE:
        return ["superseded_retire_not_work_lane"]
    return [] if lane else ["superseded_retire_worktree_not_linked"]


def _source_lane_gaps(
    lane: dict[str, object],
    *,
    branch: str,
    successor: dict[str, object],
) -> list[str]:
    gaps = string_sequence(lane.get("required_gaps"))
    if not successor:
        return gaps
    gaps = [gap for gap in gaps if gap != f"work_lane_missing_lease:{branch}"]
    if lane.get("lease_state") != "missing":
        gaps.append("retirement_source_lease_present")
    return gaps


def _absorption_gap(
    repo: Path,
    *,
    source_head: str,
    absorbed_by: str,
    accepted_head: str,
    successor: dict[str, object],
    lane: dict[str, object],
) -> str:
    if not source_head or not absorbed_by:
        return ""
    if absorbed_by == accepted_head:
        return (
            ""
            if effects.absorbed(repo, source_head, accepted_head) or lane.get("archive_absorption")
            else "superseded_lane_not_absorbed_by_accepted"
        )
    if successor and not is_ancestor(repo, source_head, absorbed_by):
        return "superseded_lane_not_absorbed_by_successor"
    return ""


def _leased_successor(
    *,
    repo: Path,
    policy: BranchRolePolicy,
    worktrees: list[dict[str, object]],
    leases: dict[str, dict[str, object]],
    target_branch: str,
    absorbed_by: str,
    accepted_head: str,
) -> dict[str, object]:
    """Resolve the current exact leased Work Lane that absorbed a source lane."""
    branch = output(repo, "symbolic-ref", "--short", "HEAD") or ""
    current = next(
        (
            worktree
            for worktree in worktrees
            if worktree["branch"] == branch
            and worktree["role"] == ROLE_WORK_LANE
            and branch != target_branch
            and worktree["head"] == absorbed_by
        ),
        None,
    )
    if current is None or policy.role_for_branch(branch) != ROLE_WORK_LANE:
        return {}
    return effects.lane(
        repo,
        current,
        leases,
        accepted_head=accepted_head,
        mode="superseded",
    )

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import MutationAdmissionRequest
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


class LinkedRetirementRequest(BaseModel):
    """Exact request for one linked Work Lane retirement transition."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    branch: str | None = None
    expect_head: str | None = None
    absorbed_by: str = ""
    reason: str = ""
    authorize: bool = False
    apply: bool = False


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
    accepted_head = effects.output(repo, "rev-parse", policy.accepted_branch) or ""
    control_root = effects.control_root(worktrees, repo)
    leases = leases_by_branch(repo)
    candidates = [
        lane
        for lane in worktrees
        if lane["role"] == ROLE_WORK_LANE
        and ((mode == "landed" and request.branch is None) or lane["branch"] == branch)
    ]
    lanes = [
        effects.lane(
            repo,
            lane,
            leases,
            accepted_head=accepted_head,
            mode=mode,
        )
        for lane in candidates
    ]
    lane = lanes[0] if lanes else {}
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
    if request.apply and control_root is None:
        gaps.append("retirement_control_root_unavailable")
    required_gaps = sorted(set(gaps))

    verdict = _retirement_verdict(required_gaps)
    if lane:
        lane = {**lane, "retire_ready": not required_gaps, "required_gaps": required_gaps}

    def mutation(current_gaps: list[str]) -> dict[str, object]:
        required_holder = effects.holder_ref(authority)
        gaps = tuple(sorted(set(current_gaps)))
        current_verdict = _retirement_verdict(gaps)
        return mutation_envelope(
            command=f"lane-retire-{mode}",
            apply=request.apply,
            authorized=request.authorize,
            expect_head=request.expect_head,
            admission=MutationAdmissionRequest(
                action=f"lane.retire.{mode}",
                resource=f"refs/heads/{branch}" if branch else "work-lane",
                expected_state={
                    "ref": f"refs/heads/{branch}" if branch else "",
                    "head": (request.expect_head or "").strip(),
                    "invocation_holder_ref": effects.actor_ref(),
                    "required_holder_ref": required_holder,
                    "authority_branch": authority.get("branch", ""),
                    "authority_head": authority.get("head", ""),
                    "accepted_head": accepted_head,
                    "lease": authority.get("lease", {}),
                    "target_lease": lane.get("lease", {}),
                    **(
                        {"absorbed_by": absorbed_by, "reason": reason}
                        if mode == "superseded"
                        else {}
                    ),
                },
                verdict=current_verdict,
                required_gaps=gaps,
                state=(
                    "ready"
                    if current_verdict == "pass"
                    else "unknown"
                    if current_verdict == "unknown"
                    else "blocked"
                ),
                identity_basis=("exact_lease_generation" if required_holder else "not_evaluated"),
                evidence_boundary="current_git_lane_and_lease_observation",
                enforcement_boundary=(
                    "sqlite_generation_lock_and_git_ref_transaction"
                    if required_holder
                    else "git_ref_and_worktree_transition"
                ),
                verifier_provenance="current_runner",
            ),
        )

    report: dict[str, object] = {
        "verdict": verdict,
        "state": (
            "unknown"
            if verdict == "unknown"
            else "blocked"
            if verdict == "block"
            else "planned"
            if mode == "landed"
            else "ready_to_retire_superseded"
        ),
        "branch": branch,
        "mutation": mutation(required_gaps),
        "required_gaps": required_gaps,
    }
    if mode == "landed":
        report["lanes"] = lanes
    else:
        report["lane"] = lane
    if required_gaps:
        if "foreign_work_lane_retire_authority_required" in required_gaps:
            report["next_action"] = "set ETHOS_ACTOR to the current holder_ref or obtain handoff"
        return report
    if not request.apply:
        return report

    effect = effects.apply_retirement(
        repo,
        cast("Path", control_root),
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head=accepted_head,
    )
    effect_gaps = string_sequence(effect.get("required_gaps"))
    if effect_gaps:
        report.update(effect)
        report["verdict"] = "block"
        report["mutation"] = mutation(effect_gaps)
        report["required_gaps"] = effect_gaps
        return report
    observed = cast("dict[str, object]", effect["observed"])
    report.update(
        state="retired" if mode == "landed" else "retired_superseded",
        retired=observed,
    )
    return report


def _retirement_verdict(gaps: list[str] | tuple[str, ...]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


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
    if effects.output(repo, "rev-parse", "--verify", branch) is None:
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
        gaps.append("successor_retire_target_lease_present")
    return gaps


def _absorption_gap(
    repo: Path,
    *,
    source_head: str,
    absorbed_by: str,
    accepted_head: str,
    successor: dict[str, object],
) -> str:
    if not source_head or not absorbed_by:
        return ""
    if absorbed_by == accepted_head:
        return (
            ""
            if effects.absorbed(repo, source_head, accepted_head)
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
    branch = effects.output(repo, "symbolic-ref", "--short", "HEAD") or ""
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

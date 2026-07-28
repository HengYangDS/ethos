from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import MutationAdmissionRequest
from ethos.contracts.lifecycle.reducer import LifecycleModel
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path


class LinkedRetirementRequest(LifecycleModel):
    """Exact request for one linked Work Lane retirement transition."""

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
            accepted_head=accepted_head,
        )
    )
    if request.apply and control_root is None:
        gaps.append("retirement_control_root_unavailable")
    required_gaps = sorted(set(gaps))

    def mutation(current_gaps: list[str]) -> dict[str, object]:
        required_holder = effects.holder_ref(lane)
        transition = TransitionRequest(
            command=f"lane-retire-{mode}",
            apply=request.apply,
            authorized=request.authorize,
            expect_head=request.expect_head,
        )
        gaps = tuple(sorted(set(current_gaps)))
        return mutation_envelope(
            transition,
            MutationAdmissionRequest(
                action=f"lane.retire.{mode}",
                resource=f"refs/heads/{branch}" if branch else "work-lane",
                expected_state={
                    "ref": f"refs/heads/{branch}" if branch else "",
                    "head": (request.expect_head or "").strip(),
                    "invocation_holder_ref": effects.actor_ref(),
                    "required_holder_ref": required_holder,
                    "accepted_head": accepted_head,
                    "lease": lane.get("lease", {}),
                    **(
                        {"absorbed_by": absorbed_by, "reason": reason}
                        if mode == "superseded"
                        else {}
                    ),
                },
                verdict="allow" if not gaps else "block",
                required_gaps=gaps,
                state="ready" if not gaps else "blocked",
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
        "ok": not required_gaps,
        "state": (
            "blocked"
            if required_gaps
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
        accepted_head=accepted_head,
    )
    if effect:
        effect_gaps = string_sequence(effect.get("required_gaps"))
        report.update(effect)
        report["mutation"] = mutation(effect_gaps)
        report["required_gaps"] = effect_gaps
        return report
    report.update(
        state="retired" if mode == "landed" else "retired_superseded",
        retired=lane,
    )
    return report


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
    accepted_head: str,
) -> list[str]:
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    if not branch:
        gaps = ["superseded_retire_branch_required"]
    elif effects.output(repo, "rev-parse", "--verify", branch) is None:
        gaps = ["superseded_retire_branch_not_found"]
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps = ["superseded_retire_not_work_lane"]
    else:
        gaps = [] if lane else ["superseded_retire_worktree_not_linked"]
    if lane:
        gaps.extend(map(str, cast("list[object]", lane["required_gaps"])))
        gaps.extend(effects.holder_gaps(lane))
    gaps.extend(
        gap
        for failed, gap in (
            (not reason, "retire_reason_required"),
            (not accepted_head, "accepted_head_unavailable"),
            (not absorbed_by, "absorbed_by_required"),
            (
                bool(absorbed_by and accepted_head and absorbed_by != accepted_head),
                "absorbed_by_not_current_accepted_head",
            ),
            (request.apply and not request.authorize, "authorization_required"),
        )
        if failed
    )
    head = str(lane.get("head") or "")
    if (
        lane
        and all((branch, head, accepted_head))
        and absorbed_by == accepted_head
        and not effects.absorbed(repo, head, accepted_head)
    ):
        gaps.append("superseded_lane_not_absorbed_by_accepted")
    expected = (request.expect_head or "").strip()
    if not expected:
        gaps.append("expect_head_required")
    elif head and expected != head:
        gaps.append("expect_head_mismatch")
    return gaps

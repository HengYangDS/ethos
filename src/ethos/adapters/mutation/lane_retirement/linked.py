from __future__ import annotations

import shlex
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_retirement.observation import output
from ethos.adapters.mutation.lane_retirement.recovery import recover_worktree
from ethos.adapters.mutation.lane_retirement.recovery import recovery_lane
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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
        enforcement_boundary = (
            "sqlite_generation_lock_and_git_ref_transaction"
            if required_holder
            else "git_ref_and_worktree_transition"
        )
        decision = admission_decision(
            subject=MutationSubject(
                action=f"lane.retire.{mode}",
                resource=f"refs/heads/{branch}" if branch else "work-lane",
                expected_state=expected_state,
            ),
            verdict=current_verdict,
            basis=DecisionBasis(
                enforcement_boundary=enforcement_boundary,
                identity_basis="exact_lease_generation" if required_holder else "not_evaluated",
                state_bindings=tuple(expected_state),
                evidence_boundary="current_git_lane_and_lease_observation",
                verifier_provenance="current_runner",
                time_basis="evaluation_time",
            ),
            policy_ref=f"commitment:lane-retire-{mode}-admission",
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
        "state": _retirement_state(verdict, mode=mode, recovery=lane.get("recovery_required")),
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

    recovery = _apply_recovery(cast("Path", control_root), lane, mutation=mutation)
    if recovery:
        report |= recovery
        if report.get("verdict") == "block":
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
        return (
            report
            | effect
            | {
                "verdict": "block",
                "mutation": mutation(effect_gaps),
                "required_gaps": effect_gaps,
            }
        )
    observed = cast("dict[str, object]", effect["observed"])
    return report | {
        "state": "retired" if mode == "landed" else "retired_superseded",
        "retired": observed,
        "next_action": f"ethos status --root {shlex.quote(repo.as_posix())} --json",
        "user_decision_required": False,
    }


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
    lane = recovery_lane(
        policy=policy,
        worktrees=worktrees,
        leases=leases,
        branch=branch,
        path=(request.path or "").strip(),
        head=(output(repo, "rev-parse", "--verify", branch) or "") if branch else "",
    )
    return lanes, _with_archive_absorption(repo, lane, accepted_head) if lane else {}


def _retirement_state(
    verdict: Verdict,
    *,
    mode: Literal["landed", "superseded"],
    recovery: object,
) -> str:
    if verdict in {"unknown", "block"}:
        return "blocked" if verdict == "block" else "unknown"
    if mode == "landed":
        return "planned"
    return "ready_to_recover_and_retire_superseded" if recovery else "ready_to_retire_superseded"


def _apply_recovery(
    control_root: Path,
    lane: dict[str, object],
    *,
    mutation: Callable[[list[str]], dict[str, object]],
) -> dict[str, object]:
    if not lane.get("recovery_required"):
        return {}
    recovery = recover_worktree(control_root, lane)
    gaps = string_sequence(recovery.get("required_gaps"))
    return (
        {
            "recovery": recovery,
            "verdict": "block",
            "state": "blocked",
            "mutation": mutation(gaps),
            "required_gaps": gaps,
        }
        if gaps
        else {"recovery": recovery}
    )


def _retirement_verdict(gaps: list[str] | tuple[str, ...]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


def _effect_readiness_gaps(
    repo: Path,
    control_root: Path | None,
    *,
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
        gaps.append("successor_retire_target_lease_present")
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

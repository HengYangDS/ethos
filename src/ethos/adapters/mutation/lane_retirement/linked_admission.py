from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.lane_retirement.observation import output
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.retirement import LinkedRetirementRequest
    from ethos.contracts.verdict import Verdict


def retirement_target(
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


def retirement_verdict(gaps: list[str] | tuple[str, ...]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


def effect_readiness_gaps(
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


def landed_gaps(
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


def superseded_gaps(
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


def leased_successor(
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

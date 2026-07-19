from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_lifecycle.core as lane_lifecycle
import ethos.adapters.mutation.lane_retirement.shared.core as shared
import ethos_core.contracts.branch.roles as branch_roles
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease

run_git = lane_lifecycle.run_git
_REPORT_KEYS = (
    "ok state branch head absorbed_by accepted_head reason retire_ready lane mutation required_gaps"
)


@dataclass(frozen=True, slots=True)
class SupersededLaneRetirementRequest:
    branch: str
    expect_head: str | None = None
    reason: str = ""
    absorbed_by: str = ""
    apply: bool = False
    authorized: bool = False


def retire_superseded_work_lane(
    *, root: Path, request: SupersededLaneRetirementRequest
) -> dict[str, object]:
    repo = lane_lifecycle.repo_root(root)
    status = workspace_status(repo)
    branch = request.branch.strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    selected = _linked_work_lane(status, branch)
    lane = {}
    if selected:
        worktrees = cast("list[dict[str,str]]", status["worktrees"])
        lane = _lane(repo, selected, leases_by_branch(worktrees, current_path=repo))
    accepted_head = _accepted_head(repo)
    head = str(lane.get("head") or _branch_head(repo, branch))
    gaps = _gaps(repo, request, selected, lane, head, reason, absorbed_by, accepted_head)
    state = "ready_to_retire_superseded" if not gaps else "blocked"
    mutation = shared.retire_mutation_envelope(
        command="lane-retire-superseded",
        action="lane.retire.superseded",
        branch=branch,
        expect_head=request.expect_head,
        apply=request.apply,
        confirmed=request.authorized,
        required_gaps=gaps,
        holder_ref=shared.current_holder_ref(),
        required_holder_ref=shared.lane_holder_ref(lane),
        extra_state={"absorbed_by": absorbed_by, "accepted_head": accepted_head},
    )
    values = (
        *(not gaps, state, branch, head, absorbed_by),
        *(accepted_head, reason, bool(lane.get("retire_ready")) and not gaps, lane),
        mutation,
        sorted(set(gaps)),
    )
    report: dict[str, object] = dict(zip(_REPORT_KEYS.split(), values, strict=True))
    if gaps:
        return {**report, **shared.retire_authority_guidance(gaps)}
    if not request.apply:
        return report
    removed = shared.remove_linked_lane(repo, lane, expect_head=request.expect_head)
    if removed:
        report.update(removed)
        return report
    subject = str(lane["branch"])
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=subject)
    shared.delete_json_projection_lease(repo, subject=subject)
    report.update(state="retired_superseded", retired=lane, retire_ready=True)
    return report


def _gaps(repo, request, selected, lane, head, reason, absorbed_by, accepted_head):
    branch = request.branch.strip()
    gaps = _branch_gaps(repo, branch, selected)
    if lane:
        gaps.extend(map(str, cast("list[object]", lane["required_gaps"])))
        gaps.extend(shared.holder_authority_gaps([lane]))
    gaps.extend(_absorption_gaps(reason, absorbed_by, accepted_head))
    ready = (
        selected is not None and all((branch, head, accepted_head)) and absorbed_by == accepted_head
    )
    if ready and not _absorbed(repo, branch, head, accepted_head):
        gaps.append("superseded_lane_not_absorbed_by_accepted")
    gaps.extend(_superseded_expected_head_gaps(head=head, expect_head=request.expect_head))
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    return gaps


def _branch_gaps(repo, branch, selected):
    if not branch:
        return ["superseded_retire_branch_required"]
    if not _branch_exists(repo, branch):
        return ["superseded_retire_branch_not_found"]
    if (
        branch_roles.load_branch_role_policy(repo).role_for_branch(branch)
        != branch_roles.ROLE_WORK_LANE
    ):
        return ["superseded_retire_not_work_lane"]
    return [] if selected is not None else ["superseded_retire_worktree_not_linked"]


def _absorption_gaps(reason, absorbed_by, accepted_head):
    checks = (
        (not reason, "retire_reason_required"),
        (not accepted_head, "accepted_head_unavailable"),
        (not absorbed_by, "absorbed_by_required"),
        (
            bool(absorbed_by and accepted_head and absorbed_by != accepted_head),
            "absorbed_by_not_current_accepted_head",
        ),
    )
    return [gap for failed, gap in checks if failed]


def _absorbed(repo, branch, head, accepted_head):
    if not (base := _output(repo, "merge-base", accepted_head, branch)):
        return False
    if (changed := _output(repo, "diff", "--name-only", "--no-renames", "-z", base, head)) is None:
        return False
    return all(
        (_output(repo, "rev-parse", f"{head}:{path}") or "")
        == (_output(repo, "rev-parse", f"{accepted_head}:{path}") or "")
        for path in changed.split("\0")
        if path
    )


def _superseded_expected_head_gaps(*, head, expect_head):
    expected = (expect_head or "").strip()
    if not expected:
        return ["expect_head_required"]
    return ["expect_head_mismatch"] if head and expected != head else []


def _output(root, *args):
    completed = run_git(root, *args, check=False)
    return completed.stdout.rstrip("\n") if completed.returncode == 0 else None


def _branch_exists(root, branch):
    return _output(root, "rev-parse", "--verify", branch) is not None


def _accepted_head(root):
    accepted = branch_roles.load_branch_role_policy(root).accepted_branch
    return _output(root, "rev-parse", accepted) or ""


def _branch_head(root, branch):
    return (_output(root, "rev-parse", branch) or "") if branch else ""


def _linked_work_lane(status, branch):
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None
    for lane in worktrees:
        if (
            isinstance(lane, dict)
            and lane.get("role") == branch_roles.ROLE_WORK_LANE
            and lane.get("branch") == branch
        ):
            return cast("dict[str,object]", lane)
    return None


def _lane(repo, lane, leases):
    branch, path = str(lane["branch"]), Path(str(lane["path"]))
    lease = leases.get(branch, {})
    gaps: list[str] = []
    if lane_lifecycle.is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_already_merged_use_retire_landed")
    if shared.has_changed_paths(path):
        gaps.append("work_lane_dirty")
    identity = {"branch": branch, "path": path.as_posix(), "head": str(lane["head"])}
    state = {"lease": lease_summary(lease), "retire_ready": not gaps, "required_gaps": gaps}
    return identity | {"lease_state": "leased" if lease.get("holder_ref") else "missing"} | state

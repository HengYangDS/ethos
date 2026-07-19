from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class UnboundRetirementRuntime:
    """Explicit dependencies used to retire unbound Work Lane refs."""

    repo_root: Callable[[Path], Path] = repo_root
    workspace_status: Callable[[Path], dict[str, object]] = workspace_status
    delete_lease: Callable[..., int] = delete_lease
    shared: lane_retirement_shared.RetirementRuntime = field(
        default_factory=lane_retirement_shared.RetirementRuntime
    )


def retire_unbound_work_lane_ref(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
    runtime: UnboundRetirementRuntime | None = None,
) -> dict[str, object]:
    """Retire a work-lane ref that is not linked to a local worktree."""
    active_runtime = runtime or UnboundRetirementRuntime()
    repo = active_runtime.repo_root(root)
    status = active_runtime.workspace_status(repo)
    branch = branch.strip()
    reason = reason.strip()
    current = _unbound_work_lane_ref(status, branch)
    binding = _branch_binding(status, branch)
    head = str((current or binding or {}).get("head") or "")
    policy = load_branch_role_policy(repo)
    gaps: list[str] = []
    if not branch:
        gaps.append("unbound_retire_branch_required")
    elif not _branch_exists(repo, branch, runtime=active_runtime):
        gaps.append("unbound_retire_branch_not_found")
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps.append("unbound_retire_not_work_lane")
    elif current is None:
        gaps.append("unbound_retire_ref_not_unbound")
    if not reason:
        gaps.append("retire_reason_required")
    gaps.extend(lane_retirement_shared.expected_head_gaps(head, expect_head))
    if apply and not authorized:
        gaps.append("authorization_required")
    report = lane_retirement_shared.retirement_report(
        command="lane-retire-unbound",
        action="lane.retire.unbound",
        branch=branch,
        expect_head=expect_head,
        apply=apply,
        confirmed=authorized,
        state="ready_to_retire_unbound" if not gaps else "blocked",
        gaps=gaps,
        extra_state={"reason": reason},
        fields={
            "head": head,
            "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
            "claim_id": str((current or {}).get("claim_id") or ""),
            "claim_binding": str((current or {}).get("claim_binding") or ""),
            "reason": reason,
        },
    )
    if gaps or not apply:
        return report
    deleted = active_runtime.shared.run_git(
        repo,
        "update-ref",
        "-d",
        f"refs/heads/{branch}",
        str(expect_head),
        check=False,
    )
    if deleted.returncode:
        report.update(
            ok=False,
            state="blocked",
            required_gaps=["unbound_ref_delete_failed"],
            stderr=deleted.stderr.strip(),
        )
        return report
    active_runtime.delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=branch)
    report["state"] = "retired_unbound"
    report["retired_ref"] = f"refs/heads/{branch}"
    return report


def _branch_exists(
    root: Path,
    branch: str,
    *,
    runtime: UnboundRetirementRuntime | None = None,
) -> bool:
    active_runtime = runtime or UnboundRetirementRuntime()
    return (
        active_runtime.shared.run_git(root, "rev-parse", "--verify", branch, check=False).returncode
        == 0
    )


def _unbound_work_lane_ref(status: dict[str, object], branch: str) -> dict[str, object] | None:
    coordination = status.get("coordination")
    return _find(
        coordination.get("unbound_work_lane_refs") if isinstance(coordination, dict) else None,
        branch,
    )


def _branch_binding(status: dict[str, object], branch: str) -> dict[str, object] | None:
    return _find(status.get("branch_bindings"), branch)


def _find(rows: object, branch: str) -> dict[str, object] | None:
    if not isinstance(rows, list):
        return None
    return next(
        (
            cast("dict[str, object]", row)
            for row in rows
            if isinstance(row, dict) and row.get("branch") == branch
        ),
        None,
    )

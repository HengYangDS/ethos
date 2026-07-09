from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path


import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state import delete_lease
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy


def retire_unbound_work_lane_ref(
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
) -> dict[str, object]:
    """Retire a work-lane ref that is not linked to a local worktree."""
    repo = repo_root(root)
    status = workspace_status(repo)
    branch = branch.strip()
    reason = reason.strip()
    current = _unbound_work_lane_ref(status, branch)
    binding = _branch_binding(status, branch)
    head = str((current or binding or {}).get("head") or "")
    gaps = _unbound_retire_gaps(
        {
            "repo": repo,
            "branch": branch,
            "current": current,
            "head": head,
            "reason": reason,
            "expect_head": expect_head,
            "apply": apply,
            "authorized": authorized,
        }
    )
    report = {
        "ok": not gaps,
        "state": "ready_to_retire_unbound" if not gaps else "blocked",
        "branch": branch,
        "head": head,
        "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
        "claim_id": str((current or {}).get("claim_id") or ""),
        "claim_binding": str((current or {}).get("claim_binding") or ""),
        "reason": reason,
        "mutation": {
            "apply": apply,
            "authorized": authorized,
            "expect_head": expect_head or "",
            "ref": f"refs/heads/{branch}" if branch else "",
        },
        "required_gaps": sorted(set(gaps)),
    }
    if gaps:
        return report
    if not apply:
        return report
    deleted = lane_retirement_shared.run_git(
        repo,
        "update-ref",
        "-d",
        f"refs/heads/{branch}",
        str(expect_head),
        check=False,
    )
    if deleted.returncode != 0:
        report["ok"] = False
        report["state"] = "blocked"
        report["required_gaps"] = ["unbound_ref_delete_failed"]
        report["stderr"] = deleted.stderr.strip()
        return report
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=branch)
    report["state"] = "retired_unbound"
    report["retired_ref"] = f"refs/heads/{branch}"
    return report


def _unbound_retire_gaps(context: dict[str, object]) -> list[str]:
    repo = cast("Path", context["repo"])
    branch = str(context["branch"])
    current = cast("dict[str, object] | None", context["current"])
    head = str(context["head"])
    reason = str(context["reason"])
    expect_head = cast("str | None", context["expect_head"])
    apply = bool(context["apply"])
    authorized = bool(context["authorized"])
    policy = load_branch_role_policy(repo)
    gaps: list[str] = []
    if not branch:
        gaps.append("unbound_retire_branch_required")
    elif not _branch_exists(repo, branch):
        gaps.append("unbound_retire_branch_not_found")
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps.append("unbound_retire_not_work_lane")
    elif current is None:
        gaps.append("unbound_retire_ref_not_unbound")
    if not reason:
        gaps.append("retire_reason_required")
    if expect_head is None or not str(expect_head).strip():
        gaps.append("expect_head_required")
    elif head and expect_head != head:
        gaps.append("expect_head_mismatch")
    if apply and not authorized:
        gaps.append("authorization_required")
    return gaps


def _branch_exists(root: Path, branch: str) -> bool:
    completed = lane_retirement_shared.run_git(root, "rev-parse", "--verify", branch, check=False)
    return completed.returncode == 0


def _unbound_work_lane_ref(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    coordination = status.get("coordination")
    if not isinstance(coordination, dict):
        return None
    refs = coordination.get("unbound_work_lane_refs")
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if isinstance(ref, dict) and ref.get("branch") == branch:
            return cast("dict[str, object]", ref)
    return None


def _branch_binding(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    bindings = status.get("branch_bindings")
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if isinstance(binding, dict) and binding.get("branch") == branch:
            return cast("dict[str, object]", binding)
    return None

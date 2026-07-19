from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def retire_unbound_work_lane_ref(  # noqa: PLR0913, RUF100 - exact head-bound request
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
) -> dict[str, object]:
    """Inspect an unbound Work Lane ref without treating absence as safety.

    An unbound ref has no locally observable checkout, lease holder, or
    uncommitted-file inventory.  Ordinary retirement must therefore not delete
    it merely because its registered worktree is absent.  An evidence-bound
    exceptional deletion admission is required instead.
    """
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
    return {
        "ok": not gaps,
        "state": "ready_to_retire_unbound" if not gaps else "blocked",
        "branch": branch,
        "head": head,
        "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
        "claim_id": str((current or {}).get("claim_id") or ""),
        "claim_binding": str((current or {}).get("claim_binding") or ""),
        "reason": reason,
        "mutation": lane_retirement_shared.retire_mutation_envelope(
            command="lane-retire-unbound",
            action="lane.retire.unbound",
            branch=branch,
            expect_head=expect_head,
            apply=apply,
            confirmed=authorized,
            required_gaps=gaps,
            extra_state={"reason": reason},
        ),
        "required_gaps": sorted(set(gaps)),
    }


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
    else:
        gaps.append("unbound_retire_requires_exceptional_deletion_admission")
    if not reason:
        gaps.append("retire_reason_required")
    if expect_head is None or not str(expect_head).strip():
        gaps.append("expect_head_required")
    elif head and expect_head != head:
        gaps.append("expect_head_mismatch")
    if apply and not authorized:
        gaps.append("authorization_required")
    return gaps


def _branch_exists(
    root: Path,
    branch: str,
) -> bool:
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

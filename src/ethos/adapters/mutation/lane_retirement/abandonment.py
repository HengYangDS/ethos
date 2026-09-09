"""Derive exact abandonment of divergent history or explicitly reviewed content."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.lane_retirement.linked_effect import compile_retirement_operation
from ethos.adapters.mutation.lane_retirement.operation import persist_operation
from ethos.adapters.mutation.lane_retirement.operation import retirement_failure
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from ethos.contracts.retirement import RetirementOperation

_REASON_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _blocked(branch: str, error: Exception) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        **retirement_failure(error),
        "next_action": "",
        "user_decision_required": False,
    }


def _selected_worktree(
    worktrees: list[dict[str, object]], branch: str, *, review_content: bool
) -> Path | None:
    matches = [row for row in worktrees if row.get("branch") == branch]
    if len(matches) > 1:
        _fail("lane_abandonment_worktree_ambiguous")
    if not matches:
        if review_content:
            _fail("retirement_reviewed_worktree_required")
        return None
    path = Path(str(matches[0]["path"]))
    if path.is_symlink() or is_junction(path) or not path.is_dir():
        _fail("retirement_content_unsafe")
    if matches[0].get("locked") == "true":
        _fail("retirement_worktree_locked")
    if not review_content and effects.has_changed_paths(path):
        _fail("lane_abandonment_worktree_not_clean")
    return path


def _abandonment_request(
    root: Path, branch: str, *, reason_code: str, reason: str, review_content: bool
) -> RetirementOperation:
    """Observe an owner-bound topic without resolving away unsafe target identity."""
    policy = load_branch_role_policy(root)
    if not (
        policy.is_topic_branch(branch)
        if review_content
        else policy.role_for_branch(branch) == ROLE_WORK_LANE
    ):
        _fail("lane_abandonment_branch_invalid")
    status = workspace_status(root)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    control_root = effects.control_root(worktrees, root)
    if control_root is None:
        _fail("retirement_control_root_unavailable")
    assert control_root is not None
    head = ref_head(control_root, branch)
    accepted_head = ref_head(control_root, policy.accepted_branch)
    tree = current_tree(control_root, head) if head else ""
    if not head or not tree or not accepted_head:
        _fail("lane_abandonment_coordinates_unavailable")
    if not review_content and (
        is_ancestor(control_root, head, accepted_head)
        or is_ancestor(control_root, accepted_head, head)
    ):
        _fail("lane_abandonment_divergence_required")
    path = _selected_worktree(worktrees, branch, review_content=review_content)
    lease = leases_by_branch(control_root).get(branch, {})
    lease_state = str(lease.get("lease_state") or "missing")
    if not review_content and lease_state != "valid":
        _fail(f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}")
    actor = effects.actor_ref()
    lane = {
        "branch": branch,
        "head": head,
        "path": path.as_posix() if path else "",
        "lease_state": lease_state,
        "lease": lease,
    }
    if gaps := effects.holder_gaps(lane):
        _fail(gaps[0])
    return compile_retirement_operation(
        control_root,
        mode="abandon",
        policy=policy,
        lane=lane,
        authority=lane,
        accepted_head=accepted_head,
        reason_code=reason_code,
        reason=reason,
        actor=actor,
        review_content=review_content,
    )


def derive_lane_abandonment(
    *, root: Path, branch: str, reason_code: str, reason: str, review_content: bool = False
) -> dict[str, object]:
    """Derive and persist one exact current abandonment operation."""
    branch = branch.strip()
    try:
        _require_reason(reason_code, reason)
        repo = repository_root(root)
        request = _abandonment_request(
            repo,
            branch,
            reason_code=reason_code,
            reason=reason.strip(),
            review_content=review_content,
        )
        receipt = persist_operation(Path(request.control_root), request)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return _blocked(branch, error)
    return {
        "verdict": "pass",
        "state": "derived",
        "branch": request.branch,
        "head": request.head,
        "request": request.model_dump(mode="json"),
        "receipt": receipt,
        "required_gaps": [],
        "next_action": (
            "ethos lane retire abandon "
            f"--receipt {receipt['path']} --receipt-sha256 {receipt['sha256']} "
            f"--authorize --apply --root {request.control_root} --json"
        ),
        "user_decision_required": True,
    }


def _require_reason(reason_code: str, reason: str) -> None:
    if not _REASON_CODE.fullmatch(reason_code) or not reason.strip():
        _fail("lane_abandonment_reason_invalid")

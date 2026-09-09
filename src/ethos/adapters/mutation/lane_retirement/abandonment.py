"""Derive exact abandonment of divergent history or explicitly reviewed content."""

from __future__ import annotations

import re
from pathlib import Path
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
from ethos.adapters.repo.worktree_effects import worktree_record
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy

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
    root: Path, worktrees: list[dict[str, object]], branch: str, *, review_content: bool, path: str
) -> tuple[Path | None, str]:
    if path and not Path(path).is_absolute():
        _fail("retirement_target_path_not_absolute")
    key, value = ("path", path) if path else ("branch", branch)
    matches = [row for row in worktrees if row.get(key) == value]
    if len(matches) > 1:
        _fail("lane_abandonment_worktree_ambiguous")
    if not matches:
        if review_content:
            _fail("retirement_reviewed_worktree_required")
        return None, ref_head(root, branch)
    selected = Path(str(matches[0]["path"]))
    if selected.is_symlink() or is_junction(selected) or not selected.is_dir():
        _fail("retirement_content_unsafe")
    if matches[0].get("locked") == "true":
        _fail("retirement_worktree_locked")
    if not review_content and effects.has_changed_paths(selected):
        _fail("lane_abandonment_worktree_not_clean")
    if path:
        record = worktree_record(root, selected)
        if "detached" not in record or "branch" in record:
            _fail("retirement_target_not_detached")
        return selected, record.get("HEAD", "")
    return selected, ref_head(root, branch)


def derive_lane_abandonment(
    *,
    root: Path,
    branch: str,
    reason_code: str,
    reason: str,
    review_content: bool = False,
    path: str = "",
) -> dict[str, object]:
    """Derive and persist one exact current abandonment operation."""
    branch = branch.strip()
    try:
        if not _REASON_CODE.fullmatch(reason_code) or not reason.strip():
            _fail("lane_abandonment_reason_invalid")
        reason = reason.strip()
        root = repository_root(root)
        policy = load_branch_role_policy(root)
        if path and (branch or not review_content):
            _fail("retirement_target_selection_invalid")
        if not path and not (
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
        selected, head = _selected_worktree(
            control_root, worktrees, branch, review_content=review_content, path=path
        )
        accepted_head = ref_head(control_root, policy.accepted_branch)
        tree = current_tree(control_root, head) if head else ""
        if not head or not tree or not accepted_head:
            _fail("lane_abandonment_coordinates_unavailable")
        if not review_content and (
            is_ancestor(control_root, head, accepted_head)
            or is_ancestor(control_root, accepted_head, head)
        ):
            _fail("lane_abandonment_divergence_required")
        lease = leases_by_branch(control_root).get(branch, {}) if branch else {}
        lease_state = str(lease.get("lease_state") or "missing")
        if not review_content and lease_state != "valid":
            _fail(f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}")
        lane: dict[str, object] = {
            "branch": branch,
            "head": head,
            "path": selected.as_posix() if selected else "",
            "lease_state": lease_state,
            "lease": lease,
        }
        if gaps := effects.holder_gaps(lane):
            _fail(gaps[0])
        request = compile_retirement_operation(
            control_root,
            mode="abandon",
            policy=policy,
            lane=lane,
            authority=lane,
            accepted_head=accepted_head,
            reason_code=reason_code,
            reason=reason,
            actor=effects.actor_ref(),
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

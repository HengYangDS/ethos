"""Derive explicit clean divergent-lane retirement operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import TypedDict
from typing import cast

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.lane_retirement.linked_effect import linked_retirement_plan
from ethos.adapters.mutation.lane_retirement.operation import apply_operation
from ethos.adapters.mutation.lane_retirement.operation import load_operation
from ethos.adapters.mutation.lane_retirement.operation import persist_operation
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.retirement import RetirementOperation

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.value import JsonObject

_REASON_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AbandonmentCoordinates(TypedDict):
    """Exact native coordinates admitted for one abandonment request."""

    repository_common_dir: str
    repository_identity: str
    control_root: str
    branch: str
    head: str
    tree: str
    accepted_branch: str
    accepted_head: str
    worktree_path: str
    worktree_initial: str
    lease_state: str
    lease: JsonObject
    authority: JsonObject


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _blocked(branch: str, error: BaseException) -> dict[str, object]:
    gap = getattr(error, "code", "") or str(error).partition(":")[0] or type(error).__name__
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "required_gaps": [str(gap)],
        "stderr": str(error),
        "next_action": "",
        "user_decision_required": False,
    }


def abandonment_coordinates(root: Path, branch: str) -> AbandonmentCoordinates:
    """Observe one exact owner-bound clean divergent Work Lane."""
    policy = load_branch_role_policy(root)
    if policy.role_for_branch(branch) != ROLE_WORK_LANE:
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
    if is_ancestor(control_root, head, accepted_head) or is_ancestor(
        control_root, accepted_head, head
    ):
        _fail("lane_abandonment_divergence_required")
    matches = [row for row in worktrees if row.get("branch") == branch]
    if len(matches) > 1:
        _fail("lane_abandonment_worktree_ambiguous")
    path = Path(str(matches[0]["path"])) if matches else None
    if path is not None and effects.has_changed_paths(path):
        _fail("lane_abandonment_worktree_not_clean")
    lease = leases_by_branch(control_root).get(branch, {})
    if lease.get("lease_state") != "valid":
        _fail(f"work_lane_lease_{lease.get('lease_state') or 'missing'}:{branch}")
    actor = effects.actor_ref()
    if not actor:
        _fail(f"invocation_actor_missing:{branch}")
    if effects.holder_ref({"lease": lease}) != actor:
        _fail("foreign_work_lane_retire_authority_required")
    return {
        "repository_common_dir": Path(git_common_dir(control_root)).resolve().as_posix(),
        "repository_identity": repository_identity(control_root, tree_ref=head),
        "control_root": control_root.as_posix(),
        "branch": branch,
        "head": head,
        "tree": tree,
        "accepted_branch": policy.accepted_branch,
        "accepted_head": accepted_head,
        "worktree_path": path.resolve().as_posix() if path else "",
        "worktree_initial": "linked" if path else "unbound",
        "lease_state": "valid",
        "lease": effects.lease_generation(lease),
        "authority": {"kind": "owner", "actor": actor},
    }


def compile_abandonment_plan(
    control_root: Path, coordinates: AbandonmentCoordinates
) -> tuple[Path, TransitionPlan]:
    """Compile the exact ref deletion using the common retirement plan owner."""
    lane = {
        "branch": coordinates["branch"],
        "head": coordinates["head"],
        "path": coordinates["worktree_path"],
        "lease_state": coordinates["lease_state"],
        "lease": coordinates["lease"],
    }
    return linked_retirement_plan(
        control_root,
        lane,
        accepted=(str(coordinates["accepted_branch"]), str(coordinates["accepted_head"])),
        authority=lane,
        mode="abandon",
        actor=str(cast("dict[str, object]", coordinates["authority"])["actor"]),
        worktree_clean=True,
    )


def derive_lane_abandonment(
    *, root: Path, branch: str, reason_code: str, reason: str
) -> dict[str, object]:
    """Derive and persist one exact current abandonment operation."""
    branch = branch.strip()
    try:
        _require_reason(reason_code, reason)
        repo = repository_root(root)
        coordinates = abandonment_coordinates(repo, branch)
        execution_root, plan = compile_abandonment_plan(
            Path(str(coordinates["control_root"])), coordinates
        )
        request = RetirementOperation.model_validate(
            {
                **coordinates,
                "execution_root": execution_root.as_posix(),
                "mode": "abandon",
                "reason": {"code": reason_code, "summary": reason.strip()},
                "git_plan": plan.model_dump(mode="json"),
            },
            strict=True,
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


def execute_lane_abandonment(
    *,
    root: Path,
    receipt_path: str,
    receipt_sha256: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Apply or inspect one current abandonment operation."""
    try:
        if apply and not authorized:
            _fail("authorization_required")
        request = load_operation(root, receipt_path, receipt_sha256)
        _require_abandonment(request)
        return apply_operation(
            Path(request.control_root),
            request,
            request_receipt={"path": receipt_path, "sha256": receipt_sha256},
            apply=apply,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return _blocked("", error)


def _require_reason(reason_code: str, reason: str) -> None:
    if not _REASON_CODE.fullmatch(reason_code) or not reason.strip():
        _fail("lane_abandonment_reason_invalid")


def _require_abandonment(request: RetirementOperation) -> None:
    if request.mode != "abandon":
        _fail("lane_retirement_receipt_mode_invalid")

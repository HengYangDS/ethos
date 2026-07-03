from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ethos_adapters.status import workspace_status
from ethos_contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_contracts.branch_roles import ROLE_WORK_LANE
from ethos_contracts.branch_roles import load_branch_role_policy


@dataclass(frozen=True)
class MutationRequest:
    command: str
    apply: bool
    authorized: bool
    expect_head: str | None


@dataclass(frozen=True)
class MutationDecision:
    ok: bool
    state: str
    gaps: tuple[str, ...] = ()


def evaluate_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationDecision:
    if not request.apply:
        return MutationDecision(ok=True, state="dry_run")
    gaps: list[str] = []
    if not request.authorized:
        gaps.append("authorization_required")
    if request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    return MutationDecision(ok=True, state=f"{request.command}_ready")


def evaluate_closeout_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationDecision:
    if not request.apply:
        return MutationDecision(ok=True, state="dry_run")
    gaps: list[str] = []
    if not request.authorized:
        gaps.append("authorization_required")
    if request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    candidate = status["candidate"]
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    else:
        candidate_path = Path(str(candidate["worktree_path"]))
        if workspace_status(candidate_path)["dirty"]:
            gaps.append("candidate_worktree_dirty")
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    return MutationDecision(ok=True, state=f"{request.command}_ready")


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_mutation(
        MutationRequest(
            command="land",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            "ok": False,
            "state": decision.state,
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": list(decision.gaps),
        }
    base_report = candidate_base_report(root=root)
    if not base_report["ok"]:
        return base_report
    candidate_path = Path(str(base_report["path"]))
    completed = _git(candidate_path, "merge", "--ff-only", current_head, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_update_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }


def apply_candidate_to_accepted(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_closeout_mutation(
        MutationRequest(
            command="closeout",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            "ok": False,
            "state": decision.state,
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": list(decision.gaps),
        }
    status = workspace_status(root)
    candidate_head = str(status["candidate"]["head"])
    completed = _git(root, "merge", "--ff-only", policy.candidate_branch, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": ["accepted_update_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate_head,
        "previous_head": current_head,
        "required_gaps": [],
    }


def candidate_base_report(*, root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    status = workspace_status(root)
    if not status["candidate"]["exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_branch_missing"],
        }
    if not status["candidate"]["worktree_exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_worktree_missing"],
        }
    candidate_path = Path(str(status["candidate"]["worktree_path"]))
    candidate_status = workspace_status(candidate_path)
    if candidate_status["dirty"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_worktree_dirty"],
        }
    candidate_head = str(status["candidate"]["head"])
    if not _is_ancestor(root, candidate_head, current_head):
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "candidate_head": candidate_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_base_stale"],
        }
    return {
        "ok": True,
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return completed.returncode == 0


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )

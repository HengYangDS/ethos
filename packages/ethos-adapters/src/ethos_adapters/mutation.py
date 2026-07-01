from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ethos_adapters.status import CANDIDATE_BRANCH, workspace_status


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
    if status["role"] != "work_lane":
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    return MutationDecision(ok=True, state=f"{request.command}_ready")


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
) -> dict[str, object]:
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
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "required_gaps": list(decision.gaps),
        }
    status = workspace_status(root)
    if not status["candidate"]["exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "required_gaps": ["candidate_branch_missing"],
        }
    if not status["candidate"]["worktree_exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "required_gaps": ["candidate_worktree_missing"],
        }
    candidate_path = Path(str(status["candidate"]["worktree_path"]))
    candidate_status = workspace_status(candidate_path)
    if candidate_status["dirty"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_worktree_dirty"],
        }
    completed = _git(candidate_path, "merge", "--ff-only", current_head, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_update_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": CANDIDATE_BRANCH,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )

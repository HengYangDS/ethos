from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_retirement.shared.core import current_holder_ref
from ethos.adapters.mutation.lane_retirement.shared.core import retire_mutation_envelope
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.lifecycle.core import LifecycleModel
from ethos_core.normalization.core import string_sequence


class LinkedRetirementRequest(LifecycleModel):
    """Exact request for one linked Work Lane retirement transition."""

    branch: str | None = None
    expect_head: str | None = None
    absorbed_by: str = ""
    reason: str = ""
    authorize: bool = False
    apply: bool = False


def retire_linked_work_lane(
    *,
    root: Path,
    mode: Literal["landed", "superseded"],
    request: LinkedRetirementRequest,
) -> dict[str, object]:
    """Plan or execute one holder-bound linked-lane retirement."""
    repo = repo_root(root)
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    policy = load_branch_role_policy(repo)
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    accepted_head = _output(repo, "rev-parse", policy.accepted_branch) or ""
    control_root = _control_root(worktrees, repo)
    leases = leases_by_branch(cast("list[dict[str, str]]", worktrees), current_path=repo)
    candidates = [
        lane
        for lane in worktrees
        if lane["role"] == ROLE_WORK_LANE
        and ((mode == "landed" and request.branch is None) or lane["branch"] == branch)
    ]
    lanes = [
        _lane(
            repo,
            lane,
            leases,
            accepted_head=accepted_head,
            mode=mode,
        )
        for lane in candidates
    ]
    lane = lanes[0] if lanes else {}
    gaps = (
        _landed_gaps(
            branch=branch,
            request=request,
            lanes=lanes,
        )
        if mode == "landed"
        else _superseded_gaps(
            repo=repo,
            policy=policy,
            request=request,
            lane=lane,
            accepted_head=accepted_head,
        )
    )
    if request.apply and control_root is None:
        gaps.append("retirement_control_root_unavailable")
    required_gaps = sorted(set(gaps))

    def mutation(current_gaps: list[str]) -> dict[str, object]:
        return retire_mutation_envelope(
            command=f"lane-retire-{mode}",
            action=f"lane.retire.{mode}",
            branch=branch,
            expect_head=request.expect_head,
            apply=request.apply,
            confirmed=request.authorize,
            required_gaps=current_gaps,
            holder_ref=current_holder_ref(),
            required_holder_ref=_holder_ref(lane),
            extra_state={
                "accepted_head": accepted_head,
                "lease": lane.get("lease", {}),
                **({"absorbed_by": absorbed_by, "reason": reason} if mode == "superseded" else {}),
            },
        )

    report: dict[str, object] = {
        "ok": not required_gaps,
        "state": (
            "blocked"
            if required_gaps
            else "planned"
            if mode == "landed"
            else "ready_to_retire_superseded"
        ),
        "branch": branch,
        "mutation": mutation(required_gaps),
        "required_gaps": required_gaps,
    }
    if mode == "landed":
        report["lanes"] = lanes
    else:
        report["lane"] = lane
    if required_gaps:
        if "foreign_work_lane_retire_authority_required" in required_gaps:
            report["next_action"] = "set ETHOS_ACTOR to the current holder_ref or obtain handoff"
        return report
    if not request.apply:
        return report

    effect = _apply_retirement(
        cast("Path", control_root),
        policy=policy,
        lane=lane,
        accepted_head=accepted_head,
    )
    if effect:
        effect_gaps = string_sequence(effect.get("required_gaps"))
        report.update(effect)
        report["mutation"] = mutation(effect_gaps)
        report["required_gaps"] = effect_gaps
        return report
    report.update(
        state="retired" if mode == "landed" else "retired_superseded",
        retired=lane,
    )
    return report


def _apply_retirement(
    control_root: Path,
    *,
    policy: BranchRolePolicy,
    lane: dict[str, object],
    accepted_head: str,
) -> dict[str, object]:
    removed = False
    lease = cast("dict[str, object]", lane.get("lease") or {})
    try:
        with closing(
            sqlite3.connect(control_root / ".ethos" / "state" / "state.sqlite")
        ) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            revoke_lease_from_connection(
                connection,
                subject=str(lane["branch"]),
                holder_ref=_holder_ref(lane),
                expected_lease_id=str(lease.get("lease_id") or ""),
                expected_epoch=int(lease.get("epoch") or 0),
                expected_head=str(lane["head"]),
                expected_expires_at=str(lease.get("expires_at") or ""),
                expected_payload_sha256=str(lease.get("payload_sha256") or ""),
            )
            if gaps := _effect_gaps(
                control_root,
                policy=policy,
                lane=lane,
                accepted_head=accepted_head,
            ):
                return _blocked(gaps)
            if effect := _remove_linked_lane(
                control_root,
                lane,
                accepted_branch=policy.accepted_branch,
                accepted_head=accepted_head,
            ):
                return {
                    **effect,
                    **({"lease_state": "retained"} if effect.get("worktree_removed") else {}),
                }
            removed = True
            connection.commit()
    except ValueError as exc:
        return _blocked([str(exc).partition(":")[0]], str(exc))
    except (OSError, sqlite3.Error) as exc:
        if not removed:
            return _blocked(["lease_cleanup_failed"], str(exc))
        try:
            restored = run_git(
                control_root,
                "update-ref",
                f"refs/heads/{lane['branch']}",
                str(lane["head"]),
                "0" * 40,
                check=False,
            )
        except OSError:
            restored = None
        gaps = ["lease_cleanup_failed_after_lane_removed"]
        if restored is None or restored.returncode != 0:
            gaps.append("branch_restore_failed_after_lease_cleanup")
        return {
            **_blocked(gaps, str(exc)),
            "worktree_removed": True,
            "ref_restored": restored is not None and restored.returncode == 0,
            "lease_state": "retained",
        }
    return {}


def _remove_linked_lane(
    control_root: Path,
    lane: dict[str, object],
    *,
    accepted_branch: str,
    accepted_head: str,
) -> dict[str, object]:
    branch, path, expected = (str(lane.get(key) or "") for key in ("branch", "path", "head"))
    if gaps := _reobservation_gaps(branch, path, expected):
        return _blocked(gaps)
    removed = run_git(control_root, "worktree", "remove", path, check=False)
    if removed.returncode != 0:
        return _blocked(["worktree_remove_failed"], removed.stderr)
    try:
        deleted = run_git(
            control_root,
            "update-ref",
            "--stdin",
            check=False,
            stdin=(
                f"start\nverify refs/heads/{accepted_branch} {accepted_head}\n"
                f"delete refs/heads/{branch} {expected}\nprepare\ncommit\n"
            ),
        )
        if deleted.returncode == 0:
            return {}
        accepted_changed = _output(control_root, "rev-parse", accepted_branch) != accepted_head
    except OSError as exc:
        return {
            **_blocked(["branch_delete_failed_after_worktree_removed"], str(exc)),
            "worktree_removed": True,
            "ref_preserved": True,
        }
    gap = (
        "accepted_ref_changed_after_worktree_removed"
        if accepted_changed
        else "branch_delete_failed_after_worktree_removed"
    )
    return {
        **_blocked([gap], deleted.stderr),
        "worktree_removed": True,
        "ref_preserved": True,
    }


def _landed_gaps(
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
        )
        if failed
    ]
    if branch and lanes:
        gaps.extend(map(str, cast("list[object]", lanes[0]["required_gaps"])))
        gaps.extend(_holder_gaps(lanes[0]))
        expected = (request.expect_head or "").strip()
        if request.apply and not expected:
            gaps.append("expect_head_required")
        elif request.apply and expected != str(lanes[0]["head"]):
            gaps.append("expect_head_mismatch")
    return gaps


def _superseded_gaps(
    *,
    repo: Path,
    policy: BranchRolePolicy,
    request: LinkedRetirementRequest,
    lane: dict[str, object],
    accepted_head: str,
) -> list[str]:
    branch = (request.branch or "").strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    if not branch:
        gaps = ["superseded_retire_branch_required"]
    elif _output(repo, "rev-parse", "--verify", branch) is None:
        gaps = ["superseded_retire_branch_not_found"]
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps = ["superseded_retire_not_work_lane"]
    else:
        gaps = [] if lane else ["superseded_retire_worktree_not_linked"]
    if lane:
        gaps.extend(map(str, cast("list[object]", lane["required_gaps"])))
        gaps.extend(_holder_gaps(lane))
    gaps.extend(
        gap
        for failed, gap in (
            (not reason, "retire_reason_required"),
            (not accepted_head, "accepted_head_unavailable"),
            (not absorbed_by, "absorbed_by_required"),
            (
                bool(absorbed_by and accepted_head and absorbed_by != accepted_head),
                "absorbed_by_not_current_accepted_head",
            ),
            (request.apply and not request.authorize, "authorization_required"),
        )
        if failed
    )
    head = str(lane.get("head") or "")
    if (
        lane
        and all((branch, head, accepted_head))
        and absorbed_by == accepted_head
        and not _absorbed(repo, head, accepted_head)
    ):
        gaps.append("superseded_lane_not_absorbed_by_accepted")
    expected = (request.expect_head or "").strip()
    if not expected:
        gaps.append("expect_head_required")
    elif head and expected != head:
        gaps.append("expect_head_mismatch")
    return gaps


def _absorbed(repo: Path, head: str, accepted_head: str) -> bool:
    if not (base := _output(repo, "merge-base", accepted_head, head)):
        return False
    changed = _output(repo, "diff", "--name-only", "--no-renames", "-z", base, head)
    if changed is None:
        return False
    paths = [path for path in changed.split("\0") if path]
    return (
        not paths
        or run_git(
            repo, "diff", "--quiet", head, accepted_head, "--", *paths, check=False
        ).returncode
        == 0
    )


def _output(root: Path, *args: str) -> str | None:
    completed = run_git(root, *args, check=False)
    return completed.stdout.rstrip("\n") if completed.returncode == 0 else None


def _control_root(worktrees: list[dict[str, object]], default: Path) -> Path | None:
    root = accepted_worktree_root(worktrees, default).resolve()
    observed = any(
        lane["role"] == ROLE_ACCEPTED_ROOT and Path(str(lane["path"])).resolve() == root
        for lane in worktrees
    )
    return root if observed and root.is_dir() else None


def _lane(
    repo: Path,
    lane: dict[str, object],
    leases: dict[str, dict[str, object]],
    *,
    accepted_head: str,
    mode: Literal["landed", "superseded"],
) -> dict[str, object]:
    branch, path = str(lane["branch"]), Path(str(lane["path"]))
    head = str(lane["head"])
    lease = leases.get(branch, {})
    merged = is_ancestor(repo, head, accepted_head)
    gaps = [
        gap
        for failed, gap in (
            (mode == "landed" and not merged, "work_lane_not_merged"),
            (mode == "superseded" and merged, "work_lane_already_merged_use_retire_landed"),
            (has_changed_paths(path), "work_lane_dirty"),
        )
        if failed
    ]
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "lease": lease_summary(lease),
        "lease_state": "leased" if lease.get("holder_ref") else "missing",
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }


def _holder_ref(lane: dict[str, object]) -> str:
    return str(cast("dict[str, object]", lane.get("lease") or {}).get("holder_ref") or "")


def _holder_gaps(lane: dict[str, object]) -> list[str]:
    required = _holder_ref(lane)
    return (
        []
        if required and current_holder_ref() == required
        else ["foreign_work_lane_retire_authority_required"]
    )


def _effect_gaps(
    control_root: Path,
    *,
    policy: BranchRolePolicy,
    lane: dict[str, object],
    accepted_head: str,
) -> list[str]:
    if _output(control_root, "symbolic-ref", "--short", "HEAD") != policy.accepted_branch:
        return ["retirement_control_root_stale"]
    current_accepted = _output(control_root, "rev-parse", policy.accepted_branch) or ""
    if current_accepted != accepted_head:
        return ["accepted_ref_stale"]
    if current_holder_ref() != _holder_ref(lane):
        return ["foreign_work_lane_retire_authority_required"]
    return []


def _reobservation_gaps(
    branch: str,
    path: str,
    expect_head: str,
) -> list[str]:
    gaps: list[str] = []
    lane_path = Path(path) if path else Path()
    if not path or not lane_path.is_dir():
        return [*gaps, "retirement_worktree_path_unavailable"]
    for args, gap, expected in (
        (("rev-parse", f"refs/heads/{branch}"), "retirement_ref", expect_head),
        (("rev-parse", "HEAD"), "retirement_worktree_head", expect_head),
        (("status", "--porcelain", "--untracked-files=all"), "retirement_worktree_status", ""),
    ):
        result = run_git(lane_path, *args, check=False)
        value = result.stdout.strip()
        if result.returncode != 0:
            gaps.append(f"{gap}_unavailable")
        elif expected and value != expected:
            gaps.append(f"{gap}_stale")
        elif gap == "retirement_worktree_status" and value:
            gaps.append("work_lane_dirty")
    return sorted(set(gaps))


def _blocked(gaps: list[str], stderr: str = "") -> dict[str, object]:
    report: dict[str, object] = {"ok": False, "state": "blocked", "required_gaps": gaps}
    if stderr.strip():
        report["stderr"] = stderr.strip()
    return report

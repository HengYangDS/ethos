"""Git and lease effects for linked Work Lane retirement."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.coordination import LeaseOperationRequest

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy


def apply_retirement(
    repo: Path,
    control_root: Path,
    *,
    policy: BranchRolePolicy,
    lane: dict[str, object],
    accepted_head: str,
) -> dict[str, object]:
    removed = False
    lease = cast("dict[str, object]", lane.get("lease") or {})
    try:
        with closing(sqlite3.connect(state_database(repo))) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            revoke_lease_from_connection(
                connection,
                request=LeaseOperationRequest(
                    operation="revoke",
                    branch=str(lane["branch"]),
                    holder_ref=holder_ref(lane),
                    lease_id=str(lease.get("lease_id") or ""),
                    expected_epoch=integer_value(lease.get("epoch")),
                    expect_head=str(lane["head"]),
                    expected_expires_at=str(lease.get("expires_at") or ""),
                    expected_payload_sha256=str(lease.get("payload_sha256") or ""),
                    apply=True,
                ),
            )
            if gaps := effect_gaps(
                control_root,
                policy=policy,
                lane=lane,
                accepted_head=accepted_head,
            ):
                return blocked(gaps)
            if effect := remove_linked_lane(
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
        return blocked([str(exc).partition(":")[0]], str(exc))
    except (OSError, sqlite3.Error) as exc:
        if not removed:
            return blocked(["lease_cleanup_failed"], str(exc))
        try:
            restored = run_git(
                control_root,
                "update-ref",
                "--stdin",
                check=False,
                stdin=f"create refs/heads/{lane['branch']} {lane['head']}\n",
            )
        except OSError:
            restored = None
        gaps = ["lease_cleanup_failed_after_lane_removed"]
        if restored is None or restored.returncode != 0:
            gaps.append("branch_restore_failed_after_lease_cleanup")
        return {
            **blocked(gaps, str(exc)),
            "worktree_removed": True,
            "ref_restored": restored is not None and restored.returncode == 0,
            "lease_state": "retained",
        }
    return {}


def remove_linked_lane(
    control_root: Path,
    lane: dict[str, object],
    *,
    accepted_branch: str,
    accepted_head: str,
) -> dict[str, object]:
    branch, path, expected = (str(lane.get(key) or "") for key in ("branch", "path", "head"))
    if gaps := reobservation_gaps(branch, path, expected):
        return blocked(gaps)
    removed = run_git(control_root, "worktree", "remove", path, check=False)
    if removed.returncode != 0:
        return blocked(["worktree_remove_failed"], removed.stderr)
    try:
        deleted = run_git(
            control_root,
            "update-ref",
            "--stdin",
            check=False,
            stdin=(
                f"start\nupdate refs/heads/{accepted_branch} {accepted_head} {accepted_head}\n"
                f"delete refs/heads/{branch} {expected}\nprepare\ncommit\n"
            ),
        )
        if deleted.returncode == 0:
            return {}
    except OSError as exc:
        return failed_ref_transition(
            control_root,
            target=(branch, expected),
            accepted=(accepted_branch, accepted_head),
            stderr=str(exc),
        )
    return failed_ref_transition(
        control_root,
        target=(branch, expected),
        accepted=(accepted_branch, accepted_head),
        stderr=deleted.stderr,
    )


def failed_ref_transition(
    control_root: Path,
    *,
    target: tuple[str, str],
    accepted: tuple[str, str],
    stderr: str,
) -> dict[str, object]:
    branch, expected = target
    accepted_branch, accepted_head = accepted
    accepted_state = ref_outcome(control_root, accepted_branch, accepted_head)
    ref_state = ref_outcome(control_root, branch, expected)
    gaps = [
        "accepted_ref_changed_after_worktree_removed"
        if accepted_state in {"absent", "moved"}
        else "branch_delete_failed_after_worktree_removed"
    ]
    if accepted_state == "unavailable":
        gaps.append("accepted_ref_state_unavailable_after_worktree_removed")
    ref_gap = {
        "absent": "retirement_ref_absent_after_failed_delete",
        "moved": "retirement_ref_moved_after_worktree_removed",
        "unavailable": "retirement_ref_state_unavailable_after_worktree_removed",
    }.get(ref_state)
    if ref_gap:
        gaps.append(ref_gap)
    return {
        **blocked(gaps, stderr),
        "worktree_removed": True,
        "ref_state": ref_state,
        "ref_preserved": ref_state == "expected",
    }


def ref_outcome(root: Path, branch: str, expected: str) -> str:
    try:
        observed = run_git(
            root,
            "show-ref",
            "--verify",
            "--hash",
            f"refs/heads/{branch}",
            check=False,
        )
    except OSError:
        return "unavailable"
    if observed.returncode == 0:
        return "expected" if observed.stdout.strip() == expected else "moved"
    return "absent" if observed.returncode == 1 else "unavailable"


def absorbed(repo: Path, head: str, accepted_head: str) -> bool:
    if not (base := output(repo, "merge-base", accepted_head, head)):
        return False
    changed = output(repo, "diff", "--name-only", "--no-renames", "-z", base, head)
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


def output(root: Path, *args: str) -> str | None:
    completed = run_git(root, *args, check=False)
    return completed.stdout.rstrip("\n") if completed.returncode == 0 else None


def control_root(worktrees: list[dict[str, object]], default: Path) -> Path | None:
    root = accepted_worktree_root(worktrees, default).resolve()
    observed = any(
        lane["role"] == ROLE_ACCEPTED_ROOT and Path(str(lane["path"])).resolve() == root
        for lane in worktrees
    )
    return root if observed and root.is_dir() else None


def lane(
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
    lease_state = str(lease.get("lease_state") or "missing")
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
    if lease_state != "valid":
        gaps.append(
            {
                "unknown": f"work_lane_lease_unknown:{branch}",
                "expired": f"work_lane_lease_expired:{branch}",
            }.get(lease_state, f"work_lane_missing_lease:{branch}")
        )
    else:
        try:
            load_profile_lease_bound_commitment(
                path,
                expected_head=head,
                base_commitment_digest=str(lease.get("base_commitment_digest") or ""),
            )
        except ValueError as exc:
            gaps.append(str(exc))
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "lease": lease_summary(lease),
        "lease_state": lease_state,
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }


def holder_ref(lane: dict[str, object]) -> str:
    return str(cast("dict[str, object]", lane.get("lease") or {}).get("holder_ref") or "")


def holder_gaps(lane: dict[str, object]) -> list[str]:
    required = holder_ref(lane)
    return (
        []
        if required and actor_ref() == required
        else ["foreign_work_lane_retire_authority_required"]
    )


def effect_gaps(
    control_root: Path,
    *,
    policy: BranchRolePolicy,
    lane: dict[str, object],
    accepted_head: str,
) -> list[str]:
    if output(control_root, "symbolic-ref", "--short", "HEAD") != policy.accepted_branch:
        return ["retirement_control_root_stale"]
    current_accepted = output(control_root, "rev-parse", policy.accepted_branch) or ""
    if current_accepted != accepted_head:
        return ["accepted_ref_stale"]
    if actor_ref() != holder_ref(lane):
        return ["foreign_work_lane_retire_authority_required"]
    return []


def reobservation_gaps(
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


def actor_ref() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip()


def blocked(gaps: list[str], stderr: str = "") -> dict[str, object]:
    report: dict[str, object] = {"ok": False, "state": "blocked", "required_gaps": gaps}
    if stderr.strip():
        report["stderr"] = stderr.strip()
    return report

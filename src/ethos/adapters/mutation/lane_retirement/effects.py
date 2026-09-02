"""Git and lease effects for linked Work Lane retirement."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.mutation.lane_retirement.linked_effect import linked_retirement_plan
from ethos.adapters.mutation.lane_retirement.observation import output
from ethos.adapters.mutation.lane_retirement.observation import ref_outcome
from ethos.adapters.mutation.lane_retirement.observation import retirement_observation
from ethos.adapters.mutation.lane_retirement.observation import retirement_terminal
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import observe_lease_from_connection
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.coordination import LeaseOperationRequest

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy


def apply_retirement(
    repo: Path,
    control_root: Path,
    *,
    mode: Literal["landed", "superseded"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority_lane: dict[str, object],
    accepted_head: str,
) -> dict[str, object]:
    result: dict[str, object] = {}
    error: OSError | sqlite3.Error | None = None
    successor_authority = authority_lane.get("branch") != lane.get("branch")
    try:
        with closing(sqlite3.connect(state_database(repo))) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            if successor_authority:
                require_missing_lease(connection, str(lane["branch"]))
                expected_current_lease(
                    connection,
                    request=lease_request(authority_lane),
                    require_expired=False,
                )
            else:
                prepare_source_lease_retirement(connection, lane)
            if gaps := effect_gaps(
                repo,
                control_root,
                mode=mode,
                policy=policy,
                lane=lane,
                authority_lane=authority_lane,
                accepted_head=accepted_head,
            ):
                result = blocked(gaps)
            else:
                effect = remove_linked_lane(
                    control_root,
                    lane,
                    mode=mode,
                    accepted=(policy.accepted_branch, accepted_head),
                    authority=authority_lane,
                )
                result = effect
            if result or successor_authority:
                if result:
                    connection.rollback()
                else:
                    connection.commit()
            else:
                connection.commit()
    except ValueError as exc:
        result = blocked([str(exc).partition(":")[0]], str(exc))
    except (OSError, sqlite3.Error) as exc:
        error = exc
    return retirement_result(
        repo,
        control_root,
        lane,
        result=result,
        error=error,
    )


def prepare_source_lease_retirement(
    connection: sqlite3.Connection,
    lane: dict[str, object],
) -> None:
    """Recheck and remove only the observed target Lease state."""
    branch = str(lane["branch"])
    state = str(lane.get("lease_state") or "unknown")
    if state == "unknown":
        message = f"work_lane_lease_unknown:{branch}"
        raise ValueError(message)
    if state == "missing":
        require_missing_lease(connection, branch)
        return
    expected_current_lease(
        connection,
        request=lease_request(lane),
        require_expired=state == "expired",
    )
    revoke_lease_from_connection(connection, request=lease_request(lane))
    require_missing_lease(connection, branch)


def retirement_result(
    _repo: Path,
    control_root: Path,
    lane: dict[str, object],
    *,
    result: dict[str, object],
    error: OSError | sqlite3.Error | None,
) -> dict[str, object]:
    """Resolve one retirement attempt from fresh native carrier observations."""
    observed = retirement_observation(control_root, control_root, lane)
    if error is not None:
        if retirement_terminal(observed):
            return {"observed": observed}
        return {**blocked(["lease_cleanup_failed"], str(error)), "observed": observed}
    if result:
        return {**result, "observed": observed}
    if retirement_terminal(observed):
        return {"observed": observed}
    return {
        **blocked(["retirement_postcondition_not_terminal"]),
        "observed": observed,
    }


def remove_linked_lane(
    control_root: Path,
    lane: dict[str, object],
    *,
    mode: Literal["landed", "superseded"],
    accepted: tuple[str, str],
    authority: dict[str, object],
) -> dict[str, object]:
    accepted_branch, accepted_head = accepted
    authority_branch = str(authority.get("branch") or "")
    authority_head = str(authority.get("head") or "")
    branch, path, expected = (str(lane.get(key) or "") for key in ("branch", "path", "head"))
    if gaps := reobservation_gaps(branch, path, expected):
        return blocked(gaps)
    actor = actor_ref()
    try:
        transaction_root, plan = linked_retirement_plan(
            control_root,
            lane,
            accepted=accepted,
            authority=authority,
            mode=mode,
            actor=actor,
            worktree_clean=True,
        )
        admit_git_effect(transaction_root, plan)
    except (OSError, ValueError) as error:
        return blocked([str(error).partition(":")[0]], str(error))
    try:
        remove_worktree(control_root, Path(path), branch=branch, head=expected)
    except ValueError as error:
        return blocked(["worktree_remove_failed"], str(error))
    try:
        execute_git_effect(transaction_root, plan, issuer=actor)
    except (OSError, ValueError) as exc:
        return failed_ref_transition(
            control_root,
            lane=lane,
            target=(branch, expected),
            accepted=(accepted_branch, accepted_head),
            authority=(authority_branch, authority_head),
            stderr=str(exc),
        )
    else:
        return {}


def failed_ref_transition(
    control_root: Path,
    *,
    lane: dict[str, object],
    target: tuple[str, str],
    accepted: tuple[str, str],
    authority: tuple[str, str],
    stderr: str,
) -> dict[str, object]:
    branch, expected = target
    accepted_branch, accepted_head = accepted
    accepted_state = ref_outcome(control_root, accepted_branch, accepted_head)
    authority_branch, authority_head = authority
    authority_state = (
        ref_outcome(control_root, authority_branch, authority_head)
        if authority_branch not in {accepted_branch, branch}
        else "expected"
    )
    ref_state = ref_outcome(control_root, branch, expected)
    gaps = [
        "accepted_ref_changed_after_worktree_removed"
        if accepted_state in {"absent", "moved"}
        else "branch_delete_failed_after_worktree_removed"
    ]
    if accepted_state == "unavailable":
        gaps.append("accepted_ref_state_unavailable_after_worktree_removed")
    if authority_state in {"absent", "moved"}:
        gaps.append("authority_ref_changed_after_worktree_removed")
    elif authority_state == "unavailable":
        gaps.append("authority_ref_state_unavailable_after_worktree_removed")
    ref_gap = {
        "absent": "retirement_ref_absent_after_failed_delete",
        "moved": "retirement_ref_moved_after_worktree_removed",
        "unavailable": "retirement_ref_state_unavailable_after_worktree_removed",
    }.get(ref_state)
    if ref_gap:
        gaps.append(ref_gap)
    restoration = restore_worktree(control_root, lane) if ref_state == "expected" else {}
    worktree_restored = restoration.get("state") in {"applied", "recognized"}
    if ref_state == "expected" and not worktree_restored:
        gaps.append("worktree_restore_failed_after_ref_transition")
    return {
        **blocked(gaps, stderr),
        "worktree_removed": not worktree_restored,
        "worktree_restored": worktree_restored,
        "worktree_restoration": restoration,
        "ref_state": ref_state,
        "ref_preserved": ref_state == "expected",
    }


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


def archived_carrier_absorption(
    repo: Path,
    *,
    head: str,
    accepted_head: str,
) -> dict[str, object]:
    """Derive one exact active-to-archive OpenSpec mapping from Git facts."""
    if not is_ancestor(repo, accepted_head, head):
        return {}
    source_paths = _carrier_delta_paths(repo, accepted_head, head)
    roots = {
        "/".join(path.split("/")[:3])
        for path in source_paths
        if path.startswith("openspec/changes/")
        and not path.startswith("openspec/changes/archive/")
        and len(path.split("/")) >= 4
    }
    if len(roots) != 1:
        return {}
    active_root = next(iter(roots))
    if any(path != active_root and not path.startswith(f"{active_root}/") for path in source_paths):
        return {}
    change = active_root.rsplit("/", 1)[-1]
    candidates = _archive_roots(repo, accepted_head, change)
    if len(candidates) != 1:
        return {}
    archive_root = candidates[0]
    mapping: dict[str, dict[str, str]] = {}
    for source in source_paths:
        target = archive_root + source.removeprefix(active_root)
        source_blob = output(repo, "rev-parse", f"{head}:{source}") or ""
        target_blob = output(repo, "rev-parse", f"{accepted_head}:{target}") or ""
        if not source_blob or source_blob != target_blob:
            return {}
        mapping[source] = {"target": target, "blob": source_blob}
    return {"change": change, "archive_root": archive_root, "paths": mapping}


def _carrier_delta_paths(repo: Path, accepted_head: str, head: str) -> tuple[str, ...]:
    changed = output(repo, "diff", "--name-only", "--no-renames", "-z", accepted_head, head)
    return tuple(path for path in (changed or "").split("\0") if path)


def _archive_roots(repo: Path, accepted_head: str, change: str) -> tuple[str, ...]:
    archives = run_git(
        repo,
        "ls-tree",
        "-d",
        "--name-only",
        accepted_head,
        "openspec/changes/archive/",
        check=False,
    )
    return (
        tuple(
            path
            for path in archives.stdout.splitlines()
            if path.rsplit("/", 1)[-1].endswith(f"-{change}")
        )
        if archives.returncode == 0
        else ()
    )


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
    if lease_state == "unknown" or (mode == "superseded" and lease_state != "valid"):
        gaps.append(
            {
                "unknown": f"work_lane_lease_unknown:{branch}",
                "expired": f"work_lane_lease_expired:{branch}",
            }.get(lease_state, f"work_lane_missing_lease:{branch}")
        )
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "lease": {key: value for key, value in lease_generation(lease).items() if key != "lane_ref"}
        | {"mints_authority": False},
        "lease_state": lease_state,
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }


def holder_ref(lane: dict[str, object]) -> str:
    return str(cast("dict[str, object]", lane.get("lease") or {}).get("holder_ref") or "")


def holder_gaps(lane: dict[str, object]) -> list[str]:
    branch = str(lane.get("branch") or "")
    if lane.get("lease_state") == "unknown":
        return [f"work_lane_lease_unknown:{branch}"]
    actor = actor_ref()
    if not actor:
        return [f"invocation_actor_missing:{branch}"]
    if lane.get("lease_state") in {"expired", "missing"}:
        return []
    required = holder_ref(lane)
    return [] if required and actor == required else ["foreign_work_lane_retire_authority_required"]


def effect_gaps(
    invocation_root: Path,
    control_root: Path,
    *,
    mode: Literal["landed", "superseded"],
    policy: BranchRolePolicy,
    lane: dict[str, object],
    authority_lane: dict[str, object],
    accepted_head: str,
) -> list[str]:
    gaps: list[str] = []
    if output(control_root, "symbolic-ref", "--short", "HEAD") != policy.accepted_branch:
        gaps.append("retirement_control_root_stale")
    current_accepted = output(control_root, "rev-parse", policy.accepted_branch) or ""
    if not gaps and current_accepted != accepted_head:
        gaps.append("accepted_ref_stale")
    if not gaps and authority_lane.get("branch") != lane.get("branch"):
        authority_path = Path(str(authority_lane.get("path") or ""))
        authority_branch = str(authority_lane.get("branch") or "")
        if (
            invocation_root.resolve() != authority_path.resolve()
            or output(invocation_root, "symbolic-ref", "--short", "HEAD") != authority_branch
        ):
            gaps.append("retirement_authority_checkout_stale")
        elif observed_gaps := reobservation_gaps(
            str(authority_lane.get("branch") or ""),
            str(authority_lane.get("path") or ""),
            str(authority_lane.get("head") or ""),
        ):
            gaps.extend(observed_gaps)
    if not gaps:
        gaps.extend(holder_gaps(authority_lane))
    if not gaps:
        gaps.extend(archive_absorption_gaps(control_root, lane, accepted_head))
    if not gaps:
        try:
            transaction_root, plan = linked_retirement_plan(
                control_root,
                lane,
                accepted=(policy.accepted_branch, accepted_head),
                authority=authority_lane,
                mode=mode,
                actor=actor_ref(),
                worktree_clean=True,
            )
            admit_git_effect(transaction_root, plan)
        except (OSError, ValueError) as error:
            gaps.append(str(error).partition(":")[0])
    return gaps


def archive_absorption_gaps(
    control_root: Path, lane: dict[str, object], accepted_head: str
) -> list[str]:
    """Recheck the exact archived carrier mapping before retirement."""
    archive_absorption = cast("dict[str, object]", lane.get("archive_absorption") or {})
    if not archive_absorption:
        return []
    observed = archived_carrier_absorption(
        control_root,
        head=str(lane.get("head") or ""),
        accepted_head=accepted_head,
    )
    return [] if observed == archive_absorption else ["retirement_archive_absorption_stale"]


def lease_request(lane: dict[str, object]) -> LeaseOperationRequest:
    """Bind one exact Lease row for retirement or successor authority validation."""
    lease = cast("dict[str, object]", lane.get("lease") or {})
    return LeaseOperationRequest(
        operation="revoke",
        branch=str(lane["branch"]),
        holder_ref=holder_ref(lane),
        generation=integer_value(lease.get("generation")),
        expires_at=str(lease.get("expires_at") or ""),
        apply=True,
    )


def require_missing_lease(connection: sqlite3.Connection, branch: str) -> None:
    """Require the retired source to remain ownerless inside the effect transaction."""
    if observe_lease_from_connection(connection, branch).state == "missing":
        return
    message = "retirement_source_lease_present"
    raise ValueError(message)


def restore_worktree(control_root: Path, lane: dict[str, object]) -> dict[str, object]:
    """Restore one removed linked worktree and retain its exact effect result."""
    path = str(lane.get("path") or "")
    branch = str(lane.get("branch") or "")
    if not path or not branch:
        return {"state": "blocked", "error": "worktree_restore_coordinates_missing"}
    try:
        attestation = add_worktree(
            control_root,
            Path(path),
            branch=branch,
            head=str(lane.get("head") or ""),
        )
    except (OSError, ValueError) as error:
        return {
            "state": "blocked",
            "error": str(error).strip() or error.__class__.__name__,
        }
    if attestation is None:
        return {"state": "recognized"}
    result = attestation.payload.body.get("result")
    state = str(result.get("state") or "") if isinstance(result, Mapping) else ""
    return {"state": state, "attestation_id": attestation.id}


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
        (("symbolic-ref", "--short", "HEAD"), "retirement_worktree_branch", branch),
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
    report: dict[str, object] = {
        "verdict": "block",
        "state": "blocked",
        "required_gaps": gaps,
    }
    if stderr.strip():
        report["stderr"] = stderr.strip()
    return report

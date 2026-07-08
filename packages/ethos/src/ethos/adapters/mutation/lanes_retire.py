from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state import active_leases
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
    deleted = run_git(
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


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    status = workspace_status(repo)
    leases = _active_lane_leases(repo)
    lanes = [
        _retirement_lane(repo, lane, leases=leases)
        for lane in cast("list[dict[str, object]]", status["worktrees"])
        if lane["role"] == ROLE_WORK_LANE
    ]
    selected = [lane for lane in lanes if branch is None or lane["branch"] == branch]
    gaps: list[str] = []
    if branch is not None and not selected:
        gaps.append("retire_branch_not_found")
    if apply and not branch:
        gaps.append("retire_branch_required")
    if branch:
        for lane in selected:
            gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(_landed_actor_gaps(selected))
        gaps.extend(_landed_expect_head_gaps(selected, expect_head=expect_head, apply=apply))
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
            ),
            "required_gaps": sorted(set(gaps)),
            **retire_authority_guidance(gaps),
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
            ),
            "required_gaps": [],
        }
    lane = selected[0]
    removed = remove_linked_lane(repo, lane, expect_head=expect_head)
    if removed:
        return {
            "branch": branch or "",
            "lanes": lanes,
            "mutation": retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
            ),
            **removed,
        }
    # Release the lane's lease so it cannot outlive the lane — a recreated
    # same-named branch must re-acquire, not inherit a stale lease.
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"]))
    return {
        "ok": True,
        "state": "retired",
        "branch": branch or "",
        "retired": lane,
        "lanes": lanes,
        "mutation": retire_mutation_binding(
            branch=branch,
            expect_head=expect_head,
            actor=_current_actor(),
            required_actor=_selected_lease_owner(selected),
        ),
        "required_gaps": [],
    }


def remove_linked_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    expect_head: str | None,
) -> dict[str, object]:
    """Delete a lane ref head-bound, then remove its previously clean worktree."""
    ref = f"refs/heads/{lane['branch']}"
    delete = run_git(
        repo,
        "update-ref",
        "-d",
        ref,
        str(expect_head),
        check=False,
    )
    if delete.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["branch_delete_failed"],
            "stderr": delete.stderr.strip(),
        }
    remove = run_git(repo, "worktree", "remove", "--force", str(lane["path"]), check=False)
    if remove.returncode == 0:
        return {}
    restore = run_git(
        repo,
        "update-ref",
        ref,
        str(expect_head),
        "0" * 40,
        check=False,
    )
    gaps = ["worktree_remove_failed"]
    if restore.returncode != 0:
        gaps.append("branch_restore_failed")
    return {
        "ok": False,
        "state": "blocked",
        "required_gaps": gaps,
        "stderr": remove.stderr.strip(),
        "rollback_stderr": restore.stderr.strip(),
    }


def _landed_actor_gaps(selected: list[dict[str, object]]) -> list[str]:
    if not selected:
        return []
    lease_owner = _selected_lease_owner(selected)
    actor = _current_actor()
    if not lease_owner or actor != lease_owner:
        return ["foreign_work_lane_retire_authority_required"]
    return []


def _selected_lease_owner(selected: list[dict[str, object]]) -> str:
    if not selected:
        return ""
    return str(selected[0].get("lease_owner") or "")


def retire_authority_guidance(gaps: list[str]) -> dict[str, str]:
    """Return next-action guidance for owner-bound Work Lane retirement gaps."""
    if "foreign_work_lane_retire_authority_required" not in gaps:
        return {}
    return {"next_action": "set ETHOS_ACTOR to the lane lease owner or obtain handoff"}


def _landed_expect_head_gaps(
    selected: list[dict[str, object]],
    *,
    expect_head: str | None,
    apply: bool,
) -> list[str]:
    if not apply:
        return []
    expected = (expect_head or "").strip()
    if not expected:
        return ["expect_head_required"]
    if selected and expected != str(selected[0]["head"]):
        return ["expect_head_mismatch"]
    return []


def retire_mutation_binding(
    *,
    branch: str | None,
    expect_head: str | None,
    actor: str = "",
    required_actor: str = "",
) -> dict[str, str]:
    """Build the common mutation binding envelope for lane retirement commands."""
    actor = actor.strip()
    mutation = {
        "actor": actor,
        "expect_head": (expect_head or "").strip(),
        "ref": f"refs/heads/{branch}" if branch else "",
    }
    if required_actor:
        mutation.update(
            {
                "actor_bound": str(bool(actor)).lower(),
                "actor_source": "ETHOS_ACTOR",
                "required_actor": required_actor,
            }
        )
    return mutation


def _current_actor() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip()


def _branch_exists(root: Path, branch: str) -> bool:
    completed = run_git(root, "rev-parse", "--verify", branch, check=False)
    return completed.returncode == 0


def has_changed_paths(root: Path) -> bool:
    completed = run_git(root, "status", "--porcelain", "--untracked-files=all", check=False)
    if completed.returncode != 0:
        return True
    return bool(completed.stdout.strip())


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


def _active_lane_leases(repo: Path) -> dict[str, dict[str, object]]:
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    return {str(lease["subject"]): lease for lease in active_leases(db_path)}


def _retirement_lane(
    repo: Path, lane: dict[str, object], *, leases: dict[str, dict[str, object]] | None = None
) -> dict[str, object]:
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    lease = (leases or {}).get(branch, {})
    lease_owner = str(lease.get("owner") or "")
    if not is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_not_merged")
    if has_changed_paths(path):
        gaps.append("work_lane_dirty")
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": str(lane["head"]),
        "lease_owner": lease_owner,
        "lease_state": "leased" if lease_owner else "missing",
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }

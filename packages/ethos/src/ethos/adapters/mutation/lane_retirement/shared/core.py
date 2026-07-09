from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


from ethos.adapters.mutation.lane_lifecycle.core import run_git


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


def delete_json_projection_lease(repo: Path, *, subject: str) -> int:
    """Remove a Work Lane lease from the JSON local-state projection."""
    path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    rows = payload.get("leases")
    if not isinstance(rows, list):
        return 0
    kept: list[object] = []
    removed = 0
    for row in rows:
        branch = ""
        if isinstance(row, dict):
            branch = str(row.get("branch") or row.get("subject") or "")
        if branch == subject:
            removed += 1
        else:
            kept.append(row)
    if not removed:
        return 0
    payload = dict(payload)
    payload["leases"] = kept
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return removed


def retire_authority_guidance(gaps: list[str]) -> dict[str, str]:
    """Return next-action guidance for owner-bound Work Lane retirement gaps."""
    if "foreign_work_lane_retire_authority_required" not in gaps:
        return {}
    return {"next_action": "set ETHOS_ACTOR to the lane lease owner or obtain handoff"}


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

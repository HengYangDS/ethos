from __future__ import annotations

import json
import os
from pathlib import Path

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos_core.contracts.lifecycle.core import MutationRequest


def remove_linked_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    expect_head: str | None,
) -> dict[str, object]:
    """Retire one clean linked lane without forcing a destructive removal.

    The worktree is removed before its branch ref.  Git will refuse that normal
    removal if the worktree became dirty after the caller's plan observation.
    Only after the checkout is gone do we delete the exact previously observed
    ref.  A concurrent ref advance therefore leaves an unbound ref behind for
    later inspection instead of deleting a newer target.
    """
    branch = str(lane.get("branch") or "")
    path = str(lane.get("path") or "")
    expected = (expect_head or "").strip()
    gaps = _linked_lane_reobservation_gaps(
        branch=branch,
        path=path,
        expect_head=expected,
    )
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "required_gaps": gaps,
        }
    remove = run_git(
        repo,
        "worktree",
        "remove",
        path,
        check=False,
    )
    if remove.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["worktree_remove_failed"],
            "stderr": remove.stderr.strip(),
        }
    ref = f"refs/heads/{branch}"
    delete = run_git(
        repo,
        "update-ref",
        "-d",
        ref,
        expected,
        check=False,
    )
    if delete.returncode == 0:
        return {}
    return {
        "ok": False,
        "state": "blocked",
        "required_gaps": ["branch_delete_failed_after_worktree_removed"],
        "stderr": delete.stderr.strip(),
    }


def _linked_lane_reobservation_gaps(
    *,
    branch: str,
    path: str,
    expect_head: str,
) -> list[str]:
    """Reobserve the exact linked lane immediately before any effect.

    This is deliberately duplicated beneath the public planning checks.  A
    plan is only an observation; the destructive transition must independently
    reject a missing path, a moved worktree/ref, or any tracked or untracked
    residue.  The subsequent non-forced ``git worktree remove`` supplies a
    final Git-native cleanliness fence against a race after this read.
    """
    gaps: list[str] = []
    lane_path = Path(path) if path else Path()
    if not branch:
        gaps.append("retirement_branch_missing")
    if not expect_head:
        gaps.append("expect_head_required")
    if not path or not lane_path.exists() or not lane_path.is_dir():
        gaps.append("retirement_worktree_path_unavailable")
        return gaps
    ref = f"refs/heads/{branch}"
    ref_check = run_git(lane_path, "rev-parse", ref, check=False)
    if ref_check.returncode != 0:
        gaps.append("retirement_ref_unavailable")
    elif expect_head and ref_check.stdout.strip() != expect_head:
        gaps.append("retirement_ref_stale")
    head_check = run_git(lane_path, "rev-parse", "HEAD", check=False)
    if head_check.returncode != 0:
        gaps.append("retirement_worktree_head_unavailable")
    elif expect_head and head_check.stdout.strip() != expect_head:
        gaps.append("retirement_worktree_head_stale")
    status = run_git(
        lane_path,
        "status",
        "--porcelain",
        "--untracked-files=all",
        check=False,
    )
    if status.returncode != 0:
        gaps.append("retirement_worktree_status_unavailable")
    elif status.stdout.strip():
        gaps.append("work_lane_dirty")
    return sorted(set(gaps))


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
    """Return next-action guidance for holder-bound Work Lane retirement gaps."""
    if "foreign_work_lane_retire_authority_required" not in gaps:
        return {}
    return {"next_action": "set ETHOS_ACTOR to the current holder_ref or obtain handoff"}


def current_holder_ref() -> str:
    """Read the sole local holder identity input for retirement commands."""
    return os.environ.get("ETHOS_ACTOR", "").strip()


def lane_holder_ref(lane: dict[str, object]) -> str:
    """Project the holder identity from a normalized lane lease payload."""
    lease = lane.get("lease")
    return str(lease.get("holder_ref") or "") if isinstance(lease, dict) else ""


def selected_holder_ref(selected: list[dict[str, object]]) -> str:
    """Project the selected lane holder, preserving the empty-selection contract."""
    return lane_holder_ref(selected[0]) if selected else ""


def holder_authority_gaps(selected: list[dict[str, object]]) -> list[str]:
    """Reject retirement unless the invocation holder owns the selected lane."""
    if not selected:
        return []
    required = selected_holder_ref(selected)
    return (
        []
        if required and current_holder_ref() == required
        else ["foreign_work_lane_retire_authority_required"]
    )


def has_changed_paths(root: Path) -> bool:
    """Fail closed when Git cannot prove the linked Work Lane is clean."""
    try:
        completed = run_git(root, "status", "--porcelain", "--untracked-files=all", check=False)
    except OSError:
        return True
    return completed.returncode != 0 or bool(completed.stdout.strip())


def retire_mutation_binding(
    *,
    branch: str | None,
    expect_head: str | None,
    holder_ref: str = "",
    required_holder_ref: str = "",
) -> dict[str, str]:
    """Build the common mutation binding envelope for lane retirement commands."""
    holder_ref = holder_ref.strip()
    mutation = {
        "invocation_holder_ref": holder_ref,
        "expect_head": (expect_head or "").strip(),
        "ref": f"refs/heads/{branch}" if branch else "",
    }
    if required_holder_ref:
        mutation.update(
            {
                "holder_bound": str(bool(holder_ref)).lower(),
                "invocation_source": "ETHOS_ACTOR",
                "required_holder_ref": required_holder_ref,
            }
        )
    return mutation


def retire_mutation_envelope(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    command: str,
    action: str,
    branch: str | None,
    expect_head: str | None,
    apply: bool,
    confirmed: bool,
    required_gaps: list[str],
    holder_ref: str = "",
    required_holder_ref: str = "",
    extra_state: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the canonical retirement request/decision while retaining migration hints."""
    legacy_binding = retire_mutation_binding(
        branch=branch,
        expect_head=expect_head,
        holder_ref=holder_ref,
        required_holder_ref=required_holder_ref,
    )
    expected_state: dict[str, object] = {
        "ref": str(legacy_binding["ref"]),
        "head": str(legacy_binding["expect_head"]),
        "invocation_holder_ref": holder_ref,
        "required_holder_ref": required_holder_ref,
        **(extra_state or {}),
    }
    canonical = mutation_envelope(
        MutationRequest(
            command=command,
            apply=apply,
            authorized=confirmed,
            expect_head=expect_head,
        ),
        action=action,
        resource=str(legacy_binding["ref"] or branch or "work-lane"),
        expected_state=expected_state,
        verdict="allow" if not required_gaps else "block",
        required_gaps=tuple(sorted(set(required_gaps))),
        state="ready" if not required_gaps else "blocked",
        identity_basis="holder_ref_equality" if required_holder_ref else "not_evaluated",
        evidence_boundary="current_git_lane_and_lease_observation",
        enforcement_boundary="git_ref_and_worktree_transition",
        verifier_provenance="current_runner",
    )
    return {**legacy_binding, **canonical, "legacy_binding_authoritative": False}

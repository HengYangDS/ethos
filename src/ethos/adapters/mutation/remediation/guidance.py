from __future__ import annotations

from ethos.normalization.coercion import string_mapping


def prewrite_next_action(admission: dict[str, object]) -> str:
    """Return the unique public recovery action for one prewrite block."""
    lease = string_mapping(admission.get("work_lane_lease"))
    reason = str(lease.get("reason") or "")
    holder = str(lease.get("holder_ref") or "").strip()
    if reason.startswith("invocation_actor_missing:"):
        return (
            f"set ETHOS_ACTOR={holder} and rerun the blocked command"
            if holder
            else "set ETHOS_ACTOR to the current holder_ref and rerun the blocked command"
        )
    if reason.startswith("lease_holder_mismatch:"):
        return (
            f"set ETHOS_ACTOR={holder} and rerun the blocked command, or obtain handoff"
            if holder
            else "set ETHOS_ACTOR to the current holder_ref or obtain handoff"
        )
    if reason.startswith("work_lane_missing_lease:"):
        return (
            "ethos lane start <name> --commitment <commitment.toml> "
            "--holder-ref <holder-ref> --apply --json"
        )
    editor = string_mapping(admission.get("editor_root"))
    if editor.get("reason") == "editor_root_missing":
        expected = str(editor.get("expected") or "")
        return f"ethos lane prewrite <path> --editor-root {expected} --require-editor-root --json"
    return "ethos lane prewrite <path>"


def commitment_rebind_remediation(target_commit: str) -> dict[str, object]:
    """Project the dedicated hook recovery for one valid dangling target."""
    next_command = f"ethos lane rebind-commitment derive --target-commit {target_commit} --json"
    return {
        "target_commit": target_commit,
        "target_commit_valid": True,
        "partial_effects": {
            "commit_object_created": True,
            "ref_updated": False,
            "lease_updated": False,
            "index_updated": False,
        },
        "next_action": next_command,
        "remediation": [
            {
                "gap": "commitment_rebind_required",
                "kind": "authority_denied",
                "owner": "lane rebind-commitment",
                "reason": "active Commitment bytes or semantics changed",
                "retryable": True,
                "mutation": False,
                "user_decision_required": False,
                "next_command": next_command,
            }
        ],
    }


def remediation_for_gaps(gaps: tuple[str, ...] | list[str]) -> list[dict[str, object]]:
    """Machine-readable repair hints for common mutation blockers."""
    hints: list[dict[str, object]] = []
    gap_set = tuple(str(gap) for gap in gaps)
    for gap in gap_set:
        if gap in {"work_lane_dirty", "accepted_root_dirty", "candidate_worktree_dirty"}:
            hints.append(
                {
                    "gap": gap,
                    "kind": "dirty_state",
                    "next_action": "inspect dirty_provenance in ethos status --json",
                }
            )
        elif gap == "candidate_base_stale":
            hints.append(
                {
                    "gap": gap,
                    "kind": "stale_base",
                    "next_action": (
                        "ethos lane refresh-base --apply --authorize --expect-head <head> --json"
                    ),
                }
            )
        elif gap == "accepted_advanced_concurrently":
            hints.append(
                {
                    "gap": gap,
                    "kind": "accepted_advanced_concurrently",
                    "next_action": "re-read the accepted head and rebase candidate onto it",
                }
            )
        elif gap.startswith("coordination_gap:scope_overlap:"):
            branch = gap.rsplit(":", 1)[-1]
            hints.append(
                {
                    "gap": gap,
                    "kind": "lane_overlap",
                    "next_action": (
                        f"move the verified head through the legitimate leased lane {branch}"
                    ),
                }
            )
    return hints

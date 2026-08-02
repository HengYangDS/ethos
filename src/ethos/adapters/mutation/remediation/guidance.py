from __future__ import annotations


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
                        "move or replay the verified head through "
                        f"the legitimate leased lane {branch}"
                    ),
                }
            )
    return hints

"""Select bounded recovery commands from current lifecycle gaps."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def proof_recovery_command(expect_head: str, *, change: str = "") -> str:
    """Request the full admission floor; equal default/full floors select the same work."""
    selected = f" --change {shlex.quote(change)}" if change else ""
    return f"ethos prove --full --execute --expect-head {expect_head}{selected} --json"


def archive_recovery_command(
    change: str, expect_head: str, *, subject: str | None = None, compensate: bool = False
) -> str:
    """Return the sole public continuation for an observed archive effect or its compensation."""
    subject_argument = f" --subject {shlex.quote(subject)}" if subject is not None else ""
    mode = " --compensate" if compensate else ""
    return (
        f"ethos lane archive-change --change {change} --expect-head {expect_head}"
        f"{subject_argument}{mode} --apply --json"
    )


def closeout_apply_command(
    root: Path,
    *,
    accepted_head: str,
    candidate_head: str,
    receipt_path: Path | None = None,
    status: dict[str, object] | None = None,
    identity_transition: bool = False,
) -> str:
    """Render the sole exact public accepted-closeout command."""
    worktrees = (
        status.get("worktrees")
        if status is not None
        else worktree_records(root, current_path=root, policy=load_branch_role_policy(root))
    )
    accepted_root = accepted_worktree_root(worktrees, root).resolve()
    receipt = (
        f" --independent-verification-receipt {receipt_path.resolve().as_posix()}"
        if receipt_path is not None
        else ""
    )
    identity = " --identity-transition" if identity_transition else ""
    return (
        "ethos land --closeout --apply --authorize "
        f"--expect-head {accepted_head} --candidate-head {candidate_head}{receipt}{identity} "
        f"--root {accepted_root.as_posix()} --json"
    )


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

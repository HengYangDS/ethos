"""The exact merge refresh request and the recovery each merge gap names."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.lane_lifecycle.merge import MergeMode


def merge_command(
    root: Path, mode: str, head: str, token: str, message: str, source_ref: str | None = None
) -> str:
    """Render the exact merge refresh request that one preview admits."""
    return shlex.join(
        (
            "ethos",
            "lane",
            "refresh-base",
            "--strategy",
            "merge",
            *(("--source-ref", source_ref) if source_ref is not None else ()),
            "--mode",
            mode,
            "--expect-head",
            head,
            "--expect-state",
            token,
            "--subject",
            message,
            "--root",
            str(root.resolve()),
            "--apply",
            "--authorize",
            "--json",
        )
    )


def merge_recovery_action(root: Path, mode: MergeMode, gap: str) -> str:
    """Derive a fresh coordinate request or name the exact external prerequisite."""
    if gap in {
        "authorization_required",
        "merge_exact_request_required",
        "expect_head_mismatch",
        "merge_state_stale",
        "merge_runtime_changed",
        "merge_candidate_changed",
    }:
        return shlex.join(
            (
                "ethos",
                "lane",
                "refresh-base",
                "--strategy",
                "merge",
                "--mode",
                mode,
                "--root",
                str(root.resolve()),
                "--json",
            )
        )
    if gap.startswith("merge_ignored_content_collision:"):
        return "Preserve the reported ignored content, then request a new merge preview."
    if gap == "merge_operation_busy":
        return "Wait for the current merge operation to finish, then replay the exact request."
    if gap == "merge_unstaged_resolution":
        return "Admit and stage the intended resolution, then request a fresh continue preview."
    return "Resolve the reported authority/native-state boundary; retain recovery material."

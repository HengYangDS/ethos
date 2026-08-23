"""Terminal receipts and runner guidance for Work Lane start."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable
    from pathlib import Path

    from ethos.adapters.mutation.lane_start_carrier import LaneStartContext
    from ethos.adapters.repo.hook.binding import HookRuntimeBinding
    from ethos.contracts.semantic import Attestation


def started_lane_report(
    context: LaneStartContext,
    *,
    base_head: str,
    head: str,
    lease: dict[str, object],
    carrier_attestation: Attestation | None,
    attachment_attestation: Attestation,
    hook_runtime: HookRuntimeBinding,
) -> dict[str, object]:
    """Build the receipt for an exact, leased, linked Work Lane."""
    return {
        "verdict": "pass",
        "state": "started",
        "branch": context.branch,
        "base": context.policy.candidate_branch,
        "base_head": base_head,
        "head": head,
        "path": context.target.as_posix(),
        "source_root": context.source_root.resolve().as_posix() if context.source_head else "",
        "source_head": context.source_head,
        "source_lease_state": "revoked" if context.source_lease else "not_applicable",
        "source_change_id": context.source_commitment.id.removeprefix("change:"),
        "source_commitment_digest": context.source_commitment.digest(),
        "worktree": started_worktree(branch=context.branch, path=context.target, run=context.run),
        "holder_ref": context.holder_ref,
        "base_commitment_digest": context.source_commitment.digest(),
        "lease": lease,
        "carrier_attestation": (
            carrier_attestation.model_dump(mode="json") if carrier_attestation else {}
        ),
        "attachment_attestation": attachment_attestation.model_dump(mode="json"),
        "hook_runtime": hook_runtime,
        "runner_bootstrap": runner_bootstrap(context.target),
        "required_gaps": [],
    }


def started_worktree(
    *, branch: str, path: Path, run: Callable[..., subprocess.CompletedProcess[str]]
) -> dict[str, str]:
    """Return the linked-worktree receipt for a started lane."""
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": run(path, "rev-parse", "HEAD").stdout.strip(),
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def runner_bootstrap(target: Path) -> dict[str, str]:
    """Return the non-mutating checkout-bound runner contract for a new lane."""
    resolved = target.resolve().as_posix()
    return {
        "command": "uv run --frozen --offline ethos",
        "project_environment": ".venv",
        "environment_scope": "checkout",
        "uv_cache": "host_or_ci_content_addressed",
        "cache_scope": "host_or_ci",
        "next_action": f"cd {resolved} && uv run --frozen --offline ethos status --json",
    }

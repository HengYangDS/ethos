from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ethos_workspace.status import workspace_status


@dataclass(frozen=True)
class MutationRequest:
    command: str
    apply: bool
    authorized: bool
    expect_head: str | None


@dataclass(frozen=True)
class MutationDecision:
    ok: bool
    state: str
    gaps: tuple[str, ...] = ()


def evaluate_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationDecision:
    if not request.apply:
        return MutationDecision(ok=True, state="dry_run")
    gaps: list[str] = []
    if not request.authorized:
        gaps.append("authorization_required")
    if request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != "work_lane":
        gaps.append("protected_root_mutation")
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    return MutationDecision(ok=True, state=f"{request.command}_ready")
